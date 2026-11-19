"""Edit links in CSV reports must open the Omeka S admin page (issue #44)."""

import csv

from sgb_validator.reports import export_validation_csv
from sgb_validator.validation import DataValidationError, Findings


def test_edit_links_use_omeka_admin_routes(tmp_path) -> None:
    base_url = "https://omeka.unibe.ch"
    validator = Findings()
    validator.errors.append(DataValidationError("Item", 12755, "dcterms:title", "x"))
    validator.errors.append(DataValidationError("Media", 13371, "dcterms:title", "x"))

    export_validation_csv(validator, base_url, tmp_path)

    with open(tmp_path / "items_validation.csv", encoding="utf-8") as f:
        item_row = next(csv.DictReader(f))
    with open(tmp_path / "media_validation.csv", encoding="utf-8") as f:
        media_row = next(csv.DictReader(f))

    assert item_row["edit_link"] == "https://omeka.unibe.ch/admin/item/12755/edit"
    assert media_row["edit_link"] == "https://omeka.unibe.ch/admin/media/13371/edit"


def test_edit_links_follow_configured_omeka_instance(tmp_path) -> None:
    base_url = "https://other.example.org/api"
    validator = Findings()
    validator.errors.append(DataValidationError("Item", 12755, "dcterms:title", "x"))

    export_validation_csv(validator, base_url, tmp_path)

    with open(tmp_path / "items_validation.csv", encoding="utf-8") as f:
        item_row = next(csv.DictReader(f))

    assert item_row["edit_link"] == "https://other.example.org/admin/item/12755/edit"
