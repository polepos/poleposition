from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AddedIntegrationResult:
    integration_name: str
    project_root: Path
    package_root: Path
    integration_files: tuple[Path, ...]
    updated_files: tuple[Path, ...]
    next_steps: tuple[str, ...]

    @property
    def package_name(self) -> str:
        return self.package_root.name
