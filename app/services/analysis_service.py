import os
import uuid
import asyncio
import traceback
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.document import Document, DocStatus, FileType
from app.models.knowledge import KnowledgePoint, UserKnowledge
from app.config import settings
from app.schemas.analysis import (
    UploadResponse, ProgressResponse, Stage, AnalysisResult,
    ExtractedKnowledge, WeakPoint, OriginalFile, HistoryRecord,
    CorrectionRequest, KnowledgePoint,
)
from fastapi import HTTPException, UploadFile
from app.core.logging import get_logger

logger = get_logger("analysis_service")


async def _get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def _validate_file(file: UploadFile) -> str:
    ext = await _get_file_extension(file.filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: .{ext}，支持: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read content to check size
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持{settings.MAX_FILE_SIZE // (1024*1024)}MB",
        )
    await file.seek(0)  # Reset for later reading
    return ext


async def _save_file(user_id: int, file: UploadFile, ext: str) -> str:
    """Save uploaded file to local filesystem."""
    from app.main import UPLOAD_DIR
    upload_dir = str(UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


async def upload_file(
    db: AsyncSession,
    user_id: int,
    file: UploadFile,
    file_type: Optional[str] = None,
) -> UploadResponse:
    """Upload a file for analysis."""
    logger.info(f"File upload started: user_id={user_id}, filename={file.filename}")
    ext = await _validate_file(file)
    file_path = await _save_file(user_id, file, ext)

    # Map file_type to enum
    ftype = None
    if file_type:
        try:
            ftype = FileType(file_type)
        except ValueError:
            ftype = None

    file_size = os.path.getsize(file_path)
    size_str = (
        f"{file_size / 1024:.1f}KB"
        if file_size < 1024 * 1024
        else f"{file_size / (1024*1024):.1f}MB"
    )

    doc = Document(
        user_id=user_id,
        file_name=file.filename,
        file_url=file_path,
        file_type=ftype,
        status=DocStatus.processing,
        file_size=file_size,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Start async analysis in background (non-blocking)
    asyncio.create_task(_run_analysis(doc.id, file_path, ext))

    return UploadResponse(
        fileId=str(doc.id),
        fileName=file.filename,
        fileSize=size_str,
        uploadStatus="processing",
        previewUrl=f"/uploads/{os.path.basename(file_path)}",
    )


async def _run_analysis(doc_id: int, file_path: str, ext: str):
    """Background analysis task — does NOT block the upload response."""
    from app.database import AsyncSessionLocal
    from app.agents.analysis_chain import analysis_chain

    logger.info(f"Background analysis started: doc_id={doc_id}, file={file_path}, ext={ext}")
    async with AsyncSessionLocal() as db:
        try:
            doc = await db.get(Document, doc_id)
            if not doc:
                logger.warning(f"Document not found: doc_id={doc_id}")
                return

            # Extract text from file based on extension
            text = ""
            if ext == "txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                logger.debug(f"Text file read: doc_id={doc_id}, length={len(text)}")
            elif ext == "pdf":
                try:
                    from PyPDF2 import PdfReader

                    with open(file_path, "rb") as f:
                        reader = PdfReader(f)
                        text = "\n".join(
                            page.extract_text() or "" for page in reader.pages
                        )
                    logger.debug(f"PDF file read: doc_id={doc_id}, pages={len(reader.pages)}, text_length={len(text)}")
                except Exception as e:
                    logger.warning(f"PDF extraction failed: doc_id={doc_id}, error={str(e)}")
                    text = f"[PDF文件: {doc.file_name}]"
            else:
                # Run OCR on image files
                try:
                    from app.utils.ocr import ocr_image
                    text = await ocr_image(file_path)
                    logger.debug(f"OCR completed: doc_id={doc_id}, text_length={len(text)}")
                except Exception as e:
                    logger.warning(f"OCR failed: doc_id={doc_id}, error={str(e)}")
                    text = f"[图片: {doc.file_name}]"

            if not text.strip():
                logger.warning(f"No text extracted: doc_id={doc_id}")
                text = f"[文件: {doc.file_name}]"

            logger.info(f"Calling analysis chain: doc_id={doc_id}, text_length={len(text)}")
            # Run AI analysis via the singleton chain
            result = await analysis_chain.analyze(text)
            logger.info(f"Analysis chain returned: doc_id={doc_id}, has_result={bool(result)}")

            doc.result = result
            # Sync analysis results to knowledge graph
            if result and result.get("extractedKnowledge"):
                logger.info(f"Syncing to knowledge graph: doc_id={doc_id}")
                from app.services.knowledge_service import sync_analysis_to_knowledge
                await sync_analysis_to_knowledge(db, doc.user_id, result)
            doc.status = DocStatus.completed
            await db.commit()
            logger.info(f"Analysis completed successfully: doc_id={doc_id}")

        except Exception as e:
            logger.error(
                f"Analysis failed: doc_id={doc_id}, error={str(e)}, "
                f"type={type(e).__name__}, traceback={traceback.format_exc()}"
            )
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = DocStatus.failed
                doc.result = {"error": str(e)}
                await db.commit()




async def get_progress(db: AsyncSession, file_id: int) -> ProgressResponse:
    """Get parsing progress for a file."""
    doc = await db.get(Document, file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    status_map = {
        DocStatus.pending: ("pending", "等待处理", 0),
        DocStatus.processing: ("parsing", "正在提取文本...", 45),
        DocStatus.completed: ("completed", "解析完成", 100),
        DocStatus.failed: ("failed", "解析失败", 0),
    }

    status, stage, progress = status_map.get(doc.status, ("pending", "未知", 0))

    stages = [
        Stage(
            name="文本提取",
            status="completed" if status in ("parsing", "completed") else "pending",
        ),
        Stage(
            name="大纲匹配",
            status="completed"
            if status == "completed"
            else ("processing" if status == "parsing" else "pending"),
        ),
        Stage(
            name="薄弱项识别",
            status="completed" if status == "completed" else "pending",
        ),
        Stage(
            name="报告生成",
            status="completed" if status == "completed" else "pending",
        ),
    ]

    return ProgressResponse(
        fileId=str(file_id),
        status=status,
        stage=stage,
        progress=progress if status != "parsing" else 75,
        stages=stages,
    )


async def get_result(db: AsyncSession, file_id: int) -> AnalysisResult:
    """Get analysis result for a file."""
    doc = await db.get(Document, file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    if doc.status != DocStatus.completed:
        raise HTTPException(status_code=400, detail="文件尚未完成分析")

    result_data = doc.result or {}

    return AnalysisResult(
        fileId=str(file_id),
        originalFile=OriginalFile(url=doc.file_url, name=doc.file_name),
        extractedKnowledge=[
            ExtractedKnowledge(name=k.get("name", ""), confidence=k.get("confidence", 0))
            for k in result_data.get("extractedKnowledge", [])
        ],
        weakPoints=[
            WeakPoint(name=w.get("name", ""), severity=w.get("severity", "medium"))
            for w in result_data.get("weakPoints", [])
        ],
        suggestions=result_data.get("suggestions", []),
        summary=result_data.get("summary", ""),
        analyzedAt=doc.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        if doc.updated_at
        else None,
    )


async def get_history(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10
) -> dict:
    """Get paginated analysis history."""
    # Count total
    result = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    total = result.scalar() or 0

    # Get records
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(desc(Document.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    docs = result.scalars().all()

    status_map = {
        DocStatus.pending: "待处理",
        DocStatus.processing: "处理中",
        DocStatus.completed: "已分析",
        DocStatus.failed: "失败",
    }

    records = [
        HistoryRecord(
            id=doc.id,
            fileName=doc.file_name,
            uploadTime=doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if doc.created_at
            else None,
            status=status_map.get(doc.status, "未知"),
            thumbnail=None,
        )
        for doc in docs
    ]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "records": [r.model_dump() for r in records],
    }


async def correct_result(
    db: AsyncSession,
    user_id: int,
    file_id: int,
    correction: CorrectionRequest,
):
    """Manually correct analysis result."""
    doc = await db.get(Document, file_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    if doc.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此文件")

    # Preserve existing summary; overwrite knowledge/weak-points/suggestions
    doc.result = {
        "extractedKnowledge": [
            {"name": k.name, "confidence": k.confidence}
            for k in correction.extractedKnowledge
        ],
        "weakPoints": [
            {"name": w.name, "severity": w.severity} for w in correction.weakPoints
        ],
        "suggestions": correction.suggestions,
        "summary": doc.result.get("summary", "") if doc.result else "",
    }
    await db.commit()
    return {"message": "校正成功"}