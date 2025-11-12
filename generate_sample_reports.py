#!/usr/bin/env python3
"""
Generate sample validation reports for documentation purposes.

This script creates realistic validation reports without requiring API access.
"""

import csv
from pathlib import Path

# Create output directory
output_dir = Path("analysis")
output_dir.mkdir(exist_ok=True)

# Sample validation data with various issues
items_data = [
    {
        "resource_id": 10780,
        "edit_link": "https://omeka.unibe.ch/admin/items/10780",
        "dcterms:identifier": "error: Field is required",
        "dcterms:description": "",
        "dcterms:temporal": "",
        "dcterms:subject": "",
        "dcterms:language": "",
    },
    {
        "resource_id": 10781,
        "edit_link": "https://omeka.unibe.ch/admin/items/10781",
        "dcterms:identifier": "",
        "dcterms:description": "warning: Missing field",
        "dcterms:temporal": "",
        "dcterms:subject": "",
        "dcterms:language": "",
    },
    {
        "resource_id": 10782,
        "edit_link": "https://omeka.unibe.ch/admin/items/10782",
        "dcterms:identifier": "",
        "dcterms:description": "",
        "dcterms:temporal": "",
        "dcterms:subject": "error: Invalid Iconclass code: XYZ123",
        "dcterms:language": "",
    },
    {
        "resource_id": 10783,
        "edit_link": "https://omeka.unibe.ch/admin/items/10783",
        "dcterms:identifier": "",
        "dcterms:description": "",
        "dcterms:temporal": "",
        "dcterms:subject": "",
        "dcterms:language": "error: Invalid language code (must be valid ISO 639-1 two-letter code): xyz",
    },
]

media_data = [
    {
        "resource_id": 10778,
        "edit_link": "https://omeka.unibe.ch/admin/media/10778",
        "dcterms:identifier": "",
        "dcterms:creator": "warning: Missing field",
        "dcterms:license": "",
        "o:media_type": "",
    },
    {
        "resource_id": 10779,
        "edit_link": "https://omeka.unibe.ch/admin/media/10779",
        "dcterms:identifier": "error: Field is required",
        "dcterms:creator": "",
        "dcterms:license": "",
        "o:media_type": "error: Invalid MIME type: application/unknown",
    },
]

# Write items validation CSV
items_csv_path = output_dir / "items_validation.csv"
if items_data:
    fieldnames = list(items_data[0].keys())
    with open(items_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items_data)
    print(f"Created: {items_csv_path}")

# Write media validation CSV
media_csv_path = output_dir / "media_validation.csv"
if media_data:
    fieldnames = list(media_data[0].keys())
    with open(media_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(media_data)
    print(f"Created: {media_csv_path}")

# Write validation summary CSV
summary_data = [
    ["metric", "value"],
    ["items_validated", 150],
    ["media_validated", 300],
    ["total_errors", 12],
    ["total_warnings", 45],
    ["items_with_issues", 4],
    ["media_with_issues", 2],
    ["uris_checked", 450],
    ["failed_uris", 3],
]

summary_csv_path = output_dir / "validation_summary.csv"
with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(summary_data)
print(f"Created: {summary_csv_path}")

# Create a sample text report
report_path = output_dir / "validation_report.txt"
report_content = """================================================================================
VALIDATION REPORT
================================================================================
Items validated: 150
Media validated: 300
Total errors: 12
Total warnings: 45
URIs checked: 450
Failed URIs: 3
================================================================================

ERRORS:
  [Item 10780] dcterms:identifier: Field is required
  [Item 10782] dcterms:subject[0]: Invalid Iconclass code: XYZ123
  [Item 10783] dcterms:language[0]: Invalid language code (must be valid ISO 639-1 two-letter code): xyz
  [Media 10779] dcterms:identifier: Field is required
  [Media 10779] o:media_type: Invalid MIME type: application/unknown

WARNINGS (informational):
  [Item 10781] dcterms:description: Missing field
  [Media 10778] dcterms:creator: Missing field
  [Item 10777] dcterms:description: Literal field contains URL: https://example.com/...
  [Item 10785] dcterms:source: URI is not reachable: https://broken-link.example.com (404 Not Found)

Report saved to: analysis/validation_report.txt
"""

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_content)
print(f"Created: {report_path}")

print("\n✓ Sample validation reports generated successfully!")
print(f"  Output directory: {output_dir}/")
