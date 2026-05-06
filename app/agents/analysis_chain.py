"""Document analysis chain using direct OpenAI client for structured output."""
import traceback
import json
from typing import Dict, List
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from app.config import settings
from app.core.logging import get_logger

logger = get_logger("analysis_chain")


class ExtractedKnowledge(BaseModel):
    name: str = Field(description="知识点名称")
    confidence: float = Field(description="置信度 0-1", ge=0, le=1)


class WeakPoint(BaseModel):
    name: str = Field(description="薄弱知识点名称")
    severity: str = Field(description="严重程度: high/medium/low")


class AnalysisResultSchema(BaseModel):
    extracted_knowledge: List[ExtractedKnowledge] = Field(description="提取的知识点列表")
    weak_points: List[WeakPoint] = Field(description="薄弱知识点列表")
    suggestions: List[str] = Field(description="学习建议列表")
    summary: str = Field(description="分析总结文字，100-200字")


SYSTEM_PROMPT = """你是一位专业的教育AI分析助手。分析学生上传的学习文档，提取知识点，识别薄弱环节，给出学习建议。

分析重点：
1. 提取所有提到的学科/知识点
2. 根据成绩/错误率识别薄弱项（低分=薄弱）
3. 给出具体、可操作的学习建议
4. 用中文输出

请严格按照以下JSON格式输出，不要包含任何其他内容：
{
  "extracted_knowledge": [
    {"name": "知识点名称", "confidence": 0.95}
  ],
  "weak_points": [
    {"name": "薄弱项名称", "severity": "high/medium/low"}
  ],
  "suggestions": ["建议1", "建议2"],
  "summary": "总结文字"
}"""

RETRY_PROMPT = "请重新分析以下文档内容，严格按JSON格式输出，不要包含任何解释或markdown标记："


def _parse_result(content: str) -> Dict:
    """Parse LLM output into analysis result dict. Handles JSON with markdown wrappers."""
    # Strip possible markdown code fences
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines if they are markdown code fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    result_data = json.loads(content)
    return {
        "extractedKnowledge": [
            {"name": k["name"], "confidence": k["confidence"]}
            for k in result_data.get("extracted_knowledge", [])
        ],
        "weakPoints": [
            {"name": wp["name"], "severity": wp["severity"]}
            for wp in result_data.get("weak_points", [])
        ],
        "suggestions": result_data.get("suggestions", []),
        "summary": result_data.get("summary", ""),
    }


class AnalysisChain:
    def __init__(self, max_retries: int = 2):
        self.client = AsyncOpenAI(
            api_key=settings.ECNU_API_KEY,
            base_url=settings.ECNU_API_BASE,
        )
        self.model = settings.LLM_MODEL
        self.max_retries = max_retries
        logger.info(f"AnalysisChain initialized: model={self.model}")

    async def analyze(self, document_text: str) -> Dict:
        text_length = len(document_text)
        logger.info(f"Starting document analysis, text_length={text_length}")

        truncated = document_text[:8000]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下文档内容：\n{truncated}"},
        ]

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=2048,
                    temperature=0.3 + (attempt - 1) * 0.2,  # gradually increase
                )
                content = response.choices[0].message.content or "{}"
                logger.info(f"Analysis attempt {attempt}: {content[:150]}...")
                result = _parse_result(content)

                # Validate: must have at least one extracted knowledge point
                if result["extractedKnowledge"]:
                    logger.info(
                        f"Analysis completed: {len(result['extractedKnowledge'])} knowledge, "
                        f"{len(result['weakPoints'])} weak points"
                    )
                    return result
                else:
                    logger.warning(f"Analysis attempt {attempt}: empty knowledge, retrying...")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": RETRY_PROMPT})

            except json.JSONDecodeError as e:
                last_error = f"JSON parse failed: {e}"
                logger.warning(f"Analysis attempt {attempt}: {last_error}")
                messages.append({"role": "user", "content": RETRY_PROMPT})
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(f"Analysis attempt {attempt} failed: {last_error}\n{traceback.format_exc()}")

        # All retries exhausted
        logger.error(f"All {self.max_retries} analysis attempts failed. Last error: {last_error}")
        return {
            "extractedKnowledge": [],
            "weakPoints": [],
            "suggestions": ["AI分析暂时不可用，请稍后重新上传。"],
            "summary": f"分析失败（{last_error}），请稍后重试。",
            "error": last_error,
        }


analysis_chain = AnalysisChain()
