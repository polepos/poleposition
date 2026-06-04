from dataclasses import dataclass

CRUD_FEATURE_FLAGS = {
    "--pagination": "pagination",
    "--timestamps": "timestamps",
    "--soft-delete": "soft_delete",
    "--tenant-scoped": "tenant_scoped",
    "--auth-required": "auth_required",
}
CRUD_FEATURE_LABELS = {
    "pagination": "pagination",
    "timestamps": "timestamps",
    "soft_delete": "soft-delete",
    "tenant_scoped": "tenant-scoped",
    "auth_required": "auth-required",
}
CRUD_FEATURE_NAMES_BY_LABEL = {
    label: name for name, label in CRUD_FEATURE_LABELS.items()
}
CRUD_FEATURE_NAMES = tuple(CRUD_FEATURE_LABELS)


@dataclass(frozen=True)
class CrudFeatureSet:
    pagination: bool = False
    timestamps: bool = False
    soft_delete: bool = False
    tenant_scoped: bool = False
    auth_required: bool = False

    @classmethod
    def from_names(cls, names: set[str]) -> "CrudFeatureSet":
        unsupported = sorted(names.difference(CRUD_FEATURE_NAMES))
        if unsupported:
            formatted = ", ".join(unsupported)
            raise ValueError(f"Unsupported CRUD feature option: {formatted}")

        return cls(**{name: name in names for name in CRUD_FEATURE_NAMES})

    @classmethod
    def from_labels(cls, labels: set[str]) -> "CrudFeatureSet":
        unsupported = sorted(labels.difference(CRUD_FEATURE_NAMES_BY_LABEL))
        if unsupported:
            formatted = ", ".join(unsupported)
            raise ValueError(f"Unsupported CRUD feature option: {formatted}")

        names = {CRUD_FEATURE_NAMES_BY_LABEL[label] for label in labels}
        return cls.from_names(names)

    @property
    def enabled_names(self) -> tuple[str, ...]:
        return tuple(name for name in CRUD_FEATURE_NAMES if getattr(self, name))

    @property
    def enabled_labels(self) -> tuple[str, ...]:
        return tuple(CRUD_FEATURE_LABELS[name] for name in self.enabled_names)

    @property
    def has_any(self) -> bool:
        return bool(self.enabled_names)


DEFAULT_CRUD_FEATURES = CrudFeatureSet()
