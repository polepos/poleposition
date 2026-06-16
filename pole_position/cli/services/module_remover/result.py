from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RemovedModuleResult:
    module_name: str
    template: str
    project_root: Path
    package_root: Path
    removed_paths: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]
    trace: bool = False
    force: bool = False
    wiring_only: bool = False
    custom_changes: tuple[str, ...] = ()
    blocked_by_custom_changes: bool = False

    @property
    def package_name(self) -> str:
        return self.package_root.name
