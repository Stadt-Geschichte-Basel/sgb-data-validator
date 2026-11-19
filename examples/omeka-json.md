# Native Omeka JSON

Use the property IDs and data types from your Omeka instance. Use `sgb download` to see JSON for existing records.

## Item

Save the JSON as `item.json`. Run `sgb create item item.json --item-set-id 10780` to preview the item.

```json
{
	"o:is_public": false,
	"dcterms:title": [{ "type": "literal", "property_id": 1, "@value": "Example illustration" }],
	"dcterms:identifier": [
		{ "type": "literal", "property_id": 10, "@value": "example-illustration" }
	],
	"dcterms:isPartOf": [
		{ "type": "uri", "property_id": 33, "@id": "https://doi.org/10.5281/zenodo.17192327" }
	]
}
```

Add the other properties from the collection's data model. Add `--apply` when the item is ready.

## Media

Save the JSON as `media.json`. Use the ID of the parent item from Omeka.

```json
{
	"o:is_public": false,
	"o:ingester": "upload",
	"dcterms:title": [{ "type": "literal", "property_id": 1, "@value": "Example image file" }],
	"dcterms:identifier": [
		{ "type": "literal", "property_id": 10, "@value": "example-illustration-file" }
	]
}
```

Run `sgb create media media.json --item-id 12345 --file example.png` to preview the attachment. Add the media properties from the collection's data model. Add `--apply` when the media is ready.
