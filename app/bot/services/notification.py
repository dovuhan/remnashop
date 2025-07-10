import asyncio
from typing import Any, Optional, cast

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from app.bot.states import Notification
from app.core.enums import (
    Locale,
    MediaType,
    MessageEffect,
    SystemNotificationType,
    UserNotificationType,
)
from app.core.storage_keys import SystemNotificationSettingsKey, UserNotificationSettingsKey
from app.core.utils.types import AnyInputFile, AnyKeyboard
from app.db.models.dto import UserDto
from app.db.models.dto.notification_settings import SystemNotificationDto, UserNotificationDto

from .base import BaseService


class NotificationService(BaseService):
    async def notify_user(
        self,
        user: Optional[UserDto],
        text_key: str,
        ntf_type: Optional[UserNotificationType] = None,
        media: Optional[AnyInputFile] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: Optional[AnyKeyboard] = None,
        auto_delete_after: Optional[int] = 5,
        add_close_button: bool = False,
        message_effect: Optional[MessageEffect] = None,
        **kwargs: Any,
    ) -> bool:
        if not user:
            logger.warning("Skipping user notification: user object is empty")
            return False

        if ntf_type:
            settings = await self.get_user_settings()
            settings_data = settings.model_dump()

            if not settings_data.get(ntf_type, False):
                logger.debug(
                    f"Skipping user notification for '{user.telegram_id}': "
                    f"notification type is disabled in settings"
                )
                return False

        logger.debug(f"Attempting to send user notification '{text_key}' to '{user.telegram_id}'")

        sent_message = await self._send_message(
            chat_id=user.telegram_id,
            text_key=text_key,
            locale=user.language,
            media=media,
            media_type=media_type,
            reply_markup=reply_markup,
            auto_delete_after=auto_delete_after,
            add_close_button=add_close_button,
            message_effect=message_effect,
            **kwargs,
        )

        return bool(sent_message)

    async def system_notify(
        self,
        devs: Optional[list[UserDto]],
        text_key: str,
        ntf_type: SystemNotificationType,
        media: Optional[AnyInputFile] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: Optional[AnyKeyboard] = None,
        auto_delete_after: Optional[int] = None,
        add_close_button: bool = True,
        message_effect: Optional[MessageEffect] = None,
        **kwargs: Any,
    ) -> list[bool]:
        if not devs:
            logger.warning("Skipping system notification: devs list is empty")
            return []

        settings = await self.get_system_settings()
        settings_data = settings.model_dump()

        if not settings_data.get(ntf_type, False):
            logger.debug("Skipping system notification: notification type is disabled in settings")
            return []

        logger.debug(f"Attempting to send system notification '{text_key}' to {len(devs)} devs")

        results: list[bool] = []
        for dev in devs:
            success = bool(
                await self._send_message(
                    chat_id=dev.telegram_id,
                    text_key=text_key,
                    locale=dev.language,
                    media=media,
                    media_type=media_type,
                    reply_markup=reply_markup,
                    auto_delete_after=auto_delete_after,
                    add_close_button=add_close_button,
                    message_effect=message_effect,
                    **kwargs,
                )
            )
            results.append(success)

        return results

    async def notify_super_dev(
        self,
        dev: Optional[UserDto],
        text_key: str,
        media: Optional[AnyInputFile] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: Optional[AnyKeyboard] = None,
        auto_delete_after: Optional[int] = None,
        add_close_button: bool = True,
        message_effect: Optional[MessageEffect] = None,
        **kwargs: Any,
    ) -> bool:
        if not dev:
            logger.warning("Skipping super dev notification: user object is empty")
            return False

        if dev.telegram_id != self.config.bot.dev_id:
            logger.warning(
                f"Skipping super dev notification: "
                f"user ID does not match configured dev_id '{self.config.bot.dev_id}'"
            )
            return False

        logger.debug(
            f"Attempting to send super dev notification '{text_key}' to '{dev.telegram_id}'"
        )

        return bool(
            await self._send_message(
                chat_id=dev.telegram_id,
                text_key=text_key,
                locale=dev.language,
                media=media,
                media_type=media_type,
                reply_markup=reply_markup,
                auto_delete_after=auto_delete_after,
                add_close_button=add_close_button,
                message_effect=message_effect,
                **kwargs,
            )
        )

    #

    async def get_system_settings(self) -> SystemNotificationDto:
        key = SystemNotificationSettingsKey()
        settings = await self.redis_repository.get(
            key=key, validator=SystemNotificationDto, default=SystemNotificationDto()
        )
        return cast(SystemNotificationDto, settings)

    async def set_system_settings(self, data: SystemNotificationDto) -> None:
        key = SystemNotificationSettingsKey()
        await self.redis_repository.set(key=key, value=data)

    async def get_user_settings(self) -> UserNotificationDto:
        key = UserNotificationSettingsKey()
        settings = await self.redis_repository.get(
            key=key, validator=UserNotificationDto, default=UserNotificationDto()
        )
        return cast(UserNotificationDto, settings)

    async def set_user_settings(self, data: UserNotificationDto) -> None:
        key = UserNotificationSettingsKey()
        await self.redis_repository.set(key=key, value=data)

    #

    async def _send_message(
        self,
        chat_id: int,
        text_key: str,
        locale: Locale = Locale.EN,
        media: Optional[AnyInputFile] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: Optional[AnyKeyboard] = None,
        auto_delete_after: Optional[int] = None,
        add_close_button: bool = True,
        message_effect: Optional[MessageEffect] = None,
        **kwargs: Any,
    ) -> Optional[Message]:
        i18n_formatter = self.i18n.get_formatter(locale=locale)
        message_text = i18n_formatter(text_key, kwargs)
        message_effect_id = message_effect if message_effect is not None else None
        sent_message: Optional[Message] = None

        final_reply_markup = self._prepare_reply_markup(
            reply_markup,
            add_close_button,
            auto_delete_after,
            locale,
            chat_id,
        )

        try:
            if media and media_type:
                send_func = media_type.get_function(self.bot)
                media_arg_name = media_type
                payload = {
                    "chat_id": chat_id,
                    "caption": message_text,
                    "reply_markup": final_reply_markup,
                    "message_effect_id": message_effect_id,
                    media_arg_name: media,
                }
                sent_message = await send_func(**payload)
            else:
                if media and not media_type:
                    logger.warning(
                        f"Validation error: Media provided but media_type is missing "
                        f"for chat '{chat_id}'. Sending as text message"
                    )
                sent_message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    message_effect_id=message_effect_id,
                    reply_markup=final_reply_markup,
                )

            if sent_message:
                logger.info(f"Notification '{text_key}' successfully sent to '{chat_id}'")
                if auto_delete_after is not None:
                    asyncio.create_task(
                        self._schedule_message_deletion(
                            chat_id,
                            sent_message.message_id,
                            auto_delete_after,
                        )
                    )
                return sent_message
            return None

        except Exception as exception:
            logger.error(
                f"Failed to send notification '{text_key}' to '{chat_id}': {exception}",
                exc_info=True,
            )
            return None

    def _prepare_reply_markup(
        self,
        reply_markup: Optional[AnyKeyboard],
        add_close_button: bool,
        auto_delete_after: Optional[int],
        locale: Locale,
        chat_id: int,
    ) -> Optional[AnyKeyboard]:
        if auto_delete_after is not None:
            return reply_markup

        if add_close_button:
            if reply_markup is None:
                return self._get_close_notification_keyboard(locale=locale)
            if isinstance(reply_markup, InlineKeyboardMarkup):
                logger.debug(f"Merging close button with existing keyboard for chat '{chat_id}'")
                return self._merge_keyboards_with_close_button(reply_markup, locale)
            logger.warning(
                f"Unsupported reply_markup type '{type(reply_markup).__name__}' "
                f"for chat '{chat_id}'. Close button will not be added"
            )
        return reply_markup

    async def _schedule_message_deletion(self, chat_id: int, message_id: int, delay: int) -> None:
        logger.debug(
            f"Scheduling message '{message_id}' for auto-deletion in {delay}s (chat {chat_id})"
        )
        try:
            await asyncio.sleep(delay)
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.debug(
                f"Message '{message_id}' in chat '{chat_id}' deleted after {delay} seconds"
            )
        except Exception as exception:
            logger.error(
                f"Failed to delete message '{message_id}' in chat '{chat_id}': {exception}"
            )

    def _get_close_notification_button(self, locale: Locale) -> InlineKeyboardButton:
        formatter = self.i18n.get_formatter(locale=locale)
        button_text = formatter("btn-close-notification", {})
        return InlineKeyboardButton(
            text=button_text,
            callback_data=Notification.CLOSE.state,
        )

    def _get_close_notification_keyboard(self, locale: Locale) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(self._get_close_notification_button(locale=locale))
        return builder.as_markup()

    def _merge_keyboards_with_close_button(
        self,
        existing_markup: InlineKeyboardMarkup,
        locale: Locale,
    ) -> InlineKeyboardMarkup:
        merged_builder = InlineKeyboardBuilder()

        for row in existing_markup.inline_keyboard:
            merged_builder.row(*row)

        merged_builder.row(self._get_close_notification_button(locale=locale))
        return merged_builder.as_markup()
