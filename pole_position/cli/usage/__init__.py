import textwrap

from pole_position.cli import console
from pole_position.cli.usage.catalog import (
    COMMAND_HELP,
    COMMAND_TOPIC_ORDER,
    TOP_LEVEL_SECTIONS,
)
from pole_position.cli.usage.model import OptionHelp

__all__ = [
    "print_command_help",
    "print_help_topic",
    "print_top_level_help",
]


def print_top_level_help() -> None:
    console.heading("PolePosition project lifecycle CLI for FastAPI projects.")
    print()
    print("Usage: polepos <command> [options]")
    print("       polepos help <command> [subcommand]")
    print()
    print("Tip: use `polepos help <command>` for focused command help.")
    print()

    for title, entries in TOP_LEVEL_SECTIONS:
        console.heading(f"{title}:")
        _print_entries(entries)
        print()

    console.heading("Common Workflows:")
    for example in (
        "polepos start shop-api",
        "polepos add module customers",
        "polepos check",
        'polepos db revision -m "add customers table"',
        "polepos db upgrade",
    ):
        print(f"  {example}")
    print()

    console.heading("Usage and Commands:")
    for path in COMMAND_TOPIC_ORDER:
        print()
        print_command_help(*path, heading=True)


def print_command_help(*path: str, heading: bool = False) -> bool:
    topic = COMMAND_HELP.get(tuple(path))
    if topic is None:
        return False

    if heading:
        console.heading(_title_for_path(topic.path))

    print(topic.usage)
    _print_paragraphs(topic.summary)

    if topic.subcommands:
        console.heading("Subcommands:")
        _print_entries(topic.subcommands)

    if topic.options:
        console.heading("Options:")
        _print_entries(topic.options)

    if topic.examples:
        console.heading("Examples:")
        for example in topic.examples:
            print(f"  {example}")

    if topic.notes:
        console.heading("Notes:")
        for note in topic.notes:
            _print_wrapped(note, initial="  - ", subsequent="    ")

    return True


def print_help_topic(args: list[str]) -> None:
    if not args or args == ["-h"] or args == ["--help"]:
        print_top_level_help()
        return

    topic = tuple(args)
    if print_command_help(*topic):
        return

    console.error(f"Unknown help topic: {' '.join(args)}")
    print("Run `polepos help` for available commands.")
    raise SystemExit(1)


def _print_entries(entries: tuple[OptionHelp, ...]) -> None:
    width = max(len(entry.name) for entry in entries) if entries else 0
    for entry in entries:
        _print_wrapped(
            entry.description,
            initial=f"  {entry.name:<{width}}  ",
            subsequent=f"  {'':<{width}}  ",
        )


def _print_paragraphs(paragraphs: tuple[str, ...]) -> None:
    if not paragraphs:
        return
    for paragraph in paragraphs:
        _print_wrapped(paragraph, initial="  ", subsequent="  ")


def _print_wrapped(text: str, *, initial: str, subsequent: str) -> None:
    print(
        textwrap.fill(
            text,
            width=88,
            initial_indent=initial,
            subsequent_indent=subsequent,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def _title_for_path(path: tuple[str, ...]) -> str:
    return f"polepos {' '.join(path)}"
