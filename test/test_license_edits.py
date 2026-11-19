"""Tests for the rights / license edit mode and its CSV builder (#44)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_license_edits import build_rows, fix_typos  # noqa: E402
from fix_safe_validation_errors import plan_edits  # noqa: E402
from generate_triage import suggested_license_uri  # noqa: E402

BY = "https://creativecommons.org/licenses/by/4.0/"
BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
PDM = "https://creativecommons.org/publicdomain/mark/1.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
INC = "http://rightsstatements.org/vocab/InC/1.0/"


def lic(uri: str) -> list[dict]:
    return [
        {
            "type": "customvocab:16",
            "property_id": 49,
            "property_label": "License",
            "is_public": True,
            "@value": uri,
            "@language": "en",
        }
    ]


def rights(text: str) -> list[dict]:
    return [
        {
            "type": "literal",
            "property_id": 15,
            "property_label": "Rights",
            "is_public": True,
            "@value": text,
        }
    ]


def row(field: str, old: str, new: str) -> dict:
    return {"kind": "media", "id": "1", "field": field, "old": old, "new": new}


def test_license_value_is_replaced_in_place():
    rec = {"o:id": 1, "dcterms:license": lic(BY), "dcterms:title": [{"@value": "t"}]}
    new, reason = plan_edits(rec, [row("dcterms:license", BY, BY_SA)])
    assert reason is None
    assert new["dcterms:license"] == lic(BY_SA)
    assert new["dcterms:title"] == rec["dcterms:title"]


def test_missing_license_is_added_with_the_vocabulary_shape():
    new, reason = plan_edits({"o:id": 1}, [row("dcterms:license", "", PDM)])
    assert reason is None
    assert new["dcterms:license"] == lic(PDM)


def test_changed_old_value_blocks_the_record():
    rec = {"o:id": 1, "dcterms:license": lic(BY_SA)}
    new, reason = plan_edits(rec, [row("dcterms:license", BY, BY_SA)])
    assert new is None
    assert "not" in reason


def test_noop_row_is_reported_as_no_change():
    rec = {"o:id": 1, "dcterms:license": lic(BY_SA)}
    new, reason = plan_edits(rec, [row("dcterms:license", BY_SA, BY_SA)])
    assert (new, reason) == (None, "no change")


def test_two_fields_of_one_record_are_applied_together():
    rec = {
        "o:id": 1,
        "dcterms:rights": rights("CC BY-SA 4.0., HMB"),
        "dcterms:license": lic(PDM),
    }
    new, reason = plan_edits(
        rec,
        [
            row("dcterms:rights", "CC BY-SA 4.0., HMB", "CC BY-SA 4.0, HMB"),
            row("dcterms:license", PDM, BY_SA),
        ],
    )
    assert reason is None
    assert new["dcterms:rights"][0]["@value"] == "CC BY-SA 4.0, HMB"
    assert new["dcterms:license"][0]["@value"] == BY_SA


def test_multiline_rights_need_the_exact_old_value():
    text = "CC BY-SA 4.0\nQuelle: X"
    rec = {"o:id": 1, "dcterms:rights": rights(text)}
    assert plan_edits(rec, [row("dcterms:rights", text, "CC BY-SA 4.0")])[1] is None
    assert (
        plan_edits(rec, [row("dcterms:rights", "CC BY-SA 4.0 Quelle: X", "x")])[0]
        is None
    )


def test_field_outside_the_allow_list_is_refused():
    new, reason = plan_edits({"o:id": 1}, [row("dcterms:title", "", "x")])
    assert new is None
    assert "not allowed" in reason


def test_suggested_license_uri_follows_the_text():
    assert suggested_license_uri("CC BY-SA 4.0, Foto X") == BY_SA
    assert suggested_license_uri("Public Domain Mark") == PDM
    assert suggested_license_uri("Bilddaten gemeinfrei, StABS") == PDM
    assert suggested_license_uri("In Copyright, Foto X") == INC
    assert suggested_license_uri("CC0") == CC0
    assert suggested_license_uri("icona basel, Christoph Gysin") is None


def test_typos_are_fixed_without_touching_good_text():
    assert fix_typos("Puböic Domain Mark") == "Public Domain Mark"
    assert fix_typos("CC BY-SA 4.0., Historisches Museum Basel") == (
        "CC BY-SA 4.0, Historisches Museum Basel"
    )
    assert fix_typos("Historisches Museum Base. Inv. Inv. 1882.87.") == (
        "Historisches Museum Basel, Inv. 1882.87."
    )
    good = "CC BY-SA 4.0, Historisches Museum Basel, Inv. 1901.42, Foto X"
    assert fix_typos(good) == good


def test_build_rows_uses_the_fixed_text_and_skips_matching_records():
    records = [
        {
            "o:id": 1,
            "dcterms:rights": rights("CC BY-SA 4.0"),
            "dcterms:license": lic(BY),
        },
        {
            "o:id": 2,
            "dcterms:rights": rights("CC BY-SA 4.0"),
            "dcterms:license": lic(BY_SA),
        },
        {"o:id": 3, "dcterms:rights": rights("Public Domain Mark")},
        {
            "o:id": 4,
            "dcterms:rights": rights("icona basel"),
            "dcterms:license": lic(INC),
        },
        {"o:id": 5},
    ]
    rows = build_rows(records)
    assert [(r["id"], r["field"], r["new"]) for r in rows] == [
        (1, "dcterms:license", BY_SA),
        (3, "dcterms:license", PDM),
    ]
