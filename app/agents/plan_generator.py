"""Study plan generator chain with validated output."""
import json
from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.agents.llm_client import get_llm
from app.core.logging import get_logger

logger = get_logger("plan_generator")

JSON_SCHEMA = """{
  "weeks": [
    {
      "weekNumber": 1,
      "theme": "第1周 基础概念",
      "tasks": [
        {"day": 1, "content": "具体学习内容", "estimatedMinutes": 45, "resources": ["教材", "视频"]}
      ]
    }
  ]
}"""

HUMAN_TEMPLATE = """请为学科「{focus_areas}」生成4周学习计划。
- 目标日期：{target_date}
- 每天可用：{daily_hours}小时
- 梯度：基础概念→公式推导→计算练习→综合应用"""


def _validate_plan(result: dict) -> bool:
    """Check that the generated plan has valid weeks with tasks."""
    if not isinstance(result, dict):
        return False
    weeks = result.get("weeks", [])
    if not weeks or not isinstance(weeks, list):
        return False
    for week in weeks:
        tasks = week.get("tasks", [])
        if not tasks:
            return False
        for task in tasks:
            if not task.get("content"):
                return False
    return True


class PlanGenerator:
    """Chain for generating validated study plans."""

    def __init__(self):
        self.llm = get_llm()
        self.parser = JsonOutputParser()
        self.max_retries = 3

    def _build_system_prompt(self, focus_areas: List[str]) -> str:
        """Build system prompt with focus area embedded as hard constraint."""
        subjects = "、".join(focus_areas) if focus_areas else "指定学科"
        return f"""你是「{subjects}」学习规划专家。

你的唯一任务：为「{subjects}」生成4周学习计划。
禁止生成其他学科的内容，禁止输出"安装软件"、"配置环境"等非学科任务。

输出格式 — 必须是合法JSON：
{JSON_SCHEMA}

规则：
- 每个 content 必须包含「{subjects}」的具体知识点（章节名、定理名、题型类）
- estimatedMinutes：30 / 45 / 60 / 90
- 每天至少1个任务
- 仅返回 JSON，不输出任何其他文字"""

    async def generate(
        self,
        target_date: str,
        focus_areas: List[str],
        daily_hours: int = 3,
    ) -> Dict[str, Any]:
        """Generate a validated study plan with retry on invalid output."""
        system = self._build_system_prompt(focus_areas)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", HUMAN_TEMPLATE),
        ], template_format="jinja2")
        structured_llm = self.llm.bind(response_format={"type": "json_object"})
        chain = prompt | structured_llm | self.parser

        focus_str = "、".join(focus_areas) if focus_areas else "无特定限制"
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await chain.ainvoke({
                    "focus_areas": focus_str,
                    "target_date": target_date,
                    "daily_hours": daily_hours,
                })
                if _validate_plan(result):
                    logger.info(f"Plan OK on attempt {attempt}")
                    return result
                else:
                    logger.warning(f"Plan validation failed on attempt {attempt}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Plan error on attempt {attempt}: {e}")

        logger.error(f"All {self.max_retries} attempts failed. Last: {last_error}")
        return self._fallback_plan(target_date, focus_areas, daily_hours)

    def _fallback_plan(self, target_date: str, focus_areas: List[str], daily_hours: int) -> dict:
        """Last-resort structured fallback."""
        areas = focus_areas if focus_areas else ["核心知识"]
        weeks = []
        for w in range(1, 5):
            tasks = []
            for d in range(1, 8):
                area = areas[(d - 1) % len(areas)]
                tasks.append({
                    "day": d,
                    "content": f"{area} — 第{w}周第{d}天：完成教材练习题与知识点总结",
                    "estimatedMinutes": min(daily_hours * 60, 90),
                    "resources": ["教材", "在线课程"],
                })
            weeks.append({
                "weekNumber": w,
                "theme": f"第{w}周 {'基础巩固' if w <= 2 else '进阶提升'}",
                "tasks": tasks,
            })
        return {"weeks": weeks}


plan_generator = PlanGenerator()
