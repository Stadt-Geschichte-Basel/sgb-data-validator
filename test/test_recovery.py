"""Recovery checks and opt-in drills against disposable loopback instances."""

import os
from uuid import uuid4

import httpx2
import pytest
from typer.testing import CliRunner

from sgb_validator.api import OmekaAPI, OmekaError
from sgb_validator.cli import app
from sgb_validator.recovery import backup, load_backup, optional_get, restore
from sgb_validator.snapshots import Snapshot, read_json, write_snapshot
from sgb_validator.writes import create_record, update_record


def test_metadata_only_backup_uses_existing_names(tmp_path):
    snapshot = Snapshot({"o:id": 1}, [], [], "https://omeka.example")
    path = tmp_path / "legacy"
    write_snapshot(path, snapshot, "")
    loaded, _, full = load_backup(path)
    assert loaded == snapshot
    assert full is False


def literal(name, pid):
    return {"type": "literal", "property_id": pid, "@value": name}


def record(name, public=True):
    return {
        "o:is_public": public,
        "dcterms:title": [literal(name, 1)],
        "dcterms:identifier": [literal(name, 10)],
    }


class InterruptedUpload(OmekaAPI):
    def post(self, kind, payload, file=None, *, filename=None):
        written = super().post(kind, payload, file, filename=filename)
        if kind == "media":
            raise KeyboardInterrupt
        return written


def remove_fixture(api, kind, rid):
    try:
        api.request("DELETE", f"{kind}/{rid}")
    except OmekaError as exc:
        # Omeka S 3 can fail to render a successfully deleted resource.
        if exc.status != 500:
            raise
    assert optional_get(api, kind, rid) is None


def media_ids(item):
    return [ref["o:id"] for ref in item["o:media"]]


DRILL_URLS = os.getenv("SGB_DRILL_URLS", "").split(",")


@pytest.mark.integration
@pytest.mark.parametrize("base", DRILL_URLS)
def test_disposable_omeka_recovery(base, tmp_path, monkeypatch):
    if not base:
        pytest.skip("Set SGB_DRILL_URLS to run the disposable Omeka drill")
    if httpx2.URL(base).host not in {"127.0.0.1", "::1", "localhost"}:
        pytest.fail("The recovery drill requires a disposable loopback instance")
    identity = os.environ["SGB_DRILL_KEY_IDENTITY"]
    credential = os.environ["SGB_DRILL_KEY_CREDENTIAL"]
    auth = base, identity, credential
    tag = f"drill-{uuid4().hex}"
    path = tmp_path / "backup"
    private_file = tmp_path / "private.txt"
    private_file.write_bytes(b"private original")
    other_file = tmp_path / "other.txt"
    other_file.write_bytes(b"surviving original")

    with OmekaAPI(*auth) as api:
        set_id = api.post("item_sets", record(f"{tag}-set"))["o:id"]
        a = create_record(
            api, "items", record(f"{tag}-a", False), target_id=set_id, apply=True
        )["o:id"]
        b = create_record(
            api, "items", record(f"{tag}-b"), target_id=set_id, apply=True
        )["o:id"]
        medium = create_record(
            api,
            "media",
            record(f"{tag}-private", False),
            target_id=a,
            file=private_file,
            apply=True,
        )
        survivor = create_record(
            api,
            "media",
            record(f"{tag}-survivor", False),
            target_id=a,
            file=other_file,
            apply=True,
        )
        html = create_record(
            api,
            "media",
            {**record(f"{tag}-html"), "o:ingester": "html", "html": "<p>Drill</p>"},
            target_id=b,
            apply=True,
        )
        for origin, destination in ((a, b), (b, a)):
            before = api.get("items", origin)
            relation = {
                "type": "resource:item",
                "property_id": 13,
                "value_resource_id": destination,
            }
            after = {**before, "dcterms:relation": [relation]}
            if origin == a:
                after["o:media"] = [
                    {"o:id": medium["o:id"]},
                    {"o:id": survivor["o:id"]},
                ]
                after["dcterms:hasPart"] = [
                    {
                        "type": "uri",
                        "property_id": 34,
                        "@id": f"{api.base_url}/api/items/{b}",
                    }
                ]
            update_record(
                api,
                "items",
                before,
                after,
                apply=True,
                backup_dir=tmp_path / "before",
                skip_recent_hours=0,
            )
        manifest = backup(api, set_id, path)
        assert manifest["complete"], manifest["errors"]
        original = path / manifest["originals"][str(medium["o:id"])]["path"]
        original.write_bytes(b"corrupt")
        with pytest.raises(ValueError, match="size or SHA-256"):
            load_backup(path)
        original.write_bytes(private_file.read_bytes())
        remove_fixture(api, "media", medium["o:id"])
        remove_fixture(api, "items", b)
        remove_fixture(api, "item_sets", set_id)
        restore(api, path, skip_recent_hours=0)
        assert not (path / "restore-progress.json").exists()

    with InterruptedUpload(*auth) as api, pytest.raises(KeyboardInterrupt):
        restore(api, path, apply=True, skip_recent_hours=0)
    progress = path / "restore-progress.json"
    assert read_json(progress)["pending"]

    monkeypatch.setenv("KEY_IDENTITY", identity)
    monkeypatch.setenv("KEY_CREDENTIAL", credential)
    result = CliRunner().invoke(
        app,
        [
            "restore",
            str(path),
            "--base-url",
            base,
            "--apply",
            "--skip-recent-hours",
            "0",
        ],
    )
    assert result.exit_code == 0, result.output
    mapping = read_json(progress)["ids"]
    assert all(
        mapping[str(rid)] != rid for rid in (set_id, b, medium["o:id"], html["o:id"])
    )

    with OmekaAPI(*auth) as api:
        aa = api.get("items", a)
        bb = api.get("items", mapping[str(b)])
        media = api.get("media", mapping[str(medium["o:id"])])
        markup = api.get("media", mapping[str(html["o:id"])])
        assert not aa["o:is_public"] and not media["o:is_public"]
        assert bb["o:is_public"] and markup["o:is_public"]
        assert media_ids(aa) == [media["o:id"], survivor["o:id"]]
        assert media_ids(bb) == [markup["o:id"]]
        assert aa["dcterms:relation"][0]["value_resource_id"] == bb["o:id"]
        assert aa["dcterms:hasPart"][0]["@id"] == bb["@id"]
        assert bb["dcterms:relation"][0]["value_resource_id"] == aa["o:id"]
        assert media["o:sha256"] == medium["o:sha256"]
        assert httpx2.get(media["o:original_url"]).content == private_file.read_bytes()
        assert markup["data"]["html"] == "<p>Drill</p>"
        assert len(api.find("media", f"{tag}-private")) == 1
        assert [ref["o:id"] for ref in aa["o:item_set"]] == [mapping[str(set_id)]]
