"""Data model for systems engineering YAML definitions.

Provides dataclasses for functional decomposition and product breakdown trees,
parse functions for converting raw YAML dicts into typed structures, and tree
operations for traversal, filtering, and verification.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Function:
    name: str
    description: str = ""
    functions: list['Function'] = field(default_factory=list)


@dataclass
class ConfigurationItem:
    name: str
    description: str = ""
    functions: list[str] = field(default_factory=list)


@dataclass
class Component:
    name: str
    description: str = ""
    components: list['Component'] = field(default_factory=list)
    configuration_items: list[ConfigurationItem] = field(default_factory=list)


Node = Function | Component | ConfigurationItem


def _get_children(node: Node) -> dict[str, list[Node]]:
    """Return children grouped by field name."""
    if isinstance(node, Function):
        return {"functions": node.functions} if node.functions else {}
    if isinstance(node, Component):
        result: dict[str, list[Node]] = {}
        if node.components:
            result["components"] = node.components
        if node.configuration_items:
            result["configuration_items"] = node.configuration_items
        return result
    return {}


def _reconstruct(node: Node, children: dict[str, list]) -> Node:
    """Build a new node with the given children, preserving scalar fields."""
    if isinstance(node, Function):
        return Function(name=node.name, description=node.description,
                        functions=children.get("functions", []))
    if isinstance(node, Component):
        return Component(name=node.name, description=node.description,
                         components=children.get("components", []),
                         configuration_items=children.get("configuration_items", []))
    return node


def parse_functional_decomposition(raw: dict) -> Function:
    """Recursively convert a raw YAML dict into a Function tree."""
    return Function(
        name=raw["name"],
        description=raw.get("description", ""),
        functions=[parse_functional_decomposition(f) for f in raw.get("functions", [])],
    )


def parse_product_breakdown(raw: dict) -> Component:
    """Recursively convert a raw YAML dict into a Component tree."""
    return Component(
        name=raw["name"],
        description=raw.get("description", ""),
        components=[parse_product_breakdown(c) for c in raw.get("components", [])],
        configuration_items=[
            ConfigurationItem(
                name=ci["name"],
                description=ci.get("description", ""),
                functions=list(ci.get("functions", [])),
            )
            for ci in raw.get("configuration_items", [])
        ],
    )


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def find_subtree(data: Node, root_name: str) -> Node | None:
    """Find and return the subtree rooted at the node with the given name."""
    if data.name == root_name:
        return data
    for children in _get_children(data).values():
        for child in children:
            result = find_subtree(child, root_name)
            if result is not None:
                return result
    return None


def filter_tree(data: Node, filters: list[str], include_descendants: bool) -> Node:
    """Return a pruned copy of the tree containing only matching nodes and their ancestors.

    A node matches if any filter regex matches its name via re.search().
    The root node is always included. Intermediary nodes on the path from root
    to a matched node are included to keep the tree connected.
    If include_descendants is True, all descendants of matched nodes are also included.
    """
    compiled = [re.compile(f, re.IGNORECASE) for f in filters]

    def matches(name: str) -> bool:
        return any(p.search(name) for p in compiled)

    def prune(node: Node) -> Node | None:
        """Return a pruned copy of node, or None if it should be excluded."""
        node_matched = matches(node.name)

        if node_matched and include_descendants:
            return node

        children_by_key = _get_children(node)
        pruned_by_key: dict[str, list] = {}
        for key, children in children_by_key.items():
            pruned_list = []
            for child in children:
                pruned = prune(child)
                if pruned is not None:
                    pruned_list.append(pruned)
            if pruned_list:
                pruned_by_key[key] = pruned_list

        if node_matched or pruned_by_key:
            return _reconstruct(node, pruned_by_key)

        return None

    result = prune(data)
    if result is None:
        return _reconstruct(data, {})
    return result


def is_leaf(function: Function) -> bool:
    """Return True if this function has no children."""
    return not function.functions


def collect_functions(function: Function, parent_name: str, rows: list[tuple[str, str, str]]):
    """Recursively collect function rows as (parent, name, description) tuples."""
    name = function.name
    description = function.description
    rows.append((parent_name, name, description))
    for child in function.functions:
        collect_functions(child, name, rows)


def collect_all_rows(data: Function) -> list[tuple[str, str, str]]:
    """Collect all rows for tabular output, including the root node."""
    rows: list[tuple[str, str, str]] = []
    root_name = data.name
    rows.append(("", root_name, data.description))
    for function in data.functions:
        collect_functions(function, root_name, rows)
    return rows


def _collect_product_rows(component: Component, parent_name: str,
                          rows: list[tuple[str, str, str, str, str]]):
    """Recursively collect product breakdown rows as (parent, name, type, description, functions) tuples."""
    name = component.name
    description = component.description
    rows.append((parent_name, name, "Component", description, ""))
    for child in component.components:
        _collect_product_rows(child, name, rows)
    for ci in component.configuration_items:
        functions_str = ", ".join(ci.functions)
        rows.append((name, ci.name, "Configuration Item", ci.description, functions_str))


def product_collect_all_rows(data: Component) -> list[tuple[str, str, str, str, str]]:
    """Collect all rows for product breakdown tabular output, including the root node."""
    rows: list[tuple[str, str, str, str, str]] = []
    root_name = data.name
    rows.append(("", root_name, "System", data.description, ""))
    for component in data.components:
        _collect_product_rows(component, root_name, rows)
    return rows


def collect_leaf_function_names(data: Function) -> set[str]:
    """Collect names of all leaf functions (excluding root) from a functional decomposition tree."""
    names: set[str] = set()
    for child in data.functions:
        if is_leaf(child):
            names.add(child.name)
        else:
            names |= collect_leaf_function_names(child)
    return names


def collect_allocated_functions(data: Component) -> set[str]:
    """Collect all function names allocated to CIs in a product breakdown tree."""
    allocated: set[str] = set()
    for component in data.components:
        allocated |= collect_allocated_functions(component)
    for ci in data.configuration_items:
        allocated |= set(ci.functions)
    return allocated
