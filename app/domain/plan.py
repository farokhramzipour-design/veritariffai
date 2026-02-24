from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"


class PlanUpgradeRequired(Exception):
    def __init__(self, required_plan: PlanTier, upgrade_url: str | None = None):
        self.required_plan = required_plan
        self.upgrade_url = upgrade_url or "/upgrade"
        super().__init__(f"plan {required_plan} required")


def requires_plan(user_plan: PlanTier, required: PlanTier, plan_expires_at: datetime | None) -> None:
    if required == PlanTier.FREE:
        return
    if user_plan != PlanTier.PRO:
        raise PlanUpgradeRequired(required)
    if plan_expires_at is not None and plan_expires_at <= datetime.utcnow():
        raise PlanUpgradeRequired(required)
