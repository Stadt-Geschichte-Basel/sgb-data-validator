"""Check live and offline validation against the same records."""

from pathlib import Path

import httpx2
import pytest
from test_issue16_validation import create_minimal_item, create_minimal_media
from typer.testing import CliRunner

from sgb_validator import api as client_module
from sgb_validator.api import OmekaAPI, OmekaError
from sgb_validator.cli import app
from sgb_validator.snapshots import download_snapshot, read_snapshot, write_snapshot
from sgb_validator.validation import validate_records
from sgb_validator.vocabularies import VocabularyLoader


@pytest.fixture
def source():
    item = create_minimal_item(2)
    item["o:media"] = [{"o:id": 3, "@id": "https://omeka.example/api/media/3"}]
    media = create_minimal_media(3)
    media["o:item"] = {"o:id": 2, "@id": "https://omeka.example/api/items/2"}
    media["o:filename"] = "sgb-fdp-platzhalter.png"
    media["o:is_public"] = True
    return {"item_sets/1": {"o:id": 1}, "items": [item], "media": [media]}


def api_for(source, *, truncate_media=False):
    def handler(request):
        field = request.url.path.removeprefix("/api/")
        body = source[field]
        if isinstance(body, dict):
            return httpx2.Response(200, json=body)
        results = body if request.url.params["page"] == "1" else []
        if truncate_media and field == "media":
            return httpx2.Response(200, json=[])
        return httpx2.Response(
            200, json=results, headers={"omeka-s-total-results": str(len(body))}
        )

    return OmekaAPI("https://omeka.example", transport=httpx2.MockTransport(handler))


@pytest.mark.parametrize("suffix", ["raw", "transformed", ""])
def test_offline_and_live_findings_match(tmp_path, source, suffix):
    with api_for(source) as api:
        live = download_snapshot(api, 1)
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
        for e in offline_findings.errors
    )
    assert any(
        e.field == "o:is_public" and e.resource_type == "Item"
        for e in offline_findings.errors
    )
    report = tmp_path / "report"
    result = CliRunner().invoke(
        app, ["validate", str(path), "--export-csv", "--csv-output", str(report)]
    )
    assert result.exit_code == 1
    assert (
        "https://omeka.example/admin/media/3/edit"
        in (report / "media_validation.csv").read_text()
    )
    assert (report / "validation_summary.csv").is_file()


def test_media_truncation_detected_without_count_header(monkeypatch, source):
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    with api_for(source, truncate_media=True) as api:
        with pytest.raises(OmekaError, match="Incomplete media listing"):
            download_snapshot(api, 1)


def test_transform_leaves_source_intact_and_reports_visibility_change(tmp_path, source):
    with api_for(source) as api:
        snapshot = download_snapshot(api, 1)
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
