"""Service for today page endpoints: push, recommendations, progress, goals, start-study."""
import uuid
import json
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm.attributes import flag_modified

from app.models.knowledge import UserKnowledge, KnowledgePoint
from app.models.learning_record import UserLearningRecord, LearningAction
from app.models.study_plan import StudyPlan
from app.models.resource import Resource, ResourceType, Difficulty
from app.models.study_session import StudySession
from app.schemas.today import (
    TodayPushData,
    RecommendationItem,
    TodayRecommendationsData,
    TodayProgressData,
    WeeklyTrendItem,
    TodayGoalItem,
    TodayGoalsData,
    StudySessionData,
)
from app.agents.llm_client import get_llm
from app.core.logging import get_logger

logger = get_logger("today_service")

# 类型标签映射
TYPE_LABEL_MAP = {"video": "视频", "exercise": "练习", "article": "文章", "course": "课程"}

# 星期映射
WEEKDAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

# 天气映射（基于月份简单模拟）
WEATHER_OPTIONS = ["晴", "晴", "多云", "多云", "晴", "阴", "小雨", "晴", "多云", "晴", "晴", "多云"]


def _get_weather() -> str:
    """Get simulated weather based on month."""
    return WEATHER_OPTIONS[datetime.now().month - 1]


def _get_week_range(offset: int = 0) -> tuple[datetime, datetime]:
    """Get start (Monday 00:00) and end (Sunday 23:59) of the week, offset weeks."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    start = datetime.combine(monday, datetime.min.time())
    end = datetime.combine(monday + timedelta(days=6), datetime.max.time())
    return start, end


async def _get_weekly_duration(db: AsyncSession, user_id: int, offset: int = 0) -> float:
    """Get total study duration (hours) for a given week offset."""
    start, end = _get_week_range(offset)
    result = await db.execute(
        select(func.coalesce(func.sum(UserLearningRecord.duration_seconds), 0))
        .where(
            and_(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.created_at >= start,
                UserLearningRecord.created_at <= end,
            )
        )
    )
    total_seconds = result.scalar() or 0
    return round(total_seconds / 3600, 1)


async def _get_daily_durations(db: AsyncSession, user_id: int) -> dict[int, float]:
    """Get study duration (hours) grouped by day-of-week for current week (local time)."""
    start, end = _get_week_range(0)
    result = await db.execute(
        select(
            UserLearningRecord.created_at,
            UserLearningRecord.duration_seconds,
        )
        .where(
            and_(
                UserLearningRecord.user_id == user_id,
                UserLearningRecord.created_at >= start,
                UserLearningRecord.created_at <= end,
            )
        )
    )
    rows = result.all()
    day_hours: dict[int, float] = {}
    # UTC+8 offset: SQLite stores UTC, compute Shanghai local weekday
    shift = timedelta(hours=8)
    for row in rows:
        ts = row.created_at
        seconds = row.duration_seconds or 0
        local_ts = ts + shift  # Convert UTC to Shanghai time
        dow = local_ts.weekday()  # 0=Mon, 6=Sun
        day_hours[dow] = round(day_hours.get(dow, 0) + seconds / 3600, 1)
    return day_hours


async def _get_knowledge_rate(db: AsyncSession, user_id: int) -> float:
    """Get average knowledge mastery rate (0-1)."""
    result = await db.execute(
        select(func.avg(UserKnowledge.score))
        .where(UserKnowledge.user_id == user_id)
    )
    avg_score = result.scalar()
    if avg_score is None:
        return 0.0
    return round(float(avg_score) / 100, 2)


async def _get_weak_points(db: AsyncSession, user_id: int) -> list[str]:
    """Get list of weak/warning knowledge point names (score < 75)."""
    result = await db.execute(
        select(KnowledgePoint.name, UserKnowledge.score)
        .join(UserKnowledge, UserKnowledge.knowledge_id == KnowledgePoint.id)
        .where(
            and_(
                UserKnowledge.user_id == user_id,
                UserKnowledge.score < 75,
            )
        )
    )
    rows = result.all()
    return [row[0] for row in rows]  # row[0] = KnowledgePoint.name


# =====================================================
# Public API
# =====================================================


async def get_push(db: AsyncSession, user_id: int) -> TodayPushData:
    """Get today's push header data."""
    now = datetime.now()

    # 建议学习时长：基于薄弱点数动态计算
    weak_count = await db.execute(
        select(func.count())
        .select_from(UserKnowledge)
        .where(
            and_(
                UserKnowledge.user_id == user_id,
                UserKnowledge.score < 75,
            )
        )
    )
    n_weak = weak_count.scalar() or 0
    suggested = min(max(2 + n_weak, 2), 5)

    # 学习状态：基于本周学习时长
    this_week_hours = await _get_weekly_duration(db, user_id, 0)
    if this_week_hours >= 15:
        status = "最佳"
    elif this_week_hours >= 8:
        status = "良好"
    else:
        status = "一般"

    # 较上周增长率
    last_week_hours = await _get_weekly_duration(db, user_id, -1)
    if last_week_hours > 0:
        growth = round((this_week_hours - last_week_hours) / last_week_hours, 2)
    else:
        growth = 0.0 if this_week_hours == 0 else 1.0

    return TodayPushData(
        date=now.strftime("%Y-%m-%d"),
        weather=_get_weather(),
        suggestedStudyHours=suggested,
        status=status,
        weeklyGrowthRate=max(growth, -1.0),  # floor at -1.0
    )


async def get_recommendations(
    db: AsyncSession, user_id: int
) -> TodayRecommendationsData:
    """Get personalized recommendations — LLM selects & justifies from resource pool."""
    # 1. Get user weak points with scores
    result = await db.execute(
        select(KnowledgePoint.name, UserKnowledge.score)
        .join(UserKnowledge, UserKnowledge.knowledge_id == KnowledgePoint.id)
        .where(UserKnowledge.user_id == user_id)
        .order_by(UserKnowledge.score.asc())
        .limit(10)
    )
    user_kp_rows = result.all()
    if not user_kp_rows:
        # No data yet — return empty with hint
        return TodayRecommendationsData(recommendations=[RecommendationItem(
            type="article", typeLabel="文章", difficulty="入门",
            title="上传成绩单获取个性化推荐",
            platform="系统", duration=None,
            reason="上传试卷或成绩单后，AI 将为你智能匹配学习资源",
            url="", thumbnail=None,
        )])

    user_kps = [{"name": row[0], "score": round(row[1], 1)} for row in user_kp_rows]

    # 2. Get available resources
    all_resources = await db.execute(select(Resource).limit(30))
    resources = all_resources.scalars().all()

    resource_pool = []
    for r in resources:
        tags_dict = r.tags if isinstance(r.tags, dict) else {}
        resource_pool.append({
            "id": r.id,
            "title": r.title,
            "type": r.type.value if r.type else "article",
            "difficulty": r.difficulty.value if r.difficulty else "入门",
            "platform": r.platform,
            "url": r.url,
            "summary": r.summary or "",
            "duration": tags_dict.get("duration", "") or tags_dict.get("count", ""),
        })

    # 3. Ask LLM to select & justify
    llm = get_llm().bind(response_format={"type": "json_object"})
    prompt = f"""你是学业啄木鸟的学习推荐专家。根据学生的知识掌握情况，从资源池中选出最适合的3-6个学习资源。

**学生知识点掌握情况：**
{json.dumps(user_kps, ensure_ascii=False)}

**可用资源池：**
{json.dumps(resource_pool, ensure_ascii=False, indent=2)}

**任务：**
1. 选出3-6个最匹配学生薄弱点的资源（分数越低越需要优先推荐）
2. 为每个选中的资源写一句个性化推荐理由（必须引用学生的具体分数和薄弱点名称）
3. 难度级别根据学生该知识点的分数匹配：0-40→入门，40-70→中级，70+→进阶

**严格按照以下JSON格式返回：**
{{"recommendations": [{{"resourceId": 1, "reason": "推荐理由", "difficulty": "入门"}}]}}

只返回JSON，不要其他文字。"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n```", 1)[0] if "\n```" in content else content[3:-3]
        llm_result = json.loads(content)
        selected = llm_result.get("recommendations", [])
    except Exception as e:
        logger.warning(f"LLM recommendation failed: {e}, falling back to rule-based")
        # Fallback: simple rule-based matching
        weak_names = [k["name"] for k in user_kps]
        items: list[RecommendationItem] = []
        for r in resources[:6]:
            items.append(_build_recommendation_item(r, weak_names))
        return TodayRecommendationsData(recommendations=items)

    # 4. Map LLM selections back to resource objects
    resource_map = {r.id: r for r in resources}
    items: list[RecommendationItem] = []
    for sel in selected[:6]:
        r = resource_map.get(sel["resourceId"])
        if not r:
            continue
        r_type = r.type.value if r.type else "article"
        tags_dict = r.tags if isinstance(r.tags, dict) else {}
        items.append(RecommendationItem(
            type=r_type,
            typeLabel=TYPE_LABEL_MAP.get(r_type, "文章"),
            difficulty=sel.get("difficulty", r.difficulty.value if r.difficulty else "入门"),
            title=r.title,
            platform=r.platform,
            duration=tags_dict.get("duration") or tags_dict.get("count"),
            reason=sel.get("reason", ""),
            url=r.url,
            thumbnail=r.thumbnail,
        ))

    if not items:
        weak_names = [k["name"] for k in user_kps]
        for r in resources[:3]:
            items.append(_build_recommendation_item(r, weak_names))

    return TodayRecommendationsData(recommendations=items)


def _build_recommendation_item(r: Resource, weak_names: list[str]) -> RecommendationItem:
    """Build a single recommendation item from a Resource (rule-based fallback)."""
    r_type = r.type.value if r.type else "article"
    tags_dict = r.tags if isinstance(r.tags, dict) else {}
    # Simple matching for reason
    matched = [w for w in weak_names if w in (r.title or "")]
    if matched:
        reason = f"根据你当前的薄弱知识点「{matched[0]}」，推荐加强学习"
        difficulty = r.difficulty.value if r.difficulty else "中级"
    elif weak_names:
        reason = f"针对薄弱知识点「{weak_names[0]}」，推荐相关练习巩固基础"
        difficulty = "入门"
    else:
        reason = "帮助你巩固知识体系，拓展学习视野"
        difficulty = r.difficulty.value if r.difficulty else "入门"
    return RecommendationItem(
        type=r_type,
        typeLabel=TYPE_LABEL_MAP.get(r_type, "文章"),
        difficulty=difficulty,
        title=r.title,
        platform=r.platform,
        duration=tags_dict.get("duration") or tags_dict.get("count"),
        reason=reason,
        url=r.url,
        thumbnail=r.thumbnail,
    )


async def get_progress(db: AsyncSession, user_id: int) -> TodayProgressData:
    """Get weekly learning progress and trends."""
    this_week_hours = await _get_weekly_duration(db, user_id, 0)
    last_week_hours = await _get_weekly_duration(db, user_id, -1)

    if last_week_hours > 0:
        weekly_growth = round((this_week_hours - last_week_hours) / last_week_hours, 2)
    else:
        weekly_growth = 0.0 if this_week_hours == 0 else 1.0

    knowledge_rate = await _get_knowledge_rate(db, user_id)
    # knowledgeGrowthRate 简单估算：基于本周新增学习记录
    knowledge_growth = 0.02 if this_week_hours > 0 else 0.0

    # 本周每日趋势
    day_hours = await _get_daily_durations(db, user_id)
    today_dow = datetime.now().weekday()  # 0=Mon, 6=Sun
    # 转换为统一的 0=Mon (Python weekday: 0=Mon)
    trend = []
    for d in range(7):
        trend.append(WeeklyTrendItem(
            day=WEEKDAY_MAP[d],
            hours=day_hours.get(d, 0),
            isToday=(d == today_dow),
        ))

    return TodayProgressData(
        weeklyStudyHours=this_week_hours,
        weeklyGrowthRate=max(weekly_growth, -1.0),
        knowledgeRate=knowledge_rate,
        knowledgeGrowthRate=knowledge_growth,
        weeklyTrend=trend,
    )


async def start_study(db: AsyncSession, user_id: int) -> StudySessionData:
    """Record that user started a study session."""
    today_str = datetime.now().strftime("%Y%m%d")
    session_id = f"sess_{today_str}_{uuid.uuid4().hex[:6]}"

    session = StudySession(
        user_id=user_id,
        session_id=session_id,
    )
    db.add(session)
    await db.commit()

    logger.info(f"Study session started: user_id={user_id}, session_id={session_id}")
    return StudySessionData(sessionId=session_id)


async def get_today_goals(db: AsyncSession, user_id: int) -> TodayGoalsData:
    """Get today's learning goals adapted from current study plan."""
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .order_by(StudyPlan.created_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return TodayGoalsData(
            planId=None,
            todayGoals=[],
            studyTips=["上传成绩单或试卷即可生成个性化学习计划"],
        )

    plan_data = plan.plan_data or {}
    weeks = plan_data.get("weeks", [])

    today_goals = []
    if weeks:
        # Take first week's tasks as today's goals
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
    )


async def update_goal_completed(
    db: AsyncSession, user_id: int, goal_id: str
) -> bool:
    """Update a goal's completed status. Goal ID format: goal_{planId}_{taskIndex}."""
    try:
        parts = goal_id.split("_")
        if len(parts) < 3 or parts[0] != "goal":
            return False
        plan_id = int(parts[1])
        task_index = int(parts[2]) - 1  # 1-based → 0-based
    except (ValueError, IndexError):
        return False

    result = await db.execute(
        select(StudyPlan).where(
            and_(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return False

    plan_data = plan.plan_data or {}
    weeks = plan_data.get("weeks", [])

    if not weeks:
        return False

    first_week = weeks[0]
    tasks = first_week.get("tasks", [])

    if task_index < 0 or task_index >= len(tasks):
        return False

    # Toggle completed
    tasks[task_index]["completed"] = not tasks[task_index].get("completed", False)
    plan.plan_data = plan_data
    flag_modified(plan, "plan_data")  # force SQLAlchemy to detect JSON column mutation
    await db.commit()

    return True
