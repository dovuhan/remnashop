import logging
from typing import Union

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select

from app.bot.models import AppContainer
from app.core.constants import APP_CONTAINER_KEY, USER_KEY
from app.core.enums import SystemNotificationType, UserNotificationType
from app.core.formatters import format_log_user
from app.db.models import UserDto

logger = logging.getLogger(__name__)


def get_notification_enum_member(
    value: str,
) -> Union[SystemNotificationType, UserNotificationType, None]:
    for enum_type in [UserNotificationType, SystemNotificationType]:
        for member in enum_type:
            if member.value == value:
                return member
    return None


async def on_type_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_type: str,
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]
    notification = container.services.notification
    settings = await container.services.notification_settings.get()
    selected_notification = get_notification_enum_member(selected_type)

    if not hasattr(settings, selected_notification):
        logger.error(
            f"{format_log_user(user)} Tried to change "
            f"unknown notification type: '{selected_notification}'"
        )
        await notification.notify_user(
            telegram_id=user.telegram_id,
            text_key="ntf-error-unknown_notification_type",
        )
        return

    setattr(settings, selected_notification, not getattr(settings, selected_notification))
    await container.services.notification_settings.update(settings)

    logger.info(
        f"{format_log_user(user)} Changed notification type: "
        f"'{selected_notification}' to '{getattr(settings, selected_notification)}'"
    )
