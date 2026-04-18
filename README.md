# Singapore Parliament Speech Scraper (local fork)

A local CLI tool for scraping Singapore Parliament Hansard speeches into CSV/JSON files.

This is a fork of [parleh-mate/singapore-parliament-speeches](https://github.com/parleh-mate/singapore-parliament-speeches), which built a cloud-based ETL pipeline (BigQuery, Google Drive, Cloud Functions) for structuring Hansard data. This fork strips out the cloud infrastructure and replaces it with a simple command-line scraper that saves files locally.

## What changed from upstream

- **Removed:** BigQuery, Google Drive, Telegram notifications, Docker, Cloud Functions, GitHub Actions
- **Added:** `sgparl/` package — a lean CLI tool (`python -m sgparl`) that outputs CSV/JSON to disk
- **Kept:** The core parsing logic (HTML speech extraction, MP name cleaning, text metrics) and `seeds/dates.csv`

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Single sitting date
python -m sgparl --date 2024-05-07

# Multiple dates
python -m sgparl --date 2024-05-07 2024-02-05

# Date range (uses seeds/dates.csv to find known sitting dates)
python -m sgparl --from 2024-01-01 --to 2024-03-31

# Output options
python -m sgparl --date 2024-05-07 --output my-data/   # default: data/
python -m sgparl --date 2024-05-07 --format json        # csv (default), json, or both
```

## Output

Four files saved to the output directory:

| File | Description |
|------|-------------|
| `sittings.csv` | Sitting metadata — parliament, session, volume, date/time |
| `attendance.csv` | MP attendance per sitting |
| `topics.csv` | Topics discussed, with section type |
| `speeches.csv` | Individual speech paragraphs with speaker, text, and word/syllable/sentence counts |

## Data source

[Singapore Parliament Hansard](https://sprs.parl.gov.sg/search/home) — no API key required.

## Credits

Original project by [parleh-mate](https://github.com/parleh-mate/singapore-parliament-speeches) (Jeremy Chia). See the upstream repo for the full cloud pipeline, dbt models, and research references.

## License

MIT — see [LICENSE](LICENSE).
