"""Check live and offline validation against the same records."""

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from omeka_s_client import SnapshotConsistencyError, TransportResponse
from omeka_s_client.testing import FakeOmeka
from test_issue16_validation import create_minimal_item, create_minimal_media
from typer.testing import CliRunner

from sgb_validator.api import Omeka
from sgb_validator.cli import app
from sgb_validator.snapshots import capture_snapshot, read_snapshot, write_snapshot
from sgb_validator.validation import validate_records
from sgb_validator.vocabularies import VocabularyLoader


@pytest.fixture
def source():
    item = create_minimal_item(2)
    item["o:media"] = [{"o:id": 3, "@id": "https://omeka.example/api/media/3"}]
    media = create_minimal_media(3)
    media["o:item"] = {"o:id": 2, "@id": "https://omeka.example/api/items/2"}
    media["o:filename"] = "0011aabb.png"
    media["o:source"] = "sgb-fdp-platzhalter[1].png"
    media["o:is_public"] = True
    item["o:item_set"] = [{"o:id": 1}]
    return {"item_sets": [{"o:id": 1}], "items": [item], "media": [media]}


def api_for(source, *, truncate_media=False):
    fake = FakeOmeka(source)

    def transport(request):
        if truncate_media and urlsplit(request.url).path == "/api/media":
            # An empty page without a count header hides the missing media.
            return TransportResponse(200, content=b"[]")
        return fake(request)

    return Omeka("https://omeka.example", transport=transport, sleep=lambda _: None)


@pytest.mark.parametrize("suffix", ["raw", "transformed", ""])
def test_offline_and_live_findings_match(tmp_path, source, suffix):
    with api_for(source) as api:
        live = capture_snapshot(api, 1)
    path = tmp_path / "snapshot"
    write_snapshot(path, live, suffix)
    offline = read_snapshot(path)
    vocabulary = VocabularyLoader()
    live_findings = validate_records(live.items, live.media, vocabulary)
    offline_findings = validate_records(offline.items, offline.media, vocabulary)
    assert [str(e) for e in live_findings.errors] == [
        str(e) for e in offline_findings.errors
    ]
    assert [str(w) for w in live_findings.warnings] == [
        str(w) for w in offline_findings.warnings
    ]
    assert any(
        e.field == "o:is_public" and e.resource_type == "Media"
        for e in offline_findings.warnings
    )
    assert any(
        e.field == "o:is_public" and e.resource_type == "Item"
        for e in offline_findings.warnings
    )
    report = tmp_path / "report"
    result = CliRunner().invoke(
        app, ["validate", str(path), "--export-csv", "--csv-output", str(report)]
    )
    assert result.exit_code == int(bool(offline_findings.errors))
    assert (
        "https://omeka.example/admin/media/3/edit"
        in (report / "media_validation.csv").read_text()
    )
    assert (report / "validation_summary.csv").is_file()


def test_media_truncation_detected_without_count_header(source):
    with api_for(source, truncate_media=True) as api:
        with pytest.raises(SnapshotConsistencyError, match="Missing examples: \\[3\\]"):
            capture_snapshot(api, 1)


def test_transform_leaves_source_intact_and_reports_visibility_change(tmp_path, source):
    with api_for(source) as api:
        snapshot = capture_snapshot(api, 1)
    raw = tmp_path / "raw"
    write_snapshot(raw, snapshot, "raw")
    before = (raw / "media_raw.json").read_bytes()
    result = CliRunner().invoke(
        app, ["transform", str(raw), "--output-dir", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert "media/3  o:is_public" in result.output
    transformed = read_snapshot(Path(result.output.splitlines()[-1]))
    assert transformed.media[0]["o:is_public"] is False
    assert transformed.items[0]["o:is_public"] is False
    assert (raw / "media_raw.json").read_bytes() == before


def test_capture_keeps_the_item_media_order(tmp_path, source):
    item = source["items"][0]
    second = {**source["media"][0], "o:id": 1}
    source["media"].append(second)
    item["o:media"] = [{"o:id": 3}, {"o:id": 1}]
    with api_for(source) as api:
        snapshot = capture_snapshot(api, 1)
    assert [medium["o:id"] for medium in snapshot.media] == [3, 1]
    path = write_snapshot(tmp_path / "nested" / "raw", snapshot, "raw")
    assert sorted(entry.name for entry in path.iterdir()) == [
        "download_metadata.json",
        "item_set_raw.json",
        "items_raw.json",
        "media_raw.json",
    ]
    assert read_snapshot(path) == snapshot


def test_legacy_sgb_snapshot_stays_readable(tmp_path, source):
    path = tmp_path / "legacy"
    path.mkdir()
    for name, value in (
        ("item_set_raw", source["item_sets"][0]),
        ("items_raw", source["items"]),
        ("media_raw", source["media"]),
    ):
        (path / f"{name}.json").write_text(json.dumps(value))
    (path / "download_metadata.json").write_text(
        json.dumps(
            {
                "source": "https://omeka.example",
                "item_set_id": 1,
                "items_count": 1,
                "media_count": 1,
                "status": "raw",
                "timestamp": "20250101_120000",
            }
        )
    )
    snapshot = read_snapshot(path)
    assert snapshot.source == "https://omeka.example"
    assert snapshot.item_set_id == 1
    assert [medium["o:id"] for medium in snapshot.media] == [3]
