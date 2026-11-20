"""Recovery checks and opt-in drills against disposable loopback instances."""

import os
from urllib.parse import urlsplit
from uuid import uuid4

import httpx2
import pytest
from typer.testing import CliRunner

from sgb_validator.api import OmekaAPI, OmekaError
from sgb_validator.cli import app
from sgb_validator.recovery import backup, load_backup, optional_get, restore
from sgb_validator.snapshots import Snapshot, read_json, read_snapshot, write_snapshot
from sgb_validator.writes import create_record, update_record


def test_metadata_only_backup_uses_existing_names(tmp_path):
    snapshot = Snapshot({"o:id": 1}, [], [], "https://omeka.example")
    path = tmp_path / "legacy"
    write_snapshot(path, snapshot, "")
    loaded, _, full = load_backup(path)
    assert loaded == snapshot
    assert full is False


@pytest.mark.parametrize("apply", [False, True])
def test_metadata_only_restore_refuses_deleted_resources(tmp_path, apply):
    source = "https://omeka.example"
    item_set = {"o:id": 1, "o:is_public": False}
    item = {"o:id": 2, "o:item_set": [{"o:id": 1}]}
    path = tmp_path / "legacy"
    write_snapshot(path, Snapshot(item_set, [item], [], source), "")
    messages = []

    class FakeAPI:
        base_url = source
        auth = True

        def get(self, kind, rid):
            if kind == "items":
                raise OmekaError("Not found", status=404)
            return {**item_set, "o:is_public": True}

    with pytest.raises(OmekaError, match="deleted records require a complete backup"):
        restore(
            FakeAPI(),
            path,
            apply=apply,
            exclusive_write=apply,
            announce=messages.append,
        )
    assert any("Missing items/2" in line for line in messages)
    if not apply:
        assert any("Restore item_sets/1: o:is_public" in line for line in messages)
    assert not (path / "before-edit").exists()
    assert not (path / "restore-progress.json").exists()


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
            api, "items", record(f"{tag}-a"), target_id=set_id, apply=True
        )["o:id"]
        b = create_record(
            api, "items", record(f"{tag}-b"), target_id=set_id, apply=True
        )["o:id"]
        # Simulate a placeholder from an older collection whose parent is public.
        medium = api.post(
            "media",
            {
                **record(f"{tag}-private", False),
                "o:ingester": "upload",
                "o:source": "sgb-fdp-platzhalter[1].txt",
                "o:item": {"o:id": a},
                "file_index": 0,
            },
            private_file,
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
        ingest_base = os.getenv("SGB_DRILL_INGEST_BASE", base)
        url_media_source = f"{ingest_base}{urlsplit(survivor['o:original_url']).path}"
        url_media = create_record(
            api,
            "media",
            {
                **record(f"{tag}-url"),
                "o:ingester": "url",
                "ingest_url": url_media_source,
                "o:source": "https://example.test/original.txt",
            },
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
                exclusive_write=True,
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
        restore(api, path, apply=True, exclusive_write=True, skip_recent_hours=0)
    progress = path / "restore-progress.json"
    assert read_json(progress)["pending"]

    monkeypatch.setenv("KEY_IDENTITY", identity)
    monkeypatch.setenv("KEY_CREDENTIAL", credential)
    result = CliRunner().invoke(
        app,
        [
            "restore",
            str(path),
            "--apply",
            "--exclusive-write",
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
        restored_url = api.get("media", mapping[str(url_media["o:id"])])
        expected_order = [
            mapping[str(ref["o:id"])] for ref in read_snapshot(path).items[1]["o:media"]
        ]
        assert media_ids(bb) == expected_order
        assert markup["o:id"] in expected_order
        assert restored_url["o:ingester"] == "upload"
        assert restored_url["o:source"] == url_media["o:source"]
        assert restored_url["o:sha256"] == url_media["o:sha256"]
        assert (
            httpx2.get(restored_url["o:original_url"]).content
            == other_file.read_bytes()
        )
        assert aa["dcterms:relation"][0]["value_resource_id"] == bb["o:id"]
        assert aa["dcterms:hasPart"][0]["@id"] == bb["@id"]
        assert bb["dcterms:relation"][0]["value_resource_id"] == aa["o:id"]
        assert media["o:sha256"] == medium["o:sha256"]
        assert httpx2.get(media["o:original_url"]).content == private_file.read_bytes()
        assert markup["data"]["html"] == "<p>Drill</p>"
        assert len(api.find("media", f"{tag}-private")) == 1
        assert [ref["o:id"] for ref in aa["o:item_set"]] == [mapping[str(set_id)]]


def test_full_restore_reads_only_metadata_verified_by_the_manifest(tmp_path):
    from sgb_validator.recovery import FILES
    from sgb_validator.snapshots import write_json
    from sgb_validator.writes import file_digest

    source = "https://omeka.example"
    snapshot = Snapshot({"o:id": 1}, [record("verified") | {"o:id": 2}], [], source)
    directory = tmp_path / "full"
    write_snapshot(directory, snapshot, "")
    write_json(
        directory / "manifest.json",
        {
            "version": 1,
            "complete": True,
            "source": source,
            "metadata": {name: file_digest(directory / name)[1] for name in FILES},
        },
    )
    write_json(
        directory / "items_transformed.json", [record("unverified") | {"o:id": 2}]
    )
    loaded, _, full = load_backup(directory)
    assert full and loaded == snapshot


def test_order_required_links_and_report_cycles():
    from sgb_validator.recovery import creation_order

    class TemplateAPI:
        def get(self, kind, rid):
            assert kind == "resource_templates" and rid == 4
            return {
                "o:resource_template_property": [
                    {"o:property": {"o:id": 13}, "o:is_required": True},
                ]
            }

    def depends_on(rid, target):
        return {
            "o:id": rid,
            "o:resource_template": {"o:id": 4},
            "dcterms:relation": [
                {
                    "type": "resource:item",
                    "property_id": 13,
                    "value_resource_id": target,
                },
            ],
        }

    a = ("items", depends_on(1, 2))
    b = ("items", {"o:id": 2})
    assert creation_order(TemplateAPI(), [a, b], "https://omeka.example") == [b, a]
    with pytest.raises(OmekaError, match=r"Required-link cycle.*items/1.*items/2"):
        creation_order(
            TemplateAPI(), [a, ("items", depends_on(2, 1))], "https://omeka.example"
        )


def test_pending_creation_does_not_adopt_a_preexisting_record_after_retries(tmp_path):
    from sgb_validator.recovery import restore_records

    class UnavailableAPI:
        base_url = "https://omeka.example"

        def get(self, kind, rid):
            raise OmekaError("Not found", 404)

        def listing(self, kind, **scope):
            return [{"o:id": 2, "o:is_public": True}]

        def post(self, *args, **kwargs):
            raise OmekaError("POST failed")

    snapshot = Snapshot(
        {"o:id": 1, "o:is_public": True}, [], [], UnavailableAPI.base_url
    )
    progress = tmp_path / "restore-progress.json"
    for _ in range(3):
        with pytest.raises(OmekaError, match="POST failed"):
            restore_records(
                UnavailableAPI(),
                tmp_path,
                snapshot,
                {},
                True,
                progress,
                "backup",
                True,
                0,
                lambda _: None,
            )
        state = read_json(progress)
        assert state["pending"]["1"]["before"] == [2]
        assert state["ids"] == {}
