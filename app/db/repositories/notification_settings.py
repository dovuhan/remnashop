from typing import Any, Optional

from app.db.models.sql.notification_settings import NotificationSettings

from .base import BaseRepository


class NotificationSettingsRepository(BaseRepository):
    async def get_singleton(self) -> Optional[NotificationSettings]:
        return await self._get(NotificationSettings, NotificationSettings.id == 1)

    async def update_singleton(self, **data: Any) -> Optional[NotificationSettings]:
        return await self._update(
            model=NotificationSettings,
            conditions=[NotificationSettings.id == 1],
            load_result=True,
            **data,
        )
