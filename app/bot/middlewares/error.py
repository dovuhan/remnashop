from typing import Any, Awaitable, Callable, Optional

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
)
from aiogram.types import ErrorEvent
from aiogram.types import User as AiogramUser
from aiogram.utils.formatting import Bold, Text
from aiogram_dialog.api.exceptions import UnknownState

from app.bot.models.containers import AppContainer
from app.core.constants import APP_CONTAINER_KEY
from app.core.enums import MiddlewareEventType

from .base import EventTypedMiddleware


class ErrorMiddleware(EventTypedMiddleware):
    __event_types__ = [MiddlewareEventType.ERROR]

    async def __call__(
        self,
        handler: Callable[[ErrorEvent, dict[str, Any]], Awaitable[Any]],
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> Any:
        aiogram_user: Optional[AiogramUser] = self._get_aiogram_user(event)
        container: AppContainer = data[APP_CONTAINER_KEY]
        user = container.services.user.get(telegram_id=aiogram_user.id)

        if isinstance(event.exception, TelegramForbiddenError):
            self.logger.info(f"[User:{aiogram_user.id} ({aiogram_user.full_name})] Blocked the bot")
            await container.services.user.set_bot_blocked(user, blocked=True)
        elif isinstance(event.exception, TelegramBadRequest):
            self.logger.warning(f"[User:{aiogram_user.id} ({aiogram_user.full_name})] Bad request")
        elif isinstance(event.exception, TelegramNotFound):
            self.logger.warning(f"[User:{aiogram_user.id} ({aiogram_user.full_name})] Not found")
        elif isinstance(event.exception, UnknownState):
            self.logger.warning(
                f"[User:{aiogram_user.id} ({aiogram_user.full_name})] Unknown state"
            )
        else:
            self.logger.exception(f"Update: {event.update}\nException: {event.exception}")

        try:
            text = Text(
                Bold((type(event.exception).__name__)), f": {str(event.exception)[:1021]}..."
            )
            await container.services.notification.notify_super_dev(text_key=text)

        except TelegramBadRequest as exception:
            self.logger.warning(f"Failed to send error details: {exception}")
        except Exception as exception:
            self.logger.error(f"Unexpected error in error handler: {exception}")

        return await handler(event, data)
