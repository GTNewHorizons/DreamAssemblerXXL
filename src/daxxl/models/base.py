from typing import Any, Callable

import orjson
from pydantic import BaseModel


def orjson_default(obj: Any) -> Any:
    if isinstance(obj, set):
        return sorted(list(obj))
    raise TypeError


def orjson_dumps(v: Any, *, default: Callable[..., Any] = orjson_default) -> str:
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    # Overriding the decoder with our own
    return orjson.dumps(v, default=orjson_default, option=orjson.OPT_INDENT_2).decode()


class GTNHBaseModel(BaseModel):
    class Config:
        json_loads = orjson.loads
        json_dumps = orjson_dumps
