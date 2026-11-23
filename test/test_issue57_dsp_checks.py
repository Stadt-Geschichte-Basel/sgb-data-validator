"""Check the DSP conversion checks from issue 57."""

import pytest
from test_issue16_validation import create_minimal_item, create_minimal_media
from test_offline_workflow import api_for, source  # noqa: F401
from typer.testing import CliRunner

from sgb_validator import cli
from sgb_validator.cli import app
from sgb_validator.validation import validate_records
from sgb_validator.vocabularies import VocabularyLoader

VOCAB = VocabularyLoader()


def findings(*, item=None, media=None, **kwargs):
    item = item or create_minimal_item(1)
    media = media or create_minimal_media(1)
    for record in (item, media):
        for key, values in record.items():
            if key.startswith("dcterms:"):
                for value in values:
                    value.setdefault("property_id", 1)
                    value.setdefault("is_public", True)
                    value.setdefault("property_label", "Label")
    return validate_records([item], [media], VOCAB, **kwargs)


def errors_for(result, field):
    return [e for e in result.errors if e.field.startswith(field)]


def entry(value):
    return prop(type="literal", **{"@value": value})


def prop(**fields):
    return {"property_id": 1, "is_public": True, **fields}


def test_two_is_part_of_values_fail():
    item = create_minimal_item(1)
    item["dcterms:isPartOf"] = [entry("a"), entry("b")]
    assert errors_for(findings(item=item), "dcterms:isPartOf")


def test_language_uri_without_value_fails():
    item = create_minimal_item(1)
    uri = "http://id.loc.gov/vocabulary/iso639-2/lat"
    item["dcterms:language"] = [
        prop(**{"type": "valuesuggest:lc:iso6392", "@id": uri, "o:label": "Latein"})
    ]
    errors = errors_for(findings(item=item), "dcterms:language[0]")
    assert [e.error for e in errors] == [
        f"Use a literal language code, not a URI: {uri}"
    ]


@pytest.mark.parametrize(("code", "valid"), [("ar", True), ("AR", True), ("xx", False)])
def test_language_codes(code, valid):
    item = create_minimal_item(1)
    item["dcterms:language"] = [entry(code)]
    assert bool(errors_for(findings(item=item), "dcterms:language")) is not valid


@pytest.mark.parametrize(("value", "valid"), [("im", False), ("image", True)])
def test_type_value(value, valid):
    media = create_minimal_media(1)
    media["dcterms:type"] = [{"type": "valuesuggestall:dc:types", "@value": value}]
    assert bool(errors_for(findings(media=media), "dcterms:type")) is not valid


def test_interactive_resource_uri_passes():
    media = create_minimal_media(1)
    media["dcterms:type"] = [
        {
            "type": "valuesuggestall:dc:types",
            "@id": "http://purl.org/dc/dcmitype/InteractiveResource",
            "o:label": "Interactive Resource",
        }
    ]
    assert not errors_for(findings(media=media), "dcterms:type")


def test_swapped_uri_fails():
    item = create_minimal_item(1)
    item["dcterms:creator"] = [
        {
            "type": "valuesuggest:wikidata",
            "@id": "Hans Holbein d. j.",
            "o:label": "https://www.wikidata.org/wiki/Q9374",
        }
    ]
    errors = errors_for(findings(item=item), "dcterms:creator[0]")
    assert "swapped" in errors[0].error


def test_uri_with_space_fails():
    item = create_minimal_item(1)
    item["dcterms:source"] = [
        {"type": "uri", "@id": "http:// www.e-codices.ch/x", "o:label": "x"}
    ]
    assert "Invalid URI" in errors_for(findings(item=item), "dcterms:source")[0].error


def test_unparsable_uri_fails():
    item = create_minimal_item(1)
    item["dcterms:source"] = [{"type": "uri", "@id": "http://[", "o:label": "x"}]
    assert "Invalid URI" in errors_for(findings(item=item), "dcterms:source")[0].error


def test_legacy_subject_uri_is_not_checked():
    item = create_minimal_item(1)
    item["dcterms:subject"] = [{"type": "uri", "@id": "urn:legacy:subject"}]
    assert not errors_for(findings(item=item), "dcterms:subject")


def test_resource_link_is_not_flagged():
    item = create_minimal_item(1)
    item["dcterms:isPartOf"] = [
        {"type": "resource:item", "value_resource_id": 5, "@id": "api/items/5"}
    ]
    assert not errors_for(findings(item=item), "dcterms:isPartOf")


def test_file_size_warning():
    media = create_minimal_media(1)
    media["o:size"] = 600_000_000
    warnings = [w for w in findings(media=media).warnings if w.field == "o:size"]
    assert warnings[0].message == (
        "File is 600 MB; DSP conversion may fail above 500 MB"
    )
    media["o:size"] = 400_000_000
    assert not [w for w in findings(media=media).warnings if w.field == "o:size"]


def test_file_size_check_can_be_off():
    media = create_minimal_media(1)
    media["o:size"] = 600_000_000
    result = findings(media=media, max_file_size=None)
    assert not [w for w in result.warnings if w.field == "o:size"]


def test_download_needs_keys_or_public_only(monkeypatch, tmp_path, source):  # noqa: F811
    monkeypatch.delenv("KEY_IDENTITY", raising=False)
    monkeypatch.delenv("KEY_CREDENTIAL", raising=False)
    monkeypatch.setattr(cli, "connect", lambda *_: api_for(source))
    args = ["download", "--item-set-id", "1", "--output-dir", str(tmp_path)]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert "--public-only" in result.output
    result = CliRunner().invoke(app, [*args, "--public-only"])
    assert result.exit_code == 0, result.output


def test_live_validate_needs_keys_or_public_only(monkeypatch, source):  # noqa: F811
    monkeypatch.delenv("KEY_IDENTITY", raising=False)
    monkeypatch.delenv("KEY_CREDENTIAL", raising=False)
    monkeypatch.setattr(cli, "connect", lambda *_: api_for(source))
    result = CliRunner().invoke(app, ["validate", "--item-set-id", "1"])
    assert result.exit_code == 1
    assert "--public-only" in result.output
    result = CliRunner().invoke(
        app, ["validate", "--item-set-id", "1", "--public-only"]
    )
    assert "--public-only" not in result.output


@pytest.mark.parametrize("code", ["he", "gsw", "gmh"])
def test_dsp_language_codes_without_iso639_1_pass(code):
    item = create_minimal_item(1)
    item["dcterms:language"] = [entry(code)]
    assert not errors_for(findings(item=item), "dcterms:language")


def test_cc_by_nc_nd_license_passes():
    assert VOCAB.is_valid_license("https://creativecommons.org/licenses/by-nc-nd/4.0/")
