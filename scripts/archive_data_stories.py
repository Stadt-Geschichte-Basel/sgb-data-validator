"""Archive the sources inside the SGB Data Stories as Omeka items (issue #44).

One parent item per story (the existing story-level item) and one child item per
source object (image, dataset). The work goes through a manifest CSV that a
person reviews before upload.

Steps (dry run is the default for every step that writes to Omeka):
    uv run --with openpyxl python scripts/archive_data_stories.py collect schulden
    # review data/data_stories/schulden/manifest.csv
    uv run python scripts/archive_data_stories.py upload schulden            # dry run
    uv run python scripts/archive_data_stories.py upload schulden --apply --limit 3
    uv run python scripts/archive_data_stories.py parent schulden --screenshot shot.png

Rules:
  - Files are the "item-resource" originals that were uploaded to the StoryMap.
    Replace a file in files/ (and set sha256/width/height to empty) when the
    holder has a larger original.
  - A record is public only if rights_status is "verified". Else it is private.
  - Before each create, the script looks for the identifier in Omeka. A rerun
    does not create duplicates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validate import OmekaValidator  # noqa: E402

ITEM_SET_ID = 10780
ITEM_TEMPLATE = 48
MEDIA_TEMPLATE = 33
WORK = ROOT / "data" / "data_stories"
AI_NOTE = "Metadaten mit KI-Unterstützung erstellt."
OLD_AI_NOTE = (
    "Metadaten mit KI-Unterstützung (Claude) erfasst und redaktionell geprüft."
)

# slug -> story facts. DOI and license: index.qmd front matter in
# Stadt-Geschichte-Basel/stadt-geschichte-basel.github.io/products/publications/.
STORIES: dict[str, dict[str, Any]] = {
    "schulden": {
        "title": "Schulden in der Stadt",
        "item": 12856,
        "doi": "10.5281/zenodo.17192327",
        "arcgis": "1955ccada8d74ff6919e9e1397cb168a",
        "authors": ["Benjamin Hitz"],
        "date": "2025-03-22",
        "license": "https://creativecommons.org/licenses/by/4.0/",
    },
    "seide": {
        "title": "Verbriefte Märkte – Seidene Beziehungen",
        "item": 12858,
        "doi": "10.5281/zenodo.15260738",
        "arcgis": "90a309d6d21342608d0ad3ee16fb3f30",
        "authors": ["Yiğit Topkaya"],
        "date": "2025-03-23",
        "license": None,
    },
    "kirche": {
        "title": "Bleibt die Kirche in der Stadt?",
        "item": 12861,
        "doi": "10.5281/zenodo.17192857",
        "arcgis": "34ef391bd4fa419cb82d488906608154",
        "authors": ["Benjamin Hitz", "Jonas Aeby"],
        "date": "2025-04-02",
        "license": "https://creativecommons.org/licenses/by/4.0/",
    },
    "schnupftabak": {
        "title": "Von Basler Fumoirs & Schnupftabakdosen",
        "item": 12863,
        "doi": "10.5281/zenodo.15252990",
        "arcgis": "e2096bc80f714932b8eba10ee7e23b4b",
        "authors": ["Ariane Engler", "Margherita De Fregias"],
        "date": "2025-04-20",
        "license": None,
    },
    "konzil": {
        "title": "Konzil und Koran",
        "item": 12866,
        "doi": "10.5281/zenodo.15242726",
        "arcgis": "0cac069fdac24f13a06377a1c7294a33",
        "authors": ["Lucas Burkart"],
        "date": "2025-03-10",
        "license": None,
    },
    "juedisches-basel": {
        "title": "Das jüdische Basel 1850–1914",
        "item": 12869,
        "doi": "10.5281/zenodo.15681537",
        "arcgis": None,
        "url": "https://das-juedische-basel.stadtgeschichtebasel.ch/",
        "authors": ["Beni Pfister", "Jonas Schneider", "David Knecht"],
        "date": "2024-02-29",
        "license": None,  # MIT applies to the code only.
    },
    "bioarchaeologie": {
        "title": "Mit Bioarchäologie Geschichte schreiben",
        "item": 12871,
        "doi": "10.5281/zenodo.15241041",
        "arcgis": "54d35e03bcdf4841b092d4c4906227e9",
        "authors": ["Margaux L. C. Depaermentier"],
        "date": "2024-01-09",
        "license": None,
    },
    "kontrollbuero": {
        "title": "Das Kontrollbüro und die Wundermaschine",
        "item": 12874,
        "doi": "10.5281/zenodo.15240927",
        "arcgis": "6be823309a7b4254aa27b5486703b68b",
        "portal": "https://unibas.maps.arcgis.com",
        "authors": ["Cristina Wildisen-Münch", "Nico Görlich", "Moritz Mähr"],
        "date": "2022-06-07",
        "license": None,  # CC BY-NC-ND 4.0 is not in the Omeka license list.
        "zenodo_license": "CC BY-NC-ND 4.0",
    },
}

COLUMNS = [
    "key",
    "identifier",
    "kind",
    "decision",
    "rights_status",
    "title",
    "description",
    "caption",
    "attribution",
    "context",
    "creator",
    "date",
    "temporal",
    "holder",
    "shelfmark",
    "permalink",
    "rights",
    "license",
    "rights_evidence",
    "file",
    "source_url",
    "mime",
    "width",
    "height",
    "bytes",
    "sha256",
    "match",
    "notes",
    "omeka_item",
    "omeka_media",
]

# Manifest columns that hold review work. A forced collect keeps them.
REVIEWED = [
    c
    for c in COLUMNS
    if c
    not in {
        "key",
        "kind",
        "caption",
        "attribution",
        "context",
        "file",
        "source_url",
        "mime",
        "width",
        "height",
        "bytes",
        "sha256",
        "match",
    }
]

HOLDERS = {
    "StABS": "Staatsarchiv Basel-Stadt",
    "Staatsarchiv Basel": "Staatsarchiv Basel-Stadt",
    "HMB": "Historisches Museum Basel",
    "Historisches Museum Basel": "Historisches Museum Basel",
    "UB Basel": "Universitätsbibliothek Basel",
    "Universitätsbibliothek Basel": "Universitätsbibliothek Basel",
    "ABBS": "Archäologische Bodenforschung Basel-Stadt",
    "Archäologische Bodenforschung": "Archäologische Bodenforschung Basel-Stadt",
    "Kunstmuseum Basel": "Kunstmuseum Basel",
    "Wikimedia": "Wikimedia Commons",
    "STABS": "Staatsarchiv Basel-Stadt",
    "Bodenforschung": "Archäologische Bodenforschung Basel-Stadt",
    "UB,": "Universitätsbibliothek Basel",
    "ETH-Bibliothek": "ETH-Bibliothek Zürich",
    "ETH Zürich": "ETH Zürich",
    "BnF": "Bibliothèque nationale de France",
    "Kunstmus": "Kunstmuseum Basel",
    "SRF": "Schweizer Radio und Fernsehen SRF",
}

PDM = "https://creativecommons.org/publicdomain/mark/1.0/"
BY_SA = "https://creativecommons.org/licenses/by-sa/4.0/"
# House practice in Omeka item set 10780 (counts 2026-11-19). Suggestions only:
# a row stays story_cleared (private) until the rights are checked.
HOUSE_RIGHTS = {
    "Archäologische Bodenforschung Basel-Stadt": ("CC BY-SA 4.0", BY_SA),
    "Historisches Museum Basel": ("CC BY-SA 4.0", BY_SA),
    "Universitätsbibliothek Basel": ("Public Domain Mark", PDM),
    "Kunstmuseum Basel": ("Bilddaten gemeinfrei", PDM),
    "Staatsarchiv Basel-Stadt": ("Bilddaten gemeinfrei", PDM),
}
CREDIT = re.compile(
    r"(?:Foto|Fotos|Bild|Graphik|Grafik|Karte|Plan|Fotograf):\s*([^.;(]+)"
)


def suggest(row: dict[str, Any], authors: list[str]) -> None:
    """Pre-fill title, creator, holder, rights and decision from the credit text."""
    text = f"{row.get('caption', '')} {row.get('attribution', '')}"
    if not row.get("title"):
        row["title"] = row.get("caption") or row.get("alt", "")
    if not row.get("title"):
        # The attribution often holds the description before the credit.
        head = re.split(
            r"(?:Foto|Fotos|Bild|Graphik|Grafik|Karte|Plan|Quelle):",
            row.get("attribution", ""),
        )[0]
        head = head.strip(" .,;")
        if len(head.split()) >= 3:
            row["title"] = head
    credits = [c.strip() for c in CREDIT.findall(text)]
    if credits and not row.get("creator"):
        row["creator"] = "; ".join(dict.fromkeys(credits))
    author = next((a for a in authors if a.split()[-1] in text), None)
    if author and not row.get("holder"):
        row["holder"] = "Stadt.Geschichte.Basel"
        row["creator"] = row.get("creator") or author
    if row.get("holder") in HOUSE_RIGHTS and not row.get("rights"):
        label, lic = HOUSE_RIGHTS[row["holder"]]
        credit = ", ".join(
            x for x in (row["holder"], row.get("shelfmark"), row.get("creator")) if x
        )
        row["rights"] = f"{label}, {credit}"
        row["license"] = lic
        row["notes"] = (
            row.get("notes", "") + " Rechte nach Hauspraxis (ungeprüft)."
        ).strip()
    elif row.get("holder") == "Stadt.Geschichte.Basel" and not row.get("rights"):
        row["rights"] = ", ".join(x for x in ("CC BY-SA 4.0", row.get("creator")) if x)
        row["license"] = BY_SA
        row["notes"] = (
            row.get("notes", "")
            + " Eigene Grafik der Story, Lizenz beim Autor bestätigen."
        ).strip()
    if "SRF" in text:
        row["decision"] = "review"
        row["notes"] = (
            row.get("notes", "")
            + " Fernseh-Still: urheberrechtlich geschützt, Bewilligung nötig."
        ).strip()
    elif not row.get("decision"):
        has_source = row.get("holder") or row.get("creator")
        row["decision"] = "ingest" if row.get("title") and has_source else "review"
    if row.get("context") and not row.get("description"):
        # A period after a digit is an ordinal ("17. Jh."), not a sentence end.
        sentences = re.split(r"(?<=[^\d\s][.!?])\s+", row["context"].split(" | ")[-1])
        row["description"] = " ".join(sentences[:2])
        row["notes"] = (
            row.get("notes", "") + " Beschreibung aus dem Story-Text, prüfen."
        ).strip()


FORMATS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".geojson": "application/geo+json",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
}

TYPES = {
    "image": ("http://purl.org/dc/dcmitype/Image", "Image"),
    "dataset": ("http://purl.org/dc/dcmitype/Dataset", "Dataset"),
    "story": (
        "http://purl.org/dc/dcmitype/InteractiveResource",
        "Interactive Resource",
    ),
}


# --------------------------------------------------------------------------- helpers


def clean(text: str | None) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def norm(text: str | None) -> str:
    text = unicodedata.normalize("NFKC", clean(text)).casefold()
    return re.sub(r"[^\w]+", " ", text).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_json(client: httpx.Client, url: str, **params: Any) -> dict[str, Any]:
    for attempt in range(4):
        try:
            response = client.get(url, params={"f": "json", **params})
            response.raise_for_status()
            data = response.json()
        except httpx.TransportError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
            continue
        if isinstance(data, dict) and "error" in data:
            # ArcGIS reports errors (e.g. a missing token) with HTTP 200.
            raise httpx.HTTPError(f"{url}: {data['error']}")
        return data
    raise RuntimeError("unreachable")


def download(client: httpx.Client, url: str, path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with client.stream("GET", url) as response:
        response.raise_for_status()
        tmp = path.with_suffix(path.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
        tmp.rename(path)


def read_manifest(slug: str) -> list[dict[str, str]]:
    with (WORK / slug / "manifest.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_manifest(slug: str, rows: list[dict[str, Any]]) -> Path:
    path = WORK / slug / "manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def omeka_env() -> tuple[str, str | None, str | None]:
    load_dotenv(ROOT / ".env")
    return (
        os.getenv("OMEKA_URL", "https://omeka.unibe.ch").rstrip("/"),
        os.getenv("KEY_IDENTITY"),
        os.getenv("KEY_CREDENTIAL"),
    )


# --------------------------------------------------------------------------- collect


MEDIA_TYPES = {"image", "video", "audio", "webmap", "embed"}
# Blocks whose images share the text that follows the block.
GROUP_TYPES = {"gallery", "carousel", "swipe"}


def walk(
    nodes: dict[str, Any], root: str
) -> list[tuple[str, dict[str, Any], str, str, str]]:
    """Media nodes in reading order: (node_id, node, heading, next_text, source).

    source: a "Quelle: ..." paragraph in the same immersive slide (the credit
    of an image in a sidecar is in the narrative panel, not in the caption).
    """
    order: list[str] = []
    parent: dict[str, str] = {}

    def visit(node_id: str) -> None:
        if node_id in parent.values() and node_id in order:
            return
        order.append(node_id)
        node = nodes.get(node_id, {})
        # Swipe and similar blocks reference their content in data, not children.
        refs = [
            v
            for v in json.dumps(node.get("data", {})).split('"')
            if v in nodes and v != node_id
        ]
        for child in (node.get("children", []) or []) + refs:
            if child in order:
                continue
            parent[child] = node_id
            visit(child)

    def subtree_texts(node_id: str, paragraphs: bool = False) -> list[str]:
        node = nodes.get(node_id, {})
        data = node.get("data") or {}
        is_text = node.get("type") == "text"
        if paragraphs:
            is_text = is_text and data.get("type") == "paragraph"
        texts = [clean(data.get("text"))] if is_text else []
        for child in node.get("children", []) or []:
            texts += subtree_texts(child, paragraphs)
        return texts

    def slide_source(node_id: str) -> str:
        current = node_id
        while current in parent:
            current = parent[current]
            if nodes.get(current, {}).get("type") == "immersive-slide":
                hits = [t for t in subtree_texts(current) if re.match(r"Quellen?:", t)]
                return " ".join(hits)
        return ""

    def slide_narrative(node_id: str) -> str | None:
        """First non-credit paragraph of the enclosing immersive slide, or None."""
        current = node_id
        while current in parent:
            current = parent[current]
            if nodes.get(current, {}).get("type") == "immersive-slide":
                texts = [
                    t
                    for t in subtree_texts(current, paragraphs=True)
                    if t and not re.match(r"Quellen?:", t)
                ]
                return texts[0][:500] if texts else ""
        return None

    visit(root)
    result = []
    heading = ""
    for i, node_id in enumerate(order):
        node = nodes.get(node_id, {})
        data = node.get("data", {}) or {}
        if node.get("type") == "text" and data.get("type", "").startswith("h"):
            heading = clean(data.get("text"))
        if node.get("type") in MEDIA_TYPES:
            following = ""
            in_group = nodes.get(parent.get(node_id, ""), {}).get("type") in GROUP_TYPES
            steps = 0
            for later in order[i + 1 :]:
                lnode = nodes.get(later, {})
                ldata = lnode.get("data", {}) or {}
                if lnode.get("type") in MEDIA_TYPES:
                    if in_group and parent.get(later) == parent.get(node_id):
                        continue  # other images of the same gallery do not count
                    break  # the text after the next media belongs to that media
                steps += 1
                if steps > 5:
                    break
                if lnode.get("type") == "text" and ldata.get("type") == "paragraph":
                    following = clean(ldata.get("text"))[:500]
                    break
            narrative = slide_narrative(node_id)
            if narrative is not None:
                # Sidecar: the text of the same slide describes the image. The
                # next paragraph in reading order belongs to the next slide.
                following = narrative
            result.append((node_id, node, heading, following, slide_source(node_id)))
    return result


def omeka_index(client: httpx.Client, cache: Path) -> dict[str, Any]:
    """Public media and items of the item set: sha256, titles, identifiers."""
    if not cache.exists():
        base, _, _ = omeka_env()
        out: dict[str, list[dict[str, Any]]] = {"media": [], "items": []}
        for kind in ("media", "items"):
            page = 1
            while True:
                response = client.get(
                    f"{base}/api/{kind}",
                    params={"item_set_id": ITEM_SET_ID, "per_page": 100, "page": page},
                    timeout=120,
                )
                response.raise_for_status()
                batch = response.json()
                if not batch:
                    break
                for rec in batch:
                    out[kind].append(
                        {
                            "id": rec["o:id"],
                            "item": (rec.get("o:item") or {}).get("o:id"),
                            "sha256": rec.get("o:sha256"),
                            "title": rec.get("o:title"),
                            "identifier": [
                                v.get("@value")
                                for v in rec.get("dcterms:identifier", [])
                            ],
                        }
                    )
                page += 1
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    data = json.loads(cache.read_text(encoding="utf-8"))
    return {
        "sha": {m["sha256"]: m for m in data["media"] if m["sha256"]},
        "title": {
            norm(m["title"]): m for m in data["media"] + data["items"] if m["title"]
        },
        "ident": {i: m for m in data["items"] for i in m["identifier"] if i},
    }


def bildredaktion() -> dict[str, dict[str, str]]:
    """Book figure rights from the Bildredaktion tables, by normalized title."""
    try:
        import openpyxl  # optional: uv run --with openpyxl
    except ImportError:
        print("openpyxl not installed: skip Bildredaktion match")
        return {}
    result: dict[str, dict[str, str]] = {}
    for path in sorted(ROOT.glob("*Bildredaktion*.xlsx")):
        sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[
            0
        ]
        header: list[str] | None = None
        for row in sheet.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if header is None:
                if "Grafiktitel" in cells:
                    header = cells
                continue
            rec = dict(zip(header, cells, strict=False))
            title = rec.get("Grafiktitel") or rec.get("Titel (selbst vergeben)")
            if title:
                result[norm(title)] = {
                    "abb": rec.get("Abbildungsnummer", ""),
                    "holder": next(
                        (v for k, v in rec.items() if k.startswith("Copyright 1")), ""
                    ),
                    "shelfmark": next(
                        (v for k, v in rec.items() if k.startswith("Copyright 2")), ""
                    ),
                    "rights": rec.get("DC: Rights", ""),
                    "permalink": rec.get("Permalink Katalogeintrag", ""),
                    "file": path.name,
                }
    return result


def guess_holder(text: str) -> tuple[str, str]:
    for key, holder in HOLDERS.items():
        if key in text:
            rest = text.split(key, 1)[1].strip(" ,:;")
            return holder, rest
    return "", ""


def layer_rows(
    client: httpx.Client, portal: str, webmap_id: str, seen: set[str]
) -> list[dict[str, Any]]:
    """One dataset row for each feature layer of a web map not seen before."""
    rows = []
    data = get_json(client, f"{portal}/sharing/rest/content/items/{webmap_id}/data")
    for layer in data.get("operationalLayers", []):
        url = (layer.get("url") or "").rstrip("/")
        if not url and layer.get("featureCollection"):
            print(
                f"  NOTE webmap {webmap_id}: inline layer {layer.get('title')!r} not exported"
            )
        if (
            not url
            or "FeatureServer" not in url
            and "MapServer" not in url
            or url in seen
        ):
            continue
        seen.add(url)
        meta: dict[str, Any] = {}
        if layer.get("itemId"):
            try:
                meta = get_json(
                    client, f"{portal}/sharing/rest/content/items/{layer['itemId']}"
                )
            except httpx.HTTPError:
                meta = {}
        rows.append(
            {
                "key": "layer:" + url,
                "kind": "dataset",
                "title": clean(layer.get("title")),
                "caption": clean(meta.get("snippet")),
                "attribution": clean(meta.get("accessInformation")),
                "rights": clean(meta.get("licenseInfo")),
                "creator": meta.get("owner", ""),
                "source_url": url,
                "permalink": f"{portal}/home/item.html?id={layer['itemId']}"
                if layer.get("itemId")
                else "",
                "notes": f"webmap {webmap_id}",
            }
        )
    return rows


def export_layer(client: httpx.Client, url: str, path: Path) -> None:
    """Save all features of a layer as GeoJSON (paged query)."""
    if path.exists():
        return
    features: list[Any] = []
    offset = 0
    while True:
        response = client.get(
            f"{url}/query",
            params={
                "where": "1=1",
                "outFields": "*",
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": 1000,
            },
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise httpx.HTTPError(f"{url}: {body['error']}")
        batch = body.get("features", [])
        features.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)
    count = client.get(
        f"{url}/query",
        params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
        timeout=120,
    ).json()
    if "error" in count or count.get("count") is None:
        raise httpx.HTTPError(f"{url}: no feature count ({count.get('error')})")
    count = count["count"]
    if count != len(features):
        raise httpx.HTTPError(f"exported {len(features)} of {count} features")
    path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features}, ensure_ascii=False
        ),
        encoding="utf-8",
    )


def collect(slug: str, force: bool) -> int:
    story = STORIES[slug]
    if not story.get("arcgis"):
        print(
            f"{slug}: not an ArcGIS StoryMap. Collect it by hand (see README of the story repo)."
        )
        return 1
    out = WORK / slug
    if (out / "manifest.csv").exists() and not force:
        print(
            f"{out / 'manifest.csv'} exists (it may hold review work). Use --force to replace it."
        )
        return 1
    # Rows of an earlier run keep their review work and identifiers.
    old = (
        {r["key"]: r for r in read_manifest(slug)}
        if (out / "manifest.csv").exists()
        else {}
    )
    portal = story.get("portal", "https://www.arcgis.com")
    sid = story["arcgis"]
    client = httpx.Client(timeout=120, follow_redirects=True)
    data = get_json(client, f"{portal}/sharing/rest/content/items/{sid}/data")
    (out / "files").mkdir(parents=True, exist_ok=True)
    (out / "story.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    nodes, resources = data["nodes"], data["resources"]
    index = omeka_index(client, WORK / "omeka_index.json")
    book = bildredaktion()
    story_url = f"https://storymaps.arcgis.com/stories/{sid}"

    rows: list[dict[str, Any]] = []
    seen_res: set[str] = set()
    seen_layers: set[str] = set()
    seen_sha: dict[str, str] = {}
    for node_id, node, heading, following, source in walk(nodes, data["root"]):
        ndata = node.get("data", {}) or {}
        kind = node["type"]
        base = {
            "caption": clean(ndata.get("caption")),
            "attribution": clean(ndata.get("attribution")) or source,
            "context": " | ".join(x for x in (heading, following) if x),
            "rights_status": "unknown",
        }
        if kind == "webmap":
            res = resources.get(ndata.get("map", ""), {}).get("data", {})
            if res.get("itemId"):
                for row in layer_rows(client, portal, res["itemId"], seen_layers):
                    rows.append({**base, **row, "context": base["context"]})
            continue
        if kind == "embed":
            rows.append(
                {
                    **base,
                    "key": f"node:{node_id}",
                    "kind": "link",
                    "source_url": ndata.get("url", ""),
                    "title": clean(ndata.get("title")),
                    "decision": "exclude:embed (Darstellung, Daten über Layer erfasst)"
                    if "dashboards" in ndata.get("url", "")
                    else "review",
                }
            )
            continue
        ref = ndata.get("image") or ndata.get("video") or ndata.get("audio")
        res = resources.get(ref or "", {})
        rdata = res.get("data", {})
        if not rdata.get("resourceId") or ref in seen_res:
            continue
        seen_res.add(ref)
        rid = rdata["resourceId"]
        file = out / "files" / rid
        url = f"{portal}/sharing/rest/content/items/{sid}/resources/{rid}"
        download(client, url, file)
        row = {
            **base,
            "key": f"res:{rid}",
            "kind": "image" if kind == "image" else kind,
            "file": str(file.relative_to(out)),
            "source_url": url,
            "mime": FORMATS.get(
                file.suffix.lower(), mimetypes.guess_type(file.name)[0] or ""
            ),
            "width": rdata.get("width", ""),
            "height": rdata.get("height", ""),
            "bytes": file.stat().st_size,
            "sha256": sha256(file),
        }
        row["title"] = row["caption"]
        holder, shelf = guess_holder(row["caption"] + " " + row["attribution"])
        row.update(holder=holder, shelfmark=shelf)
        if row["sha256"] in seen_sha:
            row["decision"] = f"exclude:Duplikat von {seen_sha[row['sha256']]}"
            rows.append(row)
            continue
        seen_sha[row["sha256"]] = row["key"]
        if row["sha256"] in index["sha"]:
            hit = index["sha"][row["sha256"]]
            row.update(
                decision=f"reuse:{hit['item']}", match=f"sha256 = media {hit['id']}"
            )
        elif norm(row["caption"]) and norm(row["caption"]) in index["title"]:
            hit = index["title"][norm(row["caption"])]
            row.update(decision="review", match=f"title = Omeka {hit['id']}")
        if norm(row["caption"]) in book:
            b = book[norm(row["caption"])]
            row["match"] = (
                row.get("match", "") + f" | Bildredaktion {b['abb']} ({b['file']})"
            ).strip(" |")
            row.update(
                {
                    k: row.get(k) or b[k]
                    for k in ("holder", "shelfmark", "rights", "permalink")
                }
            )
            if b["abb"] in index["ident"] and not row.get("decision"):
                row.update(decision=f"reuse:{index['ident'][b['abb']]['id']}")
        row["alt"] = clean(ndata.get("alt"))
        if kind in {"video", "audio"}:
            row["decision"] = "review"
        suggest(row, story["authors"])
        rows.append(row)

    # Export datasets and assign identifiers.
    numbers = [
        int(m.group(1))
        for r in old.values()
        if (m := re.fullmatch(rf"ds-{re.escape(slug)}-(\d+)", r.get("identifier", "")))
    ]
    n = max(numbers, default=0)
    for row in rows:
        if row["kind"] == "dataset":
            # The URL hash keeps layers with the same title apart.
            url_hash = hashlib.sha256(row["source_url"].encode()).hexdigest()[:8]
            title = re.sub(r"[^\w-]+", "_", row["title"] or "layer")[:60]
            name = f"{title}-{url_hash}.geojson"
            path = out / "files" / name
            try:
                export_layer(client, row["source_url"], path)
                row.update(
                    file=str(path.relative_to(out)),
                    mime="application/geo+json",
                    bytes=path.stat().st_size,
                    sha256=sha256(path),
                )
                row.setdefault(
                    "decision",
                    "review" if "grundkarte" in row["title"].lower() else "ingest",
                )
            except httpx.HTTPError as exc:
                row.update(
                    decision="review",
                    notes=f"{row.get('notes', '')} export failed: {exc}",
                )
        if row["key"] in old:
            row.update({k: v for k in REVIEWED if (v := old[row["key"]].get(k))})
        row.setdefault("decision", "review")
        if not row["decision"].startswith(("exclude", "reuse")) and not row.get(
            "identifier"
        ):
            n += 1
            row["identifier"] = f"ds-{slug}-{n:02d}"
    keys = {row["key"] for row in rows}
    for key, row in old.items():
        if key not in keys:
            # Keep the row and its Omeka ids, even if the story no longer has it.
            row["notes"] = f"{row.get('notes', '')} Nicht mehr in der Story.".strip()
            rows.append(row)
    path = write_manifest(slug, rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["decision"].split(":")[0]] = (
            counts.get(row["decision"].split(":")[0], 0) + 1
        )
    print(f"{slug}: {len(rows)} rows -> {path}  {counts}  story {story_url}")
    return 0


# --------------------------------------------------------------------------- payloads


def story_url(slug: str) -> str:
    story = STORIES[slug]
    return story.get("url") or f"https://storymaps.arcgis.com/stories/{story['arcgis']}"


def literal(pid: int, label: str, value: str) -> dict[str, Any]:
    return {
        "type": "literal",
        "property_id": pid,
        "property_label": label,
        "is_public": True,
        "@value": value,
    }


def uri(pid: int, label: str, target: str, text: str | None = None) -> dict[str, Any]:
    value = {
        "type": "uri",
        "property_id": pid,
        "property_label": label,
        "is_public": True,
        "@id": target,
    }
    if text:
        value["o:label"] = text
    return value


def vocab(
    pid: int, label: str, kind: str, value: str, lang: str | None = None
) -> dict[str, Any]:
    out = {
        "type": kind,
        "property_id": pid,
        "property_label": label,
        "is_public": True,
        "@value": value,
    }
    if lang:
        out["@language"] = lang
    return out


# EDTF levels 0 and 1 as used here: year, month, day, qualifiers ~ ? %, intervals.
_EDTF_DATE = r"-?\d{4}(?:-\d{2}(?:-\d{2})?)?[~?%]?"
EDTF = re.compile(rf"{_EDTF_DATE}(?:/(?:{_EDTF_DATE}|\.\.)?)?|\.\./{_EDTF_DATE}")


def rights_problems(row: dict[str, str]) -> list[str]:
    problems = [
        f"missing {k}"
        for k in ("title", "description", "rights", "license", "file", "creator")
        if not row.get(k)
    ]
    if row.get("kind") not in TYPES:
        problems.append(f"kind {row.get('kind')} not supported")
    if row.get("rights_status") == "verified" and not row.get("rights_evidence"):
        problems.append("verified without rights_evidence")
    if row.get("date") and not EDTF.fullmatch(row["date"]):
        problems.append(
            f"date {row['date']!r} is not EDTF (use e.g. 1497~ for 'um 1497')"
        )
    return problems


def item_payload(slug: str, row: dict[str, str], temporal: list[str]) -> dict[str, Any]:
    story = STORIES[slug]
    return {
        "o:is_public": row["rights_status"] == "verified",
        "o:resource_template": {"o:id": ITEM_TEMPLATE},
        "o:item_set": [{"o:id": ITEM_SET_ID}],
        # Explicit empty list: Omeka otherwise adds new items to every site
        # with "assign new items" enabled (sites 48 and 49 on omeka.unibe.ch).
        "o:site": [],
        "dcterms:identifier": [literal(10, "Identifier", row["identifier"])],
        "dcterms:title": [literal(1, "Title", row["title"])],
        "dcterms:description": [
            literal(4, "Description", f"{row['description']}\n\n{AI_NOTE}")
        ],
        "dcterms:temporal": [
            vocab(41, "Temporal Coverage", "customvocab:14", t, "de") for t in temporal
        ],
        "dcterms:language": [vocab(12, "Language", "valuesuggest:lc:iso6392", "de")],
        "dcterms:isPartOf": [
            uri(33, "Is Part Of", f"https://doi.org/{story['doi']}", story["title"])
        ],
    }


def media_payload(
    slug: str, row: dict[str, str], item_id: int | None, temporal: list[str]
) -> dict[str, Any]:
    story = STORIES[slug]
    type_uri, type_label = TYPES[row["kind"]]
    payload: dict[str, Any] = {
        "o:is_public": row["rights_status"] == "verified",
        "o:ingester": "upload",
        "file_index": 0,
        "o:item": {"o:id": item_id},
        "o:resource_template": {"o:id": MEDIA_TEMPLATE},
        "o:title": row["title"],
        "dcterms:identifier": [literal(10, "Identifier", f"m-{row['identifier']}_1")],
        "dcterms:title": [literal(1, "Title", row["title"])],
        "dcterms:description": [
            literal(4, "Description", f"{row['description']}\n\n{AI_NOTE}")
        ],
        "dcterms:creator": [
            literal(2, "Creator", c.strip())
            for c in row["creator"].split(";")
            if c.strip()
        ],
        "dcterms:temporal": [
            vocab(41, "Temporal Coverage", "customvocab:14", t, "de") for t in temporal
        ],
        "dcterms:type": [
            {**uri(8, "Type", type_uri, type_label), "type": "valuesuggestall:dc:types"}
        ],
        "dcterms:format": [vocab(9, "Format", "customvocab:15", row["mime"])],
        "dcterms:language": [vocab(12, "Language", "valuesuggest:lc:iso6392", "de")],
        "dcterms:relation": [
            uri(13, "Relation", f"https://doi.org/{story['doi']}", story["title"]),
            uri(
                13,
                "Relation",
                story_url(slug),
                "Verwendet in der interaktiven Data Story",
            ),
        ],
        "dcterms:rights": [literal(15, "Rights", row["rights"])],
        "dcterms:license": [
            vocab(49, "License", "customvocab:16", row["license"], "en")
        ],
    }
    if row.get("holder"):
        payload["dcterms:publisher"] = [literal(5, "Publisher", row["holder"])]
    if row.get("date"):
        payload["dcterms:date"] = [literal(7, "Date", row["date"])]
    if row.get("width") and row.get("height"):
        payload["dcterms:extent"] = [
            literal(25, "Extent", f"{row['width']} x {row['height']} px")
        ]
    source = []
    if row.get("permalink"):
        source.append(
            uri(
                11,
                "Source",
                row["permalink"],
                row.get("shelfmark") or row.get("holder") or None,
            )
        )
    elif row.get("shelfmark"):
        source.append(
            literal(11, "Source", f"{row['holder']}, {row['shelfmark']}".strip(", "))
        )
    if source:
        payload["dcterms:source"] = source
    return payload


def validation_errors(payload: dict[str, Any], kind: str) -> list[str]:
    """Run the repo validator on a payload (server fields filled with dummies)."""
    when = {"@value": "2000-01-01T00:00:00+00:00", "@type": "xsd:dateTime"}
    stub = json.loads(json.dumps(payload))
    for key in ("o:resource_template", "o:item"):
        if isinstance(stub.get(key), dict):
            stub[key] = {"@id": "", "o:id": stub[key].get("o:id") or 0}
    stub["o:item_set"] = [
        {"@id": "", "o:id": s["o:id"]} for s in stub.get("o:item_set", [])
    ]
    stub.update(
        {
            "@context": "",
            "@id": "",
            "@type": "o:Item" if kind == "item" else "o:Media",
            "o:id": 0,
            "o:created": when,
            "o:modified": when,
            "o:title": stub["dcterms:title"][0]["@value"],
        }
    )
    if kind == "media":
        stub.update(
            {"o:renderer": "file", "o:media_type": stub["dcterms:format"][0]["@value"]}
        )
    validator = OmekaValidator("https://example.invalid")
    (validator.validate_item if kind == "item" else validator.validate_media)(stub)
    return [str(e) for e in validator.errors]


# --------------------------------------------------------------------------- upload


def masked_url(url: httpx.URL | str) -> str:
    """URL without the query string, so the API key never shows in a message."""
    return str(httpx.URL(str(url)).copy_with(query=None))


class Omeka:
    def __init__(self) -> None:
        self.base, self.key_id, self.key_cred = omeka_env()
        self.client = httpx.Client(timeout=180, headers={"Cache-Control": "no-cache"})

    def auth(self, **extra: Any) -> dict[str, Any]:
        if not self.key_id or not self.key_cred:
            raise SystemExit("KEY_IDENTITY / KEY_CREDENTIAL missing in .env")
        return {
            "key_identity": self.key_id,
            "key_credential": self.key_cred,
            "_": time.time_ns(),
            **extra,
        }

    def check(self, response: httpx.Response) -> None:
        """Raise on an HTTP error. Keep the key and credential out of the message."""
        if not response.is_error:
            return
        text = response.text[:500]
        for secret in (self.key_id, self.key_cred):
            if secret:
                text = text.replace(secret, "***")
        raise RuntimeError(
            f"{response.request.method} {masked_url(response.request.url)}: "
            f"HTTP {response.status_code}: {text}"
        )

    def get(self, kind: str, rid: int) -> dict[str, Any]:
        response = self.client.get(f"{self.base}/api/{kind}/{rid}", params=self.auth())
        self.check(response)
        return response.json()

    def find(self, kind: str, identifier: str) -> list[dict[str, Any]]:
        response = self.client.get(
            f"{self.base}/api/{kind}",
            params=self.auth(
                **{
                    "property[0][property]": 10,
                    "property[0][type]": "eq",
                    "property[0][text]": identifier,
                }
            ),
        )
        self.check(response)
        return response.json()

    def post(
        self, kind: str, payload: dict[str, Any], file: Path | None = None
    ) -> dict[str, Any]:
        if file is None:
            response = self.client.post(
                f"{self.base}/api/{kind}", params=self.auth(), json=payload
            )
        else:
            mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            with file.open("rb") as f:
                response = self.client.post(
                    f"{self.base}/api/{kind}",
                    params=self.auth(),
                    files={
                        "data": (
                            None,
                            json.dumps(payload, ensure_ascii=False),
                            "application/json",
                        ),
                        "file[0]": (file.name, f, mime),
                    },
                )
        self.check(response)
        return response.json()

    def put(self, kind: str, rid: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.put(
            f"{self.base}/api/{kind}/{rid}", params=self.auth(), json=payload
        )
        self.check(response)
        return response.json()

    def delete(self, kind: str, rid: int) -> None:
        response = self.client.delete(
            f"{self.base}/api/{kind}/{rid}", params=self.auth()
        )
        self.check(response)


def backup(records: list[dict[str, Any]], name: str) -> Path:
    path = (
        ROOT
        / "backups"
        / f"data_stories_{datetime.now(UTC):%Y%m%d_%H%M%S}"
        / f"{name}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)
    return path


def story_temporal(api: Omeka, slug: str) -> list[str]:
    parent = api.get("items", STORIES[slug]["item"])
    return [v["@value"] for v in parent.get("dcterms:temporal", []) if v.get("@value")]


def upload(slug: str, apply: bool, limit: int | None) -> int:
    rows = read_manifest(slug)
    api = Omeka()
    temporal = story_temporal(api, slug)
    out = WORK / slug
    done = failed = 0
    for row in rows:
        decision = row["decision"]
        if decision.startswith("reuse:"):
            failed += not link_existing(
                api, slug, row, int(decision.split(":")[1]), apply
            )
            continue
        # A row with omeka_item but no omeka_media goes on to the RESUME check.
        if decision != "ingest" or row.get("omeka_media"):
            continue
        if limit is not None and done >= limit:
            break
        problems = rights_problems(row)
        if not problems:
            item = item_payload(slug, row, temporal)
            media = media_payload(slug, row, None, temporal)
            problems = validation_errors(item, "item") + validation_errors(
                media, "media"
            )
        if problems:
            print(f"SKIP {row['identifier']}: {'; '.join(problems)}")
            failed += 1
            continue
        existing = api.find("items", row["identifier"])
        if existing:
            item_id = existing[0]["o:id"]
            if existing[0].get("o:media"):
                print(f"EXISTS {row['identifier']} -> item {item_id}")
                if apply:  # A dry run writes nothing, also not to the manifest.
                    row["omeka_item"] = str(item_id)
                    row["omeka_media"] = str(existing[0]["o:media"][0]["o:id"])
                continue
            # The item exists without a file: an earlier run stopped after the item POST.
            print(f"RESUME {row['identifier']}: item {item_id} has no media")
        else:
            item_id = None
        public = "public" if item["o:is_public"] else "private"
        if not apply:
            print(f"DRY {row['identifier']} ({public}): {row['title'][:70]}")
            done += 1
            continue
        if item_id is None:
            item_id = api.post("items", item)["o:id"]
        row["omeka_item"] = str(item_id)
        write_manifest(slug, rows)  # Record the item before the file upload.
        media["o:item"] = {"o:id": item_id}
        new_media = api.post("media", media, out / row["file"])
        check = api.get("items", item_id)
        ok = [m["o:id"] for m in check.get("o:media", [])] == [new_media["o:id"]]
        row["omeka_media"] = str(new_media["o:id"])
        print(
            f"{'OK' if ok else 'CHECK'} {row['identifier']} -> item {item_id} "
            f"media {new_media['o:id']} ({public})"
        )
        done += 1
        write_manifest(slug, rows)  # Keep the ledger current after each write.
    if apply:
        write_manifest(slug, rows)
    print(f"{'applied' if apply else 'dry run'}: {done} new, {failed} skipped")
    return 1 if failed else 0


def link_existing(
    api: Omeka, slug: str, row: dict[str, str], item_id: int, apply: bool
) -> bool:
    """Add the story DOI to an existing item. Other fields stay as they are."""
    doi = f"https://doi.org/{STORIES[slug]['doi']}"
    record = api.get("items", item_id)
    if any(v.get("@id") == doi for v in record.get("dcterms:isPartOf", [])):
        return True
    if not apply:
        print(f"DRY link item {item_id} -> {doi}")
        return True
    backup([record], f"item_{item_id}")
    if api.get("items", item_id).get("o:modified") != record.get("o:modified"):
        print(f"SKIP link {item_id}: changed during the run")
        return False
    record.setdefault("dcterms:isPartOf", []).append(
        uri(33, "Is Part Of", doi, STORIES[slug]["title"])
    )
    api.put("items", item_id, record)
    print(f"OK link item {item_id} -> {doi}")
    row["omeka_item"] = str(item_id)
    return True


def with_note(text: str) -> str:
    """Return the description with the current AI note at its end."""
    text = text.replace(OLD_AI_NOTE, AI_NOTE)
    return text if AI_NOTE in text else f"{text}\n\n{AI_NOTE}".strip()


def ainote(slug: str, apply: bool) -> int:
    """Set the current AI note on the uploaded items and media of a story."""
    api = Omeka()
    changed = failed = 0
    for row in read_manifest(slug):
        if row["decision"] != "ingest":
            continue
        for kind, rid in (("items", row["omeka_item"]), ("media", row["omeka_media"])):
            if not rid:
                continue
            record = api.get(kind, int(rid))
            values = record.setdefault("dcterms:description", [])
            if not values:
                values.append(literal(4, "Description", ""))
            old = values[0].get("@value", "")
            new = with_note(old)
            if new == old:
                continue
            changed += 1
            if not apply:
                print(f"DRY {kind} {rid} {row['identifier']}")
                continue
            backup([record], f"{kind}_{rid}")
            # The PUT sends the whole record. Do not overwrite a concurrent edit.
            if api.get(kind, int(rid)).get("o:modified") != record.get("o:modified"):
                print(f"SKIP {kind} {rid}: changed during the run")
                failed += 1
                continue
            values[0]["@value"] = new
            api.put(kind, int(rid), record)
            check = api.get(kind, int(rid))["dcterms:description"][0]["@value"]
            ok = check == new
            failed += not ok
            print(f"{'OK' if ok else 'CHECK'} {kind} {rid} {row['identifier']}")
    print(f"{'applied' if apply else 'dry run'}: {changed} changes, {failed} failed")
    return 1 if failed else 0


# --------------------------------------------------------------------------- parent


def story_rights(story: dict[str, Any]) -> str:
    """Rights text of a story PDF; the license field holds the matching URI."""
    if story["license"]:
        return "CC BY 4.0, Stadt.Geschichte.Basel"
    if story.get("zenodo_license"):
        return f"{story['zenodo_license']} (Zenodo), Stadt.Geschichte.Basel"
    return "In Copyright, Stadt.Geschichte.Basel"


def zenodo_has_file(doi: str, path: Path) -> bool:
    """True if the Zenodo record of the DOI holds a file with the same MD5."""
    record_id = doi.rsplit("zenodo.", 1)[-1]
    response = httpx.get(
        f"https://zenodo.org/api/records/{record_id}",
        timeout=60,
        follow_redirects=True,
    )
    response.raise_for_status()
    md5 = "md5:" + hashlib.md5(path.read_bytes()).hexdigest()  # noqa: S324
    return any(f.get("checksum") == md5 for f in response.json().get("files", []))


def parent(slug: str, screenshot: Path, apply: bool, delete_old: bool) -> int:
    story = STORIES[slug]
    if not screenshot.is_file():
        print(f"{screenshot}: file not found")
        return 1
    api = Omeka()
    item = api.get("items", story["item"])
    old_media = [api.get("media", m["o:id"]) for m in item.get("o:media", [])]
    done = [
        m["o:id"]
        for m in old_media
        if any(
            v.get("@value") == f"m-story-{slug}"
            for v in m.get("dcterms:identifier", [])
        )
    ]
    if done:
        print(f"item {story['item']} already has the story media {done}: nothing to do")
        return 0
    doi = f"https://doi.org/{story['doi']}"
    url = story.get("url") or f"https://storymaps.arcgis.com/stories/{story['arcgis']}"
    temporal = [v["@value"] for v in item.get("dcterms:temporal", [])]
    licensed = bool(story["license"])
    is_pdf = screenshot.suffix.lower() == ".pdf"
    # Decision 2026-11-19: all Zenodo story PDFs are public, also without a CC license.
    # Only a PDF that matches a file of the story's Zenodo record counts.
    on_zenodo = is_pdf and zenodo_has_file(story["doi"], screenshot)
    if is_pdf and not on_zenodo:
        print(f"{screenshot}: not a file of {doi}, the media stays private")
    public = licensed or on_zenodo
    kind = "PDF" if is_pdf else "Screenshot"
    note = (
        f"PDF-Fassung der Data Story, archiviert auf Zenodo ({doi})."
        if is_pdf
        else f"Bildschirmfoto der interaktiven Data Story, aufgenommen am {datetime.now(UTC):%Y-%m-%d}."
    )
    media = {
        "o:is_public": public,
        "o:ingester": "upload",
        "file_index": 0,
        "o:item": {"o:id": story["item"]},
        "o:resource_template": {"o:id": MEDIA_TEMPLATE},
        "o:title": f"Data Story: {story['title']} ({kind})",
        "dcterms:identifier": [
            literal(10, "Identifier", f"m-story-{slug}"),
            uri(10, "Identifier", doi, doi),
        ],
        "dcterms:title": [
            literal(1, "Title", f"Data Story: {story['title']} ({kind})")
        ],
        "dcterms:description": [
            literal(
                4,
                "Description",
                clean((item.get("dcterms:description") or [{}])[0].get("@value"))
                + f"\n\n{note}",
            )
        ],
        "dcterms:creator": [literal(2, "Creator", a) for a in story["authors"]],
        "dcterms:publisher": [
            uri(
                5,
                "Publisher",
                "https://www.wikidata.org/wiki/Q122442230",
                "Stadt.Geschichte.Basel",
            )
        ],
        "dcterms:date": [literal(7, "Date", story["date"])],
        "dcterms:temporal": [
            vocab(41, "Temporal Coverage", "customvocab:14", t, "de") for t in temporal
        ],
        "dcterms:type": [
            {**uri(8, "Type", *TYPES["story"]), "type": "valuesuggestall:dc:types"}
        ],
        "dcterms:format": [
            vocab(
                9,
                "Format",
                "customvocab:15",
                FORMATS.get(screenshot.suffix.lower(), "image/png"),
            )
        ],
        "dcterms:source": [uri(11, "Source", url, "Interaktive Data Story")],
        "dcterms:language": [vocab(12, "Language", "valuesuggest:lc:iso6392", "de")],
        "dcterms:rights": [
            literal(
                15,
                "Rights",
                story_rights(story) if is_pdf else "Rechte in Prüfung",
            )
        ],
        "dcterms:license": [
            vocab(
                49,
                "License",
                "customvocab:16",
                story["license"] or "http://rightsstatements.org/vocab/InC/1.0/",
                "en",
            )
        ],
    }
    new_item = json.loads(json.dumps(item))
    new_item["o:title"] = f"Data Story: {story['title']}"
    new_item["dcterms:title"] = [literal(1, "Title", f"Data Story: {story['title']}")]
    new_item["dcterms:isPartOf"] = [uri(33, "Is Part Of", doi, story["title"])]
    problems = validation_errors(media, "media")
    print(f"item {story['item']}: title -> {new_item['o:title']!r}, isPartOf -> {doi}")
    print(
        f"new media: {screenshot} ({'public' if public else 'private'}), old media {[m['o:id'] for m in old_media]}"
    )
    if problems:
        print("validation:", *problems, sep="\n  ")
        return 1
    if not apply:
        print("dry run: nothing written")
        return 0
    path = backup([item, *old_media], f"story_{slug}")
    with httpx.Client(timeout=120) as client:
        for m in old_media:
            if m.get("o:original_url"):
                download(
                    client,
                    m["o:original_url"],
                    path.parent / f"{m['o:id']}_{m.get('o:filename')}",
                )
    print(f"backup: {path}")
    # Post the media first: if it fails, the item stays as it was.
    created = api.post("media", media, screenshot)
    # Re-read the item: a PUT replaces o:media, and the new media must stay.
    fresh = api.get("items", story["item"])
    for key in ("o:title", "dcterms:title", "dcterms:isPartOf"):
        fresh[key] = new_item[key]
    api.put("items", story["item"], fresh)
    check = api.get("items", story["item"])
    print(
        f"OK media {created['o:id']} on item {story['item']}: {[m['o:id'] for m in check['o:media']]}"
    )
    if delete_old:
        for m in old_media:
            api.delete("media", m["o:id"])
            print(f"deleted media {m['o:id']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("collect")
    p.add_argument("slug", choices=STORIES)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("upload")
    p.add_argument("slug", choices=STORIES)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--limit", type=int)
    p = sub.add_parser("ainote")
    p.add_argument("slug", choices=STORIES)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("parent")
    p.add_argument("slug", choices=STORIES)
    p.add_argument("--screenshot", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument(
        "--delete-old",
        action="store_true",
        help="delete the old story media after the upload",
    )
    args = parser.parse_args()
    if args.cmd == "collect":
        return collect(args.slug, args.force)
    if args.cmd == "upload":
        return upload(args.slug, args.apply, args.limit)
    if args.cmd == "ainote":
        return ainote(args.slug, args.apply)
    return parent(args.slug, args.screenshot, args.apply, args.delete_old)


if __name__ == "__main__":
    sys.exit(main())
