import logging
from typing import Union

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, SubManager
from aiogram_dialog.widgets.kbd import Button, Select

from app.bot.models import AppContainer
from app.bot.states import DashboardUser, MainMenu
from app.core.constants import APP_CONTAINER_KEY, USER_KEY
from app.core.enums import MessageEffect, UserRole
from app.core.formatters import format_log_user
from app.db.models import UserDto

logger = logging.getLogger(__name__)


async def handle_role_switch_preconditions(
    user: UserDto,
    target_user: UserDto,
    container: AppContainer,
    manager: Union[DialogManager, SubManager],
) -> bool:
    if target_user.telegram_id == user.telegram_id:
        logger.info(f"{format_log_user(user)} Attempted to switch role to self")
        await container.services.notification.notify_user(
            telegram_id=user.telegram_id,
            text_key="ntf-user-switch-role-self",
            message_effect=MessageEffect.POOP,
        )
        return True

    if target_user.telegram_id == container.config.bot.dev_id:
        logger.critical(
            f"{format_log_user(user)} Attempted to switch role for {format_log_user(target_user)}."
        )

        await container.services.user.set_role(user=user, role=UserRole.USER)
        await container.services.user.set_block(user=user, blocked=True)

        await manager.start(state=MainMenu.MAIN, mode=StartMode.RESET_STACK)
        await container.services.notification.notify_super_dev(
            text_key="ntf-user-switch-role-dev",
            id=str(user.telegram_id),
            name=user.name,
        )
        return True

    return False


async def start_user_window(
    manager: Union[DialogManager, SubManager],
    target_telegram_id: int,
) -> None:
    await manager.start(
        state=DashboardUser.MAIN,
        data={"target_telegram_id": target_telegram_id},
        mode=StartMode.RESET_STACK,
    )


async def on_block_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]
    target_telegram_id = dialog_manager.start_data.get("target_telegram_id")
    target_user = await container.services.user.get(telegram_id=target_telegram_id)
    blocked = not target_user.is_blocked

    if target_user.telegram_id == user.telegram_id:
        logger.info(f"{format_log_user(user)} Attempted to block to self")
        await container.services.notification.notify_user(
            telegram_id=user.telegram_id,
            text_key="ntf-user-block-self",
            message_effect=MessageEffect.POOP,
        )
        return

    if target_user.telegram_id == container.config.bot.dev_id:
        logger.critical(
            f"{format_log_user(user)} Attempted to block {format_log_user(target_user)}"
        )
        await container.services.user.set_role(user=user, role=UserRole.USER)
        await container.services.user.set_block(user=user, blocked=True)
        await dialog_manager.start(state=MainMenu.MAIN, mode=StartMode.RESET_STACK)
        await container.services.notification.notify_super_dev(
            text_key="ntf-user-block-dev",
            id=user.telegram_id,
            name=user.name,
        )

        return

    await container.services.user.set_block(user=target_user, blocked=blocked)
    logger.info(
        f"{format_log_user(user)} {'Blocked' if blocked else 'Unblocked'} "
        f"{format_log_user(target_user)}"
    )
    bg_manager = dialog_manager.bg(
        user_id=target_user.telegram_id,
        chat_id=target_user.telegram_id,
    )
    await bg_manager.start(state=MainMenu.MAIN, mode=StartMode.RESET_STACK)


async def on_role_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    selected_role: str,
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]
    target_telegram_id = dialog_manager.start_data.get("target_telegram_id")
    target_user = await container.services.user.get(telegram_id=target_telegram_id)

    if await handle_role_switch_preconditions(user, target_user, container, dialog_manager):
        return

    await container.services.user.set_role(user=target_user, role=UserRole(selected_role))
    logger.info(f"{format_log_user(user)} Switched role for {format_log_user(target_user)}")
