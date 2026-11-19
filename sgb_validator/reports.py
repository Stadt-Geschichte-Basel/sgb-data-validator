"""Write text and CSV validation reports."""

import csv
from collections import defaultdict
from pathlib import Path

from .validation import DataValidationWarning, Findings


def report_text(result: Findings) -> str:
    border = "=" * 80
    lines = [
        border,
        "VALIDATION REPORT",
        border,
        f"Items validated: {result.validated_items}",
        f"Media validated: {result.validated_media}",
        f"Total errors: {len(result.errors)}",
        f"Total warnings: {len(result.warnings)}",
    ]
    if result.check_uris:
        lines += [
            f"URIs checked: {result.checked_uris}",
            f"Failed URIs: {result.failed_uris}",
        ]
    lines += [border, ""]
    if result.errors:
        lines += ["ERRORS:", *(f"  {error}" for error in result.errors)]
    if result.warnings:
        lines += [
            "",
            "WARNINGS (informational):",
            *(f"  {warning}" for warning in result.warnings),
        ]
    return "\n".join(lines) + "\n"


def print_report(result: Findings) -> None:
    print(report_text(result), end="")


def save_report(result: Findings, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_text(result), encoding="utf-8")
    print(f"Report saved to: {output_file}")


def warning_column(warning: DataValidationWarning) -> tuple[str, str]:
    text = warning.message
    if text.startswith("Missing "):
        return text.removeprefix("Missing ").strip(), "Missing field"
    if ":" in text:
        field, message = text.split(":", 1)
        return field.strip(), message.strip()
    return "general", text


def export_validation_csv(
    result: Findings, base_url: str, output_dir: str | Path = "validation_reports"
) -> None:
    """Write the issue tables and summary with the original filenames and columns."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    admin_url = base_url.rstrip("/").removesuffix("/api") + "/admin" if base_url else ""
    issues = {"Item": defaultdict(dict), "Media": defaultdict(dict)}
    for warning in result.warnings:
        field, message = warning_column(warning)
        issues[warning.resource_type][warning.resource_id][field] = (
            f"warning: {message}"
        )
    for error in result.errors:
        issues[error.resource_type][error.resource_id][error.field] = (
            f"error: {error.error}"
        )

    for label, filename in (
        ("Item", "items_validation.csv"),
        ("Media", "media_validation.csv"),
    ):
        path = output_dir / filename
        resource_issues = issues[label]
        fields = sorted(
            {field for cells in resource_issues.values() for field in cells}
        )
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["resource_id", "edit_link", *fields])
            for rid in sorted(
                resource_issues, key=lambda rid: (isinstance(rid, str), rid)
            ):
                edit_link = (
                    f"{admin_url}/{label.lower()}/{rid}/edit" if admin_url else ""
                )
                writer.writerow(
                    [
                        rid,
                        edit_link,
                        *(resource_issues[rid].get(field, "") for field in fields),
                    ]
                )
        print(f"Validation CSV saved to: {path}")

    summary = [
        ("items_validated", result.validated_items),
        ("media_validated", result.validated_media),
        ("total_errors", len(result.errors)),
        ("total_warnings", len(result.warnings)),
        ("items_with_issues", len(issues["Item"])),
        ("media_with_issues", len(issues["Media"])),
    ]
    if result.check_uris:
        summary += [
            ("uris_checked", result.checked_uris),
            ("failed_uris", result.failed_uris),
        ]
    path = output_dir / "validation_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)
    print(f"Validation summary CSV saved to: {path}")
