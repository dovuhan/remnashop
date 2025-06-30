from datetime import datetime

from .base import TrackableModel


class TimestampSchema(TrackableModel):
    created_at: datetime
    updated_at: datetime
