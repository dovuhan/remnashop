from typing import Any, cast

from aiogram_dialog import DialogManager

from app.core.container import AppContainer
from app.core.utils.formatters import format_percent
from app.db.models.dto.user import UserDto


async def search_results_getter(
    dialog_manager: DialogManager,
    **kwargs: Any,
) -> dict[str, Any]:
    start_data = cast(dict[str, Any], dialog_manager.start_data)
    found_users_data: list[str] = start_data["found_users"]
    found_users: list[UserDto] = [
        UserDto.model_validate_json(json_string) for json_string in found_users_data
    ]

    return {
        "found_users": found_users,
        "count": len(found_users),
    }


async def recent_registered_getter(
    dialog_manager: DialogManager,
    container: AppContainer,
    **kwargs: Any,
) -> dict[str, Any]:
    users = await container.services.user.get_recent_registered_users()
    return {"recent_registered_users": users}


async def recent_activity_getter(
    dialog_manager: DialogManager,
    container: AppContainer,
    **kwargs: Any,
) -> dict[str, Any]:
    users = await container.services.user.get_recent_activity_users()
    return {"recent_activity_users": users}


async def blacklist_getter(
    dialog_manager: DialogManager,
    container: AppContainer,
    **kwargs: Any,
) -> dict[str, Any]:
    blocked_users = await container.services.user.get_blocked_users()
    users = await container.services.user.count()

    return {
        "blocked_users_exists": bool(blocked_users),
        "blocked_users": blocked_users,
        "count_blocked": len(blocked_users),
        "count_users": users,
        "percent": format_percent(part=len(blocked_users), whole=users),
    }
