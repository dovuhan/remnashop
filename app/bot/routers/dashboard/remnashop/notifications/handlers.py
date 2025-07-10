from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from loguru import logger

from app.core.constants import APP_CONTAINER_KEY, USER_KEY
from app.core.container import AppContainer
from app.core.enums import SystemNotificationType, UserNotificationType
from app.core.utils.formatters import format_log_user
from app.db.models.dto import UserDto


async def on_user_type_selected(
    callback: CallbackQuery,
    widget: Select[UserNotificationType],
    dialog_manager: DialogManager,
    selected_type: UserNotificationType,
) -> None:
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    notification = container.services.notification
    settings = await container.services.notification.get_user_settings()
    # TODO: UserNotificationType


async def on_system_type_selected(
    callback: CallbackQuery,
    widget: Select[SystemNotificationType],
    dialog_manager: DialogManager,
    selected_type: SystemNotificationType,
) -> None:
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    settings = await container.services.notification.get_system_settings()

    setattr(settings, selected_type, not getattr(settings, selected_type))
    await container.services.notification.set_system_settings(settings)

    logger.info(
        f"{format_log_user(user)} Change notification type: "
        f"'{selected_type}' to '{getattr(settings, selected_type)}'"
    )
