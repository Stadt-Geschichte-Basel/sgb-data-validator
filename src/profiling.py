"""Generate DataFrame and ydata-profiling analysis for items and media."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from ydata_profiling import ProfileReport


def flatten_dict(
    d: dict[str, Any], parent_key: str = "", sep: str = "."
) -> dict[str, Any]:
    """Flatten nested dictionary structure."""
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            # Handle list of dicts by taking first item or converting to string
            items.append((new_key, json.dumps(v)))
        elif isinstance(v, list):
            # Convert simple lists to comma-separated strings
            items.append((new_key, ", ".join(str(x) for x in v) if v else None))
        else:
            items.append((new_key, v))
    return dict(items)


def items_to_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert list of Omeka S items to a pandas DataFrame.

    Args:
        items: List of item dictionaries from Omeka S API

    Returns:
        DataFrame with flattened item data
    """
    flattened_items = [flatten_dict(item) for item in items]
    return pd.DataFrame(flattened_items)


def media_to_dataframe(media_list: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert list of Omeka S media to a pandas DataFrame.

    Args:
        media_list: List of media dictionaries from Omeka S API

    Returns:
        DataFrame with flattened media data
    """
    flattened_media = [flatten_dict(media) for media in media_list]
    return pd.DataFrame(flattened_media)


def generate_profile_report(
    df: pd.DataFrame,
    title: str,
    output_path: str | Path,
    minimal: bool = False,
) -> ProfileReport:
    """Generate a ydata-profiling report for a DataFrame.

    Args:
        df: DataFrame to profile
        title: Title for the report
        output_path: Path to save HTML report
        minimal: If True, generate minimal report for faster processing

    Returns:
        ProfileReport object
    """
    config = {
        "title": title,
        "minimal": minimal,
        "explorative": not minimal,
    }

    profile = ProfileReport(df, **config)
    profile.to_file(output_path)

    return profile


def analyze_items(
    items: list[dict[str, Any]],
    output_dir: str | Path = "analysis",
    minimal: bool = False,
) -> tuple[pd.DataFrame, ProfileReport]:
    """Analyze Omeka S items and generate profiling report.

    Args:
        items: List of item dictionaries
        output_dir: Directory to save outputs
        minimal: If True, generate minimal report

    Returns:
        Tuple of (DataFrame, ProfileReport)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create DataFrame
    df = items_to_dataframe(items)

    # Save DataFrame
    df.to_csv(output_dir / "items.csv", index=False)

    # Save as JSON with readable formatting (no escaped slashes, unicode preserved)
    with open(output_dir / "items.json", "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2, ensure_ascii=False)

    # Generate profile report
    profile = generate_profile_report(
        df,
        title="Omeka S Items Analysis",
        output_path=output_dir / "items_profile.html",
        minimal=minimal,
    )

    return df, profile


def analyze_media(
    media_list: list[dict[str, Any]],
    output_dir: str | Path = "analysis",
    minimal: bool = False,
) -> tuple[pd.DataFrame, ProfileReport]:
    """Analyze Omeka S media and generate profiling report.

    Args:
        media_list: List of media dictionaries
        output_dir: Directory to save outputs
        minimal: If True, generate minimal report

    Returns:
        Tuple of (DataFrame, ProfileReport)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create DataFrame
    df = media_to_dataframe(media_list)

    # Save DataFrame
    df.to_csv(output_dir / "media.csv", index=False)

    # Save as JSON with readable formatting (no escaped slashes, unicode preserved)
    with open(output_dir / "media.json", "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2, ensure_ascii=False)

    # Generate profile report
    profile = generate_profile_report(
        df,
        title="Omeka S Media Analysis",
        output_path=output_dir / "media_profile.html",
        minimal=minimal,
    )

    return df, profile
