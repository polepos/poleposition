"""Dynamic shell completion for the PolePosition CLI.

The completion candidates are derived from the live command registry and the
usage catalog, so adding a command, subcommand, or flag updates completion
automatically with no separate list to maintain. The generated shell scripts
are thin: they shell back into ``polepos __complete`` for every completion and
let the shell filter by the current word prefix.
"""

from collections.abc import Callable
from pathlib import Path

from pole_position.cli.registry import CommandRegistry, registry
from pole_position.cli.services.database_options import SUPPORTED_DATABASES
from pole_position.cli.services.integration_specs import SUPPORTED_INTEGRATIONS
from pole_position.cli.services.module_templates import (
    SUPPORTED_MODULE_TEMPLATES,
)
from pole_position.cli.services.project_locator import (
    find_package_root,
    find_project_root,
)
from pole_position.cli.services.project_manifest import read_project_manifest
from pole_position.cli.usage.catalog import COMMAND_HELP

SUPPORTED_SHELLS: tuple[str, ...] = ("bash", "zsh", "fish")

# Starter modules are not removable, so they are never completion candidates
# for `remove module`.
_STARTER_MODULE_NAMES = frozenset({"status"})
_IGNORED_MODULE_DIRECTORIES = frozenset({"__pycache__"})

# Flags that consume a following value, mapped to that value's candidates.
_VALUE_FLAG_CANDIDATES: dict[str, Callable[[Path | None], list[str]]] = {
    "--template": lambda cwd: list(SUPPORTED_MODULE_TEMPLATES),
    "--db": lambda cwd: list(SUPPORTED_DATABASES),
    "-m": lambda cwd: [],
    "--message": lambda cwd: [],
}


def complete(prior_words: list[str], cwd: Path | None = None) -> list[str]:
    """Return candidates for the word following ``prior_words``.

    The shell passes only the already-completed words and filters the returned
    candidates by the current (partial) word itself, so an empty trailing word
    needs no special handling. Completion must never fail loudly, so any error
    yields no candidates.
    """
    try:
        return _complete(list(prior_words), cwd)
    except Exception:
        return []


def _complete(prior: list[str], cwd: Path | None) -> list[str]:
    path, node, positional_count = _resolve(prior)

    # Completing the value after a flag: only offer values when the flag is
    # actually declared for the resolved command, so e.g. `check --template`
    # (check has no --template) offers nothing instead of template names.
    if prior and prior[-1] in _VALUE_FLAG_CANDIDATES:
        if prior[-1] in _flags_for(path):
            return _dedupe(_VALUE_FLAG_CANDIDATES[prior[-1]](cwd))
        return []

    candidates: list[str] = []
    if node is not None:
        candidates.extend(_subcommand_names(node))
    elif positional_count == 0:
        # Only offer positional values while the single positional slot is
        # still empty; once it is filled, re-offering would produce an
        # argument the command rejects.
        candidates.extend(_positional_candidates(path, cwd))

    if path:
        candidates.extend(_flags_for(path))
        candidates.extend(("-h", "--help"))

    return _dedupe(candidates)


def _resolve(
    prior: list[str],
) -> tuple[tuple[str, ...], CommandRegistry | None, int]:
    """Walk completed words through the command tree.

    Returns the resolved command path (canonical names, so aliases like
    ``startproject`` resolve to ``start``), the subcommand registry still open
    at that path (``None`` once a leaf command is reached), and the number of
    positional arguments already supplied after the command. Flags and their
    values are skipped so they do not interfere with command resolution.
    """
    node: CommandRegistry | None = registry
    path: list[str] = []
    positional_count = 0

    for word in prior:
        if word.startswith("-"):
            continue
        if node is None:
            # The command path is already resolved to a leaf; this is a
            # positional argument (or trailing garbage).
            positional_count += 1
            continue
        command = node.get(word)
        if command is None:
            # Unrecognized command word closes the context.
            node = None
            positional_count += 1
            continue
        path.append(command.name)
        node = command.subcommands

    return tuple(path), node, positional_count


def _subcommand_names(node: CommandRegistry) -> list[str]:
    return [
        command.name
        for command in node.all()
        if not command.name.startswith("_")
    ]


def _positional_candidates(
    path: tuple[str, ...], cwd: Path | None
) -> list[str]:
    if path == ("remove", "module"):
        return _module_names(cwd)
    if path == ("add", "integration"):
        return list(SUPPORTED_INTEGRATIONS)
    if path == ("completion",):
        return list(SUPPORTED_SHELLS)
    return []


def _flags_for(path: tuple[str, ...]) -> list[str]:
    command_help = COMMAND_HELP.get(path)
    if command_help is None:
        return []

    flags: list[str] = []
    for option in command_help.options:
        for token in option.name.replace(",", " ").split():
            if token.startswith("-"):
                flags.append(token)
    return flags


def _module_names(cwd: Path | None) -> list[str]:
    try:
        project_root = find_project_root(cwd)
    except Exception:
        return []

    manifest = read_project_manifest(project_root)
    names = [
        name
        for name, template in manifest.module_templates.items()
        if template != "starter" and name not in _STARTER_MODULE_NAMES
    ]
    if names:
        return sorted(names)

    try:
        package_root = find_package_root(cwd)
    except Exception:
        return []

    modules_root = package_root / "modules"
    if not modules_root.is_dir():
        return []

    return sorted(
        entry.name
        for entry in modules_root.iterdir()
        if entry.is_dir()
        and entry.name.isidentifier()
        and entry.name not in _STARTER_MODULE_NAMES
        and entry.name not in _IGNORED_MODULE_DIRECTORIES
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


_BASH_SCRIPT = """\
_poleposition_complete() {
    local prior candidates
    prior=("${COMP_WORDS[@]:1:COMP_CWORD-1}")
    # Expand a possibly-empty array safely so completion does not error under
    # `set -u` on bash < 4.4 (e.g. the macOS system bash).
    candidates="$(polepos __complete ${prior[@]+"${prior[@]}"} 2>/dev/null)"
    COMPREPLY=( $(compgen -W "${candidates}" -- "${COMP_WORDS[COMP_CWORD]}") )
}
complete -F _poleposition_complete polepos poleposition
"""

# Named `_polepos` to match the documented autoload filename
# (~/.zfunc/_polepos). The trailing guard makes the same script work both ways:
# when autoloaded from $fpath (#compdef), $funcstack[1] is the function name, so
# it runs immediately and the first Tab completes; when sourced, it registers
# via compdef instead.
_ZSH_SCRIPT = """\
#compdef polepos poleposition
_polepos() {
    local -a prior candidates
    prior=(${words[2,CURRENT-1]})
    candidates=(${(f)"$(polepos __complete $prior 2>/dev/null)"})
    compadd -a candidates
}
if [ "$funcstack[1]" = "_polepos" ]; then
    _polepos "$@"
else
    compdef _polepos polepos poleposition
fi
"""

_FISH_SCRIPT = """\
function __poleposition_complete
    set -l prior (commandline -opc)
    set -e prior[1]
    polepos __complete $prior 2>/dev/null
end
complete -c polepos -f -a '(__poleposition_complete)'
complete -c poleposition -f -a '(__poleposition_complete)'
"""

_COMPLETION_SCRIPTS: dict[str, str] = {
    "bash": _BASH_SCRIPT,
    "zsh": _ZSH_SCRIPT,
    "fish": _FISH_SCRIPT,
}


def completion_script(shell: str) -> str:
    """Return the completion script for ``shell``.

    Raises ``ValueError`` for an unsupported shell so callers can surface a
    clear CLI error.
    """
    try:
        return _COMPLETION_SCRIPTS[shell]
    except KeyError as exc:
        supported = ", ".join(SUPPORTED_SHELLS)
        raise ValueError(
            f"Unsupported shell '{shell}'. Expected one of: {supported}."
        ) from exc
