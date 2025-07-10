from typing import Any, Awaitable, Callable, Optional

from aiogram.types import TelegramObject
from aiogram.types import User as AiogramUser
from loguru import logger

from app.core.constants import APP_CONTAINER_KEY, USER_KEY
from app.core.container import AppContainer
from app.core.enums import MiddlewareEventType, SystemNotificationType
from app.core.utils.formatters import format_log_user
from app.db.models.dto import UserDto

from .base import EventTypedMiddleware


class UserMiddleware(EventTypedMiddleware):
    __event_types__ = [
        MiddlewareEventType.MESSAGE,
        MiddlewareEventType.CALLBACK_QUERY,
        MiddlewareEventType.ERROR,
        MiddlewareEventType.AIOGD_UPDATE,
        MiddlewareEventType.MY_CHAT_MEMBER,
    ]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        aiogram_user: Optional[AiogramUser] = self._get_aiogram_user(event)

        if aiogram_user is None or aiogram_user.is_bot:
            logger.warning("Terminating: event from bot or missing user")
            return

        container: AppContainer = data[APP_CONTAINER_KEY]
        user: Optional[UserDto] = await container.services.user.get(telegram_id=aiogram_user.id)

        if user is None:
            user = await container.services.user.create(aiogram_user=aiogram_user)
            logger.info(f"{format_log_user(user)} Created new user")
            await container.services.notification.system_notify(
                devs=await container.services.user.get_devs(),
                ntf_type=SystemNotificationType.USER_REGISTERED,
                text_key="ntf-event-new-user",
                id=str(user.telegram_id),
                name=user.name,
            )

        await container.services.user.update_recent_activity(telegram_id=user.telegram_id)
        data[USER_KEY] = user
        return await handler(event, data)
