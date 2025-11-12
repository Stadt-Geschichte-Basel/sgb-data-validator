"""
Tests for the TUI module.
"""


def test_tui_imports():
    """Test that TUI module can be imported."""
    from src.tui import ConfigPanel, ValidationApp, ValidationStats

    assert ValidationApp is not None
    assert ValidationStats is not None
    assert ConfigPanel is not None


def test_validation_stats_widget():
    """Test ValidationStats widget initialization."""
    from src.tui import ValidationStats

    stats = ValidationStats()
    assert stats.items_validated == 0
    assert stats.media_validated == 0
    assert stats.errors_count == 0
    assert stats.warnings_count == 0
    assert stats.is_validating is False


def test_validation_app_initialization():
    """Test ValidationApp initialization."""
    from src.tui import ValidationApp

    app = ValidationApp()
    assert app.title == "SGB Data Validator - TUI"
    assert app.sub_title == "Interactive validation for Omeka S data"
    assert app.validation_results == {}


def test_tui_main_function():
    """Test that main function exists and is callable."""
    from src.tui import main

    assert callable(main)


def test_validation_app_has_bindings():
    """Test that the app has the expected key bindings."""
    from src.tui import ValidationApp

    app = ValidationApp()
    binding_keys = [binding[0] for binding in app.BINDINGS]

    assert "q" in binding_keys  # Quit
    assert "v" in binding_keys  # Validate
    assert "c" in binding_keys  # Clear
    assert "s" in binding_keys  # Save
    assert "?" in binding_keys  # Help
