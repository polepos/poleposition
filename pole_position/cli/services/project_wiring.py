import ast


def has_router_import(
    tree: ast.Module,
    router_module: str,
    router_alias: str,
) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != router_module:
            continue
        for alias in node.names:
            if alias.name == "router" and alias.asname == router_alias:
                return True

    return False


def has_router_include(
    tree: ast.Module,
    router_alias: str,
    module_name: str,
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not is_api_router_include_call(node):
            continue
        if not node.args or not is_name(node.args[0], router_alias):
            continue
        if include_router_keywords_match(node, module_name):
            return True

    return False


def is_api_router_include_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "include_router"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "api_router"
    )


def is_name(node: ast.AST, expected_name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected_name


def include_router_keywords_match(node: ast.Call, module_name: str) -> bool:
    prefix = literal_keyword_value(node, "prefix")
    tags = literal_keyword_value(node, "tags")

    return prefix == f"/{module_name}" and tags in (
        [module_name],
        (module_name,),
    )


def literal_keyword_value(node: ast.Call, keyword_name: str) -> object:
    for keyword in node.keywords:
        if keyword.arg == keyword_name:
            return literal_value(keyword.value)

    return None


def literal_value(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def router_aliases_by_module_name(
    tree: ast.Module,
    package_name: str,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module_name = module_name_from_router_import(node, package_name)
        if module_name is None:
            continue
        for alias in node.names:
            if alias.name == "router":
                aliases[alias.asname or alias.name] = module_name

    return aliases


def module_name_from_router_import(
    node: ast.ImportFrom,
    package_name: str,
) -> str | None:
    prefix = f"{package_name}.modules."
    suffix = ".router"
    if node.module is None:
        return None
    if not node.module.startswith(prefix) or not node.module.endswith(suffix):
        return None

    module_name = node.module[len(prefix) : -len(suffix)]
    return module_name if module_name.isidentifier() else None


def module_name_from_router_include(
    node: ast.Call,
    router_aliases: dict[str, str],
) -> str | None:
    if not is_api_router_include_call(node):
        return None

    if node.args and isinstance(node.args[0], ast.Name):
        alias = node.args[0].id
        if alias in router_aliases:
            return router_aliases[alias]
        if alias.endswith("_router"):
            module_name = alias[: -len("_router")]
            if module_name.isidentifier():
                return module_name

    prefix = literal_keyword_value(node, "prefix")
    tags = literal_keyword_value(node, "tags")
    if isinstance(prefix, str) and prefix.startswith("/"):
        module_name = prefix.strip("/")
        if module_name.isidentifier() and tags in (
            [module_name],
            (module_name,),
        ):
            return module_name

    return None


def module_name_from_model_reference(
    node: ast.AST,
    package_name: str,
) -> str | None:
    if isinstance(node, ast.ImportFrom):
        return module_name_from_import_module(node.module, package_name)

    if isinstance(node, ast.Import):
        for alias in node.names:
            module_name = module_name_from_import_module(
                alias.name, package_name
            )
            if module_name is not None:
                return module_name

    return None


def module_name_from_import_module(
    module: str | None,
    package_name: str,
) -> str | None:
    prefix = f"{package_name}.modules."
    if module is None or not module.startswith(prefix):
        return None

    module_name = module[len(prefix) :].split(".", 1)[0]
    if not module_name.isidentifier():
        return None

    return module_name
