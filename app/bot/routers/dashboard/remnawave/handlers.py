import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button

from app.bot.models.containers import AppContainer
from app.bot.states import DashboardRemnawave
from app.core.constants import APP_CONTAINER_KEY, USER_KEY
from app.db.models.dto.user import UserDto

logger = logging.getLogger(__name__)


async def start_remnawave_window(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
):
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    container: AppContainer = dialog_manager.middleware_data[APP_CONTAINER_KEY]

    try:
        response = await container.remnawave.system.get_stats()
    except Exception as exception:
        logger.error(f"Remnawave: {exception}")
        container.services.notification.notify_user(
            telegram_id=user.telegram_id,
            text_key="ntf-error-connect-remnawave",
        )
        return

    await dialog_manager.start(state=DashboardRemnawave.MAIN, mode=StartMode.RESET_STACK)
