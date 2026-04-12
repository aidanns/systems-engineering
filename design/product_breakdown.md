# Systems Engineering CLI

| Parent | Name | Type | Description | Functions |
|--------|------|------|-------------|-----------|
|  | Systems Engineering CLI | System | CLI tool for generating systems engineering artefacts from YAML definitions. |  |
| Systems Engineering CLI | Application Software | Component | Python application and its library dependencies. |  |
| Application Software | systems-engineering-model | Configuration Item | Python module providing dataclasses and tree operations for the systems engineering data model. | Load YAML, Parse Functional Decomposition, Parse Product Breakdown, Find Subtree, Filter Tree, Verify Function Allocation |
| Application Software | systems-engineering-render | Configuration Item | Python module providing rendering functions for d2 diagrams, markdown, and CSV output. | Generate Functional D2, Generate Functional Markdown, Generate Functional CSV, Generate Product D2, Generate Product Markdown, Generate Product CSV |
| Application Software | systems-engineering-cli | Configuration Item | Python module providing CLI argument parsing, file processing orchestration, and test coverage verification. | Argument Parsing, File Processing, Verify Function Test Coverage |
| Application Software | PyYAML | Configuration Item | Python library for parsing and emitting YAML. |  |
| Systems Engineering CLI | Rendering Engine | Component | External tool for rendering d2 diagram definitions to visual formats. |  |
| Rendering Engine | d2 | Configuration Item | Diagram scripting language tool that renders .d2 files to SVG and PNG. | Render SVG, Render PNG |
| Systems Engineering CLI | Development Tools | Component | Tools used for testing and validation during development. |  |
| Development Tools | pytest | Configuration Item | Python test framework for running the test suite. |  |
| Development Tools | yq | Configuration Item | Command-line YAML processor used in test scripts for validation. |  |
