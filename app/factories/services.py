from typing import Any

from aiogram import Bot
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.middlewares import I18nMiddleware
from app.bot.models import ServicesContainer
from app.bot.services import MaintenanceService, NotificationService
from app.core.config import AppConfig
from app.db.crud import (
    NotificationSettingsService,
    PlanService,
    PromocodeService,
    UserService,
)


def create_services(
    bot: Bot,
    config: AppConfig,
    session_pool: async_sessionmaker[AsyncSession],
    redis: Redis,
    i18n: I18nMiddleware,
) -> ServicesContainer:
    crud_service_kwargs: dict[str, Any] = {
        "session_pool": session_pool,
        "config": config,
    }

    user_service = UserService(**crud_service_kwargs)
    plan_service = PlanService(**crud_service_kwargs)
    promocode_service = PromocodeService(**crud_service_kwargs)
    notification_settings_service = NotificationSettingsService(**crud_service_kwargs)

    maintenance_service = MaintenanceService(redis)
    notification_service = NotificationService(
        bot,
        config,
        i18n,
        user_service,
        notification_settings_service,
    )

    return ServicesContainer(
        maintenance=maintenance_service,
        notification=notification_service,
        user=user_service,
        plan=plan_service,
        promocode=promocode_service,
        notification_settings=notification_settings_service,
    )
