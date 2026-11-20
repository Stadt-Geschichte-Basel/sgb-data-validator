# How the SGB data changed

This history follows the book illustrations and Data Story sources in Omeka item set 10780. The issue logs give the details of confirmed edits.

## Clean text and link illustrations to books

The team made copies of the Omeka records to check the cleanup offline. The cleanup removed stray spaces and soft hyphens, made accented characters consistent, and repaired links. The copies showed what a later upload could change. [Offline workflow](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/pull/29) · [Text cleanup](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/pull/34)

In July 2026, the team applied text and link cleanup in Omeka. When a written citation clearly matched one of the nine books, the team replaced it with a link to the book’s DOI. This gave illustrations from the same volume a consistent link. The first July report missed some records because the download stopped early. After the team corrected the download, validation found 122 errors. [Book DOI changes](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/commit/a514931) · [July validation and edits](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/44)

The cleanup rules called for making placeholder media and their parent items private. A later review found that the old rule missed placeholders because it checked stored filenames. The current rule also checks the original source name. [Placeholder review](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/pull/52)

## Fill gaps and review identifiers and rights

On 4 November 2026, the team updated 390 records in Omeka. For example, it copied the language or historical period from a parent item when the media field was empty. It also filled empty format fields from the file type and standardized license names in rights text. The KNIL files included plain text and spreadsheets. The team added both formats to the validator’s list after it flagged those files. [Automatic edits](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/44#issuecomment-6629908653) · [Format changes](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/pull/47)

On 18 November, the team used the picture editors’ spreadsheets and media filenames to check duplicate identifiers. It assigned new numbers where different illustrations shared one identifier. It added suffixes such as `_1` and `_2` to separate files for the same object. It merged confirmed duplicates and cleared old subject values from 217 records. [Identifier and subject edits](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/44#issuecomment-6986741414)

On 19 November, the team aligned license links with the rights text and added missing licenses. That pass changed 121 media records. The issue still lists cases that need editorial decisions. [November edit log](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/44#issuecomment-6986741414) · [Open worklist](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/44)

## Archive sources from the Data Stories

The team kept the original item for each story. It attached the version from Zenodo or used a screenshot when no PDF was available. It removed the old HTML snapshots. Images, maps, charts, and datasets that readers could reuse on their own received separate items linked to the story’s DOI. [Data Story archive record](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/50) · [Story DOI correction](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/pull/51)

The team recorded a rights statement for each source it archived. The team checked the rights holder’s terms or recorded a decision from the project lead before it made a source public. It preferred higher-resolution originals and excluded duplicate files, videos, and audio. On 19 November, the archive log listed 133 public and 35 private sources. It also listed 34 sources for review and 28 exclusions. [Rights decisions and upload status](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/50) · [Source manifests](../../data/data_stories/)

## Read the evidence

- Two archived previews list 383 and 357 proposed changes. A separate upload log records 802 item updates, 988 media updates, and five media failures. [Earlier workflow guide](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/blob/4174d46c848ef01884f841a576ff74195893d7ca/API.md)
- The Data Story session notes record checks, decisions, and proposed edits. Use the issue log to confirm which edits went live. [Session 1](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/blob/4174d46c848ef01884f841a576ff74195893d7ca/data/data_stories/CHROME_SESSION.md) · [Session 2](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/blob/4174d46c848ef01884f841a576ff74195893d7ca/data/data_stories/CHROME_SESSION_2.md) · [Session 3](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/blob/4174d46c848ef01884f841a576ff74195893d7ca/data/data_stories/CHROME_SESSION_3.md)
- The examples for moving data between Omeka instances describe previews. The notes on the ontology property `hasSubjectList` record preparatory work. A live change remains unverified for either operation. [Migration guide](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/blob/4174d46c848ef01884f841a576ff74195893d7ca/examples/MIGRATION.md) · [Ontology issue](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/19)

Private comparisons, reports, and upload summaries stay in the ignored local archive. Workbooks, snapshots, media, and backups stay in their data locations.
