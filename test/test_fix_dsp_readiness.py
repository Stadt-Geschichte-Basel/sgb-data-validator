"""Tests for the reviewed DSP-readiness edits."""

import sys
from pathlib import Path

import pytest

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
