from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pole_position.cli.registry import CommandRegistry


@dataclass(frozen=True)
class Command:
    name: str
    handler: Callable[[list[str]], None] | None
    description: str
    aliases: tuple[str, ...] = ()
    subcommands: "CommandRegistry | None" = None
