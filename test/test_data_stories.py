"""Tests for the Data Story archive script (#44)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import archive_data_stories as ads  # noqa: E402
import pytest  # noqa: E402

from sgb_validator.api import OmekaHTTPError  # noqa: E402


@pytest.fixture(autouse=True)
def fake_find(monkeypatch):
    """Let the duck-typed fakes answer identifier searches."""
    monkeypatch.setattr(ads, "find", lambda api, kind, value: api.find(kind, value))


STORY = {
    "root": "n-root",
    "nodes": {
        "n-root": {"type": "story", "children": ["n-h", "n-slide", "n-img2"]},
        "n-h": {"type": "text", "data": {"type": "h2", "text": "Einleitung"}},
        "n-slide": {"type": "immersive-slide", "children": ["n-panel", "n-img1"]},
        "n-panel": {"type": "immersive-narrative-panel", "children": ["n-q"]},
        "n-q": {
            "type": "text",
            "data": {
                "type": "paragraph",
                "text": "Quelle: StABS, Gerichtsarchiv E 7, 46r",
            },
        },
        "n-img1": {"type": "image", "data": {"image": "r-1"}},
        "n-img2": {
            "type": "image",
            "data": {"image": "r-2", "caption": "<em>Bild</em>"},
        },
    },
}

ROW = {
    "identifier": "ds-schulden-02",
    "kind": "image",
    "decision": "ingest",
    "rights_status": "story_cleared",
    "title": "Urteil des Stadtgerichts, 1497",
    "description": "Eintrag im Urteilsbuch.",
    "creator": "Schultheissengericht Grossbasel",
    "holder": "Staatsarchiv Basel-Stadt",
    "shelfmark": "Gerichtsarchiv A 41, fol. 247v",
    "rights": "Bilddaten gemeinfrei, Staatsarchiv Basel-Stadt, Gerichtsarchiv A 41",
    "license": "https://creativecommons.org/publicdomain/mark/1.0/",
    "file": "files/x.jpg",
    "mime": "image/jpeg",
    "width": "1260",
    "height": "570",
}


def test_walk_finds_slide_source_and_heading():
    media = ads.walk(STORY["nodes"], STORY["root"])
    assert [m[0] for m in media] == ["n-img1", "n-img2"]
    node_id, _, heading, _, source = media[0]
    assert heading == "Einleitung"
    assert source == "Quelle: StABS, Gerichtsarchiv E 7, 46r"
    assert media[1][4] == ""


def test_payloads_pass_the_validator_and_stay_private():
    item = ads.item_payload("schulden", ROW, ["Mittelalter"])
    media = ads.media_payload("schulden", ROW, None, ["Mittelalter"])
    assert ads.validation_errors(item, "item") == []
    assert ads.validation_errors(media, "media") == []
    assert item["o:is_public"] is False and media["o:is_public"] is False
    assert (
        item["dcterms:isPartOf"][0]["@id"] == "https://doi.org/10.5281/zenodo.17192327"
    )
    assert media["dcterms:identifier"][0]["@value"] == "m-ds-schulden-02_1"
    assert ads.AI_NOTE in media["dcterms:description"][0]["@value"]


def test_verified_needs_evidence():
    row = {**ROW, "rights_status": "verified"}
    assert "verified without rights_evidence" in ads.rights_problems(row)
    row["rights_evidence"] = "https://example.org/terms"
    assert ads.rights_problems(row) == []
    assert ads.item_payload("schulden", row, [])["o:is_public"] is True


def test_upload_skips_existing_identifier(tmp_path, monkeypatch):
    monkeypatch.setattr(ads, "WORK", tmp_path)
    file = tmp_path / "schulden" / ROW["file"]
    file.parent.mkdir(parents=True)
    file.write_bytes(b"jpg")
    size, digest = ads.file_digest(file)
    ads.write_manifest("schulden", [ROW])
    posted = []

    expected = ads.create_payload(
        "media",
        ads.media_payload("schulden", ROW, None, ["Mittelalter"]),
        target_id=999,
        file=file,
    )
    existing_media = {**expected, "o:id": 5, "o:size": size, "o:sha256": digest}

    class FakeOmeka:
        def get(self, kind, rid):
            if kind == "media":
                return existing_media
            return {"dcterms:temporal": [{"@value": "Mittelalter"}]}

        def find(self, kind, identifier):
            if kind == "items":
                return [
                    {
                        "o:id": 999,
                        "o:media": [{"o:id": 5}],
                        "o:item_set": [{"o:id": ads.ITEM_SET_ID}],
                    }
                ]
            return [existing_media]

        def post(self, *args, **kwargs):
            posted.append(args)

    title = existing_media.pop("dcterms:title")
    assert ads.upload_rows(FakeOmeka(), "schulden", apply=True, limit=None) == 1
    assert not ads.read_manifest("schulden")[0]["omeka_media"]
    existing_media["dcterms:title"] = title
    assert ads.upload_rows(FakeOmeka(), "schulden", apply=True, limit=None) == 0
    assert posted == []
    assert ads.read_manifest("schulden")[0]["omeka_item"] == "999"


def test_upload_resumes_item_without_media(tmp_path, monkeypatch):
    monkeypatch.setattr(ads, "WORK", tmp_path)
    (tmp_path / "schulden" / "files").mkdir(parents=True)
    (tmp_path / "schulden" / "files" / "x.jpg").write_bytes(b"jpg")
    ads.write_manifest("schulden", [ROW])
    posted = []

    class FakeOmeka:
        def get(self, kind, rid):
            return {
                "dcterms:temporal": [{"@value": "Mittelalter"}],
                "o:media": [{"o:id": 5}],
            }

        def find(self, kind, identifier):
            return (
                [
                    {
                        "o:id": 999,
                        "o:media": [],
                        "o:item_set": [{"o:id": ads.ITEM_SET_ID}],
                    }
                ]
                if kind == "items"
                else []
            )

    def create(api, kind, payload, *, target_id, file, apply):
        posted.append((kind, target_id, file.name))
        return {"o:id": 5}

    monkeypatch.setattr(ads, "create_record", create)

    assert ads.upload_rows(FakeOmeka(), "schulden", apply=True, limit=None) == 0
    assert posted == [("media", 999, "x.jpg")]
    row = ads.read_manifest("schulden")[0]
    assert (row["omeka_item"], row["omeka_media"]) == ("999", "5")


def test_walk_takes_sidecar_text_from_the_same_slide():
    nodes = {
        "root": {"type": "story", "children": ["s1", "s2"]},
        "s1": {"type": "immersive-slide", "children": ["p1", "i1"]},
        "p1": {"type": "immersive-narrative-panel", "children": ["t1"]},
        "t1": {"type": "text", "data": {"type": "paragraph", "text": "Text A"}},
        "i1": {"type": "image", "data": {}},
        "s2": {"type": "immersive-slide", "children": ["p2", "i2"]},
        "p2": {"type": "immersive-narrative-panel", "children": ["t2"]},
        "t2": {"type": "text", "data": {"type": "paragraph", "text": "Text B"}},
        "i2": {"type": "image", "data": {}},
    }
    media = ads.walk(nodes, "root")
    assert [(m[0], m[3]) for m in media] == [("i1", "Text A"), ("i2", "Text B")]


def test_walk_does_not_take_text_across_the_next_media():
    nodes = {
        "root": {"type": "story", "children": ["i1", "i2", "t2"]},
        "i1": {"type": "image", "data": {}},
        "i2": {"type": "image", "data": {}},
        "t2": {"type": "text", "data": {"type": "paragraph", "text": "Text B"}},
    }
    media = ads.walk(nodes, "root")
    assert [(m[0], m[3]) for m in media] == [("i1", ""), ("i2", "Text B")]


def test_walk_gives_gallery_images_the_text_after_the_gallery():
    nodes = {
        "root": {"type": "story", "children": ["g", "t"]},
        "g": {"type": "gallery", "children": ["i1", "i2"]},
        "i1": {"type": "image", "data": {}},
        "i2": {"type": "image", "data": {}},
        "t": {"type": "text", "data": {"type": "paragraph", "text": "Text G"}},
    }
    media = ads.walk(nodes, "root")
    assert [(m[0], m[3]) for m in media] == [("i1", "Text G"), ("i2", "Text G")]


def test_walk_gives_the_first_of_six_gallery_images_the_text_after_it():
    images = [f"i{n}" for n in range(1, 7)]
    nodes = {
        "root": {"type": "story", "children": ["g", "t"]},
        "g": {"type": "gallery", "children": images},
        "t": {"type": "text", "data": {"type": "paragraph", "text": "Text G"}},
        **{i: {"type": "image", "data": {}} for i in images},
    }
    media = ads.walk(nodes, "root")
    assert media[0][3] == "Text G"


def test_suggest_without_creator_does_not_fail():
    row = {"holder": "Stadt.Geschichte.Basel", "caption": "Karte"}
    ads.suggest(row, [])
    assert row["rights"] == "CC BY-SA 4.0"


def test_upload_resumes_from_a_manifest_with_omeka_item(tmp_path, monkeypatch):
    monkeypatch.setattr(ads, "WORK", tmp_path)
    (tmp_path / "schulden" / "files").mkdir(parents=True)
    (tmp_path / "schulden" / "files" / "x.jpg").write_bytes(b"jpg")
    ads.write_manifest("schulden", [{**ROW, "omeka_item": "999"}])
    posted = []

    class FakeOmeka:
        def get(self, kind, rid):
            return {
                "dcterms:temporal": [{"@value": "Mittelalter"}],
                "o:media": [{"o:id": 5}],
            }

        def find(self, kind, identifier):
            return (
                [
                    {
                        "o:id": 999,
                        "o:media": [],
                        "o:item_set": [{"o:id": ads.ITEM_SET_ID}],
                    }
                ]
                if kind == "items"
                else []
            )

    def create(api, kind, payload, **kwargs):
        posted.append(kind)
        return {"o:id": 5}

    monkeypatch.setattr(ads, "create_record", create)

    assert ads.upload_rows(FakeOmeka(), "schulden", apply=True, limit=None) == 0
    assert posted == ["media"]
    assert ads.read_manifest("schulden")[0]["omeka_media"] == "5"


def test_dry_run_leaves_the_manifest_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(ads, "WORK", tmp_path)
    (tmp_path / "schulden" / "files").mkdir(parents=True)
    (tmp_path / "schulden" / "files" / "x.jpg").write_bytes(b"jpg")
    path = ads.write_manifest("schulden", [ROW])
    before = path.read_text(encoding="utf-8")

    class FakeOmeka:
        def get(self, kind, rid):
            return {"dcterms:temporal": [{"@value": "Mittelalter"}]}

        def find(self, kind, identifier):
            return (
                [
                    {
                        "o:id": 999,
                        "o:media": [],
                        "o:item_set": [{"o:id": ads.ITEM_SET_ID}],
                    }
                ]
                if kind == "items"
                else []
            )

    assert ads.upload_rows(FakeOmeka(), "schulden", apply=False, limit=None) == 0
    assert path.read_text(encoding="utf-8") == before


def test_upload_skips_an_unsupported_kind(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ads, "WORK", tmp_path)
    ads.write_manifest("schulden", [{**ROW, "kind": "video"}])

    class FakeOmeka:
        def get(self, kind, rid):
            return {"dcterms:temporal": [{"@value": "Mittelalter"}]}

    assert ads.upload_rows(FakeOmeka(), "schulden", apply=False, limit=None) == 1
    assert "kind video not supported" in capsys.readouterr().out


def test_export_layer_raises_on_an_arcgis_error_body(tmp_path):
    import httpx2
    import pytest

    def handler(request):
        return httpx2.Response(200, json={"error": {"code": 499}})

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    with pytest.raises(httpx2.HTTPError):
        ads.export_layer(client, "https://x.example/FeatureServer/0", tmp_path / "a")
    assert not (tmp_path / "a").exists()


def test_parent_resumes_cleanup_with_replacement_already_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(ads, "ROOT", tmp_path)
    slug = "schulden"
    parent_id = ads.STORIES[slug]["item"]
    replacement = {
        "o:item": {"o:id": parent_id},
        "o:ingester": "upload",
        "dcterms:identifier": [ads.literal(10, "Identifier", f"m-story-{slug}")],
    }
    existing = {**replacement, "o:id": 4, "o:size": 3, "o:sha256": "digest"}
    old = {"o:id": 3}
    path = tmp_path / "backups" / f"story_{slug}_parent_cleanup.json"
    path.parent.mkdir()
    plan = {
        "source": "https://omeka.example",
        "parent": parent_id,
        "replacement": replacement,
        "original": [3, "digest"],
        "old_media": [{"o:id": 2}, old],
        "completed": [],
    }
    ads.write_json(path, plan)

    class FakeOmeka:
        installation_url = plan["source"]

        def __init__(self):
            self.records = {3: old, 4: existing}
            self.deleted = []

        def get(self, kind, rid):
            if kind == "items":
                return {
                    "o:id": parent_id,
                    "o:media": [{"o:id": media} for media in self.records],
                }
            if rid not in self.records:
                raise OmekaHTTPError("Not found", status=404)
            return self.records[rid]

        def delete(self, kind, rid):
            assert (kind, rid) == ("media", 3)
            self.deleted.append(self.records.pop(3)["o:id"])

    api = FakeOmeka()
    assert (
        ads.apply_parent(
            api,
            slug,
            tmp_path / "old-local-file",
            apply=True,
            delete_old=True,
            exclusive_write=True,
        )
        == 0
    )
    assert api.deleted == [3]
    assert ads.json.loads(path.read_text())["completed"] == [2, 3]
