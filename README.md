# SGB Data Validator

> **Data Validation and Management Suite for Omeka S**

The **sgb-data-validator** is a comprehensive Python toolkit for validating and managing metadata in [Omeka S](https://omeka.org/s/) digital collections. Built for the [Stadt.Geschichte.Basel](https://www.stadtgeschichtebasel.ch/) project, it ensures cultural heritage data quality through schema validation, controlled vocabularies, and automated data transformations.

[![GitHub issues](https://img.shields.io/github/issues/Stadt-Geschichte-Basel/sgb-data-validator.svg)](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues)
[![GitHub stars](https://img.shields.io/github/stars/Stadt-Geschichte-Basel/sgb-data-validator.svg)](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/stargazers)
[![Code license](https://img.shields.io/github/license/Stadt-Geschichte-Basel/sgb-data-validator.svg)](LICENSE-AGPL.md)
[![Data license](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-blue.svg)](LICENSE-CCBY.md)

<!-- [![DOI](https://zenodo.org/badge/1067376900.svg)](https://zenodo.org/badge/latestdoi/ZENODO_RECORD) -->

## Features

- ✅ **Schema validation** with Pydantic models and Dublin Core metadata
- 📚 **Controlled vocabularies** (Era, MIME types, Licenses, ICONCLASS notation)
- 🌍 **ISO 639-1 language validation** (all 184 two-letter codes)
- 🔗 **URI validation** with reachability checks and redirect detection
- 📊 **CSV reports** with direct edit links to Omeka S admin
- 📈 **Data profiling** with interactive HTML reports
- 🔄 **Data transformation** (Unicode NFC, HTML entities, whitespace normalization)
- 💾 **Offline workflow** for batch editing
- 🔒 **Privacy management** (automatic flag propagation for placeholder images)
- 🚀 **Fast and efficient** with async processing

## Documentation

**📖 [Full Documentation](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/)**

- [Quick Start Guide](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/#quick-start)
- [Validation & CSV Reports](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/validation-reports.html)
- [Data Transformation](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/#data-transformation)
- [Offline Workflow](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/#offline-workflow)
- [Python API Examples](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/#python-api)

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
pip install uv
uv sync
```

## Configuration

Create a `.env` file:

```bash
cp example.env .env
```

Edit with your Omeka S settings:

```env
OMEKA_URL=https://omeka.unibe.ch
KEY_IDENTITY=YOUR_KEY_IDENTITY
KEY_CREDENTIAL=YOUR_KEY_CREDENTIAL
ITEM_SET_ID=10780
```

> Command-line parameters override `.env` values.

## Usage

### Basic Validation

```bash
# Validate using .env settings
uv run python validate.py

# With specific options
uv run python validate.py --item-set-id 12345 --output report.txt

# Enable URI checking and profiling
uv run python validate.py --check-uris --profile

# Export CSV reports
uv run python validate.py --export-csv

# Get help
uv run python validate.py --help
```

### Offline Workflow

```bash
# 1. Download
uv run python workflow.py download --item-set-id 10780

# 2. Transform
uv run python workflow.py transform data/raw_itemset_10780_*/

# 3. Edit JSON files offline with any text editor

# 4. Validate
uv run python workflow.py validate data/transformed_itemset_10780_*/

# 5. Dry run
uv run python workflow.py upload data/transformed_itemset_10780_*/

# 6. Upload for real
uv run python workflow.py upload data/transformed_itemset_10780_*/ --no-dry-run
```

## Development

Run linter and formatter:

```bash
uv run ruff check .
uv run ruff format .
```

Run tests (96 tests: 72 unit + 24 integration):

```bash
uv run pytest
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
```

## Repository Structure

Following [The Turing Way](https://the-turing-way.netlify.app/project-design/project-repo/project-repo-advanced.html):

```text
sgb-data-validator/
├── src/                    # Source modules
│   ├── models.py          # Pydantic validation models
│   ├── api.py             # Omeka S API client
│   ├── transformations.py # Data transformation utilities
│   ├── vocabularies.py    # Controlled vocabulary loader
│   └── iconclass.py       # ICONCLASS notation parser
├── test/                   # Test suite (96 tests)
├── examples/               # Usage examples
├── data/raw/              # Controlled vocabularies
├── validate.py            # CLI validation script
└── workflow.py            # CLI offline workflow script
```

## Contributing

Contributions are welcome! See:

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community standards
- [SECURITY.md](SECURITY.md) - Security policy
- [CHANGELOG.md](CHANGELOG.md) - Version history

## License

- **Code**: [AGPL-3.0](LICENSE-AGPL.md)
- **Data**: [CC BY 4.0](LICENSE-CCBY.md)

## Citation

See [CITATION.cff](CITATION.cff) for citation metadata.

## Support

- [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues)
- [GitHub Discussions](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/discussions)

---

**Maintained by [@maehr](https://github.com/maehr)** | **[Stadt.Geschichte.Basel](https://www.stadtgeschichtebasel.ch/)**
