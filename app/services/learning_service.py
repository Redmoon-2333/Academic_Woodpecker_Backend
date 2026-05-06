"""Service for tracking user learning activities."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, text
from app.models.learning_record import UserLearningRecord, LearningAction
from app.models.resource import Resource
from app.schemas.learning import (
    CreateLearningRecordRequest,
    LearningRecordItem,
    LearningStats,
)
from fastapi import HTTPException


ACTION_CONTENT_MAP = {
    LearningAction.viewed: "浏览了学习资源",
    LearningAction.studied: "学习了课程内容",
    LearningAction.completed: "完成了学习任务",
}


async def create_record(
    db: AsyncSession,
    user_id: int,
    req: CreateLearningRecordRequest,
) -> LearningRecordItem:
    """Create a new learning activity record."""
    action = LearningAction(req.action) if req.action in [a.value for a in LearningAction] else LearningAction.viewed

    # Build human-readable content
    content = ACTION_CONTENT_MAP.get(action, "学习活动")
    if req.resource_id:
        resource = await db.get(Resource, req.resource_id)
        if resource:
            content = f"{content}：《{resource.title}》"

    record = UserLearningRecord(
        user_id=user_id,
        resource_id=req.resource_id,
        action=action,
        content=content,
        duration_seconds=req.duration_seconds,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    resource_title = None
    if record.resource_id:
        res = await db.get(Resource, record.resource_id)
        if res:
            resource_title = res.title

    return LearningRecordItem(
        id=record.id,
        resource_id=record.resource_id,
        resource_title=resource_title,
        action=record.action.value,
        content=record.content,
        duration_seconds=record.duration_seconds,
        created_at=record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
    )


async def get_records(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    action: Optional[str] = None,
) -> dict:
    """Get paginated learning records for a user."""
    query = select(UserLearningRecord).where(UserLearningRecord.user_id == user_id)

    if action:
        try:
            query = query.where(UserLearningRecord.action == LearningAction(action))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的动作类型: {action}")

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Page
    query = query.order_by(desc(UserLearningRecord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    # Batch-fetch resource titles
    resource_ids = {r.resource_id for r in records if r.resource_id}
    title_map: dict[int, str] = {}
    if resource_ids:
        res_result = await db.execute(
            select(Resource.id, Resource.title).where(Resource.id.in_(resource_ids))
        )
        for row in res_result.all():
            title_map[row[0]] = row[1]

    items = [
        LearningRecordItem(
            id=r.id,
            resource_id=r.resource_id,
            resource_title=title_map.get(r.resource_id) if r.resource_id else None,
            action=r.action.value,
            content=r.content,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        )
        for r in records
    ]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "records": [item.model_dump() for item in items],
    }


async def get_stats(db: AsyncSession, user_id: int) -> LearningStats:
    """Get aggregated learning statistics for a user."""
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats_result = await db.execute(
            select(
                func.sum(func.case(
                    (UserLearningRecord.action == LearningAction.viewed, 1),
                    else_=0
                )).label('total_viewed'),
                func.sum(func.case(
                    (UserLearningRecord.action == LearningAction.studied, 1),
                    else_=0
                )).label('total_studied'),
                func.sum(func.case(
                    (UserLearningRecord.action == LearningAction.completed, 1),
                    else_=0
                )).label('total_completed'),
                func.coalesce(func.sum(UserLearningRecord.duration_seconds), 0).label('total_duration'),
                func.sum(func.case(
                    (UserLearningRecord.created_at >= today_start, 1),
                    else_=0
                )).label('today_records')
            ).where(UserLearningRecord.user_id == user_id)
        )

        row = stats_result.first()
        total_viewed = int(row.total_viewed or 0)
        total_studied = int(row.total_studied or 0)
        total_completed = int(row.total_completed or 0)
        total_duration = int(row.total_duration or 0)
        today_records = int(row.today_records or 0)

        streak_rows = (await db.execute(
            select(func.date(UserLearningRecord.created_at))
            .where(UserLearningRecord.user_id == user_id)
            .distinct()
            .order_by(desc(func.date(UserLearningRecord.created_at)))
        )).scalars().all()

        streak_days = 0
        if streak_rows:
            today_date = datetime.now().date()
            for i, day_str in enumerate(streak_rows):
                from datetime import date
                if isinstance(day_str, str):
                    day_date = date.fromisoformat(day_str)
                else:
                    day_date = day_str
                expected = today_date - timedelta(days=i)
                if day_date == expected:
                    streak_days += 1
                else:
                    break

        return LearningStats(
            total_viewed=total_viewed,
            total_studied=total_studied,
            total_completed=total_completed,
            total_duration_minutes=round(total_duration / 60, 1),
            today_records=today_records,
            streak_days=streak_days,
        )
    except Exception as e:
        return LearningStats()
