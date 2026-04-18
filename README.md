# Singapore Parliament Speech Scraper (local fork)

A local CLI tool for scraping Singapore Parliament Hansard speeches into CSV/JSON files.

This is a fork of [parleh-mate/singapore-parliament-speeches](https://github.com/parleh-mate/singapore-parliament-speeches), which built a cloud-based ETL pipeline (BigQuery, Google Drive, Cloud Functions) for structuring Hansard data. This fork strips out the cloud infrastructure and replaces it with a simple command-line scraper that saves files locally.

## What changed from upstream

- **Removed:** BigQuery, Google Drive, Telegram notifications, Docker, Cloud Functions, GitHub Actions
- **Added:** `sgparl/` package — a lean CLI tool (`python -m sgparl`) that outputs CSV/JSON to disk
- **Kept:** The core parsing logic (HTML speech extraction, MP name cleaning, text metrics) and `seeds/dates.csv`

## What it does

The scraper hits the [Singapore Parliament Hansard API](https://sprs.parl.gov.sg/search/home) (no API key required) and extracts structured data from each sitting:

- **Who spoke** — MP names are cleaned and standardised (handles prefixes like Mr/Mrs/Dr/Prof, Speaker titles, etc.)
- **What they said** — raw HTML from the Hansard is parsed into individual speech paragraphs, with procedural boilerplate stripped out
- **Text metrics** — each speech gets word count, character count, sentence count, and syllable count
- **Attendance** — which MPs were present or absent
- **Topics** — what was discussed (oral answers, bills, motions, etc.) with section types

Speeches from the same MP on the same topic are merged when they're consecutive paragraphs, but kept separate when they're distinct interventions (e.g. questions vs answers).

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

### Date range vs specific dates

`--from`/`--to` looks up known sitting dates in `seeds/dates.csv` to avoid hitting the API on non-sitting days. This seed file only covers sittings up to May 2024.

For anything more recent, use `--date` with specific dates instead. The Parliament API itself has no date limit — `--date 2026-04-08` works fine.

## Output

Four files saved to the output directory:

| File | Description |
|------|-------------|
| `sittings.csv` | Sitting metadata — parliament number, session, volume, sitting number, date/time |
| `attendance.csv` | One row per MP per sitting — name and whether they were present |
| `topics.csv` | Each topic discussed — title, order, and section type (OA = oral answer, WA = written answer, BI = bill, MO = motion, etc.) |
| `speeches.csv` | One row per speech paragraph — speaker (original and cleaned name), full text, word/character/sentence/syllable counts |

When scraping multiple dates, all results are combined into a single set of files.

### Example: speeches.csv columns

| Column | Example |
|--------|---------|
| `date` | 2024-05-07 |
| `speech_id` | 2024-05-07-T-001-S-00002 |
| `topic_id` | 2024-05-07-T-001 |
| `speech_order` | 2 |
| `member_name_original` | The Minister for Health (Mr Ong Ye Kung) |
| `member_name` | Ong Ye Kung |
| `text` | Mr Speaker, Sir, my response today will also address... |
| `num_words` | 186 |
| `num_characters` | 915 |
| `num_sentences` | 9 |
| `num_syllables` | 304 |

## Use cases for journalists

Some things you can do once you have the data:

- **Track what a minister said about a topic over time** — scrape multiple sittings and filter `speeches.csv` by `member_name` and keywords in `text`
- **Compare speaking patterns** — who speaks the most? Word counts and speech counts per MP across a session
- **Find all questions on a topic** — filter `topics.csv` by `section_type = "OA"` (oral answers) and search titles
- **Attendance analysis** — which MPs were absent most often? Cross-reference `attendance.csv` across sittings
- **Monitor a bill's progress** — filter topics by `section_type = "BI"` across dates to see readings and debates
- **Readability analysis** — syllable and sentence counts let you calculate Flesch-Kincaid scores to compare how different MPs communicate

The CSV output loads directly into Excel, Google Sheets, pandas, or any data tool.

## Notes

- The API occasionally returns 500 errors for specific dates — if a date fails, the scraper logs the error and continues with the remaining dates.
- Some topics (e.g. procedural motions) have minimal HTML content that produces parse warnings. These are harmless — the scraper skips unparseable paragraphs and continues.
- Dates are in `YYYY-MM-DD` format throughout.

## Credits

Original project by [parleh-mate](https://github.com/parleh-mate/singapore-parliament-speeches) (Jeremy Chia). See the upstream repo for the full cloud pipeline, dbt models, and research references.

## License

MIT — see [LICENSE](LICENSE).
