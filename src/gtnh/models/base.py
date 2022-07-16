from typing import Any, Callable

import orjson
from pydantic import BaseModel


def orjson_dumps(v: Any, *, default: Callable[..., Any]) -> str:
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    return orjson.dumps(v, default=default, option=orjson.OPT_INDENT_2).decode()


class GTNHBaseModel(BaseModel):
    class Config:
        json_loads = orjson.loads
        json_dumps = orjson_dumps
