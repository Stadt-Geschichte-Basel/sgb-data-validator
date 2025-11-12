#!/usr/bin/env python3
"""
Main entry point for the SGB Data Validator TUI.

This script launches the Text User Interface (TUI) for interactive validation
of Omeka S data using the Textual framework.
"""

import sys

from src.tui import main

if __name__ == "__main__":
    sys.exit(main())
