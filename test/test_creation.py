"""Exercise guarded creation and update with Omeka JSON."""

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlsplit

import pytest
from omeka_s_client.testing import FakeOmeka
from test_issue16_validation import create_minimal_item

from sgb_validator.api import Omeka, OmekaError
from sgb_validator.writes import create_payload, create_record, update_record


def literal(value, pid=10):
    return [{"type": "literal", "property_id": pid, "@value": value, "is_public": True}]


class Server:
    """Run FakeOmeka behind an Omeka client and record each request."""

    def __init__(self, records, before_second_read=None, after_create=None):
        self.fake = FakeOmeka({"items": [], "media": [], **records})
        self.before_second_read = before_second_read
        self.after_create = after_create
        self.record_reads = 0

    def __call__(self, request):
        path = urlsplit(request.url).path
        if request.method == "GET" and path.count("/") == 3:
            self.record_reads += 1
            if self.record_reads == 2 and self.before_second_read:
                self.before_second_read(self.fake)
        response = self.fake(request)
        if request.method == "POST" and self.after_create:
            self.after_create(self.fake)
        return response

    def client(self):
        return Omeka("https://omeka.example", "identity", "secret", transport=self)

    @property
    def writes(self):
        return [r for r in self.fake.requests if r.method != "GET"]

    @property
    def reads(self):
        return [r for r in self.fake.requests if r.method == "GET"]


def test_create_preview_includes_target_and_excludes_server_fields():
    server = Server({"item_sets": [{"o:id": 3}], "items": []})
    data = {"o:id": 101, "dcterms:identifier": literal("new")}
    with server.client() as api:
        plan = create_record(api, "items", data, target_id=3)
    assert plan == {"o:item_set": [{"o:id": 3}], "dcterms:identifier": literal("new")}
    assert not server.writes
    assert data["o:id"] == 101


def test_duplicate_identifier_blocks_creation():
    existing = {"o:id": 9, "dcterms:identifier": literal("existing")}
    server = Server({"item_sets": [{"o:id": 3}], "items": [existing]})
    with (
        server.client() as api,
        pytest.raises(OmekaError, match="Identifier collision"),
    ):
        create_record(
            api,
            "items",
            {"dcterms:identifier": literal("existing")},
            target_id=3,
            apply=True,
        )
    assert not server.writes


def test_create_item_writes_and_reads_back():
    server = Server({"item_sets": [{"o:id": 3}], "items": []})
    data = {"o:is_public": False, "dcterms:identifier": literal("new")}
    with server.client() as api:
        record = create_record(api, "items", data, target_id=3, apply=True)
    assert record["o:id"] == 1
    assert record["o:item_set"] == [{"o:id": 3}]
    assert [r.method for r in server.writes] == ["POST"]
    assert json.loads(server.writes[0].content)["dcterms:identifier"] == literal("new")


def test_create_media_uploads_the_file_as_the_first_part(tmp_path):
    file = tmp_path / "scan.png"
    file.write_bytes(b"image bytes")
    content = b"image bytes"

    def store_file_metadata(fake):
        # Omeka computes the size and digest of each upload.
        fake.records["media"][-1].update(
            {"o:size": len(content), "o:sha256": hashlib.sha256(content).hexdigest()}
        )

    server = Server(
        {"items": [{"o:id": 4, "o:is_public": False}]},
        after_create=store_file_metadata,
    )
    data = {"dcterms:identifier": literal("scan"), "o:source": "scan.png"}
    with server.client() as api:
        record = create_record(api, "media", data, target_id=4, file=file, apply=True)
    assert record["o:item"] == {"o:id": 4}
    (post,) = server.writes
    assert post.headers["content-type"].startswith("multipart/form-data")
    assert b'name="file[0]"; filename="scan.png"' in post.content
    assert b'"file_index": 0' in post.content


def test_create_media_rejects_a_different_upload_digest(tmp_path):
    file = tmp_path / "scan.png"
    file.write_bytes(b"image bytes")
    server = Server({"items": [{"o:id": 4, "o:is_public": False}]})
    data = {"dcterms:identifier": literal("scan"), "o:source": "scan.png"}
    with server.client() as api, pytest.raises(OmekaError, match="SHA-256"):
        create_record(api, "media", data, target_id=4, file=file, apply=True)


def test_upload_requires_a_parent_and_a_file(tmp_path):
    with pytest.raises(ValueError, match="parent item"):
        create_payload("media", {"o:ingester": "upload"})
    with pytest.raises(ValueError, match="Missing media file"):
        create_payload("media", {}, target_id=3, file=tmp_path / "missing")


def test_concurrent_edit_detected_after_before_copy(tmp_path):
    before = {**create_minimal_item(3), "dcterms:identifier": literal("source")}
    server = Server(
        {"items": [before]},
        before_second_read=lambda fake: fake.records["items"][0].update(
            {"dcterms:creator": literal("editor", 2)}
        ),
    )
    after = {**before, "dcterms:identifier": literal("changed")}
    with server.client() as api, pytest.raises(OmekaError, match="immediately before"):
        update_record(
            api,
            "items",
            before,
            after,
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not server.writes
    copy = next(tmp_path.iterdir())
    assert copy.stat().st_mode & 0o777 == 0o600


def test_recent_edit_is_skipped(tmp_path):
    before = {"o:id": 3, "o:modified": {"@value": datetime.now(UTC).isoformat()}}
    server = Server({"items": [before]})
    with server.client() as api, pytest.raises(OmekaError, match="edited within"):
        update_record(
            api,
            "items",
            before,
            {**before, "o:is_public": False},
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not server.writes


def test_update_preserves_unrelated_fields(tmp_path):
    before = {
        **create_minimal_item(3),
        "o:is_public": False,
        "dcterms:identifier": literal("source"),
        "custom:field": literal("preserve", 123),
    }
    server = Server({"items": [before]})
    after = {**before, "dcterms:identifier": literal("changed")}
    with server.client() as api:
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
    (patch,) = server.writes
    assert patch.method == "PATCH"
    payload = json.loads(patch.content)
    assert "o:is_public" not in payload
    assert payload["custom:field"] == before["custom:field"]


def test_already_applied_is_distinct_from_a_preview():
    before = create_minimal_item(3)
    after = {**before, "o:is_public": False}
    with Server({"items": [after]}).client() as api:
        assert update_record(api, "items", before, after).status == "already_applied"
    server = Server({"items": [before]})
    with server.client() as api:
        assert update_record(api, "items", before, after).status == "preview"
    assert not server.writes


@pytest.mark.parametrize(
    "value", ["not a list", [{"type": "literal", "property_id": 4, "@value": 42}]]
)
def test_malformed_property_cannot_be_written(tmp_path, value):
    before = create_minimal_item(3)
    server = Server({"items": [before]})
    with (
        server.client() as api,
        pytest.raises((ValueError, OmekaError), match="dcterms:description"),
    ):
        update_record(
            api,
            "items",
            before,
            {**before, "dcterms:description": value},
            apply=True,
            exclusive_write=True,
            backup_dir=tmp_path,
        )
    assert not server.writes
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize("value", [42, "", " \n"])
def test_create_rejects_invalid_native_literals_before_http(apply, value):
    server = Server({"item_sets": [{"o:id": 3}]})
    with (
        server.client() as api,
        pytest.raises(ValueError, match="dcterms:description.*non-empty string"),
    ):
        create_record(
            api,
            "items",
            {"dcterms:description": literal(value, 4)},
            target_id=3,
            apply=apply,
        )
    assert not server.fake.requests


def test_create_rejects_malformed_item_set_references():
    with pytest.raises(ValueError, match="o:item_set.*integer o:id"):
        create_payload("items", {"o:item_set": [{"o:id": 5}, {}]}, target_id=3)


def test_update_requires_an_exclusive_write_window():
    before = create_minimal_item(3)
    server = Server({"items": [before]})
    with server.client() as api, pytest.raises(ValueError, match="maintenance window"):
        update_record(
            api, "items", before, {**before, "o:is_public": False}, apply=True
        )
    assert not server.fake.requests
