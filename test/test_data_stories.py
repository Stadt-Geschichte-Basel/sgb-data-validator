"""Tests for the Data Story archive script (#44)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import archive_data_stories as ads  # noqa: E402

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
    ads.write_manifest("schulden", [ROW])
    posted = []

    class FakeOmeka:
        def get(self, kind, rid):
            return {"dcterms:temporal": [{"@value": "Mittelalter"}]}

        def find(self, kind, identifier):
            return [{"o:id": 999}]

        def post(self, *args, **kwargs):
            posted.append(args)

    monkeypatch.setattr(ads, "Omeka", FakeOmeka)
    assert ads.upload("schulden", apply=True, limit=None) == 0
    assert posted == []
    assert ads.read_manifest("schulden")[0]["omeka_item"] == "999"
