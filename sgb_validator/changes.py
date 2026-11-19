"""Calculate record changes and writable Omeka payloads."""

from copy import deepcopy

from .api import Record

COMMON_FIELDS = {
    "o:is_public",
    "o:owner",
    "o:resource_class",
    "o:resource_template",
    "o:thumbnail",
}
TYPE_FIELDS = {
    "items": {"o:item_set", "o:site", "o:media"},
    "item_sets": {"o:is_open"},
    "media": {"o:lang", "o:alt_text"},
}
VALUE_FIELDS = {
    "type",
    "property_id",
    "is_public",
    "@id",
    "@value",
    "@language",
    "o:label",
    "value_resource_id",
    "@annotation",
}


def changed_fields(before: Record, after: Record) -> list[str]:
    return sorted(
        key for key in before.keys() | after.keys() if before.get(key) != after.get(key)
    )


def properties(record: Record) -> Record:
    return {
        key: values
        for key, values in record.items()
        if ":" in key and not key.startswith("o:") and isinstance(values, list)
    }


def trim_value(value: Record) -> Record:
    result = {
        key: val
        for key, val in value.items()
        if key in VALUE_FIELDS and val is not None
    }
    result.setdefault("is_public", True)
    if result.get("value_resource_id") is not None:
        result.pop("@id", None)
        result.pop("o:label", None)
    if "@annotation" in result:
        result["@annotation"] = writable("item_sets", result["@annotation"])
    return result


def ref_id(value):
    return value.get("o:id") if isinstance(value, dict) else value


def writable(kind: str, record: Record) -> Record:
    result = {}
    for key in sorted(COMMON_FIELDS | TYPE_FIELDS[kind]):
        if key not in record:
            continue
        value = record[key]
        if key in {"o:item_set", "o:site", "o:media"}:
            result[key] = [{"o:id": ref_id(ref)} for ref in value or []]
            if key != "o:media":
                result[key].sort(key=lambda ref: ref["o:id"])
        elif key in {
            "o:owner",
            "o:resource_class",
            "o:resource_template",
            "o:thumbnail",
        }:
            result[key] = {"o:id": ref_id(value)} if ref_id(value) else None
        else:
            result[key] = deepcopy(value)
    result.update(
        {
            key: [trim_value(value) for value in values]
            for key, values in properties(record).items()
        }
    )
    return result


def record_changes(kind: str, before: Record, after: Record) -> Record:
    original = writable(kind, before)
    edited = writable(kind, after)
    # Missing RDF terms in an edited snapshot mean the editor removed their values.
    edited = {**{key: [] for key in properties(original)}, **edited}
    return {
        key: edited[key] for key in changed_fields(original, edited) if key in edited
    }


def identifiers(record: Record) -> list[tuple[int, str]]:
    return [
        (value.get("property_id", 10), value["@value"])
        for value in record.get("dcterms:identifier") or []
        if isinstance(value.get("@value"), str) and value["@value"]
    ]
