"""Semantic tests for the systems-engineering CLI output."""

import csv
import io
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from systems_engineering.cli import (
    filter_tree,
    find_subtree,
    load_yaml,
    yaml_to_csv,
    yaml_to_d2,
    yaml_to_markdown,
    process_file,
)

REPO_ROOT = Path(__file__).parent.parent
EXAMPLE_YAML = REPO_ROOT / "functional_decomposition" / "example.yaml"
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


@pytest.fixture
def generated_output(example_data, tmp_path):
    """Generate all output files and return the output directory."""
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
        # Count lines that define nodes (pattern: "fN: Name")
        node_lines = [
            line.strip()
            for line in self.lines
            if line.strip().startswith("f") and ": " in line.strip()
            and not line.strip().startswith("f") and "." in line.strip().split(":")[0]
            is None  # exclude property lines like f0.width
        ]
        # Simpler: count unique fN identifiers used as node definitions
        import re
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
        import re
        width_lines = re.findall(r"f\d+\.width: 250", self.d2)
        assert len(width_lines) == len(all_functions)


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
        self.svg_path = generated_output / "example_functions.svg"

    def test_valid_xml(self):
        ET.parse(self.svg_path)

    def test_svg_root_element(self):
        tree = ET.parse(self.svg_path)
        root = tree.getroot()
        assert "svg" in root.tag

    def test_d2_source_contains_function_names(self, all_functions, generated_output):
        """Verify the d2 source used to render the SVG contains all function names.

        d2 embeds text as base64 font glyphs in SVG, so we check the d2 source instead.
        """
        d2_text = (generated_output / "example_functions.d2").read_text()
        for _, func in all_functions:
            assert func["name"] in d2_text, (
                f"Function '{func['name']}' not found in d2 source"
            )


# --- PNG tests (require d2) ---


@pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
class TestPngOutput:
    @pytest.fixture(autouse=True)
    def setup(self, generated_output):
        self.png_path = generated_output / "example_functions.png"

    def test_png_magic_bytes(self):
        with open(self.png_path, "rb") as f:
            header = f.read(8)
        assert header[:4] == b"\x89PNG"

    def test_file_size_nontrivial(self):
        assert self.png_path.stat().st_size > 1024


# --- Golden file tests ---


class TestGoldenFiles:
    @pytest.fixture(autouse=True)
    def setup(self, example_data):
        self.data = example_data

    def test_d2_matches_golden(self):
        generated = yaml_to_d2(self.data)
        golden = (GOLDEN_DIR / "example_functions.d2").read_text()
        assert generated == golden, "D2 output does not match golden file"

    def test_markdown_matches_golden(self):
        generated = yaml_to_markdown(self.data)
        golden = (GOLDEN_DIR / "example_functions.md").read_text()
        assert generated == golden, "Markdown output does not match golden file"

    def test_csv_matches_golden(self):
        generated = yaml_to_csv(self.data)
        golden = (GOLDEN_DIR / "example_functions.csv").open(newline="").read()
        assert generated == golden, "CSV output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_svg_matches_golden(self, generated_output):
        generated = (generated_output / "example_functions.svg").read_bytes()
        golden = (GOLDEN_DIR / "example_functions.svg").read_bytes()
        assert generated == golden, "SVG output does not match golden file"

    @pytest.mark.skipif(not HAS_D2, reason="d2 not installed")
    def test_png_matches_golden(self, generated_output):
        generated = (generated_output / "example_functions.png").read_bytes()
        golden = (GOLDEN_DIR / "example_functions.png").read_bytes()
        assert generated == golden, "PNG output does not match golden file"


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


# --- D2 leaf container tests ---


class TestD2LeafContainer:
    def test_root_children_all_leaves_use_container(self, example_data):
        subtree = find_subtree(example_data, "Power Management")
        d2 = yaml_to_d2(subtree)
        assert "root_container" in d2
        assert "grid-columns: 1" in d2
        assert "grid-gap: 5" in d2
        assert "Generate Power" in d2
        assert "Store Power" in d2
        assert "Distribute Power" in d2
