"""Semantic tests for the systems-engineering CLI output."""

import argparse
import csv
import importlib.metadata
import io
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from systems_engineering.cli import (
    collect_allocated_functions,
    collect_leaf_function_names,
    filter_tree,
    find_subtree,
    load_yaml,
    process_file,
    process_product_file,
    product_collect_all_rows,
    product_yaml_to_csv,
    product_yaml_to_d2,
    product_yaml_to_markdown,
    run_function_command,
    run_product_verify_command,
    yaml_to_csv,
    yaml_to_d2,
    yaml_to_markdown,
)

REPO_ROOT = Path(__file__).parent.parent
EXAMPLE_YAML = REPO_ROOT / "example" / "functional_decomposition.yaml"
PRODUCT_EXAMPLE_YAML = REPO_ROOT / "example" / "product_breakdown.yaml"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"

HAS_D2 = shutil.which("d2") is not None


@pytest.fixture
def example_data():
    return load_yaml(EXAMPLE_YAML)


@pytest.fixture
def all_functions(example_data):
    """Return a flat list of (parent_name, function_dict) for all functions."""
    result = []

    def collect(parent_name, functions):
        for f in functions:
            result.append((parent_name, f))
            collect(f["name"], f.get("functions", []))

    collect(example_data["name"], example_data.get("functions", []))
    return result


@pytest.fixture(scope="module")
def generated_output(tmp_path_factory):
    """Generate all output files once and share across tests."""
    tmp_path = tmp_path_factory.mktemp("output")
    process_file(EXAMPLE_YAML, tmp_path)
    return tmp_path


# --- D2 structural tests ---


class TestD2Output:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data
        self.d2 = yaml_to_d2(example_data)
        self.lines = self.d2.splitlines()

    def test_config_block_present(self):
        assert "layout-engine: elk" in self.d2
        assert "theme-id: 300" in self.d2

    def test_direction_down(self):
        assert "direction: down" in self.d2

    def test_root_node(self):
        assert "root: Example System" in self.d2
        assert "root.width: 250" in self.d2

    def test_all_function_names_present(self, all_functions):
        for _, func in all_functions:
            name = func["name"]
            assert any(name in line for line in self.lines), (
                f"Function '{name}' not found in d2 output"
            )

    def test_node_count(self, all_functions):
        node_defs = re.findall(r"^[ ]*f(\d+): .+", self.d2, re.MULTILINE)
        assert len(node_defs) == len(all_functions)

    def test_parent_child_arrows(self, all_functions):
        # Root's direct children should have root -> fN
        assert "root -> f0" in self.d2

    def test_recently_updated_red_stroke(self, all_functions):
        for _, func in all_functions:
            if func.get("recently_updated"):
                name = func["name"]
                # Find the node ID for this function, then check for red stroke
                for line in self.lines:
                    if name in line and ": " in line:
                        node_id = line.strip().split(":")[0].strip()
                        assert f"{node_id}.style.stroke: red" in self.d2, (
                            f"Function '{name}' is recently_updated but no red stroke found"
                        )
                        break

    def test_leaf_containers_config(self):
        # Every container should have the correct grid and style config
        in_container = False
        for line in self.lines:
            if '_container: ""' in line:
                in_container = True
                container_lines = []
            elif in_container:
                container_lines.append(line.strip())
                if line.strip() == "}":
                    in_container = False
                    assert "grid-columns: 1" in container_lines
                    assert "grid-gap: 5" in container_lines
                    assert "stroke-width: 0" in container_lines
                    assert "fill: transparent" in container_lines

    def test_all_nodes_have_width(self, all_functions):
        width_lines = re.findall(r"f\d+\.width: 250", self.d2)
        assert len(width_lines) == len(all_functions)

    def test_root_with_all_leaf_children_uses_container(self, example_data):
        """When --root selects a node whose children are all leaves, they should
        render in a grid container — not as individual nodes with separate arrows.
        """
        subtree = find_subtree(example_data, "Power Management")
        d2 = yaml_to_d2(subtree)
        assert "root_container" in d2
        assert "grid-columns: 1" in d2
        assert "grid-gap: 5" in d2
        assert "Generate Power" in d2
        assert "Store Power" in d2
        assert "Distribute Power" in d2


# --- Markdown structural tests ---


class TestMarkdownOutput:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data
        self.md = yaml_to_markdown(example_data)
        self.lines = self.md.splitlines()

    def test_header(self):
        assert self.lines[0] == "# Example System"

    def test_table_columns(self):
        assert "| Parent | Function | Description |" in self.md

    def test_root_row_present(self):
        assert "|  | Example System |" in self.md

    def test_all_functions_present(self, all_functions):
        for parent_name, func in all_functions:
            name = func["name"]
            desc = func.get("description", "")
            expected = f"| {parent_name} | {name} | {desc} |"
            assert expected in self.md, (
                f"Expected row not found: {expected}"
            )

    def test_row_count(self, all_functions):
        # Data rows = total lines - header (1) - blank line (1) - column header (1) - separator (1)
        data_rows = [l for l in self.lines if l.startswith("| ") and "---" not in l and "Parent" not in l]
        assert len(data_rows) == len(all_functions) + 1  # +1 for root row


# --- CSV structural tests ---


class TestCsvOutput:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data
        self.csv_str = yaml_to_csv(example_data)
        reader = csv.reader(io.StringIO(self.csv_str))
        self.rows = list(reader)

    def test_header(self):
        assert self.rows[0] == ["Parent", "Function", "Description"]

    def test_root_row_present(self):
        assert self.rows[1][0] == ""
        assert self.rows[1][1] == "Example System"

    def test_all_functions_present(self, all_functions):
        data_rows = self.rows[1:]
        for parent_name, func in all_functions:
            name = func["name"]
            desc = func.get("description", "")
            assert [parent_name, name, desc] in data_rows, (
                f"Expected CSV row not found: {[parent_name, name, desc]}"
            )

    def test_row_count(self, all_functions):
        data_rows = self.rows[1:]
        assert len(data_rows) == len(all_functions) + 1  # +1 for root row


# --- SVG tests (require d2) ---


@pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
class TestSvgOutput:
    @pytest.fixture(autouse=True)
    def setup(self, generated_output):
        self.svg_path = generated_output / "functional_decomposition.svg"
        self.tree = ET.parse(self.svg_path)

    def test_valid_xml(self):
        # Parsing already succeeded in setup
        assert self.tree is not None

    def test_svg_root_element(self):
        assert "svg" in self.tree.getroot().tag

    def test_svg_contains_function_names(self, all_functions):
        """Verify function names appear as text elements in the SVG.

        d2 renders node labels as uppercase <text> elements using an embedded font.
        """
        svg_texts = {elem.text.strip() for elem in self.tree.iter("{http://www.w3.org/2000/svg}text")
                     if elem.text and elem.text.strip()}
        for _, func in all_functions:
            expected = func["name"].upper()
            assert expected in svg_texts, (
                f"Function '{func['name']}' (as '{expected}') not found in SVG text elements"
            )


# --- PNG tests (require d2) ---


@pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
class TestPngOutput:
    @pytest.fixture(autouse=True)
    def setup(self, generated_output):
        self.png_path = generated_output / "functional_decomposition.png"

    def test_png_magic_bytes(self):
        with open(self.png_path, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG"

    def test_file_size_nontrivial(self):
        assert self.png_path.stat().st_size > 1024


# --- Product diagram CLI tests ---


class TestProductDiagramCLI:
    def test_product_diagram_subcommand(self, tmp_path):
        cli_path = Path(sys.executable).parent / "systems-engineering"
        result = subprocess.run(
            [str(cli_path), "product", "diagram",
             str(PRODUCT_EXAMPLE_YAML), "-o", str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert (tmp_path / "example_products.d2").exists()
        assert (tmp_path / "example_products.md").exists()
        assert (tmp_path / "example_products.csv").exists()

    def test_product_diagram_nonexistent_input(self, tmp_path):
        cli_path = Path(sys.executable).parent / "systems-engineering"
        result = subprocess.run(
            [str(cli_path), "product", "diagram",
             str(tmp_path / "nonexistent.yaml"), "-o", str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_product_diagram_directory_input(self, tmp_path):
        cli_path = Path(sys.executable).parent / "systems-engineering"
        pb_dir = REPO_ROOT / "product_breakdown"
        result = subprocess.run(
            [str(cli_path), "product", "diagram",
             str(pb_dir), "-o", str(tmp_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert (tmp_path / "example_products.d2").exists()


# --- Golden file tests ---


class TestGoldenFiles:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data

    def test_d2_matches_golden(self):
        generated = yaml_to_d2(self.data)
        golden = (GOLDEN_DIR / "functional_decomposition.d2").read_text()
        assert generated == golden, "D2 output does not match golden file"

    def test_markdown_matches_golden(self):
        generated = yaml_to_markdown(self.data)
        golden = (GOLDEN_DIR / "functional_decomposition.md").read_text()
        assert generated == golden, "Markdown output does not match golden file"

    def test_csv_matches_golden(self):
        generated = yaml_to_csv(self.data)
        golden = (GOLDEN_DIR / "functional_decomposition.csv").open(newline="").read()
        assert generated == golden, "CSV output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_svg_matches_golden(self, generated_output):
        generated = (generated_output / "functional_decomposition.svg").read_bytes()
        golden = (GOLDEN_DIR / "functional_decomposition.svg").read_bytes()
        assert generated == golden, "SVG output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_png_matches_golden(self, generated_output):
        generated = (generated_output / "functional_decomposition.png").read_bytes()
        golden = (GOLDEN_DIR / "functional_decomposition.png").read_bytes()
        assert generated == golden, "PNG output does not match golden file"


# --- Product golden file tests ---


class TestProductGoldenFiles:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_yaml(PRODUCT_EXAMPLE_YAML)

    def test_d2_matches_golden(self):
        generated = product_yaml_to_d2(self.data)
        golden = (GOLDEN_DIR / "example_products.d2").read_text()
        assert generated == golden, "Product D2 output does not match golden file"

    def test_markdown_matches_golden(self):
        generated = product_yaml_to_markdown(self.data)
        golden = (GOLDEN_DIR / "example_products.md").read_text()
        assert generated == golden, "Product markdown output does not match golden file"

    def test_csv_matches_golden(self):
        generated = product_yaml_to_csv(self.data)
        golden = (GOLDEN_DIR / "example_products.csv").open(newline="").read()
        assert generated == golden, "Product CSV output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_svg_matches_golden(self, generated_product_output):
        generated = (generated_product_output / "example_products.svg").read_bytes()
        golden = (GOLDEN_DIR / "example_products.svg").read_bytes()
        assert generated == golden, "Product SVG output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_png_matches_golden(self, generated_product_output):
        generated = (generated_product_output / "example_products.png").read_bytes()
        golden = (GOLDEN_DIR / "example_products.png").read_bytes()
        assert generated == golden, "Product PNG output does not match golden file"


# --- find_subtree tests ---


class TestFindSubtree:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data

    def test_find_root(self):
        result = find_subtree(self.data, "Example System")
        assert result is not None
        assert result["name"] == "Example System"

    def test_find_direct_child(self):
        result = find_subtree(self.data, "Power Management")
        assert result is not None
        assert result["name"] == "Power Management"
        assert len(result.get("functions", [])) == 3

    def test_find_grandchild(self):
        result = find_subtree(self.data, "Store Power")
        assert result is not None
        assert result["name"] == "Store Power"

    def test_not_found(self):
        result = find_subtree(self.data, "Nonexistent")
        assert result is None

    def test_process_file_nonexistent_root_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            process_file(EXAMPLE_YAML, tmp_path, root="Nonexistent")


# --- filter_tree tests ---


class TestFilterTree:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data

    def _names(self, data: dict) -> set[str]:
        """Collect all function names in a tree."""
        names = {data["name"]}
        for child in data.get("functions", []):
            names |= self._names(child)
        return names

    def test_filter_leaf_includes_ancestors(self):
        result = filter_tree(self.data, ["Store Power"], include_descendants=False)
        names = self._names(result)
        assert "Example System" in names
        assert "Power Management" in names
        assert "Store Power" in names
        assert "Thermal Management" not in names
        assert "Data Processing" not in names

    def test_filter_multiple_patterns(self):
        result = filter_tree(self.data, ["Store Power", "Cool"], include_descendants=False)
        names = self._names(result)
        assert "Store Power" in names
        assert "Cool Components" in names
        assert "Power Management" in names
        assert "Thermal Management" in names
        assert "Data Processing" not in names

    def test_filter_regex_substring(self):
        result = filter_tree(self.data, ["Power"], include_descendants=False)
        names = self._names(result)
        assert "Power Management" in names
        assert "Generate Power" in names
        assert "Store Power" in names
        assert "Distribute Power" in names

    def test_filter_regex_anchored(self):
        result = filter_tree(self.data, ["^Power Management$"], include_descendants=False)
        names = self._names(result)
        assert "Power Management" in names
        assert "Example System" in names
        # Children not included since they don't match and descendants not included
        assert "Generate Power" not in names

    def test_filter_with_include_descendants(self):
        result = filter_tree(self.data, ["^Power Management$"], include_descendants=True)
        names = self._names(result)
        assert "Power Management" in names
        assert "Generate Power" in names
        assert "Store Power" in names
        assert "Distribute Power" in names
        assert "Thermal Management" not in names

    def test_filter_no_match_returns_root_only(self):
        result = filter_tree(self.data, ["Nonexistent"], include_descendants=False)
        assert result["name"] == "Example System"
        assert "functions" not in result

    def test_filter_preserves_node_properties(self):
        result = filter_tree(self.data, ["Store Power"], include_descendants=False)
        # Find Store Power in the result and check recently_updated is preserved
        pm = result["functions"][0]
        assert pm["name"] == "Power Management"
        store = pm["functions"][0]
        assert store["name"] == "Store Power"
        assert store.get("recently_updated") is True

    def test_filter_case_insensitive(self):
        result = filter_tree(self.data, ["power"], include_descendants=False)
        names = self._names(result)
        assert "Power Management" in names
        assert "Generate Power" in names
        assert "Store Power" in names
        assert "Distribute Power" in names


# --- Product verify tests ---


def _make_verify_args(fd_path, pb_path):
    """Create a namespace mimicking argparse output for product verify."""
    import argparse
    return argparse.Namespace(
        functional_decomposition=fd_path,
        product_breakdown=pb_path,
    )


class TestProductVerify:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.fd_data = example_data
        self.pb_data = load_yaml(PRODUCT_EXAMPLE_YAML)

    def test_collect_leaf_function_names(self):
        names = collect_leaf_function_names(self.fd_data)
        expected = {
            "Generate Power", "Store Power", "Distribute Power",
            "Detect Temperature", "Cool Components",
            "Collect Data", "Transform Data", "Store Data",
        }
        assert names == expected

    def test_collect_allocated_functions(self):
        allocated = collect_allocated_functions(self.pb_data)
        expected = {
            "Generate Power", "Store Power", "Distribute Power",
            "Detect Temperature", "Cool Components",
            "Collect Data", "Transform Data", "Store Data",
        }
        assert allocated == expected

    def test_all_allocated(self, capsys):
        """Example files should have all leaf functions allocated."""
        args = _make_verify_args(EXAMPLE_YAML, PRODUCT_EXAMPLE_YAML)
        run_product_verify_command(args)
        captured = capsys.readouterr()
        assert "\u2705 All functions allocated." in captured.out

    def test_some_unallocated(self, capsys, tmp_path):
        """A product breakdown missing allocations should warn with the missing function names."""
        incomplete_pb = {
            "name": "Incomplete System",
            "components": [{
                "name": "Partial",
                "configuration_items": [{
                    "name": "Only Power",
                    "functions": ["Generate Power"],
                }],
            }],
        }
        pb_path = tmp_path / "incomplete.yaml"
        pb_path.write_text(yaml.dump(incomplete_pb))

        args = _make_verify_args(EXAMPLE_YAML, pb_path)
        with pytest.raises(SystemExit) as exc_info:
            run_product_verify_command(args)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "\u26a0\ufe0f Some functions unallocated:" in captured.out
        assert "Store Power" in captured.out
        assert "Cool Components" in captured.out

    def test_unallocated_are_sorted(self, capsys, tmp_path):
        """Unallocated function names should be listed in alphabetical order."""
        empty_pb = {"name": "Empty", "components": []}
        pb_path = tmp_path / "empty.yaml"
        pb_path.write_text(yaml.dump(empty_pb))

        args = _make_verify_args(EXAMPLE_YAML, pb_path)
        with pytest.raises(SystemExit):
            run_product_verify_command(args)

        captured = capsys.readouterr()
        # Extract the list after the colon
        msg = captured.out.strip()
        names_str = msg.split(": ", 1)[1]
        names = [n.strip() for n in names_str.split(",")]
        assert names == sorted(names)

    def test_extra_allocated_warns(self, capsys, tmp_path):
        """CIs referencing functions not in the FD should warn but still pass."""
        pb_with_extra = {
            "name": "System",
            "components": [{
                "name": "Component",
                "configuration_items": [{
                    "name": "CI",
                    "functions": [
                        "Generate Power", "Store Power", "Distribute Power",
                        "Detect Temperature", "Cool Components",
                        "Collect Data", "Transform Data", "Store Data",
                        "Nonexistent Function",
                    ],
                }],
            }],
        }
        pb_path = tmp_path / "extra.yaml"
        pb_path.write_text(yaml.dump(pb_with_extra))

        args = _make_verify_args(EXAMPLE_YAML, pb_path)
        run_product_verify_command(args)
        captured = capsys.readouterr()
        assert "\u2705 All functions allocated." in captured.out
        assert "Nonexistent Function" in captured.err
        assert "not found in functional decomposition" in captured.err

    def test_nested_components(self):
        """collect_allocated_functions should recurse through nested component hierarchies."""
        nested_pb = {
            "name": "System",
            "components": [{
                "name": "Top Level",
                "components": [{
                    "name": "Mid Level",
                    "components": [{
                        "name": "Leaf",
                        "configuration_items": [{
                            "name": "Deep CI",
                            "functions": ["Deeply Nested Function"],
                        }],
                    }],
                }],
            }],
        }
        allocated = collect_allocated_functions(nested_pb)
        assert allocated == {"Deeply Nested Function"}

    def test_empty_fd_exits(self, tmp_path):
        """An FD with no leaf functions should exit with an error, not vacuously pass."""
        empty_fd = {"name": "Empty System"}
        fd_path = tmp_path / "empty_fd.yaml"
        fd_path.write_text(yaml.dump(empty_fd))

        args = _make_verify_args(fd_path, PRODUCT_EXAMPLE_YAML)
        with pytest.raises(SystemExit) as exc_info:
            run_product_verify_command(args)
        assert exc_info.value.code == 1

    def test_nonexistent_fd_exits(self, tmp_path):
        pb_path = tmp_path / "exists.yaml"
        pb_path.write_text(yaml.dump({"name": "System"}))
        args = _make_verify_args(tmp_path / "nonexistent.yaml", pb_path)
        with pytest.raises(SystemExit):
            run_product_verify_command(args)

    def test_nonexistent_pb_exits(self, tmp_path):
        args = _make_verify_args(EXAMPLE_YAML, tmp_path / "nonexistent.yaml")
        with pytest.raises(SystemExit):
            run_product_verify_command(args)


# --- version flag tests ---


class TestVersion:
    def test_version_flag(self):
        cli_path = Path(sys.executable).parent / "systems-engineering"
        result = subprocess.run(
            [str(cli_path), "--version"],
            capture_output=True,
            text=True,
        )
        expected_version = importlib.metadata.version("systems-engineering-diagrams")
        assert result.returncode == 0
        assert expected_version in result.stdout


class TestDirectoryDefaults:
    def test_function_command_directory_without_default_file_exits(self, tmp_path):
        """When given a directory without functional_decomposition.yaml, should exit with error."""
        (tmp_path / "empty_dir").mkdir()
        args = argparse.Namespace(
            input=tmp_path / "empty_dir",
            output=tmp_path / "output",
            root=None,
            filter=None,
            include_descendants=False,
        )
        with pytest.raises(SystemExit):
            run_function_command(args)

    def test_function_command_directory_resolves_default_file(self, tmp_path):
        """When given a directory containing functional_decomposition.yaml, run_function_command processes it."""
        (tmp_path / "input").mkdir()
        shutil.copy(EXAMPLE_YAML, tmp_path / "input" / "functional_decomposition.yaml")
        output_dir = tmp_path / "output"
        args = argparse.Namespace(
            input=tmp_path / "input",
            output=output_dir,
            root=None,
            filter=None,
            include_descendants=False,
        )
        run_function_command(args)
        assert (output_dir / "functional_decomposition.d2").exists()

    def test_product_verify_directory_resolves_default_files(self, tmp_path, capsys):
        """When given directories, product verify should resolve default filenames."""
        shutil.copy(EXAMPLE_YAML, tmp_path / "functional_decomposition.yaml")
        shutil.copy(PRODUCT_EXAMPLE_YAML, tmp_path / "product_breakdown.yaml")
        args = argparse.Namespace(
            functional_decomposition=tmp_path,
            product_breakdown=tmp_path,
        )
        run_product_verify_command(args)
        captured = capsys.readouterr()
        assert "\u2705 All functions allocated." in captured.out


# --- Product D2 output tests ---


class TestProductD2Output:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_yaml(PRODUCT_EXAMPLE_YAML)
        self.d2 = product_yaml_to_d2(self.data)
        self.lines = self.d2.splitlines()

    def test_config_block_present(self):
        assert "layout-engine: elk" in self.d2
        assert "theme-id: 300" in self.d2

    def test_direction_down(self):
        assert "direction: down" in self.d2

    def test_root_node(self):
        assert "root: Example System" in self.d2
        assert "root.width: 250" in self.d2

    def test_all_component_names_present(self):
        for name in ["Power Subsystem", "Thermal Subsystem", "Data Subsystem"]:
            assert any(name in line for line in self.lines), (
                f"Component '{name}' not found in d2 output"
            )

    def test_component_arrows_from_root(self):
        assert "root -> p0" in self.d2

    def test_all_ci_names_present(self):
        ci_names = [
            "Solar Panel Assembly", "Battery Pack", "Power Distribution Unit",
            "Temperature Sensor Array", "Cooling System",
            "Data Acquisition Module", "Processing Unit", "Storage Module",
        ]
        for name in ci_names:
            assert any(name in line for line in self.lines), (
                f"CI '{name}' not found in d2 output"
            )

    def test_ci_nodes_have_circle_shape(self):
        # Every CI node should have shape: circle
        circle_lines = [l for l in self.lines if "shape: circle" in l]
        assert len(circle_lines) == 8  # 8 CIs

    def test_ci_container_grid_config(self):
        in_container = False
        container_count = 0
        for line in self.lines:
            if '_container: ""' in line:
                in_container = True
                container_lines = []
            elif in_container:
                container_lines.append(line.strip())
                if line.strip() == "}":
                    in_container = False
                    container_count += 1
                    assert "grid-columns: 1" in container_lines
                    assert "grid-gap: 5" in container_lines
                    assert "stroke-width: 0" in container_lines
                    assert "fill: transparent" in container_lines
        assert container_count == 3

    def test_node_count(self):
        # 3 components + 8 CIs = 11 nodes with p prefix
        node_defs = re.findall(r"^[ ]*p(\d+): .+", self.d2, re.MULTILINE)
        assert len(node_defs) == 11

    def test_all_nodes_have_width(self):
        width_lines = re.findall(r"p\d+\.width: 250", self.d2)
        assert len(width_lines) == 11

    def test_nested_components_support(self):
        """Components with nested sub-components should recurse correctly."""
        nested_data = {
            "name": "Nested System",
            "components": [{
                "name": "Outer",
                "components": [{
                    "name": "Inner",
                    "configuration_items": [{
                        "name": "Leaf CI",
                        "functions": ["Some Function"],
                    }],
                }],
            }],
        }
        d2 = product_yaml_to_d2(nested_data)
        assert "Outer" in d2
        assert "Inner" in d2
        assert "Leaf CI" in d2

    def test_no_function_names_in_output(self):
        """Function names allocated to CIs should NOT appear in the d2 output."""
        function_names = [
            "Generate Power", "Store Power", "Distribute Power",
            "Detect Temperature", "Cool Components",
            "Collect Data", "Transform Data", "Store Data",
        ]
        for name in function_names:
            assert not any(name in line for line in self.lines), (
                f"Function name '{name}' should not appear in product d2 output"
            )


# --- Product Markdown structural tests ---


class TestProductMarkdownOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_yaml(PRODUCT_EXAMPLE_YAML)
        self.md = product_yaml_to_markdown(self.data)
        self.lines = self.md.splitlines()

    def test_header(self):
        assert self.lines[0] == "# Example System"

    def test_table_columns(self):
        assert "| Parent | Name | Type | Description | Functions |" in self.md

    def test_root_row_present(self):
        assert "|  | Example System | System |" in self.md

    def test_component_rows_have_type(self):
        assert "| Example System | Power Subsystem | Component |" in self.md
        assert "| Example System | Thermal Subsystem | Component |" in self.md
        assert "| Example System | Data Subsystem | Component |" in self.md

    def test_ci_rows_have_type(self):
        assert "| Power Subsystem | Solar Panel Assembly | Configuration Item |" in self.md
        assert "| Thermal Subsystem | Temperature Sensor Array | Configuration Item |" in self.md

    def test_ci_rows_include_functions(self):
        assert "Generate Power" in self.md
        assert "Store Power" in self.md

    def test_row_count(self):
        # Data rows = total lines - header (1) - blank line (1) - column header (1) - separator (1)
        data_rows = [l for l in self.lines if l.startswith("| ") and "---" not in l and "Parent" not in l]
        assert len(data_rows) == 12  # 1 root + 3 components + 8 CIs


# --- Product CSV structural tests ---


class TestProductCsvOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_yaml(PRODUCT_EXAMPLE_YAML)
        self.csv_str = product_yaml_to_csv(self.data)
        reader = csv.reader(io.StringIO(self.csv_str))
        self.rows = list(reader)

    def test_header(self):
        assert self.rows[0] == ["Parent", "Name", "Type", "Description", "Functions"]

    def test_root_row_present(self):
        assert self.rows[1][0] == ""
        assert self.rows[1][1] == "Example System"
        assert self.rows[1][2] == "System"

    def test_component_rows_have_type(self):
        component_rows = [r for r in self.rows[1:] if r[2] == "Component"]
        names = {r[1] for r in component_rows}
        assert names == {"Power Subsystem", "Thermal Subsystem", "Data Subsystem"}

    def test_ci_rows_have_type(self):
        ci_rows = [r for r in self.rows[1:] if r[2] == "Configuration Item"]
        assert len(ci_rows) == 8

    def test_ci_rows_include_functions(self):
        ci_rows = [r for r in self.rows[1:] if r[2] == "Configuration Item"]
        solar_row = [r for r in ci_rows if r[1] == "Solar Panel Assembly"][0]
        assert "Generate Power" in solar_row[4]

    def test_row_count(self):
        data_rows = self.rows[1:]
        assert len(data_rows) == 12  # 1 root + 3 components + 8 CIs


# --- process_product_file tests ---


@pytest.fixture(scope="module")
def generated_product_output(tmp_path_factory):
    """Generate all product output files once and share across tests."""
    tmp_path = tmp_path_factory.mktemp("product_output")
    process_product_file(PRODUCT_EXAMPLE_YAML, tmp_path)
    return tmp_path


class TestProcessProductFile:
    def test_d2_file_exists(self, generated_product_output):
        assert (generated_product_output / "example_products.d2").exists()

    def test_md_file_exists(self, generated_product_output):
        assert (generated_product_output / "example_products.md").exists()

    def test_csv_file_exists(self, generated_product_output):
        assert (generated_product_output / "example_products.csv").exists()

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_svg_file_exists(self, generated_product_output):
        assert (generated_product_output / "example_products.svg").exists()

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_png_file_exists(self, generated_product_output):
        assert (generated_product_output / "example_products.png").exists()


# --- Product SVG tests (require d2) ---


@pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
class TestProductSvgOutput:
    @pytest.fixture(autouse=True)
    def setup(self, generated_product_output):
        self.svg_path = generated_product_output / "example_products.svg"
        self.tree = ET.parse(self.svg_path)

    def test_valid_xml(self):
        assert self.tree is not None

    def test_svg_root_element(self):
        assert "svg" in self.tree.getroot().tag

    def test_svg_contains_component_and_ci_names(self):
        """Verify component and CI names appear as text elements in the SVG."""
        svg_texts = {elem.text.strip() for elem in self.tree.iter("{http://www.w3.org/2000/svg}text")
                     if elem.text and elem.text.strip()}
        for name in ["POWER SUBSYSTEM", "THERMAL SUBSYSTEM", "DATA SUBSYSTEM",
                      "SOLAR PANEL ASSEMBLY", "BATTERY PACK"]:
            assert name in svg_texts, (
                f"'{name}' not found in SVG text elements"
            )


# --- Product PNG tests (require d2) ---


@pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
class TestProductPngOutput:
    @pytest.fixture(autouse=True)
    def setup(self, generated_product_output):
        self.png_path = generated_product_output / "example_products.png"

    def test_png_magic_bytes(self):
        with open(self.png_path, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG"

    def test_file_size_nontrivial(self):
        assert self.png_path.stat().st_size > 1024
