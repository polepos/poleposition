from pole_position.cli.command import Command


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        for name in (command.name, *command.aliases):
            if name in self._commands:
                raise RuntimeError(f"Command already registered: {name}")
            self._commands[name] = command

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)

    def all(self) -> list[Command]:
        unique: dict[str, Command] = {}
        for cmd in self._commands.values():
            unique[cmd.name] = cmd
        return list(unique.values())


registry = CommandRegistry()