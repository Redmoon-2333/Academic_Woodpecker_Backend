"""Study plan generation and management service."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm.attributes import flag_modified
from app.models.study_plan import StudyPlan
from app.schemas.study_plan import (
    GeneratePlanRequest, PlanResponse, WeekPlan,
    DailyTask, ProgressUpdateRequest,
)
from app.agents.plan_generator import plan_generator
from fastapi import HTTPException


async def generate_plan(
    db: AsyncSession,
    user_id: int,
    req: GeneratePlanRequest,
) -> PlanResponse:
    """Generate a study plan using AI and save to database."""
    # Generate plan via AI
    plan_data = await plan_generator.generate(
        target_date=req.targetDate,
        focus_areas=req.focusAreas,
        daily_hours=req.dailyHours,
    )

    # Create plan record
    plan = StudyPlan(
        user_id=user_id,
        plan_data={
            "targetDate": req.targetDate,
            "focusAreas": req.focusAreas,
            "dailyHours": req.dailyHours,
            "weeks": plan_data.get("weeks", []),
        },
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return _build_plan_response(plan)


async def get_current_plan(db: AsyncSession, user_id: int) -> Optional[PlanResponse]:
    """Get the latest study plan for the user."""
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .order_by(desc(StudyPlan.created_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return None
    return _build_plan_response(plan)


async def get_current_plan_today(db: AsyncSession, user_id: int) -> dict:
    """Get today's learning goals adapted from current study plan."""
    from app.schemas.today import TodayGoalItem, TodayGoalsData

    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .order_by(desc(StudyPlan.created_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return TodayGoalsData(
            planId=None,
            todayGoals=[],
            studyTips=["上传成绩单或试卷即可生成个性化学习计划"],
        ).model_dump()

    plan_data = plan.plan_data or {}
    weeks = plan_data.get("weeks", [])

    today_goals = []
    if weeks:
        first_week = weeks[0]
        for i, task in enumerate(first_week.get("tasks", [])[:5]):
            today_goals.append(TodayGoalItem(
                id=f"goal_{plan.id}_{i+1}",
                title=task.get("content", f"学习任务{i+1}"),
                estimatedMinutes=task.get("estimatedMinutes", 30),
                completed=task.get("completed", False),
            ))

    return TodayGoalsData(
        planId=plan.id,
        todayGoals=today_goals,
        studyTips=[
            "建议先复习基础知识再做题",
            "注意劳逸结合，每学习45分钟休息10分钟",
            "睡前复习当天学习内容效果更佳",
        ],
    ).model_dump()


async def update_progress(
    db: AsyncSession,
    user_id: int,
    plan_id: int,
    req: ProgressUpdateRequest,
):
    """Update plan progress (mark a day as completed)."""
    plan = await db.get(StudyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    if plan.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此计划")

    plan_data = plan.plan_data or {}
    weeks = plan_data.get("weeks", [])

    for week in weeks:
        if week.get("weekNumber") == req.weekNumber:
            for task in week.get("tasks", []):
                if task.get("day") == req.day:
                    task["completed"] = req.completed
                    break

    plan.plan_data = plan_data
    flag_modified(plan, "plan_data")
    await db.commit()
    return {"message": "进度已更新"}


def _build_plan_response(plan: StudyPlan) -> PlanResponse:
    """Build PlanResponse from StudyPlan model."""
    plan_data = plan.plan_data or {}
    weeks_data = plan_data.get("weeks", [])

    weeks = []
    for w in weeks_data:
        tasks = [
            DailyTask(
                day=t.get("day", 1),
                content=t.get("content", ""),
                resources=t.get("resources", []),
            )
            for t in w.get("tasks", [])
        ]
        weeks.append(WeekPlan(
            weekNumber=w.get("weekNumber", 1),
            theme=w.get("theme", f"第{w.get('weekNumber', 1)}周"),
            tasks=tasks,
        ))

    return PlanResponse(
        planId=str(plan.id),
        weeks=weeks,
        createdAt=plan.created_at.strftime("%Y-%m-%d") if plan.created_at else "",
    )
