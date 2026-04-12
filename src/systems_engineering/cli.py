#!/usr/bin/env python3
"""Systems engineering CLI: diagrams, allocation verification, and test coverage checks.

Reads YAML files defining functional hierarchies and product breakdowns,
generates d2 diagrams, verifies function-to-CI allocations, and checks
test coverage of functions via static analysis of test annotations.
"""

import argparse
import ast
import functools
import importlib.metadata
import sys
from collections.abc import Callable
from pathlib import Path

from .model import (
    Component,
    Function,
    collect_allocated_functions,
    collect_leaf_function_names,
    filter_tree,
    find_subtree,
    load_yaml,
    parse_functional_decomposition,
    parse_product_breakdown,
)
from .render import (
    D2NotFoundError,
    D2RenderError,
    Highlights,
    build_highlights,
    functional_yaml_to_d2,
    product_yaml_to_csv,
    product_yaml_to_d2,
    product_yaml_to_markdown,
    render_d2,
    yaml_to_csv,
    yaml_to_markdown,
)


def resolve_directory_to_file(dir_path: Path, default_stem: str) -> Path:
    """If dir_path is a directory, look for default_stem.yaml (or .yml) inside it.

    Returns the resolved file path (which may not exist if neither extension was found).
    If dir_path is not a directory, returns it unchanged.
    """
    if not dir_path.is_dir():
        return dir_path
    candidate = dir_path / f"{default_stem}.yaml"
    if candidate.exists():
        return candidate
    candidate = dir_path / f"{default_stem}.yml"
    if candidate.exists():
        return candidate
    return dir_path / f"{default_stem}.yaml"


def _write_outputs(data: Function | Component, yaml_path: Path, output_dir: Path,
                   to_d2: Callable, to_md: Callable, to_csv: Callable):
    """Generate .d2, .svg, .png, .md, and .csv output files."""
    stem = yaml_path.stem
    d2_path = output_dir / f"{stem}.d2"
    svg_path = output_dir / f"{stem}.svg"
    png_path = output_dir / f"{stem}.png"
    md_path = output_dir / f"{stem}.md"
    csv_path = output_dir / f"{stem}.csv"

    d2_path.write_text(to_d2(data))
    print(f"Written: {d2_path}")

    try:
        render_d2(d2_path, svg_path)
        print(f"Written: {svg_path}")

        render_d2(d2_path, png_path)
        print(f"Written: {png_path}")
    except D2NotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except D2RenderError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    md_path.write_text(to_md(data))
    print(f"Written: {md_path}")

    csv_path.write_text(to_csv(data))
    print(f"Written: {csv_path}")


def process_file(yaml_path: Path, output_dir: Path, root: str | None = None,
                  filters: list[str] | None = None, include_descendants: bool = False,
                  highlights: Highlights | None = None):
    """Process a single YAML file: generate .d2, .svg, .png, .md, and .csv."""
    data = parse_functional_decomposition(load_yaml(yaml_path))

    if root is not None:
        subtree = find_subtree(data, root)
        if subtree is None:
            print(f"Error: root function '{root}' not found in {yaml_path}.", file=sys.stderr)
            sys.exit(1)
        data = subtree

    if filters:
        data = filter_tree(data, filters, include_descendants)

    to_d2 = functools.partial(functional_yaml_to_d2, highlights=highlights)

    _write_outputs(data, yaml_path, output_dir,
                   to_d2, yaml_to_markdown, yaml_to_csv)


def process_product_file(yaml_path: Path, output_dir: Path, root: str | None = None,
                         filters: list[str] | None = None,
                         include_descendants: bool = False):
    """Process a single product breakdown YAML file: generate .d2, .svg, .png, .md, and .csv."""
    data = parse_product_breakdown(load_yaml(yaml_path))

    if root is not None:
        subtree = find_subtree(data, root)
        if subtree is None:
            print(f"Error: root node '{root}' not found in {yaml_path}.",
                  file=sys.stderr)
            sys.exit(1)
        data = subtree

    if filters:
        data = filter_tree(data, filters, include_descendants)

    _write_outputs(data, yaml_path, output_dir,
                   product_yaml_to_d2, product_yaml_to_markdown, product_yaml_to_csv)


def run_product_verify_command(args):
    """Handle the 'product verify' subcommand."""
    fd_path: Path = resolve_directory_to_file(args.functional_decomposition, "functional_decomposition")
    pb_path: Path = resolve_directory_to_file(args.product_breakdown, "product_breakdown")

    if not fd_path.exists():
        print(f"Error: {fd_path} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not pb_path.exists():
        print(f"Error: {pb_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    fd_data = parse_functional_decomposition(load_yaml(fd_path))
    pb_data = parse_product_breakdown(load_yaml(pb_path))

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


def _is_covers_function_decorator(node: ast.expr) -> bool:
    """Return True if the AST node is a call to pytest.mark.covers_function(...)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    # Match: pytest.mark.covers_function(...)
    return (isinstance(func, ast.Attribute) and func.attr == "covers_function"
            and isinstance(func.value, ast.Attribute) and func.value.attr == "mark"
            and isinstance(func.value.value, ast.Name) and func.value.value.id == "pytest")


def _extract_covered_names(decorator: ast.Call) -> set[str]:
    """Extract string literal arguments from a covers_function() call."""
    names: set[str] = set()
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            names.add(arg.value)
    return names


def collect_covered_functions(test_dir: Path) -> set[str]:
    """Scan Python files for @pytest.mark.covers_function annotations and return covered function names."""
    covered: set[str] = set()
    for py_file in sorted(test_dir.rglob("*.py")):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: skipping {py_file}: {e}", file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    if _is_covers_function_decorator(decorator):
                        covered |= _extract_covered_names(decorator)
    return covered


def run_function_verify_command(args):
    """Handle the 'function verify' subcommand."""
    fd_path: Path = resolve_directory_to_file(args.functional_decomposition, "functional_decomposition")
    test_dir: Path = args.test_directory

    if not fd_path.exists():
        print(f"Error: {fd_path} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not test_dir.is_dir():
        print(f"Error: {test_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    fd_data = parse_functional_decomposition(load_yaml(fd_path))
    all_functions = collect_leaf_function_names(fd_data)

    if not all_functions:
        print("\u26a0\ufe0f No leaf functions found in functional decomposition.", file=sys.stderr)
        sys.exit(1)

    covered = collect_covered_functions(test_dir)

    unknown = sorted(covered - all_functions)
    if unknown:
        print(f"\u26a0\ufe0f Some test annotations reference functions not in functional decomposition: {', '.join(unknown)}", file=sys.stderr)

    uncovered = sorted(all_functions - covered)
    total = len(all_functions)
    covered_count = total - len(uncovered)

    if not uncovered:
        print(f"\u2705 All leaf functions covered by tests. ({covered_count}/{total})")
    else:
        print(f"\u26a0\ufe0f Some functions not covered by tests: {', '.join(uncovered)} ({covered_count}/{total} covered)")
        sys.exit(1)


def _dispatch_yaml_files(input_path: Path, output_dir: Path, process_fn,
                         default_stem: str):
    """Validate input, create output dir, and dispatch YAML files to process_fn."""
    if not input_path.exists():
        print(f"Error: {input_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        process_fn(input_path, output_dir)
    elif input_path.is_dir():
        default_file = resolve_directory_to_file(input_path, default_stem)
        if not default_file.exists():
            print(f"Error: no {default_stem}.yaml found in {input_path}.", file=sys.stderr)
            sys.exit(1)
        process_fn(default_file, output_dir)
    else:
        print(f"Error: {input_path} is not a file or directory.", file=sys.stderr)
        sys.exit(1)


def run_product_diagram_command(args):
    """Handle the 'product diagram' subcommand."""
    root = args.root
    filters = args.filter
    include_descendants = args.include_descendants

    def process_fn(yaml_path, output_dir):
        process_product_file(yaml_path, output_dir, root, filters,
                             include_descendants)

    _dispatch_yaml_files(args.input, args.output, process_fn,
                         "product_breakdown")


def run_function_command(args):
    """Handle the 'function' subcommand."""
    root = args.root
    filters = args.filter
    include_descendants = args.include_descendants
    highlights = build_highlights(args.highlight_updated, args.highlight_new)

    def process_fn(yaml_path, output_dir):
        process_file(yaml_path, output_dir, root, filters, include_descendants,
                     highlights)

    _dispatch_yaml_files(args.input, args.output, process_fn,
                         "functional_decomposition")


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

    # 'function' subcommand group
    function_parser = subparsers.add_parser(
        "function",
        help="Functional decomposition commands.",
    )
    function_subparsers = function_parser.add_subparsers(
        dest="function_command", required=True
    )

    # 'function diagram' subcommand
    function_diagram_parser = function_subparsers.add_parser(
        "diagram",
        help="Generate functional decomposition diagrams.",
    )
    function_diagram_parser.add_argument(
        "input",
        type=Path,
        help="YAML file or directory (expects functional_decomposition.yaml).",
    )
    function_diagram_parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for generated files (default: output/).",
    )
    function_diagram_parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Name of the function to use as the root of the output tree.",
    )
    function_diagram_parser.add_argument(
        "--filter",
        action="append",
        default=None,
        help="Regex pattern to filter functions by name (repeatable). "
             "Matches as substring by default; use anchors for exact match.",
    )
    function_diagram_parser.add_argument(
        "--include-descendants",
        action="store_true",
        default=False,
        help="When filtering, include all descendants of matched functions.",
    )
    function_diagram_parser.add_argument(
        "--highlight-updated",
        action="append",
        default=None,
        help="Regex pattern to highlight functions with a red border (repeatable). "
             "Matches as substring by default; use anchors for exact match.",
    )
    function_diagram_parser.add_argument(
        "--highlight-new",
        action="append",
        default=None,
        help="Regex pattern to highlight functions with a blue border (repeatable). "
             "Matches as substring by default; use anchors for exact match.",
    )
    function_diagram_parser.set_defaults(func=run_function_command)

    # 'function verify' subcommand
    function_verify_parser = function_subparsers.add_parser(
        "verify",
        help="Verify all leaf functions are covered by test annotations.",
    )
    function_verify_parser.add_argument(
        "functional_decomposition",
        type=Path,
        help="Functional decomposition YAML file or directory (expects functional_decomposition.yaml).",
    )
    function_verify_parser.add_argument(
        "-t", "--test-directory",
        type=Path,
        required=True,
        help="Directory containing Python test files with @pytest.mark.covers_function annotations.",
    )
    function_verify_parser.set_defaults(func=run_function_verify_command)

    # 'product' subcommand group
    product_parser = subparsers.add_parser(
        "product",
        help="Product breakdown commands.",
    )
    product_subparsers = product_parser.add_subparsers(
        dest="product_command", required=True
    )

    # 'product diagram' subcommand
    product_diagram_parser = product_subparsers.add_parser(
        "diagram",
        help="Generate product breakdown diagrams.",
    )
    product_diagram_parser.add_argument(
        "input",
        type=Path,
        help="YAML file or directory (expects product_breakdown.yaml).",
    )
    product_diagram_parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for generated files (default: output/).",
    )
    product_diagram_parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Name of the component or CI to use as the root of the output tree.",
    )
    product_diagram_parser.add_argument(
        "--filter",
        action="append",
        default=None,
        help="Regex pattern to filter nodes by name (repeatable). "
             "Matches as substring by default; use anchors for exact match.",
    )
    product_diagram_parser.add_argument(
        "--include-descendants",
        action="store_true",
        default=False,
        help="When filtering, include all descendants of matched nodes.",
    )
    product_diagram_parser.set_defaults(func=run_product_diagram_command)

    # 'product verify' subcommand
    product_verify_parser = product_subparsers.add_parser(
        "verify",
        help="Verify all leaf functions are allocated to configuration items.",
    )
    product_verify_parser.add_argument(
        "-p", "--product-breakdown",
        type=Path,
        required=True,
        help="Product breakdown YAML file or directory (expects product_breakdown.yaml).",
    )
    product_verify_parser.add_argument(
        "-f", "--functional-decomposition",
        type=Path,
        required=True,
        help="Functional decomposition YAML file or directory (expects functional_decomposition.yaml).",
    )
    product_verify_parser.set_defaults(func=run_product_verify_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
