from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AddedModuleResult:
    module_name: str
    template: str
    project_root: Path
    package_root: Path
    module_files: tuple[Path, ...]
    test_files: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]
    features: tuple[str, ...] = ()

    @property
    def package_name(self) -> str:
        return self.package_root.name
