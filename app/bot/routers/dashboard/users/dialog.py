from typing import Final

from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Row, ScrollingGroup, Select, Start, SwitchTo
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from app.bot.states import Dashboard, DashboardUsers
from app.bot.widgets import Banner, I18nFormat, IgnoreUpdate
from app.core.enums import BannerName

from .getters import (
    blacklist_getter,
    recent_activity_getter,
    recent_registered_getter,
    search_results_getter,
)
from .handlers import on_unblock_all, on_user_search, on_user_selected

users = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-main"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-search"),
            id="search",
            state=DashboardUsers.SEARCH,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-recent-registered"),
            id="recent_registered",
            state=DashboardUsers.RECENT_REGISTERED,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-recent-activity"),
            id="recent_activity",
            state=DashboardUsers.RECENT_ACTIVITY,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-blacklist"),
            id="blacklist",
            state=DashboardUsers.BLACKLIST,
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-back"),
            id="back",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.MAIN,
)

search = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-search"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    MessageInput(func=on_user_search),
    IgnoreUpdate(),
    state=DashboardUsers.SEARCH,
)

recent_registered = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-recent-registered"),
    Column(
        Select(
            text=Format("{item.telegram_id} ({item.name})"),
            id="user",
            item_id_getter=lambda item: item.telegram_id,
            items="recent_registered_users",
            type_factory=int,
            on_click=on_user_selected,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.RECENT_REGISTERED,
    getter=recent_registered_getter,
)

recent_activity = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-recent-activity"),
    Column(
        Select(
            text=Format("{item.telegram_id} ({item.name})"),
            id="user",
            item_id_getter=lambda item: item.telegram_id,
            items="recent_activity_users",
            type_factory=int,
            on_click=on_user_selected,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.RECENT_ACTIVITY,
    getter=recent_activity_getter,
)

search_results = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-search-results", count=F["count"]),
    ScrollingGroup(
        Select(
            text=Format("{item.telegram_id} ({item.name})"),
            id="user",
            item_id_getter=lambda item: item.telegram_id,
            items="found_users",
            type_factory=int,
            on_click=on_user_selected,
        ),
        id="scroll",
        width=1,
        height=7,
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.SEARCH,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.SEARCH_RESULTS,
    getter=search_results_getter,
)


blacklist = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-blacklist"),
    ScrollingGroup(
        Select(
            text=Format("{item.telegram_id} ({item.name})"),
            id="user",
            item_id_getter=lambda item: item.telegram_id,
            items="blocked_users",
            type_factory=int,
            on_click=on_user_selected,
        ),
        id="scroll",
        width=1,
        height=7,
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-unblock-all"),
            id="unblock_all",
            state=DashboardUsers.UNBLOCK_ALL,
            when=F["blocked_users_exists"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.BLACKLIST,
    getter=blacklist_getter,
)

unblock_all = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-unblock-all"),
    Row(
        Button(
            text=I18nFormat("btn-users-unblock-all-confirm"),
            id="unblock_all_confirm",
            on_click=on_unblock_all,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.BLACKLIST,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.UNBLOCK_ALL,
)


router: Final[Dialog] = Dialog(
    users,
    search,
    recent_registered,
    recent_activity,
    search_results,
    blacklist,
    unblock_all,
)
