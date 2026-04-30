"""Study plan generator chain."""
from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.agents.llm_client import get_llm

PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """你是一位专业的学习规划师。根据学生的需求生成详细的学习计划。

请以JSON格式返回学习计划。

每周7天，每天1-2个学习任务。计划要循序渐进，从基础到进阶。
只返回JSON，不要包含其他文字。""",
    ),
    (
        "human",
        """请为以下学生生成学习计划：
- 目标日期：{target_date}
- 重点领域：{focus_areas}
- 每天可用学习时间：{daily_hours}小时

请生成详细的学习计划，确保覆盖所有重点领域，安排合理。""",
    ),
], template_format="jinja2")


class PlanGenerator:
    """Chain for generating study plans."""

    def __init__(self):
        self.llm = get_llm()
        self.parser = JsonOutputParser()
        self.chain = PLAN_PROMPT | self.llm | self.parser

    async def generate(
        self,
        target_date: str,
        focus_areas: List[str],
        daily_hours: int = 3,
    ) -> Dict[str, Any]:
        """Generate a study plan.

        Args:
            target_date: Target date for the plan (e.g., "2025-06-30").
            focus_areas: List of subjects or topics to focus on.
            daily_hours: Available study hours per day.

        Returns:
            Dict with 'weeks' key containing weekly plans.
        """
        try:
            result = await self.chain.ainvoke({
                "target_date": target_date,
                "focus_areas": "、".join(focus_areas) if focus_areas else "无特定限制",
                "daily_hours": daily_hours,
            })
            return result
        except Exception:
            # Fallback plan when LLM call fails
            weeks = []
            for w in range(1, 5):
                tasks = []
                for d in range(1, 8):
                    tasks.append({
                        "day": d,
                        "content": (
                            f"{'、'.join(focus_areas) if focus_areas else '学习内容'}"
                            f" - 第{w}周第{d}天"
                        ),
                        "resources": ["教材", "在线课程"],
                    })
                weeks.append({
                    "weekNumber": w,
                    "theme": f"第{w}周 学习计划",
                    "tasks": tasks,
                })
            return {"weeks": weeks}


# Singleton
plan_generator = PlanGenerator()