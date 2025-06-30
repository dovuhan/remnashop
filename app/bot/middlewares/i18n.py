from typing import Any, Awaitable, Callable, Optional, Union

from aiogram.types import CallbackQuery, ErrorEvent, Message
from fluent.runtime import FluentLocalization

from app.core.constants import I18N_FORMATTER_KEY, USER_KEY
from app.core.enums import Locale, MiddlewareEventType
from app.core.formatters import format_log_user
from app.db.models import UserDto

from .base import EventTypedMiddleware

I18nFormatter = Callable[[str, Optional[dict[str, Any]]], str]


class I18nMiddleware(EventTypedMiddleware):
    __event_types__ = [
        MiddlewareEventType.MESSAGE,
        MiddlewareEventType.CALLBACK_QUERY,
        MiddlewareEventType.ERROR,
    ]

    def __init__(
        self,
        locales: dict[Locale, FluentLocalization],
        default_locale: Locale,
    ) -> None:
        super().__init__()
        self.locales = locales
        self.default_locale = default_locale
        self.logger.debug(f"Available locales: {list(locales.keys())}")

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery, ErrorEvent], dict[str, Any]],
            Awaitable[Any],
        ],
        event: Union[Message, CallbackQuery, ErrorEvent],
        data: dict[str, Any],
    ) -> Any:
        user: Optional[UserDto] = data.get(USER_KEY)
        data[I18N_FORMATTER_KEY] = self.get_formatter(user=user)
        return await handler(event, data)

    def get_locale(
        self,
        user: Optional[UserDto] = None,
        locale: Optional[Locale] = None,
    ) -> FluentLocalization:
        if locale is not None:
            target_locale = locale
        elif user is not None and user.language in self.locales:
            target_locale = user.language
        else:
            target_locale = self.default_locale

        if locale is not None:
            # self.logger.debug(f"Using explicitly provided locale: '{target_locale}'")
            pass
        elif user is not None:
            if user.language in self.locales:
                # self.logger.debug(f"{format_log_user(user)} Using locale: '{target_locale}'")
                pass
            else:
                self.logger.warning(
                    f"Locale '{user.language}' for user '{user.id}' not supported. "
                    f"Using default locale: '{self.default_locale}'"
                )
        else:
            self.logger.debug(f"User not provided. Using default locale: '{self.default_locale}'")

        if target_locale not in self.locales:
            self.logger.error(
                f"Resolved locale '{target_locale}' is not available. "
                f"Falling back to default: '{self.default_locale}'"
            )
            return self.locales[self.default_locale]

        return self.locales[target_locale]

    def get_formatter(
        self,
        user: Optional[UserDto] = None,
        locale: Optional[Locale] = None,
    ) -> I18nFormatter:
        return self.get_locale(user=user, locale=locale).format_value
