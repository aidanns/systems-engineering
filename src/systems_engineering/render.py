"""Rendering functions for systems engineering diagrams and tables.

Converts typed data model structures into d2 diagram definitions,
markdown tables, CSV tables, and rendered SVG/PNG output.
"""

import csv
import io
import math
import re
import subprocess
from pathlib import Path

from .model import (
    Component,
    ConfigurationItem,
    Function,
    Node,
    collect_all_rows,
    is_leaf,
    product_collect_all_rows,
)

Highlights = list[tuple[list[re.Pattern], str]]


def build_highlights(highlight_updated: list[str] | None,
                     highlight_new: list[str] | None) -> Highlights:
    """Build a list of (compiled_patterns, color) tuples from CLI highlight args.

    Updated (red) is checked before new (blue) so that if a node matches both,
    the updated highlight takes precedence.
    """
    highlights = []
    if highlight_updated:
        highlights.append(
            ([re.compile(p, re.IGNORECASE) for p in highlight_updated], "red"))
    if highlight_new:
        highlights.append(
            ([re.compile(p, re.IGNORECASE) for p in highlight_new], "blue"))
    return highlights


def emit_node(lines: list[str], node_id: str, node: Node, indent: str = "",
              shape: str | None = None, width: int = 400, height: int | None = None,
              wrap_label: bool = False,
              highlights: Highlights | None = None):
    """Emit d2 lines for a single labeled node."""
    label = re.sub(r'[ -]', r'\\n', node.name) if wrap_label else node.name
    lines.append(f"{indent}{node_id}: {label}")
    lines.append(f"{indent}{node_id}.width: {width}")
    if height is not None:
        lines.append(f"{indent}{node_id}.height: {height}")
    if shape:
        lines.append(f"{indent}{node_id}.shape: {shape}")
    if highlights:
        for patterns, color in highlights:
            if any(p.search(node.name) for p in patterns):
                lines.append(f"{indent}{node_id}.style.stroke: {color}")
                break


def emit_container(lines: list[str], parent_id: str,
                   children: list[Function] | list[ConfigurationItem],
                   counter: list[int], prefix: str = "f", shape: str | None = None,
                   grid_columns: int = 1, node_width: int = 400,
                   node_height: int | None = None, wrap_label: bool = False,
                   highlights: Highlights | None = None):
    """Emit a grid container holding child nodes, connected to the parent node."""
    container_id = f"{parent_id}_container"
    grid_rows = math.ceil(len(children) / grid_columns)
    lines.append(f"{container_id}: \"\" {{")
    lines.append(f"  grid-columns: {grid_columns}")
    lines.append(f"  grid-rows: {grid_rows}")
    lines.append(f"  grid-gap: 5")
    lines.append(f"  style: {{")
    lines.append(f"    stroke-width: 0")
    lines.append(f"    fill: transparent")
    lines.append(f"  }}")
    for child in children:
        child_id = f"{prefix}{counter[0]}"
        counter[0] += 1
        emit_node(lines, child_id, child, indent="  ", shape=shape,
                  width=node_width, height=node_height,
                  wrap_label=wrap_label, highlights=highlights)
    lines.append(f"}}")
    lines.append(f"{parent_id} -> {container_id}")


def function_to_d2(function: Function, parent_id: str, lines: list[str],
                   counter: list[int], highlights: Highlights | None = None):
    """Recursively convert a function node and its children to d2 lines."""
    node_id = f"f{counter[0]}"
    counter[0] += 1
    children = function.functions

    emit_node(lines, node_id, function, highlights=highlights)
    lines.append(f"{parent_id} -> {node_id}")

    if children and all(is_leaf(c) for c in children):
        emit_container(lines, node_id, children, counter, highlights=highlights)
    else:
        for child in children:
            function_to_d2(child, node_id, lines, counter, highlights=highlights)


def _emit_d2_preamble(lines: list[str], data: Node,
                      highlights: Highlights | None = None):
    """Emit the common d2 config block, direction, and root node."""
    lines.append("vars: {")
    lines.append("  d2-config: {")
    lines.append("    layout-engine: elk")
    lines.append("    # Terminal theme code")
    lines.append("    theme-id: 300")
    lines.append("  }")
    lines.append("}")
    lines.append("")
    lines.append("direction: down")
    lines.append("")
    emit_node(lines, "root", data, highlights=highlights)
    lines.append("")


def functional_yaml_to_d2(data: Function,
                          highlights: Highlights | None = None) -> str:
    """Convert a functional decomposition structure to a d2 definition."""
    lines: list[str] = []
    _emit_d2_preamble(lines, data, highlights=highlights)

    root_id = "root"

    children = data.functions
    counter = [0]
    if children and all(is_leaf(c) for c in children):
        emit_container(lines, root_id, children, counter, highlights=highlights)
        lines.append("")
    else:
        for function in children:
            function_to_d2(function, root_id, lines, counter, highlights=highlights)
            lines.append("")

    return "\n".join(lines)


def product_component_to_d2(component: Component, parent_id: str,
                            lines: list[str], counter: list[int]):
    """Recursively convert a component node and its children to d2 lines."""
    node_id = f"p{counter[0]}"
    counter[0] += 1

    emit_node(lines, node_id, component)
    lines.append(f"{parent_id} -> {node_id}")

    if component.components:
        for child in component.components:
            product_component_to_d2(child, node_id, lines, counter)
    if component.configuration_items:
        emit_container(lines, node_id, component.configuration_items, counter,
                       prefix="p", shape="circle",
                       grid_columns=3, node_width=150, node_height=150,
                       wrap_label=True)


def product_yaml_to_d2(data: Component) -> str:
    """Convert a product breakdown structure to a d2 definition."""
    lines: list[str] = []
    _emit_d2_preamble(lines, data)

    root_id = "root"
    counter = [0]
    for component in data.components:
        product_component_to_d2(component, root_id, lines, counter)
        lines.append("")

    return "\n".join(lines)


def yaml_to_markdown(data: Function) -> str:
    """Convert a functional decomposition structure to a markdown table."""
    rows = collect_all_rows(data)

    lines = [
        f"# {data.name}",
        "",
        "| Parent | Function | Description |",
        "|--------|----------|-------------|",
    ]
    for parent, name, description in rows:
        lines.append(f"| {parent} | {name} | {description} |")

    return "\n".join(lines) + "\n"


def yaml_to_csv(data: Function) -> str:
    """Convert a functional decomposition structure to a CSV table."""
    rows = collect_all_rows(data)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parent", "Function", "Description"])
    writer.writerows(rows)
    return output.getvalue()


def product_yaml_to_markdown(data: Component) -> str:
    """Convert a product breakdown structure to a markdown table."""
    rows = product_collect_all_rows(data)

    lines = [
        f"# {data.name}",
        "",
        "| Parent | Name | Type | Description | Functions |",
        "|--------|------|------|-------------|-----------|",
    ]
    for parent, name, type_, description, functions in rows:
        lines.append(f"| {parent} | {name} | {type_} | {description} | {functions} |")

    return "\n".join(lines) + "\n"


def product_yaml_to_csv(data: Component) -> str:
    """Convert a product breakdown structure to a CSV table."""
    rows = product_collect_all_rows(data)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parent", "Name", "Type", "Description", "Functions"])
    writer.writerows(rows)
    return output.getvalue()


class D2NotFoundError(RuntimeError):
    """Raised when the d2 binary is not installed or not on PATH."""


class D2RenderError(RuntimeError):
    """Raised when d2 fails to render a diagram."""


def render_d2(d2_path: Path, output_path: Path):
    """Run d2 to render a .d2 file to the given output format (determined by extension).

    Raises D2NotFoundError if d2 is not installed, or D2RenderError on render failure.
    """
    try:
        result = subprocess.run(
            ["d2", str(d2_path), str(output_path)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise D2NotFoundError(
            "d2 is not installed or not on PATH. Install it from https://d2lang.com/"
        )
    if result.returncode != 0:
        raise D2RenderError(f"Error rendering {d2_path}: {result.stderr}")
