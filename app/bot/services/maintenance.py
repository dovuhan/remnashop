from typing import cast

from aiogram.types import TelegramObject
from aiogram_dialog.utils import remove_intent_id
from loguru import logger

from app.core.enums import MaintenanceMode
from app.core.storage_keys import MaintenanceModeKey, MaintenanceWaitListKey
from app.core.utils.formatters import format_log_user
from app.db.models.dto import UserDto

from .base import BaseService


class MaintenanceService(BaseService):
    async def check_access(
        self,
        user: UserDto,
        event: TelegramObject,
    ) -> bool:
        if not await self.is_active():
            logger.debug(f"{format_log_user(user)} Access allowed (maintenance not active)")
            return True

        if user.is_privileged:
            logger.debug(f"{format_log_user(user)} Access allowed (privileged user)")
            return True

        if await self.is_global_mode():
            logger.info(f"{format_log_user(user)} Access denied (global maintenance mode)")
            return False

        if await self.is_purchase_mode() and self._is_purchase_action(event):
            logger.info(f"{format_log_user(user)} Access denied (purchase maintenance mode)")

            if await self.should_user_be_notified(user.telegram_id):
                await self.add_user_to_waitlist(user.telegram_id)
                logger.debug(
                    f"{format_log_user(user)} Added to waiting list for maintenance notification"
                )

            return False

        logger.debug(f"{format_log_user(user)} Access allowed (no specific denial condition met)")
        return True

    async def get_current_mode(self) -> MaintenanceMode:
        key = MaintenanceModeKey()
        mode = await self.redis_repository.get(
            key=key,
            validator=MaintenanceMode,
            default=MaintenanceMode.OFF,
        )
        return cast(MaintenanceMode, mode)

    async def get_available_modes(self) -> list[MaintenanceMode]:
        current = await self.get_current_mode()
        available_modes = [mode for mode in MaintenanceMode if mode != current]

        logger.debug(
            f"Available maintenance modes (excluding current '{current}'): {available_modes}"
        )
        return available_modes

    async def set_mode(self, mode: MaintenanceMode) -> None:
        key = MaintenanceModeKey()
        await self.redis_repository.set(key=key, value=mode)

    async def is_active(self) -> bool:
        return await self.get_current_mode() != MaintenanceMode.OFF

    async def is_purchase_mode(self) -> bool:
        return await self.get_current_mode() == MaintenanceMode.PURCHASE

    async def is_global_mode(self) -> bool:
        return await self.get_current_mode() == MaintenanceMode.GLOBAL

    async def add_user_to_waitlist(self, telegram_id: int) -> bool:
        key = MaintenanceWaitListKey()
        added_count = await self.redis_repository.collection_add(key, *[telegram_id])

        if added_count > 0:
            logger.info(f"User '{telegram_id}' added to waiting list")
            return True

        logger.debug(f"User '{telegram_id}' is already in the waiting list")
        return False

    async def should_user_be_notified(self, telegram_id: int) -> bool:
        is_member = await self.redis_repository.collection_is_member(
            key=MaintenanceWaitListKey(),
            value=telegram_id,
        )
        should_notify = not is_member
        logger.debug(f"Should notify user '{telegram_id}': {should_notify}")
        return should_notify

    async def get_all_waiting_users(self) -> list[int]:
        members_str = await self.redis_repository.collection_members(key=MaintenanceWaitListKey())
        waiting_users = [int(member) for member in members_str]
        logger.debug(f"Retrieved '{len(waiting_users)}' users from waiting list")
        return waiting_users

    async def remove_user_from_waitlist(self, telegram_id: int) -> bool:
        removed_count = await self.redis_repository.collection_remove(
            MaintenanceWaitListKey(),
            telegram_id,
        )
        if removed_count > 0:
            logger.info(f"User '{telegram_id}' removed from waiting list")
            return True

        logger.debug(f"User '{telegram_id}' not found in waiting list")
        return False

    async def clear_all_waiting_users(self) -> None:
        await self.redis_repository.delete(key=MaintenanceWaitListKey())
        logger.info("User waiting list completely cleared")

    def _is_purchase_action(self, event: TelegramObject) -> bool:
        # TODO: Find purchase action
        # callback_data = remove_intent_id(event.data)
        return False  # Placeholder
