from typing import Union, Dict

from pydantic import BaseModel


class User(BaseModel):
    name: str
    thread: Union[str, None] = None
    files: Dict[str, bytes] = {}
