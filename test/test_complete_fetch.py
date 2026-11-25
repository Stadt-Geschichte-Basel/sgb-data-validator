"""Validation and download must fail when the Omeka fetch is incomplete (#44)."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from omeka_s_client import TransportResponse
from omeka_s_client.testing import FakeOmeka
from test_issue16_validation import create_minimal_item, create_minimal_media
from typer.testing import CliRunner

from sgb_validator import cli
from sgb_validator.api import Omeka
from sgb_validator.snapshots import read_snapshot

BASE = "https://omeka.example"
LIVE = ["--base-url", BASE, "--item-set-id", "1", "--public-only"]


@pytest.fixture
def source():
    items = [create_minimal_item(2), create_minimal_item(4)]
    for item in items:
        item["o:item_set"] = [{"o:id": 1, "@id": f"{BASE}/api/item_sets/1"}]
    items[1]["dcterms:identifier"] = [
        {**items[1]["dcterms:identifier"][0], "@value": "test456"}
    ]
    items[1]["o:media"] = []
    items[0]["o:media"] = [{"o:id": 3, "@id": f"{BASE}/api/media/3"}]
    media = create_minimal_media(3)
    media["o:item"] = {"o:id": 2, "@id": f"{BASE}/api/items/2"}
    return {"item_sets": [{"o:id": 1}], "items": items, "media": [media]}


@pytest.fixture
def serve(monkeypatch, source):
    """Serve the source records. A hook can change each response."""

    def install(hook=None):
        fake = FakeOmeka(source)

        def transport(request):
            response = fake(request)
            return hook(request, response) if hook else response

        monkeypatch.setattr(
            cli,
            "connect",
            lambda *_: Omeka(BASE, transport=transport, sleep=lambda _: None),
        )

    return install


def drop_last_item(request, response):
    """Return one item less than the count header reports."""
    if urlsplit(request.url).path != "/api/items":
        return response
    records = json.loads(response.content)
    return TransportResponse(
        response.status, response.headers, json.dumps(records[:-1]).encode()
    )


def report_total(count):
    """Report another item total on the one-record request for the total."""

    def hook(request, response):
        url = urlsplit(request.url)
        if url.path == "/api/items" and parse_qs(url.query)["per_page"] == ["1"]:
            return TransportResponse(
                response.status,
                {**response.headers, "Omeka-S-Total-Results": str(count)},
                response.content,
            )
        return response

    return hook


@pytest.mark.parametrize("hook", [drop_last_item, report_total(3)])
@pytest.mark.parametrize("command", ["validate", "download"])
def test_incomplete_fetch_fails_and_writes_nothing(tmp_path, serve, command, hook):
    serve(hook)
    report = tmp_path / "report.txt"
    csv = tmp_path / "csv"
    data = tmp_path / "data"
    extra = (
        ["--output", str(report), "--export-csv", "--csv-output", str(csv)]
        if command == "validate"
        else ["--output-dir", str(data)]
    )
    result = CliRunner().invoke(cli.app, [command, *LIVE, *extra])
    assert result.exit_code == 1
    assert "expected" in result.stderr, result.stderr
    assert any(number in result.stderr for number in ("2", "3")), result.stderr
    assert not report.exists()
    assert not csv.exists()
    assert not data.exists()


def test_complete_fetch_saves_totals_and_validates(tmp_path, serve):
    serve()
    data = tmp_path / "data"
    result = CliRunner().invoke(cli.app, ["download", *LIVE, "--output-dir", str(data)])
    assert result.exit_code == 0, result.stderr
    (directory,) = data.iterdir()
    manifest = json.loads((directory / "download_metadata.json").read_text())
    assert manifest["expected_totals"] == {"items": 2, "media": 1}
    live = CliRunner().invoke(cli.app, ["validate", *LIVE])
    offline = CliRunner().invoke(cli.app, ["validate", str(directory)])
    assert "Incomplete fetch" not in live.stderr
    assert "no saved totals" not in offline.stderr
    assert live.exit_code == offline.exit_code == 0, live.output


def saved_snapshot(tmp_path, serve, *, totals):
    serve()
    result = CliRunner().invoke(
        cli.app, ["download", *LIVE, "--output-dir", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stderr
    (directory,) = tmp_path.iterdir()
    path = directory / "download_metadata.json"
    manifest = json.loads(path.read_text())
    if totals is None:
        del manifest["expected_totals"]
    else:
        manifest["expected_totals"] = totals
    path.write_text(json.dumps(manifest))
    return directory


def test_snapshot_that_misses_its_saved_totals_fails(tmp_path, serve):
    # The record counts still match the files. Only the saved totals differ.
    directory = saved_snapshot(tmp_path, serve, totals={"items": 3, "media": 1})
    report = tmp_path / "report.txt"
    result = CliRunner().invoke(
        cli.app, ["validate", str(directory), "--output", str(report)]
    )
    assert result.exit_code == 1
    assert "items: expected 3, found 2" in result.stderr
    assert not report.exists()


def test_old_snapshot_without_totals_passes_with_a_warning(tmp_path, serve):
    directory = saved_snapshot(tmp_path, serve, totals=None)
    assert read_snapshot(directory).items
    result = CliRunner().invoke(cli.app, ["validate", str(directory)])
    assert "no saved totals" in result.stderr
    assert "Incomplete" not in result.stderr
    assert result.exit_code == 0, result.output


def test_transform_keeps_the_saved_totals(tmp_path, serve):
    directory = saved_snapshot(tmp_path, serve, totals={"items": 2, "media": 1})
    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli.app, ["transform", str(directory), "--output-dir", str(out)]
    )
    assert result.exit_code == 0, result.stderr
    (edited,) = out.iterdir()
    meta = json.loads((edited / "transformation_metadata.json").read_text())
    assert meta["expected_totals"] == {"items": 2, "media": 1}
