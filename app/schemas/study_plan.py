from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class GeneratePlanRequest(BaseModel):
    targetDate: str
    focusAreas: List[str] = []
    dailyHours: int = 3


class DailyTask(BaseModel):
    day: int
    content: str
    resources: List[str] = []


class WeekPlan(BaseModel):
    weekNumber: int
    theme: str = ""
    tasks: List[DailyTask] = []


class PlanResponse(BaseModel):
    planId: str
    weeks: List[WeekPlan] = []
    createdAt: str = ""


class ProgressUpdateRequest(BaseModel):
    weekNumber: int
    day: int
    completed: bool = True
