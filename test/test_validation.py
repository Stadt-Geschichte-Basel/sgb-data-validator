"""Test data validation with sample Omeka S data"""

from src.models import Item, Media

# Sample Item from the issue
sample_item = {
    "@context": "https://omeka.unibe.ch/api-context",
    "@id": "https://omeka.unibe.ch/api/items/10777",
    "@type": "o:Item",
    "o:id": 10777,
    "o:is_public": True,
    "o:owner": {"@id": "https://omeka.unibe.ch/api/users/69", "o:id": 69},
    "o:resource_class": None,
    "o:resource_template": {
        "@id": "https://omeka.unibe.ch/api/resource_templates/48",
        "o:id": 48,
    },
    "o:thumbnail": None,
    "o:title": "Die Löblich und wyt berümpt Stat Basel",
    "thumbnail_display_urls": {
        "large": "https://omeka.unibe.ch/files/large/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "medium": "https://omeka.unibe.ch/files/medium/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "square": "https://omeka.unibe.ch/files/square/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
    },
    "o:created": {
        "@value": "2024-05-15T11:13:22+00:00",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
    },
    "o:modified": {
        "@value": "2025-08-05T18:09:21+00:00",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
    },
    "o:media": [{"@id": "https://omeka.unibe.ch/api/media/10778", "o:id": 10778}],
    "o:item_set": [
        {"@id": "https://omeka.unibe.ch/api/item_sets/10780", "o:id": 10780}
    ],
    "o:site": [],
    "dcterms:identifier": [
        {
            "type": "literal",
            "property_id": 10,
            "property_label": "Identifier",
            "is_public": True,
            "@value": "abb10039",
        }
    ],
    "dcterms:title": [
        {
            "type": "literal",
            "property_id": 1,
            "property_label": "Title",
            "is_public": True,
            "@value": "Die Löblich und wyt berümpt Stat Basel",
        }
    ],
    "dcterms:subject": [
        {
            "type": "customvocab:13",
            "property_id": 3,
            "property_label": "Subject",
            "is_public": True,
            "@value": "Stadt",
            "@language": "de",
        }
    ],
    "dcterms:description": [
        {
            "type": "literal",
            "property_id": 4,
            "property_label": "Description",
            "is_public": True,
            "@value": "Die Karte zeigt Basel als befestigte Grenzstadt (rechts) sowie ihre geografische Lage zwischen dem Breisgau, dem Sundgau und den eidgenössischen Gebieten (links).",
        }
    ],
    "dcterms:temporal": [
        {
            "type": "customvocab:14",
            "property_id": 41,
            "property_label": "Temporal Coverage",
            "is_public": True,
            "@value": "Frühe Neuzeit",
            "@language": "de",
        }
    ],
    "dcterms:language": [
        {
            "type": "valuesuggest:lc:iso6392",
            "property_id": 12,
            "property_label": "Language",
            "is_public": True,
            "@value": "de",
        }
    ],
    "dcterms:isPartOf": [
        {
            "type": "literal",
            "property_id": 33,
            "property_label": "Is Part Of",
            "is_public": True,
            "@value": "Burghartz, Susanna (Hg.): Aufbrüche, Krisen, Transformationen. 1510–1790, Basel 2024 (Stadt.Geschichte.Basel 4).",
        }
    ],
}

# Sample Media from the issue
sample_media = {
    "@context": "https://omeka.unibe.ch/api-context",
    "@id": "https://omeka.unibe.ch/api/media/10778",
    "@type": "o:Media",
    "o:id": 10778,
    "o:is_public": True,
    "o:owner": {"@id": "https://omeka.unibe.ch/api/users/69", "o:id": 69},
    "o:resource_class": None,
    "o:resource_template": {
        "@id": "https://omeka.unibe.ch/api/resource_templates/33",
        "o:id": 33,
    },
    "o:thumbnail": None,
    "o:title": "Die Löblich und wyt berümpt Stat Basel",
    "thumbnail_display_urls": {
        "large": "https://omeka.unibe.ch/files/large/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "medium": "https://omeka.unibe.ch/files/medium/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "square": "https://omeka.unibe.ch/files/square/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
    },
    "o:created": {
        "@value": "2024-05-15T11:16:22+00:00",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
    },
    "o:modified": {
        "@value": "2024-12-03T16:23:31+00:00",
        "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
    },
    "o:ingester": "upload",
    "o:renderer": "file",
    "o:item": {"@id": "https://omeka.unibe.ch/api/items/10777", "o:id": 10777},
    "o:source": "ABB10039.tif",
    "o:media_type": "image/tiff",
    "o:sha256": "d537771c50da2b974a105e82f55ed17517c61513f442e179be317ee60fe9fd6c",
    "o:size": 162662844,
    "o:filename": "9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.tif",
    "o:lang": None,
    "o:alt_text": "",
    "o:original_url": "https://omeka.unibe.ch/files/original/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.tif",
    "o:thumbnail_urls": {
        "large": "https://omeka.unibe.ch/files/large/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "medium": "https://omeka.unibe.ch/files/medium/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
        "square": "https://omeka.unibe.ch/files/square/9ec7e6fc95c1514198ca6b3cb46a128d60f0ecc1.jpg",
    },
    "data": [],
    "dcterms:identifier": [
        {
            "type": "literal",
            "property_id": 10,
            "property_label": "Identifier",
            "is_public": True,
            "@value": "m10039",
        }
    ],
    "dcterms:title": [
        {
            "type": "literal",
            "property_id": 1,
            "property_label": "Title",
            "is_public": True,
            "@value": "Die Löblich und wyt berümpt Stat Basel",
        }
    ],
    "dcterms:subject": [
        {
            "type": "customvocab:13",
            "property_id": 3,
            "property_label": "Subject",
            "is_public": True,
            "@value": "Stadt",
            "@language": "de",
        }
    ],
    "dcterms:description": [
        {
            "type": "literal",
            "property_id": 4,
            "property_label": "Description",
            "is_public": True,
            "@value": "Die Karte zeigt Basel als befestigte Grenzstadt (rechts) sowie ihre geografische Lage zwischen dem Breisgau, dem Sundgau und den eidgenössischen Gebieten (links).",
        }
    ],
    "dcterms:creator": [
        {
            "type": "uri",
            "property_id": 2,
            "property_label": "Creator",
            "is_public": True,
            "@id": "https://www.wikidata.org/wiki/Q61073",
            "o:label": "Sebastian Münster",
        }
    ],
    "dcterms:publisher": [
        {
            "type": "uri",
            "property_id": 5,
            "property_label": "Publisher",
            "is_public": True,
            "@id": "https://dls.staatsarchiv.bs.ch/",
            "o:label": "Staatsarchiv Basel-Stadt",
        }
    ],
    "dcterms:date": [
        {
            "type": "literal",
            "property_id": 7,
            "property_label": "Date",
            "is_public": True,
            "@value": "1538",
        }
    ],
    "dcterms:temporal": [
        {
            "type": "customvocab:14",
            "property_id": 41,
            "property_label": "Temporal Coverage",
            "is_public": True,
            "@value": "Frühe Neuzeit",
            "@language": "de",
        }
    ],
    "dcterms:type": [
        {
            "type": "valuesuggestall:dc:types",
            "property_id": 8,
            "property_label": "Type",
            "is_public": True,
            "@id": "http://purl.org/dc/dcmitype/Image",
            "o:label": "Image",
        }
    ],
    "dcterms:format": [
        {
            "type": "customvocab:15",
            "property_id": 9,
            "property_label": "Format",
            "is_public": True,
            "@value": "image/tiff",
            "@language": "en",
        }
    ],
    "dcterms:extent": [
        {
            "type": "literal",
            "property_id": 25,
            "property_label": "Extent",
            "is_public": True,
            "@value": "9752x5559",
        }
    ],
    "dcterms:source": [
        {
            "type": "uri",
            "property_id": 11,
            "property_label": "Source",
            "is_public": True,
            "@id": "https://dls.staatsarchiv.bs.ch/records/189838",
            "o:label": "Staatsarchiv Basel-Stadt, PLA 15, 1-3",
        }
    ],
    "dcterms:language": [
        {
            "type": "valuesuggest:lc:iso6392",
            "property_id": 12,
            "property_label": "Language",
            "is_public": True,
            "@value": "de",
        }
    ],
    "dcterms:relation": [
        {
            "type": "uri",
            "property_id": 13,
            "property_label": "Relation",
            "is_public": True,
            "@id": "https://hls-dhs-dss.ch/de/articles/010764/2008-07-08/",
            "o:label": "Sebastian Münster, Historisches Lexikon Schweiz",
        }
    ],
    "dcterms:rights": [
        {
            "type": "literal",
            "property_id": 15,
            "property_label": "Rights",
            "is_public": True,
            "@value": "Bilddaten gemeinfrei - Staatsarchiv Basel-Stadt, PLA 15, 1-3",
        }
    ],
    "dcterms:license": [
        {
            "type": "customvocab:16",
            "property_id": 49,
            "property_label": "License",
            "is_public": True,
            "@value": "https://creativecommons.org/publicdomain/mark/1.0/",
            "@language": "en",
        }
    ],
}


def test_item_validation() -> None:
    """Test item validation with sample data"""
    print("Testing Item validation...")
    try:
        item = Item.model_validate(sample_item)
        print(f"✓ Item {item.o_id} validated successfully")
        print(f"  Title: {item.o_title}")
        print(
            f"  Identifier: {item.dcterms_identifier[0].value if item.dcterms_identifier else 'N/A'}"
        )
    except Exception as e:
        print(f"✗ Item validation failed: {e}")


def test_media_validation() -> None:
    """Test media validation with sample data"""
    print("\nTesting Media validation...")
    try:
        media = Media.model_validate(sample_media)
        print(f"✓ Media {media.o_id} validated successfully")
        print(f"  Title: {media.o_title}")
        print(f"  Media Type: {media.o_media_type}")
        print(
            f"  License: {media.dcterms_license[0].value if media.dcterms_license else 'N/A'}"
        )
    except Exception as e:
        print(f"✗ Media validation failed: {e}")


def test_invalid_data() -> None:
    """Test validation with invalid data"""
    print("\nTesting validation with invalid data...")

    # Test item without title
    invalid_item = sample_item.copy()
    invalid_item["o:title"] = ""
    try:
        Item.model_validate(invalid_item)
        print("✗ Should have failed for empty title")
    except Exception as e:
        print(f"✓ Correctly rejected empty title: {type(e).__name__}")

    # Test media with invalid URL
    invalid_media = sample_media.copy()
    invalid_media["o:original_url"] = "not-a-url"
    try:
        Media.model_validate(invalid_media)
        print("✗ Should have failed for invalid URL")
    except Exception as e:
        print(f"✓ Correctly rejected invalid URL: {type(e).__name__}")


if __name__ == "__main__":
    test_item_validation()
    test_media_validation()
    test_invalid_data()
    print("\n✓ All tests completed")
