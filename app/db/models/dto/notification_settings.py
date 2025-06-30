from .base import TrackableModel
from .timestamp import TimestampSchema


class NotificationSettingsSchema(TrackableModel):
    bot_lifetime: bool
    user_registered: bool
    subscription: bool
    promocode_activated: bool


class NotificationSettingsDto(NotificationSettingsSchema, TimestampSchema):
    id: int
