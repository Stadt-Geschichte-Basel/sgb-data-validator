# Item set recovery

## Make a backup

Use an Omeka account that can read all items, private media, and dependencies in the set.

1. Run `sgb backup --item-set-id ID`.
2. Save the directory path that the command prints.
3. Check that `manifest.json` gives `"complete": true`.
4. Store the directory in a private location.

The backup stores the item set, items, media, and original files. The manifest records file sizes and SHA-256 hashes. The backup verifies these values against Omeka.

The tool can recreate uploads, HTML media, and URL media with stored originals. It recreates deleted URL media as uploads from the backup. It keeps the source URL in the record.

Other ingesters can depend on modules or external content. The manifest identifies unsupported ingesters and missing resources.

## Recover records

1. Run `sgb restore DIRECTORY` on the source instance.
2. Review the planned actions and external references.
3. Pause other Omeka writers during a maintenance window.
4. Run `sgb restore DIRECTORY --apply --exclusive-write`.
5. If the run stops, use the same directory to resume.
6. Review the verification output and external references.

Omeka S 3 and 4 have no conditional write check. Another writer can change a record after the final read. The flag confirms that you paused other writers.

The restore saves new resource IDs in `restore-progress.json`. Keep this file with the backup. The tool uses it to resume creation and repair links. It creates targets of required links first. Preview reports cycles that block creation.

Before it recreates a placeholder, the restore makes the placeholder and its parent item private. The preview lists the parent visibility change. The restore puts backed-up media in their recorded order. It keeps media added after the backup and puts them after the backed-up media. It checks the original file bytes after recovery.

An Omeka resource can have links from records outside the set. The tool lists known external links for editorial review. Check sites, page blocks, and external systems separately. The API limits the links that it exposes in resource metadata.

The restore skips recent edits on surviving resources. Review those records before you change `--skip-recent-hours`. Before-edit copies are in the backup directory. Omeka assigns IDs and timestamps to recreated records.

For a metadata-only backup, preview lists the proposed changes and any missing IDs. If an ID is missing, preview and apply return a failing status. Apply makes no writes in that case.

## Verification

The recovery drill used disposable Omeka S 3.2.3 and 4.2.1 instances. It restored a deleted item set, an item, and upload, URL, and HTML media on each instance.

The drill stopped after Omeka accepted a media upload. It resumed with the saved progress file. The checks covered SHA-256, file bytes, visibility, media order, and links in both directions. The drill also rejected a changed file in the backup.

Omeka S 3.2.3 returned HTTP 500 for the fixture deletes after it removed the records. Separate reads verified that the resources were absent.

Set `SGB_DRILL_URLS` to a comma-separated list of disposable loopback Omeka URLs. Use the same test API key on each instance. If Omeka runs in containers, set `SGB_DRILL_INGEST_BASE` to the URL each server uses to reach itself. Set `SGB_DRILL_KEY_IDENTITY` and `SGB_DRILL_KEY_CREDENTIAL`.

To start the instances, use the Compose files in the [omeka-s-client integration tests](https://github.com/maehr/omeka-s-client/tree/main/tests/integration). Bind each instance to the loopback interface.

Run `uv run --locked pytest test/test_recovery.py`. The drill creates and deletes its own fixture records.
