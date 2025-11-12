"""
Text User Interface (TUI) for the sgb-data-validator.

This module provides an interactive terminal interface using the Textual framework
for validating Omeka S data.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from rich.console import RenderableType
from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from src.api import OmekaAPI

# Load environment variables
load_dotenv()


class ValidationStats(Static):
    """A widget to display validation statistics."""

    items_validated = reactive(0)
    media_validated = reactive(0)
    errors_count = reactive(0)
    warnings_count = reactive(0)
    is_validating = reactive(False)

    def render(self) -> RenderableType:
        """Render the validation statistics."""
        table = Table(title="Validation Statistics", expand=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta", justify="right")

        status = "🔄 Running..." if self.is_validating else "✓ Ready"
        table.add_row("Status", status)
        table.add_row("Items Validated", str(self.items_validated))
        table.add_row("Media Validated", str(self.media_validated))
        table.add_row("Errors", str(self.errors_count), style="red")
        table.add_row("Warnings", str(self.warnings_count), style="yellow")

        return table


class ConfigPanel(Static):
    """A panel for configuration inputs."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Vertical():
            yield Label("Configuration", classes="panel-title")
            yield Label("Base URL:")
            yield Input(
                placeholder="https://omeka.unibe.ch",
                value=os.getenv("OMEKA_URL", "https://omeka.unibe.ch"),
                id="base_url",
            )
            yield Label("Item Set ID:")
            yield Input(
                placeholder="10780",
                value=os.getenv("ITEM_SET_ID", "10780"),
                id="item_set_id",
            )
            yield Label("Key Identity (optional):")
            yield Input(
                placeholder="Leave empty for public data",
                value=os.getenv("KEY_IDENTITY", ""),
                id="key_identity",
                password=True,
            )
            yield Label("Key Credential (optional):")
            yield Input(
                placeholder="Leave empty for public data",
                value=os.getenv("KEY_CREDENTIAL", ""),
                id="key_credential",
                password=True,
            )


class ValidationApp(App[None]):
    """A Textual app for validating Omeka S data."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto 1fr auto;
    }

    Header {
        column-span: 2;
    }

    Footer {
        column-span: 2;
    }

    #config_panel {
        row-span: 2;
        border: solid $accent;
        padding: 1;
    }

    #main_content {
        row-span: 2;
        border: solid $accent;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    Input {
        margin-bottom: 1;
    }

    Button {
        margin: 1 0;
    }

    #stats {
        margin-bottom: 1;
    }

    #log_container {
        height: 100%;
    }

    RichLog {
        height: 100%;
        border: solid $primary;
    }

    #button_bar {
        align: center middle;
        height: auto;
    }

    Label {
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("v", "validate", "Validate"),
        ("c", "clear", "Clear Results"),
        ("s", "save", "Save Report"),
        ("?", "help", "Help"),
    ]

    TITLE = "SGB Data Validator - TUI"
    SUB_TITLE = "Interactive validation for Omeka S data"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the app."""
        super().__init__(**kwargs)
        self.validation_results: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield ConfigPanel(id="config_panel")
        with Vertical(id="main_content"):
            yield ValidationStats(id="stats")
            with Horizontal(id="button_bar"):
                yield Button("Validate", id="validate_btn", variant="primary")
                yield Button("Clear Results", id="clear_btn", variant="default")
                yield Button("Save Report", id="save_btn", variant="success")
            with TabbedContent(id="results_tabs"):
                with TabPane("Results", id="results_tab"):
                    yield RichLog(id="results_log", wrap=True, highlight=True)
                with TabPane("Errors", id="errors_tab"):
                    yield RichLog(id="errors_log", wrap=True, highlight=True)
                with TabPane("Warnings", id="warnings_tab"):
                    yield RichLog(id="warnings_log", wrap=True, highlight=True)
                with TabPane("Help", id="help_tab"):
                    yield RichLog(id="help_log", wrap=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Display help information
        help_log = self.query_one("#help_log", RichLog)
        help_log.write("=== SGB Data Validator - Help ===\n")
        help_log.write(
            "This TUI provides an interactive interface for validating Omeka S data.\n"
        )
        help_log.write("\n[bold cyan]Configuration:[/bold cyan]")
        help_log.write("• Base URL: The URL of your Omeka S instance")
        help_log.write("• Item Set ID: The ID of the item set to validate")
        help_log.write(
            "• Credentials: Optional API keys (loaded from .env if available)\n"
        )
        help_log.write("\n[bold cyan]Keyboard Shortcuts:[/bold cyan]")
        help_log.write("• v - Start validation")
        help_log.write("• c - Clear results")
        help_log.write("• s - Save report to file")
        help_log.write("• q - Quit application")
        help_log.write("• ? - Show this help\n")
        help_log.write("\n[bold cyan]Usage:[/bold cyan]")
        help_log.write("1. Configure the Base URL and Item Set ID")
        help_log.write("2. Optionally provide API credentials for private data")
        help_log.write("3. Click 'Validate' or press 'v' to start validation")
        help_log.write("4. View results in different tabs (Results, Errors, Warnings)")
        help_log.write("5. Save the report using 'Save Report' button or 's' key\n")
        help_log.write("\n[bold cyan]Configuration File:[/bold cyan]")
        help_log.write("You can set defaults in a .env file:")
        help_log.write("  OMEKA_URL=https://omeka.unibe.ch")
        help_log.write("  ITEM_SET_ID=10780")
        help_log.write("  KEY_IDENTITY=your_key")
        help_log.write("  KEY_CREDENTIAL=your_secret\n")

    @on(Button.Pressed, "#validate_btn")
    def on_validate_button(self) -> None:
        """Handle validate button press."""
        self.action_validate()

    @on(Button.Pressed, "#clear_btn")
    def on_clear_button(self) -> None:
        """Handle clear button press."""
        self.action_clear()

    @on(Button.Pressed, "#save_btn")
    def on_save_button(self) -> None:
        """Handle save button press."""
        self.action_save()

    def action_help(self) -> None:
        """Show help information."""
        tabs = self.query_one("#results_tabs", TabbedContent)
        tabs.active = "help_tab"

    def action_clear(self) -> None:
        """Clear all results."""
        results_log = self.query_one("#results_log", RichLog)
        errors_log = self.query_one("#errors_log", RichLog)
        warnings_log = self.query_one("#warnings_log", RichLog)

        results_log.clear()
        errors_log.clear()
        warnings_log.clear()

        stats = self.query_one("#stats", ValidationStats)
        stats.items_validated = 0
        stats.media_validated = 0
        stats.errors_count = 0
        stats.warnings_count = 0

        self.validation_results = {}

        results_log.write("[green]Results cleared.[/green]")

    def action_save(self) -> None:
        """Save validation report to file."""
        if not self.validation_results:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write(
                "[yellow]No validation results to save. Run validation first.[/yellow]"
            )
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{timestamp}.txt"

        try:
            with open(filename, "w") as f:
                f.write("=== SGB Data Validator - Validation Report ===\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                base_url = self.validation_results.get("base_url", "N/A")
                f.write(f"Base URL: {base_url}\n")
                item_set_id = self.validation_results.get("item_set_id", "N/A")
                f.write(f"Item Set ID: {item_set_id}\n\n")

                f.write("=== Statistics ===\n")
                items = self.validation_results.get("items_validated", 0)
                f.write(f"Items validated: {items}\n")
                media = self.validation_results.get("media_validated", 0)
                f.write(f"Media validated: {media}\n")
                errors = self.validation_results.get("errors_count", 0)
                f.write(f"Errors: {errors}\n")
                warnings = self.validation_results.get("warnings_count", 0)
                f.write(f"Warnings: {warnings}\n\n")

                if self.validation_results.get("errors"):
                    f.write("=== Errors ===\n")
                    for error in self.validation_results["errors"]:
                        f.write(f"{error}\n")
                    f.write("\n")

                if self.validation_results.get("warnings"):
                    f.write("=== Warnings ===\n")
                    for warning in self.validation_results["warnings"]:
                        f.write(f"{warning}\n")

            results_log = self.query_one("#results_log", RichLog)
            results_log.write(f"[green]Report saved to {filename}[/green]")
        except Exception as e:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write(f"[red]Error saving report: {e}[/red]")

    def action_validate(self) -> None:
        """Start the validation process."""
        stats = self.query_one("#stats", ValidationStats)
        if stats.is_validating:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write("[yellow]Validation already in progress...[/yellow]")
            return

        # Get configuration values
        base_url = self.query_one("#base_url", Input).value
        item_set_id = self.query_one("#item_set_id", Input).value
        key_identity = self.query_one("#key_identity", Input).value
        key_credential = self.query_one("#key_credential", Input).value

        # Validate inputs
        if not base_url:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write("[red]Error: Base URL is required[/red]")
            return

        if not item_set_id:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write("[red]Error: Item Set ID is required[/red]")
            return

        try:
            item_set_id_int = int(item_set_id)
        except ValueError:
            results_log = self.query_one("#results_log", RichLog)
            results_log.write("[red]Error: Item Set ID must be a number[/red]")
            return

        # Start validation
        self.run_validation(
            base_url,
            item_set_id_int,
            key_identity or None,
            key_credential or None,
        )

    @work(exclusive=True)
    async def run_validation(
        self,
        base_url: str,
        item_set_id: int,
        key_identity: str | None,
        key_credential: str | None,
    ) -> None:
        """Run the validation process in a worker thread."""
        stats = self.query_one("#stats", ValidationStats)
        results_log = self.query_one("#results_log", RichLog)
        errors_log = self.query_one("#errors_log", RichLog)
        warnings_log = self.query_one("#warnings_log", RichLog)

        # Clear previous results
        results_log.clear()
        errors_log.clear()
        warnings_log.clear()

        stats.is_validating = True
        stats.items_validated = 0
        stats.media_validated = 0
        stats.errors_count = 0
        stats.warnings_count = 0

        results_log.write("[cyan]Starting validation...[/cyan]")
        results_log.write(f"Base URL: {base_url}")
        results_log.write(f"Item Set ID: {item_set_id}\n")

        errors = []
        warnings = []

        try:
            # Initialize API client
            with OmekaAPI(
                base_url=base_url,
                key_identity=key_identity,
                key_credential=key_credential,
            ) as api:
                # Get item set info
                results_log.write("[cyan]Fetching item set information...[/cyan]")
                try:
                    item_set = api.get_item_set(item_set_id)
                    item_set_title = item_set.get("o:title", "Unknown")
                    results_log.write(f"Item Set: {item_set_title}\n")
                except Exception as e:
                    msg = f"[yellow]Could not fetch item set info: {e}[/yellow]\n"
                    results_log.write(msg)

                # Get items
                results_log.write("[cyan]Fetching items...[/cyan]")
                items = api.get_items_from_set(item_set_id)
                results_log.write(f"Found {len(items)} items\n")

                # Validate items
                results_log.write("[cyan]Validating items...[/cyan]")
                for i, item_data in enumerate(items, 1):
                    item_id = item_data.get("o:id", "unknown")
                    stats.items_validated = i

                    # Validate item
                    is_valid, validation_errors = api.validate_item(item_data)
                    if not is_valid:
                        for error in validation_errors:
                            error_msg = f"Item {item_id}: {error}"
                            errors.append(error_msg)
                            errors_log.write(f"[red]• {error_msg}[/red]")

                    # Validate associated media
                    media_list = api.get_media_from_item(item_id)
                    for media_data in media_list:
                        media_id = media_data.get("o:id", "unknown")
                        stats.media_validated += 1

                        is_valid, validation_errors = api.validate_media(media_data)
                        if not is_valid:
                            for error in validation_errors:
                                msg = f"Media {media_id} (Item {item_id}): {error}"
                                errors.append(msg)
                                errors_log.write(f"[red]• {msg}[/red]")

                    # Update UI periodically
                    if i % 10 == 0:
                        await asyncio.sleep(0.01)  # Allow UI to update

                # Update final stats
                stats.errors_count = len(errors)
                stats.warnings_count = len(warnings)

                # Store results
                self.validation_results = {
                    "base_url": base_url,
                    "item_set_id": item_set_id,
                    "items_validated": stats.items_validated,
                    "media_validated": stats.media_validated,
                    "errors_count": len(errors),
                    "warnings_count": len(warnings),
                    "errors": errors,
                    "warnings": warnings,
                }

                # Display summary
                results_log.write(
                    "\n[bold cyan]=== Validation Complete ===[/bold cyan]"
                )
                results_log.write(f"Items validated: {stats.items_validated}")
                results_log.write(f"Media validated: {stats.media_validated}")

                if len(errors) > 0:
                    results_log.write(f"[red]Errors found: {len(errors)}[/red]")
                else:
                    results_log.write("[green]No errors found! ✓[/green]")

                if len(warnings) > 0:
                    results_log.write(f"[yellow]Warnings: {len(warnings)}[/yellow]")

                results_log.write(
                    "\n[cyan]View the Errors and Warnings tabs for details.[/cyan]"
                )

        except Exception as e:
            results_log.write(f"\n[red]Validation failed with error: {e}[/red]")
            errors_log.write(f"[red]Fatal error: {e}[/red]")
        finally:
            stats.is_validating = False


def main() -> None:
    """Run the TUI application."""
    app = ValidationApp()
    app.run()


if __name__ == "__main__":
    main()
