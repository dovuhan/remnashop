from typing import Final, Optional

from aiogram.types import User as AiogramUser
from loguru import logger

from app.core.cache_wrapper import redis_cache
from app.core.constants import TIME_1M, TIME_10M
from app.core.enums import UserRole
from app.core.storage_keys import RecentActivityUsersKey, RecentRegisteredUsersKey
from app.core.utils.key_builder import build_key
from app.db.models.dto import UserDto
from app.db.models.sql import User
from app.db.uow import UnitOfWork

from .base import BaseService


class UserService(BaseService):
    RECENT_USERS_MAX_COUNT: Final[int] = 10

    async def create(self, aiogram_user: AiogramUser) -> UserDto:
        async with UnitOfWork(self.session_pool) as uow:
            db_user = User(
                telegram_id=aiogram_user.id,
                name=aiogram_user.full_name,
                role=(UserRole.DEV if self.config.bot.dev_id == aiogram_user.id else UserRole.USER),
                language=(
                    aiogram_user.language_code
                    if aiogram_user.language_code in self.i18n.locales
                    else self.i18n.default_locale
                ),
            )
            uow.repository.add(db_user)
        await self.clear_cache(telegram_id=aiogram_user.id)
        await self.add_to_recent_registered(db_user.telegram_id)
        return db_user.dto()

    @redis_cache(prefix="get_user", ttl=TIME_1M)
    async def get(self, telegram_id: int) -> Optional[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            db_user = await uow.repository.users.get(telegram_id=telegram_id)
            return db_user.dto() if db_user else None

    async def update(self, user: UserDto) -> Optional[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            db_user = await uow.repository.users.get(telegram_id=user.telegram_id)

            if not db_user:
                return None

            db_user = await uow.repository.users.update(
                user.telegram_id,
                **user.model_state,
            )
        if db_user:
            await self.clear_cache(telegram_id=user.telegram_id)
        return db_user.dto() if db_user else None

    async def delete(self, user: UserDto) -> bool:
        async with UnitOfWork(self.session_pool) as uow:
            result = await uow.repository.users.delete(telegram_id=user.telegram_id)
        if result:
            await self.clear_cache(telegram_id=user.telegram_id)
            await self._remove_from_recent_registered(user.telegram_id)
            await self._remove_from_recent_activity(user.telegram_id)
        return result

    async def get_by_partial_name(self, query: str) -> list[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            db_users = await uow.repository.users.get_by_partial_name(query=query)
            return [user.dto() for user in db_users]

    @redis_cache(prefix="count", ttl=TIME_1M)
    async def count(self) -> int:
        async with UnitOfWork(self.session_pool) as uow:
            return await uow.repository.users.count()

    @redis_cache(prefix="get_by_role", ttl=TIME_1M)
    async def get_by_role(self, role: UserRole) -> list[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            users = await uow.repository.users.filter_by_role(role)
            return [user.dto() for user in users]

    @redis_cache(prefix="get_devs", ttl=TIME_10M)
    async def get_devs(self) -> list[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            devs = await uow.repository.users.filter_by_role(UserRole.DEV)
            return [dev.dto() for dev in devs]

    @redis_cache(prefix="get_admins", ttl=TIME_10M)
    async def get_admins(self) -> list[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            admins = await uow.repository.users.filter_by_role(UserRole.ADMIN)
            return [admin.dto() for admin in admins]

    @redis_cache(prefix="get_blocked_users", ttl=TIME_10M)
    async def get_blocked_users(self) -> list[UserDto]:
        async with UnitOfWork(self.session_pool) as uow:
            users = await uow.repository.users.filter_by_blocked()
            return [user.dto() for user in users]

    async def set_block(self, user: UserDto, blocked: bool) -> None:
        user.is_blocked = blocked
        async with UnitOfWork(self.session_pool) as uow:
            await uow.repository.users.update(
                telegram_id=user.telegram_id,
                **user.model_state,
            )
        await self.clear_cache(telegram_id=user.telegram_id)

    async def set_bot_blocked(self, user: UserDto, blocked: bool) -> None:
        user.is_bot_blocked = blocked
        async with UnitOfWork(self.session_pool) as uow:
            await uow.repository.users.update(
                telegram_id=user.telegram_id,
                **user.model_state,
            )
        await self.clear_cache(telegram_id=user.telegram_id)

    async def set_role(self, user: UserDto, role: UserRole) -> None:
        user.role = role
        async with UnitOfWork(self.session_pool) as uow:
            await uow.repository.users.update(
                telegram_id=user.telegram_id,
                **user.model_state,
            )
        await self.clear_cache(telegram_id=user.telegram_id)

    #

    async def add_to_recent_registered(self, telegram_id: int) -> None:
        key = RecentRegisteredUsersKey()
        await self.redis_repository.list_remove(key, telegram_id, count=0)  # Delete if already
        await self.redis_repository.list_push(key, telegram_id)  # Add to the beginning
        # Cut the list to leave only RECENT_USERS_MAX_COUNT
        await self.redis_repository.list_trim(key, 0, self.RECENT_USERS_MAX_COUNT - 1)
        logger.debug(f"User '{telegram_id}' added to recent registered cache")

    async def update_recent_activity(self, telegram_id: int) -> None:
        key = RecentActivityUsersKey()
        await self.redis_repository.list_remove(key, telegram_id, count=0)  # Delete if already
        await self.redis_repository.list_push(key, telegram_id)  # Add to the beginning
        # Cut the list to leave only RECENT_USERS_MAX_COUNT
        await self.redis_repository.list_trim(key, 0, self.RECENT_USERS_MAX_COUNT - 1)
        logger.debug(f"User '{telegram_id}' activity updated in recent activity cache")

    async def get_recent_registered_users(self) -> list[UserDto]:
        telegram_ids = await self._get_recent_registered()
        users: list[UserDto] = []
        for telegram_id in telegram_ids:
            user_dto = await self.get(telegram_id=telegram_id)
            if user_dto:
                users.append(user_dto)
            else:
                logger.warning(
                    f"User '{telegram_id}' not found in DB, removing from recent registered cache"
                )
                await self._remove_from_recent_registered(telegram_id)
        logger.debug(f"Retrieved {len(users)} recent registered users")
        return users

    async def get_recent_activity_users(self) -> list[UserDto]:
        telegram_ids = await self._get_recent_activity()
        users: list[UserDto] = []
        for telegram_id in telegram_ids:
            user_dto = await self.get(telegram_id=telegram_id)
            if user_dto:
                users.append(user_dto)
            else:
                logger.warning(
                    f"User '{telegram_id}' not found in DB, removing from recent activity cache"
                )
                await self._remove_from_recent_activity(telegram_id)
        logger.debug(f"Retrieved {len(users)} recent active users")
        return users

    async def clear_cache(self, telegram_id: Optional[int] = None) -> None:
        keys_to_delete: list[str] = []

        # Invalidate specific user cache
        if telegram_id is not None:
            user_cache_key: str = build_key("cache", "get_user", telegram_id=telegram_id)
            keys_to_delete.append(user_cache_key)
            logger.debug(f"Adding telegram_id '{telegram_id}' to cache invalidation list")

        # Invalidate all relevant list caches
        list_cache_keys_to_invalidate = [
            build_key("cache", "get_by_role", role=UserRole.DEV),
            build_key("cache", "get_by_role", role=UserRole.ADMIN),
            build_key("cache", "get_by_role", role=UserRole.USER),
            build_key("cache", "get_devs"),
            build_key("cache", "get_admins"),
            build_key("cache", "get_blocked_users"),
            build_key("cache", "count"),
        ]
        keys_to_delete.extend(list_cache_keys_to_invalidate)
        logger.debug(f"Adding {len(list_cache_keys_to_invalidate)} list keys to cache invalidation")

        keys_to_delete.append(RecentActivityUsersKey().pack())
        logger.debug("Adding recent activity users cache keys to invalidation")

        if keys_to_delete:
            await self.redis.delete(*keys_to_delete)
            logger.debug(f"Total {len(keys_to_delete)} cache keys invalidated in one operation")
        else:
            logger.debug("No cache keys to invalidate")

    #

    async def _remove_from_recent_registered(self, telegram_id: int) -> None:
        key = RecentRegisteredUsersKey()
        await self.redis_repository.list_remove(key, telegram_id, count=0)
        logger.debug(f"User '{telegram_id}' removed from recent registered cache")

    async def _get_recent_registered(self) -> list[int]:
        key = RecentRegisteredUsersKey()
        telegram_ids_str = await self.redis_repository.list_range(
            key, 0, self.RECENT_USERS_MAX_COUNT - 1
        )
        return [int(uid) for uid in telegram_ids_str]

    async def _remove_from_recent_activity(self, telegram_id: int) -> None:
        key = RecentActivityUsersKey()
        await self.redis_repository.list_remove(key, telegram_id, count=0)
        logger.debug(f"User '{telegram_id}' removed from recent activity cache")

    async def _get_recent_activity(self) -> list[int]:
        key = RecentActivityUsersKey()
        telegram_ids_str = await self.redis_repository.list_range(
            key, 0, self.RECENT_USERS_MAX_COUNT - 1
        )
        return [int(uid) for uid in telegram_ids_str]
