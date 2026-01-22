from typing import Any, Awaitable, Callable, Optional

from aiogram.types import Message, TelegramObject
from aiogram.types import User as AiogramUser
from aiogram_dialog.api.internal import FakeUser
from dishka import AsyncContainer
from loguru import logger

from src.bot.keyboards import get_user_keyboard
from src.core.config import AppConfig
from src.core.constants import CONTAINER_KEY, IS_SUPER_DEV_KEY, USER_KEY
from src.core.enums import MiddlewareEventType, SystemNotificationType
from src.core.storage.keys import StartSpamGuardKey
from src.core.utils.message_payload import MessagePayload
from src.infrastructure.database.models.dto import UserDto
from src.infrastructure.redis import RedisRepository
from src.services.notification import NotificationService
from src.services.referral import ReferralService
from src.services.user import UserService

from .base import EventTypedMiddleware


class UserMiddleware(EventTypedMiddleware):
    _START_SPAM_WINDOW_SECONDS = 10
    _START_SPAM_THRESHOLD = 5

    __event_types__ = [
        MiddlewareEventType.MESSAGE,
        MiddlewareEventType.CALLBACK_QUERY,
        MiddlewareEventType.ERROR,
        MiddlewareEventType.AIOGD_UPDATE,
        MiddlewareEventType.MY_CHAT_MEMBER,
        MiddlewareEventType.PRE_CHECKOUT_QUERY,
    ]

    async def middleware_logic(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        aiogram_user: Optional[AiogramUser] = self._get_aiogram_user(event)

        if aiogram_user is None or aiogram_user.is_bot:
            logger.warning("Terminating middleware: event from bot or missing user")
            return

        container: AsyncContainer = data[CONTAINER_KEY]
        config: AppConfig = await container.get(AppConfig)
        redis_repository: RedisRepository = await container.get(RedisRepository)
        user_service: UserService = await container.get(UserService)
        referral_service: ReferralService = await container.get(ReferralService)
        notification_service: NotificationService = await container.get(NotificationService)

        is_start = self._is_start_command(event)
        start_is_spam = False
        if is_start:
            start_is_spam = await self._is_start_spam(redis_repository, aiogram_user.id)

        user: Optional[UserDto] = await user_service.get(telegram_id=aiogram_user.id)

        if user is None:
            user = await user_service.create(aiogram_user)

            referrer = await referral_service.get_referrer_by_event(event, user.telegram_id)

            base_i18n_kwargs = {
                "user_id": str(user.telegram_id),
                "user_name": user.name,
                "username": user.username or False,
            }

            if referrer:
                referrer_i18n_kwargs = {
                    "has_referrer": True,
                    "referrer_user_id": str(referrer.telegram_id),
                    "referrer_user_name": referrer.name,
                    "referrer_username": referrer.username or False,
                }
            else:
                referrer_i18n_kwargs = {"has_referrer": False}

            should_notify_admin = not (is_start and start_is_spam)

            if should_notify_admin:
                await notification_service.system_notify(
                    payload=MessagePayload.not_deleted(
                        i18n_key="ntf-event-new-user",
                        i18n_kwargs={**base_i18n_kwargs, **referrer_i18n_kwargs},
                        reply_markup=get_user_keyboard(user.telegram_id),
                    ),
                    ntf_type=SystemNotificationType.USER_REGISTERED,
                )
            else:
                logger.warning(
                    "Start spam protection enabled: skipping admin notification "
                    f"(window={self._START_SPAM_WINDOW_SECONDS}s, threshold={self._START_SPAM_THRESHOLD}, user_id={aiogram_user.id})"
                )

            if await referral_service.is_referral_event(event, user.telegram_id):
                referral_code = await referral_service.get_ref_code_by_event(event)
                logger.info(f"Registered with referral code: '{referral_code}'")
                await referral_service.handle_referral(user, referral_code)

        elif not isinstance(aiogram_user, FakeUser):
            await user_service.compare_and_update(user, aiogram_user)

        await user_service.update_recent_activity(telegram_id=user.telegram_id)

        data[USER_KEY] = user
        data[IS_SUPER_DEV_KEY] = user.telegram_id == config.bot.dev_id

        return await handler(event, data)

    @staticmethod
    def _is_start_command(event: TelegramObject) -> bool:
        if not isinstance(event, Message) or not event.text:
            return False
        cmd = event.text.split(maxsplit=1)[0].lower()
        return cmd == "/start" or cmd.startswith("/start@")

    async def _is_start_spam(self, redis_repository: RedisRepository, user_id: int) -> bool:
        base_key = StartSpamGuardKey().pack()
        key = f"{base_key}:{user_id}"

        try:
            count = await redis_repository.client.incr(key)

            if count == 1:
                await redis_repository.client.expire(key, self._START_SPAM_WINDOW_SECONDS)
            else:
                ttl = await redis_repository.client.ttl(key)
                if ttl == -1:
                    await redis_repository.client.expire(key, self._START_SPAM_WINDOW_SECONDS)

            if count == self._START_SPAM_THRESHOLD:
                logger.warning(
                    "Start spam threshold reached, admin notifications will be suppressed "
                    f"for ~{self._START_SPAM_WINDOW_SECONDS}s (user_id={user_id})"
                )

            return count >= self._START_SPAM_THRESHOLD

        except Exception:
            logger.exception("Start spam guard failed (redis issue). Proceeding without suppression.")
            return False
