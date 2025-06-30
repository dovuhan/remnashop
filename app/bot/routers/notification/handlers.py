import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.states import Notification
from app.core.formatters import format_log_user
from app.db.models.dto.user import UserDto

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith(Notification.CLOSE.state))
async def callback_close_notification(callback: CallbackQuery, user: UserDto) -> None:
    logger.info(f"{format_log_user(user)} Closed notification '{callback.message.message_id}'")
    message_to_delete: Message = callback.message

    try:
        await callback.message.delete()
        logger.debug(f"Notification for user '{user.telegram_id}' deleted")
    except Exception as exception:
        logger.error(f"Failed to delete notification for user '{user.telegram_id}': {exception}")

        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=message_to_delete.chat.id,
                message_id=message_to_delete.message_id,
                reply_markup=None,
            )
            logger.debug(
                f"Inline keyboard removed from message '{message_to_delete.message_id}' "
                f"for user '{user.telegram_id}'"
            )
        except Exception as exception:
            logger.error(
                f"Failed to delete message and remove inline keyboard for user '{user.telegram_id}', "
                f"message '{message_to_delete.message_id}': {exception}"
            )
