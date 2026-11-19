# Chrome session 2: verify house practice and review open rows

> Historical record. See the [operations index](README.md) for recorded outcomes.

Status: open. Issue #44. Branch `work/issue-44-data-stories`, PR #49.
Read `docs/transformations/CHROME_SESSION.md` first. Its start, rules and finish steps also apply here.

## Start

1. Open Google Chrome with the dedicated Claude profile. Never use Brave.
2. Give the Chrome extension permission for the holder sites in part A.
3. Start the session from the repository root:

   ```sh
   CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=0 claude --chrome
   ```

4. Give this prompt: "Execute docs/transformations/CHROME_SESSION_2.md."

## Rules

- Never infer a license from the story or from house practice alone. House practice is a hint, not evidence.
- Set `rights_status=verified` only with a statement from the holder: a rights field on the record page, the published terms of use, or a written permission. Copy it into `rights_evidence` with the URL and the date.
- If the holder has a larger original than the story copy, download it and update `file`, `width`, `height`, `bytes` and `sha256`.
- After verification, set `decision=ingest`. If verification fails, keep `hold:chrome` or `review` and write the reason into `notes`.
- Do not run `--apply`. The user decides on the upload.

## Part A: verify the house practice for each holder

The suggested rights follow the practice in Omeka item set 10780 (counts of 2026-11-19).

| Holder                                           | House practice in Omeka                     | Check                                                                                                  |
| ------------------------------------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Archäologische Bodenforschung Basel-Stadt (ABBS) | CC BY-SA 4.0, credit (89 records)           | Terms of use on the ABBS website, or the agreement with Stadt.Geschichte.Basel (ask the project lead). |
| Historisches Museum Basel (HMB)                  | CC BY-SA 4.0, credit (101 records)          | Rights field of each object in the HMB online collection (search by inventory number).                 |
| Universitätsbibliothek Basel                     | Public Domain Mark (43 records)             | Rights statement on e-manuscripta, e-rara or swisscollections for each shelfmark.                      |
| Kunstmuseum Basel                                | "Bilddaten gemeinfrei" + Public Domain Mark | Rights field in sammlungonline.kunstmuseumbasel.ch for each inventory number.                          |
| Staatsarchiv Basel-Stadt                         | "Bilddaten gemeinfrei" + Public Domain Mark | No general rule. Check each record in the Digitaler Lesesaal (viewer, "i" icon).                       |
| ETH-Bibliothek Zürich, BnF, others               | –                                           | Rights statement on the record page.                                                                   |

If one statement covers a whole holder (for example published ABBS terms), record it once here. Then apply it to all rows of that holder.

## Part B: rows on hold or in review

`hold:chrome`: credit and suggested rights exist, the check at the holder is missing.
`review`: the credit, title or holder is missing. Identify the object first: use the story PDF in `data/data_stories/<story>/story.pdf` (or the Zenodo record) and the story text in `context`.
Many images without a credit are decorative or duplicates. Exclude them with `decision=exclude:<reason>`.

### seide

| Identifier  | Status | Title or credit                                                        | Holder | Note                                     |
| ----------- | ------ | ---------------------------------------------------------------------- | ------ | ---------------------------------------- |
| ds-seide-01 | review | (no credit, file 9Dimchg9XmyRUh-A0AAGX.jpeg)                           |        |                                          |
| ds-seide-02 | review | Albert Höflinger, Porträt des Kupferstechers Johann Jakob Falkeisen (1 |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-03 | review | (no credit, file fuX8EIFMdniJodsJv19-O.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-04 | review | (no credit, file \_YQSYosKanmiF3nGMlj1W.jpeg)                          |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-07 | review | (no credit, file fQBzWTyyRuGJ1KMbdclts.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-08 | review | (no credit, file kZiWioCAHAKdNCVD1BI1A.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-09 | review | (no credit, file QfTMYejAXl6zywk_ic4mr.jpg)                            |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-10 | review | (no credit, file H9WDoDshJTsgGCnFogIzf.jpg)                            |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-11 | review | (no credit, file ssPxzWKCmA9b-1Qy76dsy.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-12 | review | (no credit, file KLMZZfYW_3SbX6zHvX2An.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-13 | review | (no credit, file 3VdiKfq1k-Q8preRnnI3i.png)                            |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-14 | review | Johann Rudolf Forcart-Weiss                                            |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-15 | review | Württembergerhof                                                       |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-16 | review | (no credit, file T7DbpH0SCftpgRJPaoPoV.jpeg)                           |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-17 | review | Johann Sigmund Alioth                                                  |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-18 | review | Schappefabrik                                                          |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-19 | review | Der erste Brief von Jacques Glavany Fils & Co. an Forcart-Weiss & Söhn |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-20 | review | R. Glavany, Angestellter der Osmanischen Bank, um 1900                 |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-21 | review | Pont de Galata                                                         |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-22 | review | A. Bonnal, Angestellter der Osmanischen Bank, um 1900                  |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-23 | review | Les quais de Smyrne                                                    |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-24 | review | Kontokorrentbuch der Industriegsellschaft für Schappe, Eintrag 1898: E |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-25 | review | Dampfschiffe in Izmir                                                  |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-26 | review | Ruderboote blieben auch nach der Ausbreitung der Dampfschiffe ein wich |        | Beschreibung aus dem Story-Text, prüfen. |
| ds-seide-29 | review | Türkische Damen aus der osmanischen Oberschicht                        |        | Beschreibung aus dem Story-Text, prüfen. |

### kirche

| Identifier   | Status      | Title or credit                                                        | Holder                   | Note                                                                             |
| ------------ | ----------- | ---------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------- |
| ds-kirche-01 | review      | (no credit, file \_Entd48lpJiGu5cn3IWBk.jpg)                           |                          |                                                                                  |
| ds-kirche-02 | hold:chrome | Zinsbeschreibung eines Hauses in einem Stadtgerichtsurteil von 1497 (S | Staatsarchiv Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-kirche-03 | review      | Die Schedelsche Weltchronik von 1493 zeigt unverkennbar die Stadt Base |                          | Holzschnitt aus der Schedelschen Weltchronik (1493). Vorlage (Exemplar, Biblioth |
| ds-kirche-18 | review      | Überlieferungseffekt am Beispiel des Klosters Klingental. Deutlich ist |                          | Beschreibung aus dem Story-Text, prüfen.                                         |
| ds-kirche-19 | review      | HGB-Karteikarte Untere Rebgasse 10 (HGB 1 155/34, S. 12) mit Regionene |                          | Beschreibung aus dem Story-Text, prüfen.                                         |
| ds-kirche-20 | review      | Untersuchte Institutionen und Anzahl Treffer auf Ebene Dossier (d.h. H |                          | Beschreibung aus dem Story-Text, prüfen.                                         |

### schnupftabak

| Identifier         | Status      | Title or credit                                                        | Holder                                    | Note                                                                         |
| ------------------ | ----------- | ---------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------------------- |
| ds-schnupftabak-01 | review      | (no credit, file 9OojHW\_-rj729ROL2a7Du.mp4)                           |                                           |                                                                              |
| ds-schnupftabak-02 | hold:chrome | Nicotiana rustica, Konrad Gessner, 1554.                               |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-03 | hold:chrome | HMB 1998.103, fol. 39, um 1620                                         | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-04 | hold:chrome | HMB 1998.103, fol. 58, um 1620                                         | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-05 | review      | Tabakanbau beim Wirtshaus 'zum Neuen Haus' in Kleinhüningen vor den To |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-06 | review      | (no credit, file Q7-hbAQXYT-oZdN0HY4O0.png)                            |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-07 | review      | HMB 1873.40, Bild: Historisches Museum Basel.                          | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-08 | review      | HMB 1967.26.a-c., Bild: Historisches Museum Basel.                     | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-09 | hold:chrome | Aquarell von Johann Jakob Schneider, STABS BILD Schn. 117              | Staatsarchiv Basel-Stadt                  | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-10 | review      | Bild: Wunderlin 2019, S. 39, Abb. 6, Dezember 2018.                    |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-11 | review      | (no credit, file Ic6l1DHp-lEc20JQ6YAN1.png)                            |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-12 | review      | (no credit, file OuCQgubUAJ7Cs5LbmVrhv.png)                            |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-13 | review      | (no credit, file G03XntAZ3oxvgpQZQ0YiQ.png)                            |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-14 | hold:chrome | HMB 1935.102, Geschäftskarte, um 1830                                  | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-15 | hold:chrome | UB Basel, Avis-Blatt 1788, Nr. 1, 03.01.1788, S. 1                     | Universitätsbibliothek Basel              | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-16 | hold:chrome | HMB 1925.167, Ölbild auf Karton, gemalt von Maximilian Neustück        | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-17 | hold:chrome | HMB 1997.56.1 , gemalt von Joseph Esperlin, 1757                       | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-18 | hold:chrome | Friedrich Hey (links) HMB Inv. 1937.28                                 | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-19 | hold:chrome | HMB 1920.177 Uhr in Tabakdose; HMB 1932.21 Tabakdose mit Teleskopfernr | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-20 | hold:chrome | HMB 1928.792, gemalt von Emanuel Burckhardt-Sarasin, um 1796           | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-21 | hold:chrome | HMB 1940.49, um 1850                                                   | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-22 | hold:chrome | Schnupftabakdosen aus dem 18. Jahrhundert                              | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-24 | hold:chrome | HMB 1985.363, 1. Hälfte des 18. Jh                                     | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-25 | hold:chrome | HMB 1969.2226, um 1820                                                 | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-26 | hold:chrome | HMB 1969.2226, um 1820                                                 | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-27 | hold:chrome | HMB 1896.14, 18. Jahrhundert                                           | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-28 | review      | HMB 1896.14; Foto: Historisches Museum Basel.                          | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-29 | hold:chrome | Werbemarke der Firma Anton Coblenz für Tabakwaren, 1895.               |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-30 | hold:chrome | DPMA Nr. 15519, Henr. Oldenkott Jnr. & Comp. 25.02.1896, in: Oesterrei |                                           | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-schnupftabak-31 | review      | HMB 1967.25, Foto: Historisches Museum Basel.                          | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-32 | review      | HMB 1967.26.a-c., Bild: Historisches Museum Basel.                     | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-33 | hold:chrome | ABBS Inv. 2001/10.352 (Fundort Klosterberg 21), in: Freitag 2019, S. 1 | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-schnupftabak-34 | hold:chrome | HMB 2011.640 und HMB 1922.158                                          | Historisches Museum Basel                 | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |

### konzil

| Identifier   | Status      | Title or credit                                                        | Holder                           | Note                                                                         |
| ------------ | ----------- | ---------------------------------------------------------------------- | -------------------------------- | ---------------------------------------------------------------------------- |
| ds-konzil-01 | review      | (no credit, file H5XjiARGA5fpwHb3d9NOo.jpeg)                           |                                  |                                                                              |
| ds-konzil-02 | review      | (no credit, file i0gaVNapcxAK7bvgOh4Hf.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-03 | review      | (no credit, file zlC3E8TbpiMl9t-9RcQtz.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-04 | review      | (no credit, file lz3RNeQBwC_WDta4Kij_i.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-05 | review      | (no credit, file FFbu2qPqr2TWJ1Mzo89fo.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-06 | review      | (no credit, file NMMlOcZaAIR0mub91QIvU.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-07 | review      | (no credit, file YaE3CqYm59qHz0Uo9uALV.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-08 | review      | (no credit, file 5OcfhP6mcziA3fFsCOLWw.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-09 | review      | (no credit, file PliUhhZf6nU5NDtDvtLf9.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-10 | review      | (no credit, file -LQW-AxOVK9pSWHBra6TU.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-11 | review      | (no credit, file t7M7oRedEbxm7_MESTAmK.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-12 | review      | (no credit, file Yzm87mSdqWBXkUhGulKZb.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-13 | review      | (no credit, file S40ZpRpRq3PYx4dYXLdd3.jpg)                            |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-14 | review      | Galata Blick auf Pera, Istanbul                                        |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-15 | review      | Hartmann Schedel, Weltchronik, Nürnberg 1493, Stadtansicht von Basel,  |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-16 | review      | Matthäus Merian, Stadtansicht von Basel, 1615                          |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-17 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-18 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-19 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-20 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-21 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-22 | hold:chrome | Lateinische Übersetzung des Koran und Schriften gegen den Islam, um 11 | Bibliothèque nationale de France | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-23 | review      | Expansion des Osmanischen Reichs zwischen 1299 und 1453.               |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-24 | review      | Hartmann Schedel, Weltchronik, Nürnberg 1493, 242v-243r                |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-25 | review      | Hartmann Schedel, Weltchronik, Nürnberg 1493, 243r                     |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-26 | hold:chrome | Arabischer Koran, Basel, UB, A III 19, Innenseite Buchdeckel           | Universitätsbibliothek Basel     | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-konzil-28 | review      | Hans Leu d.Ä., Altartafeln mit der ältesten Ansicht von Zürich, Schw   |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-29 | review      | Zitat aus: Martin Luther, Verlegung des Alcoran , Wittenberg 1542.     |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-30 | review      | Titelblatt des lateinischen Koran, Basel [Johannes Oporin] 1543. Digit |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-31 | review      | Inhaltsverzeichnis von Band I. des lateinischen Koran                  |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-32 | hold:chrome | Der Drucker Johannes Oporin in einem Gemälde von Hans Bock d.Ä. (um 15 | Kunstmuseum Basel                | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-konzil-33 | review      | Der Orientalist Theodor Bibliander in einem Gemälde von Hans Asper (15 |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-34 | review      | Vorwarnung für den christlichen Leser von Martin Luther                |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-35 | review      | Expansion des osmanischen Reiches zwischen 14. und 17. Jahrhundert     |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-konzil-36 | review      | Pius II. vor Ancona, von wo er zum Kreuzzug aufbrechen wollte.         |                                  | Beschreibung aus dem Story-Text, prüfen.                                     |

### bioarchaeologie

| Identifier            | Status      | Title or credit                                                        | Holder                                    | Note                                                                             |
| --------------------- | ----------- | ---------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------- |
| ds-bioarchaeologie-01 | review      | (no credit, file 6HPXSCYnPrUUJbUStv3Qn.jpeg)                           |                                           |                                                                                  |
| ds-bioarchaeologie-03 | review      | (no credit, file dNq2jCbR0qP4Dx5r_8Dkp.png)                            |                                           | Beschreibung aus dem Story-Text, prüfen.                                         |
| ds-bioarchaeologie-04 | review      | Die spätantike Völkerwanderung in Europa.                              |                                           | Beschreibung aus dem Story-Text, prüfen.                                         |
| ds-bioarchaeologie-05 | hold:chrome | Basler Münsterhügel um 347 n. Chr.                                     | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-06 | hold:chrome | Die Grabungsfläche wurde bis auf das Niveau der Bestattungen mit dem B | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-07 | hold:chrome | Archäologische Bodenforschung Basel-Stadt                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-08 | review      | Foto: Archäologische Bodenforschung Basel-Stadt.                       | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-09 | hold:chrome | Verletzter Schädel des Mannes aus Grab 9                               | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-10 | hold:chrome | Archäologische Bodenforschung Basel-Stadt                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-11 | hold:chrome | Gesamtplan der Gräbergruppe mit hinterlegter moderner Bebauung.        | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-12 | hold:chrome | Kindergrab 1                                                           | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-13 | hold:chrome | Vollständiges Glas aus dem Kindergrab 1                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-14 | hold:chrome | Einzige Glasperle aus dem Kindergrab 1                                 | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-15 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-16 | hold:chrome | Kindergrab 6                                                           | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-17 | hold:chrome | Glas aus dem Kindergrab 6                                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-18 | hold:chrome | Recto (Vorderseite) der Münze aus dem Kindergrab 6                     | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-19 | hold:chrome | Verso (Rückseite) der Münze aus dem Kindergrab 6                       | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-20 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-21 | hold:chrome | ETH Zürich, Graphik-Grundlage: Irka Hajdas                             | ETH Zürich                                | Beschreibung aus dem Story-Text, prüfen.                                         |
| ds-bioarchaeologie-27 | hold:chrome | Archäologische Bodenforschung Basel-Stadt                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-28 | review      | Teil 1 Datastory Final                                                 |                                           |                                                                                  |
| ds-bioarchaeologie-29 | hold:chrome | Hier sieht man, welche Bestatteten im Gräberfeld für Sr- und O-Isotope | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-36 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-37 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-40 | review      | Teil 2 Datastory Final                                                 |                                           |                                                                                  |
| ds-bioarchaeologie-41 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-46 | review      | Graphik: Ben Krause-Kyora, IKMB Kiel. Verändert von: Margaux Depaermen | Stadt.Geschichte.Basel                    | Eigene Grafik der Story, Lizenz beim Autor bestätigen. Beschreibung aus dem Stor |
| ds-bioarchaeologie-49 | review      | Archäologische BodenforschungBasel-Stadt, Foto: Philippe Saurbeck.     | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-50 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-51 | hold:chrome | Archäologische Bodenforschung Basel-Stadt                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-52 | hold:chrome | Glasbecher                                                             | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-53 | hold:chrome | Glasperle                                                              | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-55 | hold:chrome | Grab 2.                                                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-56 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-57 | hold:chrome | Grab 3.                                                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-58 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-60 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-61 | hold:chrome | Grab 5.                                                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-62 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-68 | hold:chrome | Grab 7.                                                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-69 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-70 | hold:chrome | Grab 8.                                                                | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-71 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-74 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-75 | hold:chrome | Grab 10.                                                               | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |
| ds-bioarchaeologie-76 | review      | Plan: Andreas Niederhäuser, Jessica Fäh. Bearbeitung: Peter von Holz   | Archäologische Bodenforschung Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen.     |

### kontrollbuero

| Identifier          | Status      | Title or credit                                                        | Holder                   | Note                                                                         |
| ------------------- | ----------- | ---------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------- |
| ds-kontrollbuero-01 | hold:chrome | Zwei IBM 3270 Bildschirmterminal                                       | ETH-Bibliothek Zürich    |                                                                              |
| ds-kontrollbuero-02 | review      | France Gall - Der Computer Nr. 3 ( live ) - Berlin - 1968              |                          |                                                                              |
| ds-kontrollbuero-09 | review      | Lochkarten werden in dem dafür vorgesehenen Grossrechner verarbeitet   |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-18 | review      | (no credit, file VG3VVYLQL7fcwWZGBfnU5.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-19 | review      | (no credit, file nlBiqwaGZn-9aG5WBHO0a.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-20 | review      | (no credit, file 4pVhE3KMx40YmEMJe3GCZ.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-21 | review      | (no credit, file LQ1iaOSvZzmH0WMx5NGoT.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-22 | review      | (no credit, file Muxup3IGFfC515J3HGo-g.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-23 | hold:chrome | StABS BSL 1013 1-7106 1 (Foto Hans Bertolf)                            | Staatsarchiv Basel-Stadt | Rechte nach Hauspraxis (ungeprüft). Beschreibung aus dem Story-Text, prüfen. |
| ds-kontrollbuero-24 | review      | (no credit, file LAD1kpHdz084QNXxOXagj.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-25 | review      | (no credit, file IHgF3BnAFpNoHtHoLi_1t.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-26 | review      | (no credit, file UMYcIZ8xczPCYnXtehXQz.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-27 | review      | (no credit, file Dwv6XhoJGN0idSyss_iXx.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-28 | review      | (no credit, file 0owpa8L-ruIxEFKjF6yUZ.jpeg)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-29 | review      | Prinzip der Verwaltungsdatenbank: Gemäss den Aufgaben-Schwerpunkte der |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-30 | review      | (no credit, file 8AV\_-qav6_H5smPXq2-4F.png)                           |                          | Beschreibung aus dem Story-Text, prüfen.                                     |
| ds-kontrollbuero-31 | review      | Die Karte zeigt die Verwaltungsstellen, die Daten mit dem Kontrollbüro |                          |                                                                              |

### schulden

| Identifier     | Status | Title or credit                                                        | Holder                                 | Note                                                                             |
| -------------- | ------ | ---------------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------- |
| ds-schulden-01 | review | Kerbhölzer, um 1600                                                    |                                        | Chrome-Session 2026-11-19: Storytext und Story-Links ohne Bildnachweis für die K |
| ds-schulden-02 | review | Urteil des Stadtgerichts vom 2. Oktober 1497 (Peter von Wissenburg geg | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv A 41 im Digitalen Lesesaal nicht  |
| ds-schulden-05 | review | Urteil des Stadtgerichts von 1497 (Franz Galizian gegen Martin Flach)  | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv A 41 im Digitalen Lesesaal nicht  |
| ds-schulden-06 | review | Urteil des Stadtgerichts vom 11. Mai 1497 (Berchtold Müller gegen Pete | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv A 41 im Digitalen Lesesaal nicht  |
| ds-schulden-07 | review | Randzeichnung in einem Druck des frühen 16. Jahrhunderts               | Kunstmuseum Basel, Kupferstichkabinett | Chrome-Session 2026-11-19: Bildnachweis im Storytext: «Zeichnung von Hans Holbei |
| ds-schulden-08 | review | Zeugenaussage zu einem Schuhkauf auf Kredit, 1456                      | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv D 6 im Digitalen Lesesaal nicht d |
| ds-schulden-12 | review | Seite aus dem Vergichtbuch von 1497                                    | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv C 16 im Digitalen Lesesaal nicht  |
| ds-schulden-15 | review | Verbote auf das Gut von Anton Waltenhein, um 1497                      | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv E 7 im Digitalen Lesesaal nicht d |
| ds-schulden-16 | review | Frönung eines Hauses wegen versessener Zinsen, um 1497                 | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv E 7 im Digitalen Lesesaal nicht d |
| ds-schulden-17 | review | Schuldklage von Hans zum Rotenfahnen gegen Jakob Spidler, 1497         | Staatsarchiv Basel-Stadt               | Chrome-Session 2026-11-19: Band Gerichtsarchiv A 41 im Digitalen Lesesaal nicht  |

## Part C: other open work

- **Das jüdische Basel** (item 12869): collect the sources from https://das-juedische-basel.stadtgeschichtebasel.ch/ and the repository `Stadt-Geschichte-Basel/juedisches-milieu-basel`. Write `data/data_stories/juedisches-basel/manifest.csv` with the same columns. The Zenodo record holds only the code ZIP (MIT). Make a full-page screenshot for the parent media.
- **Konzil und Koran** (item 12866): the Zenodo PDF is 315 MB. Check if Omeka accepts it. If not, ask the user how to proceed.
- **Kontrollbüro**: SRF stills are uploaded as private items 13826–13852. They stay private.

## Finish

1. Run `uv run python scripts/archive_data_stories.py upload <story>` (dry run) for each changed story.
2. Commit the manifests on the work branch.
3. Report the results to the user.
