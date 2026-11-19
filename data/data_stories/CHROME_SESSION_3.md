# Chrome session 3: captions with the user, open rights, Jüdisches Basel

Status: open. Issue #44. Branch `work/issue-44-data-stories`, PR #49.
Read `CHROME_SESSION.md` and `CHROME_SESSION_2.md` first. Their rules also apply here.

## Purpose

86 story images have no usable caption or credit. A person must identify them.
In this session, Claude prepares each row and the user supplies the caption.
The session also closes the remaining rights checks and collects *Das jüdische Basel*.

## Start

1. Open Google Chrome with the dedicated Claude profile. Never use Brave.
2. Give the Chrome extension permission for these sites:
   storymaps.arcgis.com, unibas.maps.arcgis.com, gallica.bnf.fr, hmb.ch, e-rara.ch, avisblatt.philhist.unibas.ch, das-juedische-basel.stadtgeschichtebasel.ch, github.com.
3. Start the session from the repository root:

   ```sh
   CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=0 claude --chrome
   ```

4. Give this prompt: "Execute data/data_stories/CHROME_SESSION_3.md."

## Roles

| Claude | User |
|---|---|
| Opens the story at the image and shows the row data. | Looks at the image. |
| Proposes a draft from the story text and the story PDF. | Confirms, corrects or writes the caption. |
| Searches the holder for a record and a rights statement. | Passes bot checks (Cloudflare, ALTCHA). |
| Writes the manifest and runs the dry run. | Decides on exclusions, rights rulings and uploads. |

## Rules

- Never invent a caption, a creator, a date or a holder. Write only what the story, the holder or the user states.
- Record the source of each caption in `notes`: "Bildlegende vom Benutzer bestätigt, <date>" or "Bildlegende aus <URL>, <date>".
- A caption from the user does not verify the rights. The rights still need a holder statement or a user ruling (see part B).
- Set `rights_status=verified` only with evidence in `rights_evidence`. Without evidence, keep `story_cleared`. Such a record stays private.
- Descriptions marked "Neu entworfen mit dem korrigierten walk(); von Hand prüfen." are drafts. Check each one against the image.
- In sidecar stories, the text of the image is in the same slide. In other stories, the text can come before the image. Check this with the user.
- Write manifests with `csv.DictWriter(..., lineterminator="\n")`.
- Do not run `--apply`. The user decides on each upload.
- Do not close a tab inside `browser_batch`. This breaks the tab group.

## Part A: captions with the user

Do this procedure story by story, in the order of the tables below.

1. Open the story URL in a new tab. Scroll to the image of the row. If you cannot find it, use `data/data_stories/<story>/story.pdf`.
2. Show the user one batch of up to five rows. For each row, give:
   - the identifier and the file name in `data/data_stories/<story>/files/`
   - the current `title`, `description` and `attribution`
   - the story text next to the image
   - your draft for title, creator, date and holder, marked as a draft
3. Ask the user for each row:
   - **Caption:** title, creator, date (EDTF, for example `1620~`), holder and shelfmark, or
   - **Exclude:** with a reason, for example `exclude:decorative`, `exclude:duplicate of ds-<story>-NN`, `exclude:base map`, `exclude:external video`.
4. Write the answer into the manifest. Put the caption source into `notes`.
5. If the user names a holder, do part B for the row.
6. If the user does not know the image, keep `decision=review`. Write "Benutzer: unbekannt, <date>" into `notes`.
7. After each story, run the dry run: `uv run python scripts/archive_data_stories.py upload <story>`.

Links (`kind=link`) point to dashboards, external videos or web maps. A link alone does not show that its data is archived. Exclude a web map link only if the manifest has a dataset row for its layers with a `file` and a `sha256` (a successful export). Otherwise keep the row for review. Ask the user whether each other link has a separate source. If not, exclude it.

### seide (25 rows)

Story: https://storymaps.arcgis.com/stories/90a309d6d21342608d0ad3ee16fb3f30

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-seide-01 | image | (no credit) |
| ds-seide-02 | image | Albert Höflinger, Porträt des Kupferstechers Johann Jakob Falkeisen (1882) |
| ds-seide-03 | image | (no credit) |
| ds-seide-04 | image | (no credit) |
| ds-seide-07 | image | (no credit) |
| ds-seide-08 | image | (no credit) |
| ds-seide-09 | image | (no credit) |
| ds-seide-10 | image | (no credit) |
| ds-seide-11 | image | (no credit) |
| ds-seide-12 | image | (no credit) |
| ds-seide-13 | image | (no credit) |
| ds-seide-14 | image | Johann Rudolf Forcart-Weiss |
| ds-seide-15 | image | Württembergerhof |
| ds-seide-16 | image | (no credit) |
| ds-seide-17 | image | Johann Sigmund Alioth |
| ds-seide-18 | image | Schappefabrik |
| ds-seide-19 | image | Der erste Brief von Jacques Glavany Fils & Co. an Forcart-Weiss & Söhne (1825) |
| ds-seide-20 | image | R. Glavany, Angestellter der Osmanischen Bank, um 1900 |
| ds-seide-21 | image | Pont de Galata |
| ds-seide-22 | image | A. Bonnal, Angestellter der Osmanischen Bank, um 1900 |
| ds-seide-23 | image | Les quais de Smyrne |
| ds-seide-24 | image | Kontokorrentbuch der Industriegsellschaft für Schappe, Eintrag 1898: Einkauf von |
| ds-seide-25 | image | Dampfschiffe in Izmir |
| ds-seide-26 | image | Ruderboote blieben auch nach der Ausbreitung der Dampfschiffe ein wichtiges Verk |
| ds-seide-29 | image | Türkische Damen aus der osmanischen Oberschicht |

### konzil (27 rows)

Story: https://storymaps.arcgis.com/stories/0cac069fdac24f13a06377a1c7294a33

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-konzil-01 | image | (no credit) |
| ds-konzil-02 | image | (no credit) |
| ds-konzil-03 | image | (no credit) |
| ds-konzil-04 | image | (no credit) |
| ds-konzil-05 | image | (no credit) |
| ds-konzil-06 | image | (no credit) |
| ds-konzil-07 | image | (no credit) |
| ds-konzil-08 | image | (no credit) |
| ds-konzil-09 | image | (no credit) |
| ds-konzil-10 | image | (no credit) |
| ds-konzil-11 | image | (no credit) |
| ds-konzil-12 | image | (no credit) |
| ds-konzil-13 | image | (no credit) |
| ds-konzil-14 | image | Galata Blick auf Pera, Istanbul. |
| ds-konzil-15 | image | Hartmann Schedel, Weltchronik, Nürnberg 1493, Stadtansicht von Basel, 243v-244r. |
| ds-konzil-16 | image | Matthäus Merian, Stadtansicht von Basel, 1615 |
| ds-konzil-23 | video | Quelle: Youtube , besucht: 24. März 2024. |
| ds-konzil-24 | image | Hartmann Schedel, Weltchronik, Nürnberg 1493, 242v-243r. |
| ds-konzil-25 | image | Hartmann Schedel, Weltchronik, Nürnberg 1493, 243r. |
| ds-konzil-28 | image | Hans Leu d.Ä., Altartafeln mit der ältesten Ansicht von Zürich, Schweizerische |
| ds-konzil-29 | audio | Zitat aus: Martin Luther, Verlegung des Alcoran , Wittenberg 1542. |
| ds-konzil-30 | image | Titelblatt des lateinischen Koran, Basel [Johannes Oporin] 1543. Digitalisat |
| ds-konzil-31 | image | Inhaltsverzeichnis von Band I. des lateinischen Koran. |
| ds-konzil-33 | image | Der Orientalist Theodor Bibliander in einem Gemälde von Hans Asper (1550), Fraue |
| ds-konzil-34 | image | Vorwarnung für den christlichen Leser von Martin Luther |
| ds-konzil-35 | image | Expansion des osmanischen Reiches zwischen 14. und 17. Jahrhundert |
| ds-konzil-36 | image | Pinturicchio, Pius II. in Ancona, Libreria Piccolomini, Siena (1507-1507). |

### kontrollbuero (15 rows)

Story: https://storymaps.arcgis.com/stories/6be823309a7b4254aa27b5486703b68b

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-kontrollbuero-02 | link | France Gall - Der Computer Nr. 3 ( live ) - Berlin - 1968 |
| ds-kontrollbuero-09 | image | Still aus der Sendung "Gulliver im Land der Schweiz" (24.4.24) |
| ds-kontrollbuero-18 | image | (no credit) |
| ds-kontrollbuero-19 | image | (no credit) |
| ds-kontrollbuero-20 | image | (no credit) |
| ds-kontrollbuero-21 | image | (no credit) |
| ds-kontrollbuero-22 | image | (no credit) |
| ds-kontrollbuero-24 | image | (no credit) |
| ds-kontrollbuero-25 | image | (no credit) |
| ds-kontrollbuero-26 | image | (no credit) |
| ds-kontrollbuero-27 | image | (no credit) |
| ds-kontrollbuero-28 | image | (no credit) |
| ds-kontrollbuero-29 | image | Prinzip der Verwaltungsdatenbank: Gemäss den Aufgaben-Schwer |
| ds-kontrollbuero-30 | image | (no credit) |
| ds-kontrollbuero-31 | link | Die Karte zeigt die Verwaltungsstellen, die Daten mit dem Kontrollbüro austausch |

### kirche (5 rows)

Story: https://storymaps.arcgis.com/stories/34ef391bd4fa419cb82d488906608154

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-kirche-01 | image | (no credit) |
| ds-kirche-03 | image | Die Schedelsche Weltchronik von 1493 zeigt unverkennbar die Stadt Basel und die |
| ds-kirche-18 | image | Überlieferungseffekt am Beispiel des Klosters Klingental. Deutlich ist der Einfl |
| ds-kirche-19 | image | HGB-Karteikarte Untere Rebgasse 10 (HGB 1 155/34, S. 12) mit Regionenerkennung. |
| ds-kirche-20 | image | Untersuchte Institutionen und Anzahl Treffer auf Ebene Dossier (d.h. Häuser) und |

### bioarchaeologie (6 rows)

Story: https://storymaps.arcgis.com/stories/54d35e03bcdf4841b092d4c4906227e9

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-bioarchaeologie-01 | image | (no credit) |
| ds-bioarchaeologie-03 | image | (no credit) |
| ds-bioarchaeologie-04 | image | Quelle: Wikipedia (Nutzer Sansculotte; Nutzer Novarte) / F.A.Z- Karte Piron |
| ds-bioarchaeologie-28 | link | Teil 1 Datastory Final |
| ds-bioarchaeologie-40 | link | Teil 2 Datastory Final |
| ds-bioarchaeologie-46 | image | Graphik: Ben Krause-Kyora, IKMB Kiel. Verändert von: Margaux Depaermentier. |

### schnupftabak (7 rows)

Story: https://storymaps.arcgis.com/stories/e2096bc80f714932b8eba10ee7e23b4b

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-schnupftabak-01 | video | (no credit) |
| ds-schnupftabak-05 | image | Tabakanbau beim Wirtshaus 'zum Neuen Haus' in Kleinhüningen vor den Toren von Ba |
| ds-schnupftabak-06 | image | (no credit) |
| ds-schnupftabak-10 | image | Bild: Wunderlin 2019, S. 39, Abb. 6, Dezember 2018. |
| ds-schnupftabak-11 | image | (no credit) |
| ds-schnupftabak-12 | image | (no credit) |
| ds-schnupftabak-13 | image | (no credit) |

### schulden (1 rows)

Story: https://storymaps.arcgis.com/stories/1955ccada8d74ff6919e9e1397cb168a

| Identifier | Kind | Title or credit in the story |
|---|---|---|
| ds-schulden-01 | image | Kerbhölzer, um 1600 |

## Part B: rights checks

| Row | Task | Who |
|---|---|---|
| ds-konzil-17 to ds-konzil-22 | BnF Gallica, Latin Koran translation (about 1142/43). Ask the user to pass the Cloudflare check. Read the Gallica terms of use. Download the highest-resolution image (IIIF `full/max`). Check if the license is in `data/raw/vocabularies.json`. | Claude, user for the check |
| ds-schnupftabak-15 | Avis-Blatt of 3 January 1788, No. 1, p. 1 (UB Basel). The paper is "Wöchentliche Nachrichten aus dem Berichthaus zu Basel". Search avisblatt.philhist.unibas.ch and e-rara. | Claude |
| ds-schnupftabak-34 | HMB 2011.640 and HMB 1922.158. Apply the HMB ruling (CC BY-SA 4.0, hmb.ch/museum/bildbestellung). Get the originals from the HMB online collection ("Suche starten" button). | Claude |
| ds-schulden-01 | Tally sticks (Kerbhölzer), about 1600. Search the HMB online collection. If no result, the user asks Benjamin Hitz for the source. | Claude, user |
| ds-schnupftabak-02, -29, -30 | Reproductions from publications (Heege 2011; Oesterreich 2018, DPMA trademarks). Find the original holder. The user decides: ingest as private, or exclude. | User |
| ds-bioarchaeologie-21, -46 | Story graphics based on work by Irka Hajdas (ETH) and Ben Krause-Kyora (IKMB Kiel). The user confirms the license with the authors. | User |
| ds-kirche-03, ds-konzil-15, -24, -25 | Schedel, Weltchronik 1493. Identify the copy (library and shelfmark) and get its rights statement. | Claude |
| kontrollbuero, `hold:abb21892` | The fix log of 18 November 2026 decided that item 13553 keeps `abb21892`. Set `decision=reuse:13553`. The upload adds the story DOI to the item. | Claude |

## Part C: titles that are credit lines

Some uploaded items have a credit line as title, for example "HMB 1998.103, fol. 39, um 1620" or "Grab 2.".
Also the ten ready schnupftabak rows have such titles.

1. Make a list of uploaded rows whose title starts with a holder code (`HMB`, `ABBS`, `StABS`) or is "Grab N.".
2. For each row, propose a descriptive title from the holder record or the story text. Keep the credit line in `attribution`.
3. The user confirms the titles in batches.
4. Update the manifest. For uploaded rows, back up the record, change `dcterms:title` in Omeka, and read the record again. Do this only after the user approves.

## Part D: Das jüdische Basel and the Konzil PDF

1. Open https://das-juedische-basel.stadtgeschichtebasel.ch/ and the repository `Stadt-Geschichte-Basel/juedisches-milieu-basel`.
2. Make `data/data_stories/juedisches-basel/manifest.csv` by hand with the same columns. `collect` supports only ArcGIS StoryMaps.
3. Use the image credits on the site. Do part A with the user for images without a credit.
4. The code ZIP on Zenodo (DOI 10.5281/zenodo.15681537) has the MIT license. This license applies to the code, not to the images.
5. Make a screenshot of the start page for the parent item 12869 (the story has no PDF).
6. Konzil: the Zenodo PDF (DOI 10.5281/zenodo.15242726) is 315 MB. Ask the user for the Omeka upload limit before you upload. Do not compress the PDF without approval.

## Part E: decisions for the user

Ask the user these questions at the end of the session:

1. Upload the ten ready schnupftabak rows (03, 04, 14, 16, 19, 20, 21, 22, 24, 33)? The dry run passes.
2. Delete the old HTML snapshot media 12859, 12860, 12862, 12864, 12865, 12872, 12873, 12875, 12876? Keep 12867, 12868 (Konzil) and 12870 (Jüdisches Basel) until their new media exist.
3. Upload the rows that this session made ready?

## Finish

1. Run the dry run for each changed story. All rows must pass.
2. Commit the manifests on the work branch. Push.
3. Report to the user: rows with captions, rows excluded, rows still open, decisions needed.
4. Add a short status to the Data Stories issue. Do not close any issue.
