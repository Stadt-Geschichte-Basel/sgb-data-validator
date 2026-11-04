"""Edit links in CSV reports must open the Omeka S admin page (issue #44)."""

import csv

from validate import DataValidationError, OmekaValidator


def test_edit_links_use_omeka_admin_routes(tmp_path) -> None:
    validator = OmekaValidator("https://omeka.unibe.ch")
    validator.errors.append(DataValidationError("Item", 12755, "dcterms:title", "x"))
    validator.errors.append(DataValidationError("Media", 13371, "dcterms:title", "x"))

    validator.export_validation_csv(tmp_path)

    with open(tmp_path / "items_validation.csv", encoding="utf-8") as f:
        item_row = next(csv.DictReader(f))
    with open(tmp_path / "media_validation.csv", encoding="utf-8") as f:
        media_row = next(csv.DictReader(f))

    assert item_row["edit_link"] == "https://omeka.unibe.ch/admin/item/12755"
    assert media_row["edit_link"] == "https://omeka.unibe.ch/admin/media/13371"
