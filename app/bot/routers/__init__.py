from . import dashboard, menu, notification
from .dashboard import broadcast, promocodes, remnashop, remnawave, users

# NOTE: Order matters!
routers = [
    menu.handlers.router,  # NOTE: Must be registered first to handle common entrypoints!
    menu.dialog.router,
    notification.handlers.router,
    #
    dashboard.dialog.router,
    broadcast.dialog.router,
    promocodes.dialog.router,
    #
    remnashop.dialog.router,
    remnashop.notifications.dialog.router,
    remnashop.plans.dialog.router,
    #
    remnawave.dialog.router,
    #
    users.dialog.router,
    users.user.dialog.router,
]

__all__ = [
    "routers",
]
