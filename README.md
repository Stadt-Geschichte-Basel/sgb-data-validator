# SGB Data Validator

Use `sgb` to validate, edit, create, and recover Omeka S records. Use the same commands for volumes, Data Stories, and other collections.

## Install

Run `uv sync --locked` in this checkout. Or install the wheel with `uv tool install <wheel>`.

Set `OMEKA_URL` to the Omeka instance URL. Set `ITEM_SET_ID` to the target item set ID. For authenticated work, set `KEY_IDENTITY` and `KEY_CREDENTIAL`. The CLI also reads these values from `.env` in the current directory.

Use `uv run --locked sgb` from the checkout or `sgb` after a tool installation. Run `sgb --help` for command options.

## Download and validate

```sh
sgb download --item-set-id 10780
sgb validate data/raw_itemset_10780_TIMESTAMP --export-csv --output validation_report.txt
sgb validate --item-set-id 10780 --export-csv
```

Use a snapshot directory for offline validation. Add `--check-uris` to check external links. Add `--check-redirects` to report redirects to another domain.

The CLI reads `items_raw.json`, `items_transformed.json`, or `items.json` and the matching media files. Supply `--base-url` to add edit links to a snapshot that has no source URL.

## Edit and create

```sh
sgb transform data/raw_itemset_10780_TIMESTAMP
sgb update data/raw_itemset_10780_TIMESTAMP data/transformed_itemset_10780_TIMESTAMP
sgb create item item.json --item-set-id 10780
sgb create media media.json --item-id 12345 --file illustration.tif
```

Use the paths that `download` and `transform` print. To edit a record by hand, change the Omeka JSON in a separate snapshot. Keep the record ID.

The transform writes a new snapshot and lists the fields that changed. It normalizes text, fills selected empty media fields, and applies the SGB privacy rules. Supply each book or story DOI in `dcterms:isPartOf` in the Omeka JSON.

Review the output of `update` or `create`. Add `--apply` to write the changes. The update command saves private before-edit copies in `backups/`. It skips records that changed after the source snapshot and records edited within two hours. Set `--skip-recent-hours` to change this interval.

Omeka S has no conditional write for this workflow. Another edit can occur between the final read and the write. A failed read-back or a skipped record gives a failing exit status.

See the [native JSON examples](examples/omeka-json.md) for items and media.

## Backup and restore

```sh
sgb backup --item-set-id 10780
sgb restore backups/backup_itemset_10780_TIMESTAMP
sgb restore backups/backup_itemset_10780_TIMESTAMP --apply
```

Use credentials with access to all private records in the set. Keep the backup directory private. Restore to the source instance. Keep `restore-progress.json` with the backup to resume an interrupted restore.

Full recovery supports local file uploads and HTML media. The backup records unsupported ingesters and missing dependencies in its manifest. Metadata-only backups can restore metadata on the surviving records.

See the [recovery guide](docs/recovery.md) for the recovery steps and limits.

## Project work

The [Data Story archive script](scripts/archive_data_stories.py) keeps the story rights checks and upload manifests. The [issue #44 worklist generator](scripts/generate_triage.py) reads the shared validator findings.

See the [transformation history](docs/transformations/README.md) for earlier collection edits. See the [published validation reports](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/validation-reports.html) for report formats and results.

## Project information

See the [contribution guide](CONTRIBUTING.md), [community standards](CODE_OF_CONDUCT.md), and [security policy](SECURITY.md). See the [change log](CHANGELOG.md) for version history.

The code uses the [AGPL-3.0 license](LICENSE-AGPL.md). The project data uses the [CC BY 4.0 license](LICENSE-CCBY.md). See [CITATION.cff](CITATION.cff) for citation information.

Use [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues) or [GitHub Discussions](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/discussions) for project questions.

[@maehr](https://github.com/maehr) maintains this project for [Stadt.Geschichte.Basel](https://www.stadtgeschichtebasel.ch/).
