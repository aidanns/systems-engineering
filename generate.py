#!/usr/bin/env python3
"""Generate functional decomposition diagrams from YAML definitions.

Reads YAML files defining functional hierarchies, converts them to d2 diagram
definitions, and renders them to SVG using the d2 tool.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def is_leaf(function: dict) -> bool:
    """Return True if this function has no children."""
    return not function.get("functions")


def function_to_d2(function: dict, parent_id: str, lines: list[str], counter: list[int]):
    """Recursively convert a function node and its children to d2 lines."""
    node_id = f"f{counter[0]}"
    counter[0] += 1
    children = function.get("functions", [])

    lines.append(f"{node_id}: {function['name']}")
    lines.append(f"{node_id}.width: 250")
    if function.get("recently_updated"):
        lines.append(f"{node_id}.style.stroke: red")
    lines.append(f"{parent_id} -> {node_id}")

    if children and all(is_leaf(c) for c in children):
        # All children are leaves — render them in a separate grid container.
        container_id = f"{node_id}_container"
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
            lines.append(f"  {child_id}: {child['name']}")
            lines.append(f"  {child_id}.width: 250")
            if child.get("recently_updated"):
                lines.append(f"  {child_id}.style.stroke: red")
        lines.append(f"}}")
        lines.append(f"{node_id} -> {container_id}")
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
    lines.append(f"{root_id}: {data['name']}")
    lines.append(f"{root_id}.width: 250")
    lines.append("")

    counter = [0]
    for function in data.get("functions", []):
        function_to_d2(function, root_id, lines, counter)
        lines.append("")

    return "\n".join(lines)


def render_d2(d2_path: Path, svg_path: Path):
    """Run d2 to render a .d2 file to SVG."""
    try:
        result = subprocess.run(
            ["d2", str(d2_path), str(svg_path)],
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


def process_file(yaml_path: Path, output_dir: Path):
    """Process a single YAML file: generate .d2 and .svg."""
    data = load_yaml(yaml_path)
    d2_content = yaml_to_d2(data)

    stem = yaml_path.stem
    d2_path = output_dir / f"{stem}.d2"
    svg_path = output_dir / f"{stem}.svg"

    d2_path.write_text(d2_content)
    print(f"Written: {d2_path}")

    render_d2(d2_path, svg_path)
    print(f"Written: {svg_path}")


def run_function_command(args):
    """Handle the 'function' subcommand."""
    input_path: Path = args.input
    output_dir: Path = args.output

    if not input_path.exists():
        print(f"Error: {input_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        process_file(input_path, output_dir)
    elif input_path.is_dir():
        yaml_files = sorted(input_path.glob("*.yaml")) + sorted(input_path.glob("*.yml"))
        if not yaml_files:
            print(f"No YAML files found in {input_path}.", file=sys.stderr)
            sys.exit(1)
        for yaml_file in yaml_files:
            process_file(yaml_file, output_dir)
    else:
        print(f"Error: {input_path} is not a file or directory.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate systems engineering diagrams from YAML definitions."
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
    function_parser.set_defaults(func=run_function_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
