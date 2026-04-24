from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True)
class Command:
    name: str
    handler: Callable[[list[str]], None]
    description: str
    aliases: tuple[str, ...] = ()