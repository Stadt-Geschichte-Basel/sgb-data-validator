# SGB Data Validator

Use `sgb` to check metadata in an Omeka S item set. It creates reports with links to the records you can edit in Omeka.

## Get started

Install `uv`. [Installation guide](https://docs.astral.sh/uv/getting-started/installation/)

```sh
git clone https://github.com/Stadt-Geschichte-Basel/sgb-data-validator.git
cd sgb-data-validator
uv sync --locked
cp example.env .env
```

Open `.env` in a text editor.

- Set `OMEKA_URL` to the address of your Omeka instance, such as `https://omeka.unibe.ch`.
- Set `ITEM_SET_ID` to the number in your item set’s admin URL.
- For private records or edits, enter your Omeka key in `KEY_IDENTITY` and `KEY_CREDENTIAL`. For public checks, leave both values empty. [Omeka API key guide](https://omeka.org/s/docs/user-manual/admin/users/#api-keys)

## Check an item set

```sh
uv run --locked sgb validate --export-csv
```

The command prints a report and saves CSV files in `validation_reports/`. Open `items_validation.csv` or `media_validation.csv`. Use the `edit_link` column to find a record in Omeka.

## Preview edits

```sh
uv run --locked sgb download
uv run --locked sgb transform RAW_DIR
uv run --locked sgb validate EDITED_DIR
uv run --locked sgb update RAW_DIR EDITED_DIR
```

Replace `RAW_DIR` with the directory that `download` prints. Replace `EDITED_DIR` with the directory that `transform` prints. The transform keeps the original JSON and writes a cleaned copy. For manual edits, change the JSON in the copy. Keep each record’s `o:id`.

Review the update preview. Add `--apply` to the update command when you are ready to write to Omeka. The command skips recent edits and saves private copies of records before it changes them.

## Add records or recover an item set

- Use `uv run --locked sgb create item item.json` to preview a new item. See the [JSON examples](examples/omeka-json.md) to attach a media file.
- Use `uv run --locked sgb backup` to save metadata and original files. Use `uv run --locked sgb restore BACKUP_DIR` to preview recovery. Replace `BACKUP_DIR` with the path that `backup` prints. Follow the [recovery guide](docs/recovery.md) before you restore.

Run `uv run --locked sgb --help` to see all commands.

[Published reports](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/validation-reports.html) · [Transformation history](docs/transformations/README.md) · [Contributing](CONTRIBUTING.md) · [Citation](CITATION.cff)

Code uses the [AGPL-3.0 license](LICENSE-AGPL.md). Project data uses the [CC BY 4.0 license](LICENSE-CCBY.md).
