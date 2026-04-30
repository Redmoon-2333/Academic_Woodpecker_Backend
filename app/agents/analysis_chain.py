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


ANALYSIS_PROMPT = """你是一位专业的教育AI分析助手。分析学生上传的学习文档，提取知识点，识别薄弱环节，给出学习建议。

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


class AnalysisChain:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.ECNU_API_KEY,
            base_url=settings.ECNU_API_BASE,
        )
        self.model = settings.LLM_MODEL
        logger.info(f"AnalysisChain initialized: model={self.model}, base_url={settings.ECNU_API_BASE}")

    async def analyze(self, document_text: str) -> Dict:
        """Analyze document text and return structured analysis."""
        text_length = len(document_text)
        logger.info(f"Starting document analysis, text_length={text_length}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": f"请分析以下文档内容：\n{document_text[:8000]}"},
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
                temperature=0.7,
            )

            content = response.choices[0].message.content
            logger.info(f"Raw LLM response: {content[:200]}...")

            result_data = json.loads(content)

            result = {
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

            logger.info(
                f"Analysis completed: extracted {len(result['extractedKnowledge'])} knowledge points, "
                f"{len(result['weakPoints'])} weak points"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}, content={content if 'content' in locals() else 'N/A'}")
            return self._fallback_result()
        except Exception as e:
            logger.error(
                f"Analysis chain failed: type={type(e).__name__}, error={str(e)}, "
                f"traceback={traceback.format_exc()}"
            )
            return self._fallback_result()

    def _fallback_result(self) -> Dict:
        return {
            "extractedKnowledge": [{"name": "文档内容", "confidence": 0.5}],
            "weakPoints": [{"name": "待确认", "severity": "medium"}],
            "suggestions": ["请重新上传文档或手动补充知识点"],
            "summary": "AI分析暂时不可用，请稍后重试。",
        }


analysis_chain = AnalysisChain()
