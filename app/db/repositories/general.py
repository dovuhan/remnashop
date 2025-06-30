from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from .notification_settings import NotificationSettingsRepository
from .plan import PlanRepository
from .promocode import PromocodeRepository
from .user import UserRepository


class Repository(BaseRepository):
    users: UserRepository
    plans: PlanRepository
    promocodes: PromocodeRepository
    notification_settings: NotificationSettingsRepository

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.users = UserRepository(session=session)
        self.plans = PlanRepository(session=session)
        self.promocodes = PromocodeRepository(session=session)
        self.notification_settings = NotificationSettingsRepository(session=session)
