# Chrome session: verify Data Story sources at the holders

Status: open. Issue #44. Branch `work/issue-44-data-stories`.

## Purpose

Some story sources need a real browser. The StABS Digitaler Lesesaal blocks automated access with a bot check (ALTCHA).
StABS has no general reuse rule. Each record in the Lesesaal can have its own rights statement.
This session checks each source at its holder and records the evidence in the manifest.

## Start

1. Open Google Chrome with the dedicated Claude profile. Never use Brave.
2. Start the session from the repository root:

   ```sh
   CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=0 claude --chrome
   ```

3. Give this prompt: "Execute data/data_stories/CHROME_SESSION.md."

If the Lesesaal shows the bot check, wait for it to finish in the browser. Do not try to bypass it.
If it does not finish, stop and ask the user.

## Inputs

- Manifest: `data/data_stories/<story>/manifest.csv`. Rows with `decision=review` are the work list.
- Story files: `data/data_stories/<story>/files/` (git-ignored, recreate with `collect` if missing).
- Script: `scripts/archive_data_stories.py`.

## Procedure for each StABS row

Pilot rows (story `schulden`):

| Identifier | Signatur |
|---|---|
| ds-schulden-02 | Gerichtsarchiv A 41, fol. 247v |
| ds-schulden-05 | Gerichtsarchiv A 41, fol. 233r |
| ds-schulden-06 | Gerichtsarchiv A 41, fol. 211v |
| ds-schulden-08 | Gerichtsarchiv D 6, fol. 93v |
| ds-schulden-12 | Gerichtsarchiv C 16, fol. 59r |
| ds-schulden-15 | Gerichtsarchiv E 7, fol. 46r |
| ds-schulden-16 | Gerichtsarchiv E 7, fol. 40v |
| ds-schulden-17 | Gerichtsarchiv A 41, fol. 193v |

For each row, do these steps:

1. Open https://dls.staatsarchiv.bs.ch and search for the Signatur.
2. Open the record of the volume. Find the page (folio) that matches the story image.
3. Copy the permanent record URL into `permalink`.
4. Read the rights or usage statement on the record page. Copy it word for word into `rights_evidence`, with the URL and the date.
5. Set `rights` and `license` from that statement:
   - Public domain or "gemeinfrei": `rights` = `Bilddaten gemeinfrei, Staatsarchiv Basel-Stadt, <Signatur>`, `license` = `https://creativecommons.org/publicdomain/mark/1.0/`.
   - A Creative Commons license: use that license, if it is in the Omeka list (`data/raw/vocabularies.json`).
   - Permission required, or no statement: keep `rights_status=story_cleared`. Write the statement into `notes`. Do not guess.
6. Download the page image in the highest resolution that the Lesesaal offers. Save it as `files/<identifier>_stabs.<ext>`.
7. Compare it with the story copy. Use the larger file if it shows the same content. Update `file`, `width`, `height`, `bytes` and `sha256` (`shasum -a 256`).
8. Set `rights_status=verified` only if step 4 gives a clear statement that allows publication. Then set `decision=ingest`.

## Other review rows

- **ds-schulden-01** (tally sticks, cover image, no credit): find the holder and inventory number. Look first in the collections of the Historisches Museum Basel and in the StoryMap credits. If you cannot find them, keep `decision=review` and write what you searched into `notes`.
- **ds-schulden-07** (margin drawing next to Latin print text): check whether it is a Holbein margin drawing in the "Lob der Torheit" (Froben 1515), Kunstmuseum Basel, Inv. 1662.166 (compare with Bildredaktion Band 3, ABB39199). Find the folio and the rights statement in the online collection of the Kunstmuseum. Get the highest-resolution image.

## Later stories

Run the same procedure for each story after `collect <story>`. Stories that are not on www.arcgis.com:

- `kontrollbuero`: `unibas.maps.arcgis.com`. Some items can be visible to the organization only.
- `juedisches-basel`: not a StoryMap. Collect the sources from https://das-juedische-basel.stadtgeschichtebasel.ch/ and the GitHub repository `Stadt-Geschichte-Basel/juedisches-milieu-basel`.

## Parent media

The parent media is the PDF of the story from its Zenodo record, not a screenshot (decision 2026-11-19).
Download the PDF from the DOI in `STORIES` and compare its MD5 with the Zenodo checksum.
Then run the dry run: `uv run python scripts/archive_data_stories.py parent <story> --screenshot <pdf>`.
Delete the old story media only after the user confirms.

## Known limits

- Many StABS Gerichtsarchiv volumes (for example A 41, C 16, D 6, E 7) have no scans in the Lesesaal. Then no record-level rights statement exists.
  In that case, record the volume permalink in `permalink` and keep `rights_status=story_cleared`.
  To unblock such rows, order scans and a publication permit from StABS, or ask the project lead to confirm the house practice.
- The binding StABS rights statement is in the viewer of each record ("i" icon), not in the general terms.
- Give the Chrome extension permission for each holder site before the session (for example sammlungonline.kunstmuseumbasel.ch, hmb.ch).

## Finish

1. Run `uv run python scripts/archive_data_stories.py upload <story>` (dry run). All changed rows must pass.
2. Commit the manifest on the work branch.
3. Do not run `--apply`. Report the results to the user. The user decides on the upload.
