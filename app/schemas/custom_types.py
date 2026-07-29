from datetime import datetime, timezone
from typing import Annotated, Any
from pydantic import PlainSerializer, BeforeValidator

def ensure_utc(v: Any) -> datetime:
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
    return v

UTCDateTime = Annotated[
    datetime,
    BeforeValidator(ensure_utc),
    PlainSerializer(lambda v: v.isoformat().replace('+00:00', 'Z') if isinstance(v, datetime) else v, return_type=str)
]
