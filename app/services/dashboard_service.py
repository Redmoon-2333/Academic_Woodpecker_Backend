from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.knowledge import KnowledgePoint, UserKnowledge
from app.models.document import Document
from app.schemas.dashboard import (
    OverviewResponse,
    KnowledgeNode,
    KnowledgeDetail,
    RecommendedResource,
    HistoricalScore,
)


async def get_overview(db: AsyncSession, user_id: int) -> OverviewResponse:
    """Get student overview: knowledge rate, doc count, last diagnosis, etc."""
    # Get knowledge rate from user knowledge scores
    result = await db.execute(
        select(func.avg(UserKnowledge.score)).where(UserKnowledge.user_id == user_id)
    )
    avg_score = result.scalar() or 0.0
    knowledge_rate = round(avg_score, 1)

    # Count analyzed documents
    result = await db.execute(
        select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.status == "completed",
        )
    )
    doc_count = result.scalar() or 0

    # Get last diagnosis time
    result = await db.execute(
        select(Document.created_at)
        .where(Document.user_id == user_id, Document.status == "completed")
        .order_by(desc(Document.created_at))
        .limit(1)
    )
    last_diag = result.scalar()
    last_diagnosis = last_diag.strftime("%Y-%m-%d %H:%M") if last_diag else None

    # Default positive growth estimate
    growth_rate = 2.0

    return OverviewResponse(
        knowledgeRate=knowledge_rate,
        docCount=doc_count,
        lastDiagnosis=last_diagnosis,
        growthRate=growth_rate,
        studyHours=f"{doc_count * 1.5:.1f}小时",
        consecutiveDays=min(doc_count, 30),
    )


async def get_knowledge_graph(db: AsyncSession, user_id: int) -> List[dict]:
    """Get hierarchical knowledge graph with user's mastery status."""
    # Get all root knowledge points (no parent)
    result = await db.execute(
        select(KnowledgePoint).where(KnowledgePoint.parent_id.is_(None))
    )
    root_nodes = result.scalars().all()

    # Get user knowledge scores
    result = await db.execute(
        select(UserKnowledge).where(UserKnowledge.user_id == user_id)
    )
    user_knowledge = {uk.knowledge_id: uk.score for uk in result.scalars().all()}

    # Preload all knowledge points for child lookup
    result = await db.execute(select(KnowledgePoint))
    all_kps = result.scalars().all()
    children_map: dict = {}
    for kp in all_kps:
        if kp.parent_id is not None:
            children_map.setdefault(kp.parent_id, []).append(kp)

    def build_node(kp: KnowledgePoint) -> dict:
        score = user_knowledge.get(kp.id)
        if score is not None:
            if score >= 80:
                status, color = "掌握", "emerald"
            elif score >= 60:
                status, color = "预警", "amber"
            else:
                status, color = "薄弱", "rose"
        else:
            status = kp.status.value if hasattr(kp.status, "value") else kp.status
            color_map = {"掌握": "emerald", "预警": "amber", "薄弱": "rose"}
            color = color_map.get(status, "emerald")

        node = {
            "id": kp.id,
            "name": kp.name,
            "status": status,
            "statusColor": color,
        }

        kids = children_map.get(kp.id, [])
        if kids:
            node["children"] = [build_node(child) for child in kids]

        return node

    return [build_node(node) for node in root_nodes]


async def get_knowledge_detail(
    db: AsyncSession, user_id: int, knowledge_id: int
) -> KnowledgeDetail:
    """Get detailed info for a specific knowledge point."""
    from fastapi import HTTPException

    result = await db.execute(
        select(KnowledgePoint).where(KnowledgePoint.id == knowledge_id)
    )
    kp = result.scalar_one_or_none()
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")

    # Get historical scores
    result = await db.execute(
        select(UserKnowledge)
        .where(
            UserKnowledge.user_id == user_id,
            UserKnowledge.knowledge_id == knowledge_id,
        )
        .order_by(UserKnowledge.exam_date)
    )
    history = result.scalars().all()

    status = kp.status.value if hasattr(kp.status, "value") else kp.status
    exam_freq = kp.exam_frequency.value if hasattr(kp.exam_frequency, "value") else "中"

    return KnowledgeDetail(
        id=kp.id,
        name=kp.name,
        status=status,
        description=kp.description or f"{kp.name}是学习中的重要知识点，需要系统掌握。",
        examFrequency=exam_freq,
        difficultyLevel={1: "低", 2: "低", 3: "中", 4: "高", 5: "高"}.get(
            kp.difficulty, "中"
        ),
        weakPoints=[kp.name],
        recommendedResources=[
            RecommendedResource(id=1, title=f"{kp.name}教材", type="book"),
            RecommendedResource(id=2, title=f"{kp.name}视频课程", type="video"),
        ],
        historicalScores=[
            HistoricalScore(
                date=h.exam_date.strftime("%Y-%m-%d") if h.exam_date else "",
                score=h.score,
            )
            for h in history
        ],
    )
