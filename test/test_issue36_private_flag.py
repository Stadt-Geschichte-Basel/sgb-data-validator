"""Placeholders keep their visibility.

Omeka needs a media child to carry media metadata. Where SGB may not publish
the file, the media holds the placeholder image. The metadata stays public.
DSP receives these media as metadata only (omeka2dsp).
"""

from test_issue57_dsp_checks import findings

from sgb_validator.transformations import (
    has_placeholder_media,
    transform_item_set_data,
    transform_media,
)
from sgb_validator.writes import create_payload

PLACEHOLDER = "sgb-fdp-platzhalter[1].png"


def test_has_placeholder_media_detection() -> None:
    assert has_placeholder_media({"o:filename": "image-sgb-fdp-platzhalter-01.jpg"})
    assert has_placeholder_media({"o:source": PLACEHOLDER})
    assert not has_placeholder_media({"o:filename": "regular-image.jpg"})
    assert has_placeholder_media(
        {
            "o:source": "upload.png",
            "o:sha256": "2c07e74c08e23923b89470509d095b329e7d77d6bd2e9212b2a773c97ab4c16e",
        }
    )
    assert not has_placeholder_media({"o:source": "a.png", "o:sha256": "0" * 64})
    assert not has_placeholder_media({"o:source": "a.png", "o:sha256": ["x"]})
    assert not has_placeholder_media(None)  # type: ignore[arg-type]
    assert not has_placeholder_media("not a dict")  # type: ignore[arg-type]


def test_transform_media_keeps_placeholder_public() -> None:
    media = {"o:id": 1, "o:source": PLACEHOLDER, "o:is_public": True}
    assert transform_media(media)["o:is_public"] is True
    assert transform_media(media, apply_all=True)["o:is_public"] is True


def test_transform_item_set_keeps_visibility() -> None:
    items = [
        {"o:id": 10, "o:is_public": True},
        {"o:id": 11, "o:is_public": True},
    ]
    media = [
        {"o:id": 1, "o:item": {"o:id": 10}, "o:source": PLACEHOLDER},
        {"o:id": 2, "o:item": {"o:id": 11}, "o:is_public": False},
    ]
    _, new_items, new_media = transform_item_set_data({"o:id": 5}, items, media)
    assert [item["o:is_public"] for item in new_items] == [True, True]
    assert "o:is_public" not in new_media[0]
    assert new_media[1]["o:is_public"] is False


def test_validation_has_no_visibility_warning_for_placeholders() -> None:
    from test_issue16_validation import create_minimal_media

    media = create_minimal_media(1)
    media["o:source"] = PLACEHOLDER
    media["o:is_public"] = True
    result = findings(media=media)
    assert not [w for w in result.warnings if w.field == "o:is_public"]


def test_create_payload_keeps_placeholder_visibility(tmp_path) -> None:
    file = tmp_path / PLACEHOLDER
    file.write_bytes(b"placeholder")
    data = {"o:is_public": True}
    payload = create_payload("media", data, target_id=10, file=file)
    assert payload["o:is_public"] is True
