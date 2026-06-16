from dataclasses import dataclass


@dataclass(frozen=True)
class OptionHelp:
    name: str
    description: str


@dataclass(frozen=True)
class CommandHelp:
    path: tuple[str, ...]
    usage: str
    summary: tuple[str, ...]
    options: tuple[OptionHelp, ...] = ()
    examples: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    subcommands: tuple[OptionHelp, ...] = ()
