"""Exercise guarded creation and update with Omeka JSON."""

from copy import deepcopy

import pytest
from test_issue16_validation import create_minimal_item

from sgb_validator.api import OmekaError
from sgb_validator.writes import create_payload, create_record, update_record


def literal(value, pid=10):
    return [{"type": "literal", "property_id": pid, "@value": value, "is_public": True}]


class FakeAPI:
    def __init__(self, record, matches=()):
        self.record = record
        self.matches = matches
        self.writes = []
        self.reads = 0
        self.before_last_read = None

    def get(self, kind, rid):
        self.reads += 1
        if self.reads == 2 and self.before_last_read:
            self.before_last_read()
        return deepcopy(self.record)

    def find(self, *args):
        return list(self.matches)

    def post(self, *args, **kwargs):
        self.writes.append(args)
        raise AssertionError("Unexpected POST")

    def patch(self, kind, rid, payload):
        self.writes.append((kind, rid, payload))
        self.record.update(
            {key: val for key, val in payload.items() if key != "clear_property_values"}
        )


def test_create_preview_includes_target_and_excludes_server_fields():
    api = FakeAPI({"o:id": 3})
    data = {"o:id": 101, "dcterms:identifier": literal("new")}
    plan = create_record(api, "items", data, target_id=3)
    assert plan == {"o:item_set": [{"o:id": 3}], "dcterms:identifier": literal("new")}
    assert not api.writes
    assert data["o:id"] == 101


def test_duplicate_identifier_blocks_creation():
    api = FakeAPI({"o:id": 3}, matches=[{"o:id": 9}])
    with pytest.raises(OmekaError, match="Identifier collision"):
        create_record(
            api,
            "items",
            {"dcterms:identifier": literal("existing")},
            target_id=3,
            apply=True,
        )
    assert not api.writes


def test_upload_requires_a_parent_and_a_file(tmp_path):
    with pytest.raises(ValueError, match="parent item"):
        create_payload("media", {"o:ingester": "upload"})
    with pytest.raises(ValueError, match="Missing media file"):
        create_payload("media", {}, target_id=3, file=tmp_path / "missing")


def test_concurrent_edit_detected_after_before_copy(tmp_path):
    before = {**create_minimal_item(3), "dcterms:identifier": literal("source")}
    api = FakeAPI(deepcopy(before))
    api.before_last_read = lambda: api.record.update(
        {"dcterms:creator": literal("editor", 2)}
    )
    after = {**before, "dcterms:identifier": literal("changed")}
    with pytest.raises(OmekaError, match="immediately before"):
        update_record(
            api,
            "items",
            before,
            after,
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not api.writes
    copy = next(tmp_path.iterdir())
    assert copy.stat().st_mode & 0o777 == 0o600


def test_recent_edit_is_skipped(tmp_path):
    from datetime import UTC, datetime

    before = {"o:id": 3, "o:modified": {"@value": datetime.now(UTC).isoformat()}}
    api = FakeAPI(before)
    with pytest.raises(OmekaError, match="edited within"):
        update_record(
            api,
            "items",
            before,
            {**before, "o:is_public": False},
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not api.writes


def test_update_preserves_unrelated_fields(tmp_path):
    before = {
        **create_minimal_item(3),
        "o:is_public": False,
        "dcterms:identifier": literal("source"),
        "custom:field": literal("preserve", 123),
    }
    api = FakeAPI(deepcopy(before), matches=[{"o:id": 3}])
    after = {**before, "dcterms:identifier": literal("changed")}
    result = update_record(
        api,
        "items",
        before,
        after,
        apply=True,
        exclusive_write=True,
        backup_dir=tmp_path,
    )
    assert result.status == "updated"
    assert result.record["custom:field"] == before["custom:field"]
    assert result.record["dcterms:identifier"] == after["dcterms:identifier"]
    _, _, payload = api.writes[0]
    assert "o:is_public" not in payload
    assert payload["custom:field"] == before["custom:field"]


def test_already_applied_is_distinct_from_a_preview():
    before = create_minimal_item(3)
    after = {**before, "o:is_public": False}
    api = FakeAPI(after)
    assert update_record(api, "items", before, after).status == "already_applied"
    assert not api.writes
    api.record = before
    assert update_record(api, "items", before, after).status == "preview"


@pytest.mark.parametrize(
    "value", ["not a list", [{"type": "literal", "property_id": 4, "@value": 42}]]
)
def test_malformed_property_cannot_be_written(tmp_path, value):
    before = create_minimal_item(3)
    api = FakeAPI(before)
    with pytest.raises((ValueError, OmekaError), match="dcterms:description"):
        update_record(
            api,
            "items",
            before,
            {**before, "dcterms:description": value},
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not api.writes
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize("value", [42, "", " \n"])
def test_create_rejects_invalid_native_literals_before_http(apply, value):
    api = FakeAPI({"o:id": 3})
    with pytest.raises(ValueError, match="dcterms:description.*non-empty string"):
        create_record(
            api,
            "items",
            {"dcterms:description": literal(value, 4)},
            target_id=3,
            apply=apply,
        )
    assert not api.reads and not api.writes


def test_create_rejects_malformed_item_set_references():
    with pytest.raises(ValueError, match="o:item_set.*integer o:id"):
        create_payload("items", {"o:item_set": [{"o:id": 5}, {}]}, target_id=3)


def test_update_requires_an_exclusive_write_window():
    before = create_minimal_item(3)
    api = FakeAPI(before)
    with pytest.raises(ValueError, match="maintenance window"):
        update_record(
            api, "items", before, {**before, "o:is_public": False}, apply=True
        )
    assert not api.reads and not api.writes
