"""Tests for the reviewed DSP-readiness edits."""

import json
import sys
from pathlib import Path

import pytest
from omeka_s_client.testing import FakeOmeka

from sgb_validator.api import Omeka

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fix_dsp_readiness as fix  # noqa: E402

SOURCE = {
    "type": "uri",
    "@id": "Baumbesetzung entlang des Cityrings, 1973",
    "o:label": "Keytsone, 119619131 (RM)",
    "property_id": 11,
    "property_label": "Source",
    "is_public": True,
}


def test_plan_replaces_matching_values():
    before = {"o:id": 1, "dcterms:source": [SOURCE]}
    edit = {
        "field": "dcterms:source",
        "old": [{k: SOURCE[k] for k in ("type", "@id", "o:label")}],
        "new": [{"type": "literal", "@value": "Keystone, 119619131 (RM)"}],
    }
    after = fix.plan_record(before, [edit])
    assert after["dcterms:source"] == [
        {
            "property_id": 11,
            "property_label": "Source",
            "is_public": True,
            "type": "literal",
            "@value": "Keystone, 119619131 (RM)",
        }
    ]
    assert before["dcterms:source"] == [SOURCE]


def test_plan_stops_when_live_value_changed():
    before = {"o:id": 1, "dcterms:source": [{**SOURCE, "o:label": "other"}]}
    edit = {"field": "dcterms:source", "old": [SOURCE], "new": []}
    with pytest.raises(ValueError, match="not as expected"):
        fix.plan_record(before, [edit])


def test_plan_adds_new_field_and_removes_empty_field():
    before = {"o:id": 1, "dcterms:identifier": [{"type": "literal", "@value": "a"}]}
    edits = [
        {"field": "dcterms:relation", "old": [], "new": [{"type": "uri", "@id": "x"}]},
        {
            "field": "dcterms:identifier",
            "old": [{"type": "literal", "@value": "a"}],
            "new": [],
        },
    ]
    after = fix.plan_record(before, edits)
    assert after["dcterms:relation"][0]["property_id"] == 13
    assert "dcterms:identifier" not in after


def test_plan_rejects_other_fields():
    with pytest.raises(ValueError, match="not allowed"):
        fix.plan_record({}, [{"field": "dcterms:title", "old": [], "new": []}])


def test_plan_keeps_private_visibility():
    before = {"o:id": 1, "dcterms:source": [{**SOURCE, "is_public": False}]}
    edit = {
        "field": "dcterms:source",
        "old": [SOURCE],
        "new": [{"type": "literal", "@value": "x"}],
    }
    assert fix.plan_record(before, [edit])["dcterms:source"][0]["is_public"] is False


def test_plan_rejects_mixed_visibility_without_explicit_flag():
    private = {**SOURCE, "@id": "b", "is_public": False}
    before = {"o:id": 1, "dcterms:source": [SOURCE, private]}
    old = [{k: v[k] for k in ("type", "@id", "o:label")} for v in (SOURCE, private)]
    new = [{"type": "literal", "@value": "a"}, {"type": "literal", "@value": "b"}]
    edit = {"field": "dcterms:source", "old": old, "new": new}
    with pytest.raises(ValueError, match="mixes public and private"):
        fix.plan_record(before, [edit])
    edit["new"] = [{**new[0], "is_public": True}, {**new[1], "is_public": False}]
    after = fix.plan_record(before, [edit])["dcterms:source"]
    assert [v["is_public"] for v in after] == [True, False]


def test_plan_keeps_language_tag():
    before = {"o:id": 1, "dcterms:source": [{**SOURCE, "@language": "en"}]}
    edit = {
        "field": "dcterms:source",
        "old": [SOURCE],
        "new": [{"type": "literal", "@value": "x"}],
    }
    assert fix.plan_record(before, [edit])["dcterms:source"][0]["@language"] == "en"


TIME = {"@type": "o:DateTime", "@value": "2020-01-01T00:00:00+00:00"}


def literal(text, pid, public=True):
    return {
        "type": "literal",
        "property_id": pid,
        "property_label": "x",
        "@value": text,
        "is_public": public,
    }


def item(rid, public=False, sets=(10780,), ident=None):
    return {
        "@context": "x",
        "@id": f"x/{rid}",
        "@type": "o:Item",
        "o:id": rid,
        "o:is_public": public,
        "o:title": "t",
        "o:created": TIME,
        "o:modified": TIME,
        "o:item_set": [{"o:id": s} for s in sets],
        "o:media": [],
        "dcterms:title": [literal("open", 1), literal("hidden", 1, False)],
        "dcterms:identifier": [literal(ident or f"ID{rid}", 10)],
    }


def vis(rid, expected=False, target=True, ident=None, kind="items"):
    return {
        "kind": kind,
        "id": rid,
        "identifier": ident or f"ID{rid}",
        "visibility": {"expected": expected, "target": target},
        "why": "test",
    }


def patches(fake):
    return [json.loads(r.content) for r in fake.requests if r.method == "PATCH"]


def go(fake, edits, tmp_path, **options):
    options = {"apply": True, "exclusive_write": True, "backup_dir": tmp_path} | options
    with Omeka("https://omeka.example", "id", "secret", transport=fake) as api:
        return fix.run(api, edits, **options)


def test_visibility_only_patch_keeps_private_value_and_rerun_is_empty(tmp_path):
    fake = FakeOmeka({"items": [item(1)]})
    assert go(fake, [vis(1)], tmp_path)["changed"] == 1
    assert patches(fake) == [{"o:is_public": True}]
    live = fake.records["items"][0]
    assert [v["is_public"] for v in live["dcterms:title"]] == [True, False]
    again = go(fake, [vis(1)], tmp_path)
    assert (again["changed"], again["unchanged"]) == (0, 1)
    assert len(patches(fake)) == 1


def test_preview_and_missing_exclusive_write_do_not_write(tmp_path):
    fake = FakeOmeka({"items": [item(1)]})
    assert go(fake, [vis(1)], tmp_path, apply=False)["changed"] == 1
    with pytest.raises(ValueError, match="exclusive-write"):
        go(fake, [vis(1)], tmp_path, exclusive_write=False)
    assert not patches(fake)


def test_value_edit_and_visibility_make_one_patch(tmp_path):
    fake = FakeOmeka({"items": [item(1)]})
    edit = {
        "kind": "items",
        "id": 1,
        "field": "dcterms:identifier",
        "old": [{"type": "literal", "@value": "ID1"}],
        "new": [
            {"type": "literal", "@value": "ID1"},
            {"type": "literal", "@value": "B"},
        ],
        "why": "test",
    }
    assert go(fake, [edit, vis(1)], tmp_path)["changed"] == 1
    assert len(patches(fake)) == 1
    live = fake.records["items"][0]
    assert live["o:is_public"] and len(live["dcterms:identifier"]) == 2
    assert go(fake, [edit, vis(1)], tmp_path)["changed"] == 0
    assert len(patches(fake)) == 1


@pytest.mark.parametrize(
    "first, entry",
    [
        (item(1), vis(1, ident="OTHER")),
        (item(1, sets=(5,)), vis(1)),
        (item(1), vis(1, expected=True, target=True)),
    ],
    ids=["identity", "item-set", "visibility"],
)
def test_mismatch_stops_the_run(tmp_path, first, entry):
    fake = FakeOmeka({"items": [first, item(2)]})
    result = go(fake, [entry, vis(2)], tmp_path)
    assert result["stopped"] and result["not_processed"] == ["items/2"]
    assert not patches(fake)


def test_media_uses_parent_item_set(tmp_path):
    medium = item(7, ident="M7") | {"o:item": {"o:id": 1}, "o:ingester": "html"}
    medium |= {"o:renderer": "html", "o:media_type": None, "@type": "o:Media"}
    del medium["o:item_set"], medium["o:media"]
    fake = FakeOmeka({"items": [item(1)], "media": [medium]})
    assert go(fake, [vis(7, ident="M7", kind="media")], tmp_path)["changed"] == 1
    assert patches(fake) == [{"o:is_public": True}]
