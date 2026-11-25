# Contributing

Thank you for your help with sgb-data-validator. Follow the [code of conduct](CODE_OF_CONDUCT.md) in all project spaces.

## Set up

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Fork the repository on GitHub.
3. Clone your fork.
4. Run `uv sync --locked` in the repository root.
5. Copy `example.env` to `.env`.
6. Set the values in `.env`. The [README](README.md) explains each value.

## Make a change

1. Search the [issue tracker](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues) for related work.
2. Open or comment on an issue before a large change.
3. Create a branch from `main`, for example `work/add-language-check`.
4. Add tests for new behavior.
5. Run the checks in [AGENTS.md](AGENTS.md).
6. Run `npm run check` after documentation changes.

The [test guide](test/README.md) lists test commands for each area.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), for example `fix: keep the media order on restore`.
Mark a breaking change with `!` and a `BREAKING CHANGE:` footer.

Do not edit `CHANGELOG.md` by hand. Run `npm run changelog` to make it from the Git history.

## Record a live write

A live write changes records in Omeka. After a live write, add a row to the [live runs table](docs/transformations/README.md#live-runs). Keep the backup folder that the run prints in a private location.

## Open a pull request

1. Write a short title that names the change.
2. Explain what changed and why.
3. Link the related issue, for example `Fixes #123`.
4. Answer review comments.

## Repository structure

- [sgb_validator/](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/tree/main/sgb_validator/) contains the CLI, models, rules, and Omeka helpers. It uses [omeka-s-client](https://github.com/maehr/omeka-s-client) for Omeka API calls and snapshot files.
- [scripts/](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/tree/main/scripts/) contains the collection worklists and the Data Story tool.
- [test/](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/tree/main/test/) contains tests and the recovery drill.
- [docs/](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/tree/main/docs/) contains editor procedures and the transformation history.
- [examples/](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/tree/main/examples/) contains sample Omeka records and reports.

## Report a problem

- Use the [issue forms](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/new/choose).
- Give the steps that cause the problem.
- Add the error message and the version or commit that you use.

## License

The project uses these licenses for contributions:

- Code: [AGPL-3.0](LICENSE-AGPL.md)
- Data: [CC BY 4.0](LICENSE-CCBY.md)
