import asyncio
from typing import Optional, Union

from aiogram import Bot
from aiogram.types import (
    ForceReply,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.middlewares import I18nMiddleware
from app.bot.states import Notification
from app.core.config import AppConfig
from app.core.enums import (
    Locale,
    MediaType,
    MessageEffect,
    SystemNotificationType,
    UserNotificationType,
    UserRole,
)
from app.db.crud import NotificationSettingsService, UserService
from app.db.models.dto import UserDto

from .base import BaseService

ReplyMarkupType = Optional[
    Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply]
]


class NotificationService(BaseService):

    def __init__(
        self,
        bot: Bot,
        config: AppConfig,
        i18n: I18nMiddleware,
        user_service: UserService,
        notification_settings_service: NotificationSettingsService,
    ):
        super().__init__()
        self.bot = bot
        self.config = config
        self.i18n = i18n
        self.user_service = user_service
        self.notification_settings_service = notification_settings_service

    async def _send_message(
        self,
        chat_id: int,
        text_key: str,
        locale: Locale = Locale.EN,
        media: Optional[Union[FSInputFile, str]] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: ReplyMarkupType = None,
        auto_delete_after: Optional[int] = None,
        add_close_button: bool = True,
        message_effect: Optional[MessageEffect] = None,
        **kwargs,
    ) -> Optional[Message]:
        i18n_formatter = self.i18n.get_formatter(locale=locale)
        message_text = i18n_formatter(text_key, kwargs)
        message_effect_id = message_effect.value if message_effect is not None else None
        sent_message: Optional[Message] = None

        final_reply_markup = reply_markup
        if add_close_button and auto_delete_after is None:
            if reply_markup is None:
                final_reply_markup = self._get_close_notification_keyboard(locale=locale)
            elif isinstance(reply_markup, InlineKeyboardMarkup):
                self.logger.debug(
                    f"Merging close button with existing keyboard for chat '{chat_id}'"
                )
                final_reply_markup = self._merge_keyboards_with_close_button(reply_markup, locale)
            else:
                self.logger.warning(
                    f"Unsupported reply_markup type '{type(reply_markup)}' "
                    f"for chat '{chat_id}'. Close button will not be added"
                )

        try:
            if media and media_type:
                send_func = media_type.get_function(self.bot)
                media_arg_name = media_type.value

                common_args = {
                    "chat_id": chat_id,
                    "caption": message_text,
                    "reply_markup": final_reply_markup,
                    "message_effect_id": message_effect_id,
                }
                common_args[media_arg_name] = media

                sent_message = await send_func(**common_args)
            else:
                if media and not media_type:
                    self.logger.warning(
                        f"Media provided but media_type is missing for chat '{chat_id}'"
                    )

                sent_message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    message_effect_id=message_effect_id,
                    reply_markup=final_reply_markup,
                )

            if sent_message:
                self.logger.info(
                    f"Notification '{text_key}' sent to chat '{chat_id}' (lang: {locale})"
                )

                if auto_delete_after is not None and sent_message.message_id:
                    self.logger.debug(
                        f"Scheduled message '{sent_message.message_id}' for auto-deletion "
                        f"in {auto_delete_after}s (chat {chat_id})"
                    )
                    asyncio.create_task(
                        self._schedule_message_deletion(
                            chat_id, sent_message.message_id, auto_delete_after
                        )
                    )
                return sent_message
            return None

        except Exception as exception:
            self.logger.error(
                f"Error while sending notification '{text_key}' to chat '{chat_id}': {exception}",
                exc_info=True,
            )
            return None

    async def _schedule_message_deletion(self, chat_id: int, message_id: int, delay: int):
        try:
            await asyncio.sleep(delay)
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            self.logger.info(
                f"Message '{message_id}' in chat '{chat_id}' deleted after '{delay}' seconds"
            )
        except Exception as exception:
            self.logger.error(
                f"Failed to delete message '{message_id}' in chat '{chat_id}': {exception}"
            )

    def _get_close_notification_button(self, locale: Locale) -> InlineKeyboardButton:
        formatter = self.i18n.get_formatter(locale=locale)
        button_text = formatter("btn-close-notification")
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

    async def notify_user(
        self,
        telegram_id: int,
        text_key: str,
        media: Optional[Union[FSInputFile, str]] = None,
        media_type: Optional[MediaType] = None,
        reply_markup: ReplyMarkupType = None,
        auto_delete_after: Optional[int] = 5,
        add_close_button: bool = False,
        message_effect: Optional[MessageEffect] = None,
        **kwargs,
    ) -> bool:
        user = await self.user_service.get(telegram_id)

        if not user:
            self.logger.warning(f"User with ID '{telegram_id}' not found")
            return False

        return await self._send_message(
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

    async def notify_super_dev(self, text_key: str, **kwargs) -> bool:
        super_dev = await self.user_service.get(self.config.bot.dev_id)

        return await self._send_message(
            chat_id=super_dev.telegram_id,
            text_key=text_key,
            locale=super_dev.language,
            **kwargs,
        )

    async def notify_by_role(self, role: UserRole, text_key: str, **kwargs) -> list[bool]:
        users: list[UserDto] = await self.user_service.get_by_role(role)

        if not users:
            self.logger.warning(f"Users with role '{role}' not found")
            return []
        else:
            self.logger.debug(f"Found '{len(users)}' users with role '{role}' to send notification")

        results: list[bool] = []
        for user in users:
            success = await self._send_message(
                chat_id=user.telegram_id,
                text_key=text_key,
                locale=user.language,
                **kwargs,
            )
            results.append(success)

        return results

    async def system_notify(
        self,
        notification_type: SystemNotificationType,
        text_key: str,
        **kwargs,
    ) -> list[bool]:
        settings = await self.notification_settings_service.get()

        if not hasattr(settings, notification_type.value):
            self.logger.error(f"Missing setting for notification type '{notification_type.value}'")
            return []

        if not getattr(settings, notification_type.value, True):
            self.logger.debug(f"System notification '{notification_type.value}' is disabled")
            return []

        self.logger.info(f"Sending system notification '{notification_type.value}' to developers")
        return await self.notify_by_role(role=UserRole.DEV, text_key=text_key, **kwargs)
