#!/usr/bin/env python3
"""Systems engineering CLI: functional decomposition diagrams and product breakdown verification.

Reads YAML files defining functional hierarchies and product breakdowns,
generates d2 diagrams, and verifies function-to-CI allocations.
"""

import argparse
import csv
import importlib.metadata
import io
import re
import subprocess
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def find_subtree(data: dict, root_name: str) -> dict | None:
    """Find and return the subtree rooted at the node with the given name."""
    if data["name"] == root_name:
        return data
    for child in data.get("functions", []):
        result = find_subtree(child, root_name)
        if result is not None:
            return result
    return None


def filter_tree(data: dict, filters: list[str], include_descendants: bool) -> dict:
    """Return a pruned copy of the tree containing only matching functions and their ancestors.

    A function matches if any filter regex matches its name via re.search().
    The root node is always included. Intermediary nodes on the path from root
    to a matched node are included to keep the tree connected.
    If include_descendants is True, all descendants of matched nodes are also included.
    """
    compiled = [re.compile(f, re.IGNORECASE) for f in filters]

    def matches(name: str) -> bool:
        return any(p.search(name) for p in compiled)

    def prune(node: dict) -> dict | None:
        """Return a pruned copy of node, or None if it should be excluded."""
        node_matched = matches(node["name"])
        children = node.get("functions", [])

        if node_matched and include_descendants:
            # Include this node and all descendants unchanged
            return dict(node)

        pruned_children = []
        for child in children:
            pruned = prune(child)
            if pruned is not None:
                pruned_children.append(pruned)

        if node_matched or pruned_children:
            result = {k: v for k, v in node.items() if k != "functions"}
            if pruned_children:
                result["functions"] = pruned_children
            return result

        return None

    # Root is always included, so start pruning from children
    result = prune(data)
    if result is None:
        # No matches found — return root only
        return {k: v for k, v in data.items() if k != "functions"}
    return result


def is_leaf(function: dict) -> bool:
    """Return True if this function has no children."""
    return not function.get("functions")


def emit_node(lines: list[str], node_id: str, function: dict, indent: str = ""):
    """Emit d2 lines for a single function node."""
    lines.append(f"{indent}{node_id}: {function['name']}")
    lines.append(f"{indent}{node_id}.width: 250")
    if function.get("recently_updated"):
        lines.append(f"{indent}{node_id}.style.stroke: red")


def emit_leaf_container(lines: list[str], parent_id: str, children: list[dict], counter: list[int]):
    """Emit a grid container holding leaf children, connected to the parent node."""
    container_id = f"{parent_id}_container"
    lines.append(f"{container_id}: \"\" {{")
    lines.append(f"  grid-columns: 1")
    lines.append(f"  grid-gap: 5")
    lines.append(f"  style: {{")
    lines.append(f"    stroke-width: 0")
    lines.append(f"    fill: transparent")
    lines.append(f"  }}")
    for child in children:
        child_id = f"f{counter[0]}"
        counter[0] += 1
        emit_node(lines, child_id, child, indent="  ")
    lines.append(f"}}")
    lines.append(f"{parent_id} -> {container_id}")


def function_to_d2(function: dict, parent_id: str, lines: list[str], counter: list[int]):
    """Recursively convert a function node and its children to d2 lines."""
    node_id = f"f{counter[0]}"
    counter[0] += 1
    children = function.get("functions", [])

    emit_node(lines, node_id, function)
    lines.append(f"{parent_id} -> {node_id}")

    if children and all(is_leaf(c) for c in children):
        emit_leaf_container(lines, node_id, children, counter)
    else:
        for child in children:
            function_to_d2(child, node_id, lines, counter)


def yaml_to_d2(data: dict) -> str:
    """Convert a functional decomposition YAML structure to a d2 definition."""
    lines = []

    # d2 configuration
    lines.append("vars: {")
    lines.append("  d2-config: {")
    lines.append("    layout-engine: elk")
    lines.append("    # Terminal theme code")
    lines.append("    theme-id: 300")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Style: top-down layout for hierarchy
    lines.append("direction: down")
    lines.append("")

    # Root node
    root_id = "root"
    emit_node(lines, root_id, data)
    lines.append("")

    children = data.get("functions", [])
    counter = [0]
    if children and all(is_leaf(c) for c in children):
        emit_leaf_container(lines, root_id, children, counter)
        lines.append("")
    else:
        for function in children:
            function_to_d2(function, root_id, lines, counter)
            lines.append("")

    return "\n".join(lines)


def collect_functions(function: dict, parent_name: str, rows: list[tuple[str, str, str]]):
    """Recursively collect function rows as (parent, name, description) tuples."""
    name = function["name"]
    description = function.get("description", "")
    rows.append((parent_name, name, description))
    for child in function.get("functions", []):
        collect_functions(child, name, rows)


def collect_all_rows(data: dict) -> list[tuple[str, str, str]]:
    """Collect all rows for tabular output, including the root node."""
    rows: list[tuple[str, str, str]] = []
    root_name = data["name"]
    rows.append(("", root_name, data.get("description", "")))
    for function in data.get("functions", []):
        collect_functions(function, root_name, rows)
    return rows


def yaml_to_markdown(data: dict) -> str:
    """Convert a functional decomposition YAML structure to a markdown table."""
    rows = collect_all_rows(data)

    lines = [
        f"# {data['name']}",
        "",
        "| Parent | Function | Description |",
        "|--------|----------|-------------|",
    ]
    for parent, name, description in rows:
        lines.append(f"| {parent} | {name} | {description} |")

    return "\n".join(lines) + "\n"


def yaml_to_csv(data: dict) -> str:
    """Convert a functional decomposition YAML structure to a CSV table."""
    rows = collect_all_rows(data)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Parent", "Function", "Description"])
    writer.writerows(rows)
    return output.getvalue()


def render_d2(d2_path: Path, output_path: Path):
    """Run d2 to render a .d2 file to the given output format (determined by extension)."""
    try:
        result = subprocess.run(
            ["d2", str(d2_path), str(output_path)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Error: d2 is not installed or not on PATH.", file=sys.stderr)
        print("Install it from https://d2lang.com/", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"Error rendering {d2_path}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def process_file(yaml_path: Path, output_dir: Path, root: str | None = None,
                  filters: list[str] | None = None, include_descendants: bool = False):
    """Process a single YAML file: generate .d2, .svg, .png, .md, and .csv."""
    data = load_yaml(yaml_path)

    if root is not None:
        subtree = find_subtree(data, root)
        if subtree is None:
            print(f"Error: root function '{root}' not found in {yaml_path}.", file=sys.stderr)
            sys.exit(1)
        data = subtree

    if filters:
        data = filter_tree(data, filters, include_descendants)

    stem = yaml_path.stem
    d2_path = output_dir / f"{stem}_functions.d2"
    svg_path = output_dir / f"{stem}_functions.svg"
    png_path = output_dir / f"{stem}_functions.png"
    md_path = output_dir / f"{stem}_functions.md"

    d2_content = yaml_to_d2(data)
    d2_path.write_text(d2_content)
    print(f"Written: {d2_path}")

    render_d2(d2_path, svg_path)
    print(f"Written: {svg_path}")

    render_d2(d2_path, png_path)
    print(f"Written: {png_path}")

    md_content = yaml_to_markdown(data)
    md_path.write_text(md_content)
    print(f"Written: {md_path}")

    csv_path = output_dir / f"{stem}_functions.csv"
    csv_content = yaml_to_csv(data)
    csv_path.write_text(csv_content)
    print(f"Written: {csv_path}")


def collect_leaf_function_names(data: dict) -> set[str]:
    """Collect names of all leaf functions (excluding root) from a functional decomposition tree."""
    names: set[str] = set()
    for child in data.get("functions", []):
        if is_leaf(child):
            names.add(child["name"])
        else:
            names |= collect_leaf_function_names(child)
    return names


def collect_allocated_functions(data: dict) -> set[str]:
    """Collect all function names allocated to CIs in a product breakdown tree."""
    allocated: set[str] = set()
    for component in data.get("components", []):
        allocated |= collect_allocated_functions(component)
    for ci in data.get("configuration_items", []):
        allocated |= set(ci.get("functions", []))
    return allocated


def run_product_verify_command(args):
    """Handle the 'product verify' subcommand."""
    fd_path: Path = args.functional_decomposition
    pb_path: Path = args.product_breakdown

    if not fd_path.exists():
        print(f"Error: {fd_path} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not pb_path.exists():
        print(f"Error: {pb_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    fd_data = load_yaml(fd_path)
    pb_data = load_yaml(pb_path)

    all_functions = collect_leaf_function_names(fd_data)
    allocated = collect_allocated_functions(pb_data)

    if not all_functions:
        print("\u26a0\ufe0f No leaf functions found in functional decomposition.", file=sys.stderr)
        sys.exit(1)

    unknown = sorted(allocated - all_functions)
    if unknown:
        print(f"\u26a0\ufe0f Some allocated functions not found in functional decomposition: {', '.join(unknown)}", file=sys.stderr)

    unallocated = sorted(all_functions - allocated)

    if not unallocated:
        print("\u2705 All functions allocated.")
    else:
        print(f"\u26a0\ufe0f Some functions unallocated: {', '.join(unallocated)}")
        sys.exit(1)


def run_function_command(args):
    """Handle the 'function' subcommand."""
    input_path: Path = args.input
    output_dir: Path = args.output

    if not input_path.exists():
        print(f"Error: {input_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    root = args.root
    filters = args.filter
    include_descendants = args.include_descendants

    if input_path.is_file():
        process_file(input_path, output_dir, root, filters, include_descendants)
    elif input_path.is_dir():
        yaml_files = sorted(input_path.glob("*.yaml")) + sorted(input_path.glob("*.yml"))
        if not yaml_files:
            print(f"No YAML files found in {input_path}.", file=sys.stderr)
            sys.exit(1)
        for yaml_file in yaml_files:
            process_file(yaml_file, output_dir, root, filters, include_descendants)
    else:
        print(f"Error: {input_path} is not a file or directory.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate systems engineering diagrams from YAML definitions."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('systems-engineering-diagrams')}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'function' subcommand
    function_parser = subparsers.add_parser(
        "function",
        help="Generate functional decomposition diagrams.",
    )
    function_parser.add_argument(
        "input",
        type=Path,
        help="YAML file or directory containing YAML files.",
    )
    function_parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for .d2 and .svg files (default: output/).",
    )
    function_parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Name of the function to use as the root of the output tree.",
    )
    function_parser.add_argument(
        "--filter",
        action="append",
        default=None,
        help="Regex pattern to filter functions by name (repeatable). "
             "Matches as substring by default; use anchors for exact match.",
    )
    function_parser.add_argument(
        "--include-descendants",
        action="store_true",
        default=False,
        help="When filtering, include all descendants of matched functions.",
    )
    function_parser.set_defaults(func=run_function_command)

    # 'product' subcommand
    product_parser = subparsers.add_parser(
        "product",
        help="Product breakdown commands.",
    )
    product_subparsers = product_parser.add_subparsers(
        dest="product_command", required=True
    )

    # 'product verify' subcommand
    verify_parser = product_subparsers.add_parser(
        "verify",
        help="Verify all leaf functions are allocated to configuration items.",
    )
    verify_parser.add_argument(
        "-p", "--product-breakdown",
        type=Path,
        required=True,
        help="Product breakdown YAML file.",
    )
    verify_parser.add_argument(
        "-f", "--functional-decomposition",
        type=Path,
        required=True,
        help="Functional decomposition YAML file.",
    )
    verify_parser.set_defaults(func=run_product_verify_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
