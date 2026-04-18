# How to use this scraper

A step-by-step guide. All commands are run from Terminal, inside the project folder.

## First-time setup

### 1. Open Terminal and go to the project folder

```bash
cd ~/singapore-parliament-speeches
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

This installs four Python packages: `requests` (to call the API), `beautifulsoup4` (to parse HTML), `pandas` (to structure the data), and `nltk` (for text metrics like syllable counts). You only need to do this once.

### 3. Update the list of sitting dates

The scraper ships with a list of known Parliament sitting dates (`seeds/dates.csv`), but it may be out of date. Run this to bring it up to today:

```bash
python -m sgparl --update-seeds
```

This checks every weekday from the last known sitting to today against the Parliament API. It takes a few minutes the first time. After that, you only need to run it again when you think there have been new sittings since your last update.

---

## Scraping speeches

### Scrape a single sitting

You need to know the date Parliament sat. Dates are always in `YYYY-MM-DD` format.

```bash
python -m sgparl --date 2026-04-08
```

This creates four CSV files in a `data/` folder:
- `data/speeches.csv`
- `data/topics.csv`
- `data/attendance.csv`
- `data/sittings.csv`

### Scrape multiple specific dates

```bash
python -m sgparl --date 2026-04-07 2026-04-08
```

All results are combined into the same set of files.

### Scrape a date range

If you've run `--update-seeds`, you can give a range and the scraper will figure out which days Parliament actually sat:

```bash
python -m sgparl --from 2026-01-01 --to 2026-04-18
```

This is useful for pulling a whole session at once. The scraper skips non-sitting days automatically.

### Save to a different folder

By default everything goes into `data/`. To change this:

```bash
python -m sgparl --date 2026-04-08 --output my-folder/
```

### Get JSON instead of CSV (or both)

```bash
python -m sgparl --date 2026-04-08 --format json
python -m sgparl --date 2026-04-08 --format both
```

---

## Understanding the output files

### speeches.csv

This is the main file. One row per speech paragraph.

| Column | What it is | Example |
|--------|-----------|---------|
| `date` | Sitting date | 2026-04-08 |
| `speech_id` | Unique ID for each speech | 2026-04-08-T-001-S-00002 |
| `topic_id` | Which topic this speech belongs to | 2026-04-08-T-001 |
| `speech_order` | Order of speech in the sitting | 2 |
| `member_name_original` | Raw name from Hansard | The Minister for Health (Mr Ong Ye Kung) |
| `member_name` | Cleaned name | Ong Ye Kung |
| `text` | What they said | Mr Speaker, Sir, my response today... |
| `num_words` | Word count | 186 |
| `num_characters` | Character count (letters only) | 915 |
| `num_sentences` | Sentence count | 9 |
| `num_syllables` | Syllable count | 304 |
| `party` | Political party | PAP |
| `gender` | M or F | M |

### topics.csv

One row per topic discussed.

| Column | What it is | Example |
|--------|-----------|---------|
| `topic_id` | Unique ID | 2026-04-08-T-001 |
| `date` | Sitting date | 2026-04-08 |
| `topic_order` | Order in sitting | 1 |
| `title` | Topic title | Policy on Charging Patients who Choose Different Ward Classes |
| `section_type` | Type of business | OA |

**Section types:**
- `OA` = Oral answer (MP asks a question, minister answers)
- `WA` = Written answer
- `BI` = Bill (legislation being debated)
- `MO` = Motion
- `OS` = Other (ministerial statements, etc.)

### attendance.csv

One row per MP per sitting.

| Column | What it is | Example |
|--------|-----------|---------|
| `date` | Sitting date | 2026-04-08 |
| `member_name` | MP name | Pritam Singh |
| `is_present` | Whether they attended | True |
| `party` | Political party | WP |
| `gender` | M or F | M |

### sittings.csv

One row per sitting (metadata).

| Column | What it is | Example |
|--------|-----------|---------|
| `date` | Sitting date | 2026-04-08 |
| `datetime` | Date and start time | 2026-04-08T12:00:00 |
| `parliament` | Parliament number | 15 |
| `session` | Session number | 1 |
| `volume` | Volume number | 95 |
| `sittings` | Sitting number | 135 |
| `end_time` | Adjournment time (from Hansard) | 6:05 PM |
| `duration_hours` | How long the sitting lasted | 6.08 |

---

## Common tasks

### "What did Minister X say about topic Y?"

1. Scrape the sittings you're interested in
2. Open `speeches.csv` in Excel or Google Sheets
3. Filter `member_name` for the minister
4. Search the `text` column for your keyword

### "How much did each party speak this sitting?"

1. Open `speeches.csv`
2. Create a pivot table: rows = `party`, values = sum of `num_words`

### "Who was absent?"

1. Open `attendance.csv`
2. Filter `is_present` = False

**Caveat:** The attendance list comes straight from the Hansard, which records a snapshot taken at the start of the sitting. Ministers who arrive late for their portfolio questions may be marked absent even though they spoke. For example, Tan See Leng was marked absent on 8 April 2026 but delivered 14 speeches. Cross-check against `speeches.csv` if accuracy matters for your story.

### "What bills were debated this session?"

1. Open `topics.csv`
2. Filter `section_type` = BI

### "How long was the sitting?"

1. Open `sittings.csv`
2. Check the `end_time` and `duration_hours` columns

The start time comes from the Hansard metadata. The end time is extracted from the Speaker's "Adjourned accordingly at..." statement. Budget week sittings often run 10+ hours; regular sittings are typically 6-8.

Note: If the Hansard doesn't include a clear adjournment statement, `end_time` and `duration_hours` will be blank.

### "Give me everything from the current Parliament"

```bash
python -m sgparl --from 2025-09-01 --to 2026-04-18 --output data/15th-parliament --format both
```

---

## Troubleshooting

### "No module named sgparl"

You're not in the right folder. Run:
```bash
cd ~/singapore-parliament-speeches
```

### "No sitting dates found for the given range"

Your `seeds/dates.csv` might be out of date. Run:
```bash
python -m sgparl --update-seeds
```

### The API returns an error for a date I know had a sitting

The Parliament API occasionally returns 500 errors. Wait a few minutes and try again — it usually works on retry.

### Some speeches have empty `party` or `gender`

This happens for procedural entries like "Speaker" or "Deputy Speaker" — they're not MPs, so they don't have a party. You can filter these out by removing rows where `party` is empty.

### Colons are missing from speech text

The scraper strips all colons from speech text (inherited from the upstream project). This means ratios like "1:20" become "1 20" and times like "9:00" become "9 00". Be aware of this if you're quoting figures directly from the CSV — check the original Hansard to confirm.

### "The Chairman" speeches have empty member_name

During Committee of Supply debates, the chair is "The Chairman" rather than the Speaker. The name cleaner doesn't recognise this, so those rows have blank `member_name` and no party/gender. There can be hundreds of these in a budget session.

### Lots of very short "speeches" (2-3 words)

The Speaker and Deputy Speaker calling on the next MP ("Mr Yip.", "Please proceed.") are captured as speech rows. If you're doing word counts or speech counts, filter these out — remove rows where `member_name` is "Speaker" or "Deputy Speaker", or where `num_words` is 3 or fewer.

### The warnings about "parse error at paragraph"

These are harmless. Some topics (procedural motions, etc.) have HTML that doesn't follow the standard format. The scraper skips those paragraphs and moves on. The actual speech content is unaffected.
