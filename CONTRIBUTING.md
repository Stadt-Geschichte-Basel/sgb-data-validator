# Contributing

Thank you for your interest in contributing to the sgb-data-validator project! We welcome contributions from the community.

Please note we have a [code of conduct](CODE_OF_CONDUCT.md). Please follow it in all your interactions with the project.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for dependency management
- Git for version control

### Setting Up Your Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/sgb-data-validator.git
   cd sgb-data-validator
   ```

3. Install dependencies using uv:

   ```bash
   pip install uv
   uv sync
   ```

4. Set up your environment variables:

   ```bash
   cp example.env .env
   # Edit .env with your configuration
   ```

5. Verify your setup by running tests:

   ```bash
   uv run python -m pytest test/
   ```

## Development Workflow

### Before Starting Work

1. **Check for existing issues**: Search the [issue tracker](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues) to see if someone is already working on it
2. **Create or comment on an issue**: Discuss your proposed changes before starting work
3. **Create a feature branch**: Use descriptive branch names like `feature/add-validation` or `fix/iconclass-bug`

### Making Changes

1. **Write clear, focused commits**: Each commit should represent a single logical change
2. **Follow the code style**: 
   - Run `uv run ruff check .` to check for issues
   - Run `uv run ruff format .` to format code
3. **Add tests**: Ensure your changes are covered by tests
4. **Update documentation**: Update README.md, docstrings, and other docs as needed

### Code Style Guidelines

- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Write descriptive docstrings for modules, classes, and functions
- Keep functions focused and modular
- Use meaningful variable and function names

### Testing

Run the test suite before submitting:

```bash
# Run all tests
uv run python -m pytest test/ -v

# Run specific test file
uv run python test/test_validation.py

# Run with coverage
uv run python -m pytest test/ --cov=src --cov-report=html
```

### Running the Linter and Formatter

```bash
# Check for style issues
uv run ruff check .

# Auto-format code
uv run ruff format .

# Check and fix in one command
uv run ruff check . --fix
```

## Pull Request Process

1. **Update your branch**: Ensure your branch is up to date with the main branch:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests and linters**: Verify everything passes:

   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run python -m pytest test/
   ```

3. **Update documentation**: 
   - Update README.md if you've changed functionality
   - Update CHANGELOG.md with a brief description of your changes
   - Update docstrings and code comments

4. **Create a pull request**:
   - Write a clear title summarizing the change
   - Provide a detailed description of what changed and why
   - Reference any related issues (e.g., "Fixes #123")
   - Include examples or screenshots if applicable

5. **Respond to feedback**: Be responsive to review comments and make requested changes promptly

6. **Versioning**: We use [SemVer](http://semver.org/) for versioning. Maintainers will handle version bumps during the release process.

## Repository Structure

Understanding the repository layout:

```
sgb-data-validator/
├── src/                    # Source code
│   ├── models.py          # Pydantic data models
│   ├── vocabularies.py    # Controlled vocabulary loader
│   ├── iconclass.py       # Iconclass notation validator
│   ├── profiling.py       # Data profiling utilities
│   └── api.py             # API client
├── test/                   # Test suite
│   ├── test_validation.py # Validation tests
│   ├── test_iconclass.py  # Iconclass tests
│   └── ...                # Other test files
├── data/                   # Data files
│   └── raw/               # Raw input data
│       └── vocabularies.json  # Controlled vocabularies
├── examples/               # Usage examples
│   ├── api_usage.py       # API examples
│   └── iconclass_usage.py # Iconclass examples
├── validate.py            # Main validation script
├── main.py                # Alternative entry point
├── README.md              # Main documentation
├── IMPLEMENTATION.md      # Implementation details
├── CONTRIBUTING.md        # This file
└── pyproject.toml         # Project dependencies

```

## Types of Contributions

### Reporting Bugs

- Use the [issue tracker](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues)
- Include detailed steps to reproduce
- Provide error messages, logs, and system information
- Mention the version you're using

### Suggesting Enhancements

- Check if the feature has already been suggested
- Clearly describe the feature and its use case
- Explain why it would be useful to the project
- Provide examples or mockups if applicable

### Improving Documentation

- Fix typos and clarify unclear sections
- Add examples and tutorials
- Improve code comments and docstrings
- Keep documentation in sync with code changes

### Writing Code

- Bug fixes
- New features
- Performance improvements
- Test coverage improvements
- Code refactoring

## Commit Message Guidelines

Write clear, concise commit messages:

- Use the imperative mood ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Reference issues and pull requests when applicable
- Provide additional context in the commit body if needed

Examples:

```
Add ISO 639-1 language validation

Implements validation of language codes against the ISO 639-1 standard.
Also updates the README with usage examples.

Fixes #42
```

## Questions or Need Help?

- Open an [issue](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/new/choose) for questions
- Tag maintainers (@maehr) if you need guidance
- Be patient and respectful when seeking help

## License

By contributing, you agree that your contributions will be licensed under the same licenses as the project:
- Code: [AGPL-3.0](LICENSE-AGPL.md)
- Data: [CC BY 4.0](LICENSE-CCBY.md)
