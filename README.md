# SGB Data Validator

Stadt.Geschichte.Basel (SGB) researches and documents Basel’s history. The team uses Omeka S to catalog book illustrations and reusable sources from the Data Stories. The public research data platform gives readers access to the sources behind the publications. [Project documentation](https://dokumentation.stadtgeschichtebasel.ch/) · [Research data platform](https://forschung.stadtgeschichtebasel.ch/)

An Omeka item describes a source. Its media records describe the attached files, with fields for format, rights, and license. The validator checks required fields, duplicate identifiers, and allowed values such as historical periods. Its reports link to the records that need review. [SGB data model](https://dokumentation.stadtgeschichtebasel.ch/products/research-data/datamodel/)

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
- For private records or edits, enter your Omeka key in `KEY_IDENTITY` and `KEY_CREDENTIAL`. For public checks, leave both values empty and pass `--public-only`. [Omeka API key guide](https://omeka.org/s/docs/user-manual/admin/users/#api-keys)
- Omeka requests ignore `HTTP_PROXY` and `HTTPS_PROXY`. The validator needs a direct connection to Omeka.

## Check an item set

```sh
uv run --locked sgb validate --export-csv
```

The command prints a report and saves CSV files in `validation_reports/`. Open `items_validation.csv` or `media_validation.csv`. Use the `edit_link` column to find a record in Omeka. Use `--max-file-size MB` to change the file size warning limit.

## Preview edits

```sh
uv run --locked sgb download
uv run --locked sgb transform RAW_DIR
uv run --locked sgb validate EDITED_DIR
uv run --locked sgb update RAW_DIR EDITED_DIR
```

Replace `RAW_DIR` with the directory that `download` prints. Replace `EDITED_DIR` with the directory that `transform` prints. The transform keeps the original JSON and writes a cleaned copy. For manual edits, change the JSON in the copy. Keep each record’s `o:id`.

Review the update preview. Pause other Omeka writers during a maintenance window. Run the update again with `--apply --exclusive-write`. The command skips recent edits and saves private copies before it changes records.

## Add records or recover an item set

- Use `uv run --locked sgb create item item.json` to preview a new item. See the [JSON examples](examples/omeka-json.md) to attach a media file.
- Use `uv run --locked sgb backup` to save metadata and original files. Use `uv run --locked sgb restore BACKUP_DIR` to preview recovery. Replace `BACKUP_DIR` with the path that `backup` prints. Follow the [recovery guide](docs/recovery.md) before you restore.

Run `uv run --locked sgb --help` to see all commands.

[Published reports](https://dokumentation.stadtgeschichtebasel.ch/sgb-data-validator/validation-reports.html) · [Transformation history](docs/transformations/README.md) · [Changelog](CHANGELOG.md) · [Recovery guide](docs/recovery.md) · [Tests](test/README.md) · [Contributing](CONTRIBUTING.md) · [Citation](CITATION.cff)

Code uses the [AGPL-3.0 license](LICENSE-AGPL.md). Project data uses the [CC BY 4.0 license](LICENSE-CCBY.md).
