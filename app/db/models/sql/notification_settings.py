from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.dto import NotificationSettingsDto

from .base import Base
from .timestamp import TimestampMixin


class NotificationSettings(Base, TimestampMixin):
    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1, autoincrement=False)

    # subscription_3_days_left: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # subscription_24_hours_left: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # subscription_ended: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # available_after_maintenance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # maintenance_global_off: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # maintenance_purchase_off: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bot_lifetime: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_registered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    promocode_activated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def dto(self) -> NotificationSettingsDto:
        return NotificationSettingsDto.model_validate(self)
