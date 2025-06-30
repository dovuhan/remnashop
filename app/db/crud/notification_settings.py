from app.db import SQLSessionContext
from app.db.models.dto import NotificationSettingsDto, NotificationSettingsSchema
from app.db.models.sql import NotificationSettings

from .base import CrudService


class NotificationSettingsService(CrudService):
    async def get_or_create(self) -> NotificationSettingsDto:
        async with SQLSessionContext(self.session_pool) as (repository, uow):
            settings_db = await repository.notification_settings.get_singleton()

            if settings_db is None:
                settings_db = NotificationSettings()
                await uow.commit(settings_db)
                self.logger.info("Created default global notification settings record")

            return settings_db.dto()

    async def get(self) -> NotificationSettingsDto:
        return await self.get_or_create()

    async def update(self, settings: NotificationSettingsDto) -> NotificationSettingsDto:
        async with SQLSessionContext(self.session_pool) as (repository, uow):
            settings_db = await repository.notification_settings.update_singleton(
                **settings.model_state,
            )
            return settings_db.dto()
