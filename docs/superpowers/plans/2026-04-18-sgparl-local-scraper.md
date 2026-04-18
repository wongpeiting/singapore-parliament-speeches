# sgparl Local Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lean CLI tool (`python -m sgparl`) that scrapes Singapore Parliament Hansard data and saves structured CSV/JSON files locally — no cloud dependencies.

**Architecture:** Four-module Python package (`sgparl/`) with `api.py` (fetch), `parse.py` (transform), `utils.py` (helpers), `cli.py` (entry point). Ported from the existing cloud pipeline, stripping BigQuery/GDrive/Telegram/Docker. Seeds file provides known sitting dates for range queries.

**Tech Stack:** Python 3.10+, requests, beautifulsoup4, pandas, nltk

---

## File Structure

```
sgparl/                    # NEW — the package
  __init__.py              # version string
  __main__.py              # python -m sgparl entry point
  api.py                   # Parliament API client
  parse.py                 # JSON → DataFrames
  utils.py                 # name cleaning, text metrics
  cli.py                   # argparse + orchestration
seeds/
  dates.csv                # EXISTING — known sitting dates
tests/
  __init__.py
  test_utils.py
  test_api.py
  test_parse.py
  test_cli.py
  fixtures/
    sample_response.json   # recorded API response for testing
requirements.txt           # REPLACE — trimmed dependencies
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `sgparl/__init__.py`
- Create: `sgparl/__main__.py`
- Create: `tests/__init__.py`
- Create: `requirements.txt` (replace existing)

- [ ] **Step 1: Create package init**

```python
# sgparl/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 2: Create __main__.py stub**

```python
# sgparl/__main__.py
from sgparl.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create tests init**

```python
# tests/__init__.py
```

- [ ] **Step 4: Write requirements.txt**

```
beautifulsoup4>=4.11
nltk>=3.8
pandas>=2.0
requests>=2.28
pytest>=7.0
```

- [ ] **Step 5: Install dependencies**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && pip install -r requirements.txt`

- [ ] **Step 6: Commit**

```bash
git add sgparl/__init__.py sgparl/__main__.py tests/__init__.py requirements.txt
git commit -m "feat: scaffold sgparl package with trimmed dependencies"
```

---

### Task 2: utils.py — name cleaning and text metrics

**Files:**
- Create: `sgparl/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for get_mp_name**

```python
# tests/test_utils.py
from sgparl.utils import get_mp_name, count_syllables, calc_number_of_sentences


class TestGetMpName:
    def test_standard_mp_name(self):
        assert get_mp_name("Mr Leong Mun Wai") == "Leong Mun Wai"

    def test_dr_prefix(self):
        assert get_mp_name("Dr Tan See Leng") == "Tan See Leng"

    def test_mdm_prefix(self):
        assert get_mp_name("Mdm Ho Geok Choo") == "Ho Geok Choo"

    def test_speaker_format(self):
        # Speaker names have nested parentheses: (Mr Speaker Name (Title
        assert get_mp_name("SPEAKER (Mr Seah Kian Peng (Speaker)") == "Seah Kian Peng"

    def test_none_input(self):
        assert get_mp_name(None) == ""

    def test_empty_string(self):
        assert get_mp_name("") == ""

    def test_no_prefix_match(self):
        assert get_mp_name("Some Random Text") == ""


class TestCountSyllables:
    def test_one_syllable(self):
        assert count_syllables("cat") == 1

    def test_two_syllables(self):
        assert count_syllables("happy") == 2

    def test_silent_e(self):
        assert count_syllables("make") == 1

    def test_empty_word(self):
        assert count_syllables("") == 1  # minimum 1


class TestCalcNumberOfSentences:
    def test_single_sentence(self):
        assert calc_number_of_sentences("Hello world.") == 1

    def test_multiple_sentences(self):
        assert calc_number_of_sentences("Hello. World! How?") == 3

    def test_no_punctuation(self):
        assert calc_number_of_sentences("Hello world") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgparl.utils'`

- [ ] **Step 3: Implement utils.py**

```python
# sgparl/utils.py
import re

import nltk
import pandas as pd


def _ensure_nltk_data():
    """Download punkt tokenizer if not already present."""
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def get_mp_name(x):
    """Extract clean MP name from raw speaker string.

    Ported from transform/__init__.py.
    """
    if pd.isna(x) if not isinstance(x, str) else x == "":
        return ""
    if "SPEAKER" in x:
        temp = re.search(r"\(([^()]+)\(", x)
        if temp:
            match = re.sub(r"^(?:Mr|Mrs|Miss|Mdm|Ms|Dr|Prof)\s+", "", temp.group(1))
            return match.strip()
        else:
            return ""
    else:
        match = re.search(r"(?:Mr|Mrs|Miss|Mdm|Ms|Dr|Prof)\s+([\w\s-]+)", x)
        if match:
            return match.group(1).strip()
        else:
            return ""


def count_syllables(word):
    """Count syllables in a word using vowel-group heuristic.

    Ported from transform/speeches.py.
    """
    vowels = "aeiouy"
    word = word.lower()
    count = 0
    prev_char_was_vowel = False

    for char in word:
        if char in vowels:
            if not prev_char_was_vowel:
                count += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False

    if word.endswith(("e", "es", "ed")) and not word.endswith(("le", "ble", "ple")):
        count -= 1
    if count == 0:
        count = 1

    return count


def calc_number_of_syllables(text):
    """Calculate total syllables in a text string."""
    _ensure_nltk_data()
    words = nltk.word_tokenize(text)
    return sum(count_syllables(word) for word in words)


def calc_number_of_sentences(text):
    """Count sentences by splitting on sentence-ending punctuation."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    return max(len(sentences), 1)


def count_words_and_characters(text):
    """Return (num_words, num_characters) for a text string."""
    words = text.split()
    num_words = len(words)
    num_characters = len(re.findall(r"[a-zA-Z]", text))
    return num_words, num_characters
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_utils.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sgparl/utils.py tests/test_utils.py
git commit -m "feat: add utils module with name cleaning and text metrics"
```

---

### Task 3: api.py — Parliament API client

**Files:**
- Create: `sgparl/api.py`
- Create: `tests/test_api.py`
- Create: `tests/fixtures/sample_response.json`

- [ ] **Step 1: Record a real API response as a test fixture**

Run:
```bash
cd /Users/wongpeiting/singapore-parliament-speeches
mkdir -p tests/fixtures
curl -s "https://sprs.parl.gov.sg/search/getHansardReport/?sittingDate=08-01-2024" | python -m json.tool > tests/fixtures/sample_response.json
```

Verify: `python -c "import json; d=json.load(open('tests/fixtures/sample_response.json')); print(list(d.keys()))"`
Expected: `['metadata', 'attendanceList', 'takesSectionVOList']` (or similar top-level keys)

- [ ] **Step 2: Write failing tests**

```python
# tests/test_api.py
import json
from pathlib import Path
from unittest.mock import patch, Mock

from sgparl.api import fetch, _to_ddmmyyyy, NoSittingError


FIXTURES = Path(__file__).parent / "fixtures"


class TestDateConversion:
    def test_converts_yyyy_mm_dd_to_dd_mm_yyyy(self):
        assert _to_ddmmyyyy("2024-01-08") == "08-01-2024"

    def test_converts_different_date(self):
        assert _to_ddmmyyyy("1955-04-22") == "22-04-1955"


class TestFetch:
    def test_returns_parsed_json(self):
        sample = json.loads((FIXTURES / "sample_response.json").read_text())
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample

        with patch("sgparl.api.requests.get", return_value=mock_resp) as mock_get:
            result = fetch("2024-01-08")

        mock_get.assert_called_once_with(
            "https://sprs.parl.gov.sg/search/getHansardReport/?sittingDate=08-01-2024",
            timeout=30,
        )
        assert "metadata" in result
        assert "takesSectionVOList" in result

    def test_raises_on_non_200(self):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server Error")

        with patch("sgparl.api.requests.get", return_value=mock_resp):
            try:
                fetch("2024-01-08")
                assert False, "Should have raised"
            except Exception:
                pass

    def test_raises_no_sitting_on_empty_response(self):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}

        with patch("sgparl.api.requests.get", return_value=mock_resp):
            try:
                fetch("2024-01-01")
                assert False, "Should have raised NoSittingError"
            except NoSittingError:
                pass
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgparl.api'`

- [ ] **Step 4: Implement api.py**

```python
# sgparl/api.py
import datetime

import requests


class NoSittingError(Exception):
    """Raised when the API returns no data for a given date."""
    pass


def _to_ddmmyyyy(date_str):
    """Convert YYYY-MM-DD to DD-MM-YYYY for the Parliament API."""
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%d-%m-%Y")


def fetch(date):
    """Fetch Hansard report for a sitting date (YYYY-MM-DD format).

    Returns the parsed JSON response dict.
    Raises NoSittingError if no sitting found for that date.
    Raises requests.HTTPError on API errors.
    """
    date_ddmmyyyy = _to_ddmmyyyy(date)
    url = f"https://sprs.parl.gov.sg/search/getHansardReport/?sittingDate={date_ddmmyyyy}"

    print(f"Fetching: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data or "metadata" not in data:
        raise NoSittingError(f"No sitting found for {date}")

    return data
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_api.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add sgparl/api.py tests/test_api.py tests/fixtures/sample_response.json
git commit -m "feat: add API client for Parliament Hansard endpoint"
```

---

### Task 4: parse.py — transform JSON to DataFrames

**Files:**
- Create: `sgparl/parse.py`
- Create: `tests/test_parse.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_parse.py
import json
from pathlib import Path

from sgparl.parse import parse_sittings, parse_attendance, parse_topics, parse_speeches


FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture():
    return json.loads((FIXTURES / "sample_response.json").read_text())


class TestParseSittings:
    def test_returns_dataframe_with_expected_columns(self):
        data = _load_fixture()
        df = parse_sittings(data["metadata"])
        assert list(df.columns) == [
            "date", "datetime", "parliament", "session", "volume", "sittings"
        ]
        assert len(df) == 1

    def test_date_format_is_yyyy_mm_dd(self):
        data = _load_fixture()
        df = parse_sittings(data["metadata"])
        date_val = df["date"].iloc[0]
        # Should be YYYY-MM-DD format
        assert len(date_val) == 10
        assert date_val[4] == "-"


class TestParseAttendance:
    def test_returns_dataframe_with_expected_columns(self):
        data = _load_fixture()
        df = parse_attendance(data["metadata"]["sittingDate"].replace("-", "")[:4] + "-" + data["metadata"]["sittingDate"][3:5] + "-" + data["metadata"]["sittingDate"][:2] if False else "2024-01-08", data["attendanceList"])
        assert list(df.columns) == ["date", "member_name", "is_present"]
        assert len(df) > 0

    def test_all_rows_have_same_date(self):
        data = _load_fixture()
        df = parse_attendance("2024-01-08", data["attendanceList"])
        assert (df["date"] == "2024-01-08").all()


class TestParseTopics:
    def test_returns_dataframe_with_expected_columns(self):
        data = _load_fixture()
        df = parse_topics("2024-01-08", data["takesSectionVOList"])
        assert list(df.columns) == [
            "topic_id", "date", "topic_order", "title", "section_type"
        ]
        assert len(df) > 0

    def test_topic_id_format(self):
        data = _load_fixture()
        df = parse_topics("2024-01-08", data["takesSectionVOList"])
        # Topic IDs should be like "2024-01-08-T-001"
        first_id = df["topic_id"].iloc[0]
        assert first_id.startswith("2024-01-08-T-")


class TestParseSpeeches:
    def test_returns_dataframe_with_expected_columns(self):
        data = _load_fixture()
        df = parse_speeches("2024-01-08", data["takesSectionVOList"])
        expected_cols = [
            "date", "speech_id", "topic_id", "speech_order",
            "member_name_original", "member_name", "text",
            "num_words", "num_characters", "num_sentences", "num_syllables",
        ]
        assert list(df.columns) == expected_cols
        assert len(df) > 0

    def test_speech_id_format(self):
        data = _load_fixture()
        df = parse_speeches("2024-01-08", data["takesSectionVOList"])
        first_id = df["speech_id"].iloc[0]
        # Should be like "2024-01-08-T-001-S-00001"
        assert "-T-" in first_id
        assert "-S-" in first_id

    def test_text_has_no_html_tags(self):
        data = _load_fixture()
        df = parse_speeches("2024-01-08", data["takesSectionVOList"])
        for text in df["text"].head(20):
            assert "<p>" not in text
            assert "<strong>" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_parse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgparl.parse'`

- [ ] **Step 3: Implement parse.py**

```python
# sgparl/parse.py
from datetime import datetime

from bs4 import BeautifulSoup
import pandas as pd

from sgparl.utils import (
    get_mp_name,
    count_syllables,
    calc_number_of_syllables,
    calc_number_of_sentences,
    count_words_and_characters,
)


# --- Sittings ---


def parse_sittings(metadata):
    """Parse sitting metadata into a single-row DataFrame."""
    date_string = metadata["sittingDate"]
    date_object = datetime.strptime(date_string, "%d-%m-%Y")
    date_str = date_object.strftime("%Y-%m-%d")

    datetime_string = f"{date_string} {metadata['startTimeStr']}"
    datetime_string = datetime_string.replace("noon", "PM")
    datetime_object = datetime.strptime(datetime_string, "%d-%m-%Y %I:%M %p")
    datetime_str = datetime_object.strftime("%Y-%m-%dT%H:%M:%S")

    return pd.DataFrame(
        {
            "date": [date_str],
            "datetime": [datetime_str],
            "parliament": [metadata["parlimentNO"]],
            "session": [metadata["sessionNO"]],
            "volume": [metadata["volumeNO"]],
            "sittings": [metadata["sittingNO"]],
        }
    )


# --- Attendance ---


def parse_attendance(date, attendance_list):
    """Parse attendance list into a DataFrame."""
    return pd.DataFrame(
        {
            "date": [date] * len(attendance_list),
            "member_name": [get_mp_name(obj["mpName"]) for obj in attendance_list],
            "is_present": [obj["attendance"] for obj in attendance_list],
        }
    )


# --- Topics ---


def _topic_cid(date, order):
    return f"{date}-T-{order:03}"


def parse_topics(date, topics_list):
    """Parse topics list into a DataFrame."""
    orders = list(range(1, len(topics_list) + 1))
    topic_cids = [_topic_cid(date, order) for order in orders]

    return pd.DataFrame(
        {
            "topic_id": topic_cids,
            "date": [date] * len(topics_list),
            "topic_order": orders,
            "title": [section["title"] for section in topics_list],
            "section_type": [section["sectionType"] for section in topics_list],
        }
    )


# --- Speeches ---


def _process_content(soup):
    """Extract speakers and texts from BeautifulSoup-parsed HTML content.

    Ported from transform/speeches.py:process_content.
    """
    speakers = []
    texts = []
    sequences = []

    for index, p in enumerate(soup.find_all("p")):
        try:
            if p.strong:
                if (
                    str(p.strong.text).strip() == ""
                    or len(str(p.strong.text).strip()) < 3
                ) and index > 0:
                    speaker = speakers[-1]
                else:
                    speaker = str(p.strong.text).strip()
                text = str(p.find("strong").next_sibling)
                if p.find("span"):
                    text = text + " " + p.find("span").get_text()
                sequence = 1
            else:
                if len(speakers) > 0:
                    speaker = speakers[-1] if index > 0 else ""
                    sequence = sequences[-1] + 1 if index > 0 else 1
                else:
                    if soup.find_all("p")[index - 1].strong.text.strip():
                        speaker = soup.find_all("p")[index - 1].strong.text.strip()
                    else:
                        speaker = ""
                    sequence = 1
                text = str(p.text)

            speakers.append(speaker)
            texts.append(
                text.strip()
                .replace("\xa0", " ")
                .replace("\t", " ")
                .replace(":", " ")
                .strip()
            )
            sequences.append(sequence)
        except Exception as e:
            print(f"  Warning: parse error at paragraph {index}: {e}")

    # Combine consecutive texts by same speaker
    revised_speakers = []
    revised_texts = []
    last_speaker = None

    for index in range(len(speakers)):
        if (
            last_speaker == speakers[index]
            and not texts[index].strip().lower().startswith("asked")
            and "to ask" not in texts[index].strip().lower()[:10]
        ):
            revised_texts[-1] += " " + texts[index]
        else:
            revised_speakers.append(speakers[index])
            revised_texts.append(texts[index])
            last_speaker = speakers[index]

    return revised_speakers, revised_texts


def _clean_rows(df):
    """Clean speech text: strip HTML, remove boilerplate.

    Ported from transform/speeches.py:clean_rows.
    """
    df["text"] = df["text"].apply(
        lambda x: BeautifulSoup(x, "html.parser").get_text()
    )
    df["text"] = df["text"].str.replace("proc text", "", case=False)
    df["text"] = df["text"].str.replace(r"Page  \d+", "", regex=True)
    df["text"] = df["text"].str.replace("None", "")
    df = df[df["text"].astype(str).str.strip() != ""]
    return df


def _speech_cid(row):
    return f"{row['topic_id']}-S-{row['speech_order']:05}"


def _parse_topic_speeches(content, topic_cid):
    """Parse speeches from a single topic's HTML content."""
    soup = BeautifulSoup(content, "html.parser")
    speakers, texts = _process_content(soup)

    cleaned_speakers = [get_mp_name(speaker) for speaker in speakers]

    df = pd.DataFrame(
        {
            "date": [topic_cid[:10]] * len(speakers),
            "topic_id": [topic_cid] * len(speakers),
            "member_name_original": speakers,
            "member_name": cleaned_speakers,
            "text": texts,
        }
    )

    if len(df) > 0:
        df = _clean_rows(df)

    return df


def parse_speeches(date, topics_list):
    """Parse all speeches across all topics into a DataFrame."""
    all_dfs = []
    orders = list(range(1, len(topics_list) + 1))
    topic_cids = [_topic_cid(date, order) for order in orders]

    for index, topic in enumerate(topics_list):
        topic_cid = topic_cids[index]
        topic_df = _parse_topic_speeches(topic["content"], topic_cid)
        if len(topic_df) > 0:
            all_dfs.append(topic_df)

    if not all_dfs:
        return pd.DataFrame(
            columns=[
                "date", "speech_id", "topic_id", "speech_order",
                "member_name_original", "member_name", "text",
                "num_words", "num_characters", "num_sentences", "num_syllables",
            ]
        )

    df = pd.concat(all_dfs, ignore_index=True)

    # Add speech order and IDs
    df["speech_order"] = list(range(1, len(df) + 1))
    df["speech_id"] = df.apply(_speech_cid, axis=1)

    # Add text metrics
    df["num_sentences"] = df["text"].apply(calc_number_of_sentences)
    df["num_syllables"] = df["text"].apply(calc_number_of_syllables)
    wc = df["text"].apply(lambda t: pd.Series(count_words_and_characters(t), index=["num_words", "num_characters"]))
    df = pd.concat([df, wc], axis=1)

    # Final column order
    return df[
        [
            "date", "speech_id", "topic_id", "speech_order",
            "member_name_original", "member_name", "text",
            "num_words", "num_characters", "num_sentences", "num_syllables",
        ]
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_parse.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sgparl/parse.py tests/test_parse.py
git commit -m "feat: add parse module to transform API JSON into DataFrames"
```

---

### Task 5: cli.py — CLI entry point and output

**Files:**
- Create: `sgparl/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import json
from pathlib import Path
from unittest.mock import patch

from sgparl.cli import resolve_dates, save_output


FIXTURES = Path(__file__).parent / "fixtures"
SEEDS = Path(__file__).parent.parent / "seeds" / "dates.csv"


class TestResolveDates:
    def test_explicit_dates_returned_as_is(self):
        result = resolve_dates(dates=["2024-01-08", "2024-02-05"], date_from=None, date_to=None)
        assert result == ["2024-01-08", "2024-02-05"]

    def test_date_range_filters_seed_dates(self):
        result = resolve_dates(dates=None, date_from="2024-01-01", date_to="2024-01-31")
        # Should include known sitting dates in January 2024
        assert all("2024-01" in d for d in result)
        # Should not include non-sitting dates
        assert len(result) < 31

    def test_date_range_with_no_sittings_returns_empty(self):
        # Christmas week — unlikely to have sittings
        result = resolve_dates(dates=None, date_from="2024-12-24", date_to="2024-12-31")
        assert result == []


class TestSaveOutput:
    def test_save_csv(self, tmp_path):
        import pandas as pd
        data = {"sittings": pd.DataFrame({"date": ["2024-01-08"], "parliament": [14]})}
        save_output(data, str(tmp_path), "csv")
        assert (tmp_path / "sittings.csv").exists()
        df = pd.read_csv(tmp_path / "sittings.csv")
        assert len(df) == 1

    def test_save_json(self, tmp_path):
        import pandas as pd
        data = {"sittings": pd.DataFrame({"date": ["2024-01-08"], "parliament": [14]})}
        save_output(data, str(tmp_path), "json")
        assert (tmp_path / "sittings.json").exists()
        with open(tmp_path / "sittings.json") as f:
            records = json.load(f)
        assert len(records) == 1

    def test_save_both(self, tmp_path):
        import pandas as pd
        data = {"sittings": pd.DataFrame({"date": ["2024-01-08"], "parliament": [14]})}
        save_output(data, str(tmp_path), "both")
        assert (tmp_path / "sittings.csv").exists()
        assert (tmp_path / "sittings.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sgparl.cli'`

- [ ] **Step 3: Implement cli.py**

```python
# sgparl/cli.py
import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

from sgparl.api import fetch, NoSittingError
from sgparl.parse import parse_sittings, parse_attendance, parse_topics, parse_speeches


def _seeds_path():
    """Path to seeds/dates.csv, relative to this repo."""
    return Path(__file__).parent.parent / "seeds" / "dates.csv"


def resolve_dates(dates=None, date_from=None, date_to=None):
    """Resolve which dates to scrape.

    If explicit dates given, return them.
    If date_from/date_to given, filter seeds/dates.csv for sitting dates in range.
    """
    if dates:
        return sorted(dates)

    seeds_file = _seeds_path()
    if not seeds_file.exists():
        print(f"Warning: {seeds_file} not found. Cannot resolve date range.")
        return []

    seed_df = pd.read_csv(seeds_file)
    all_dates = sorted(seed_df["Sitting_Date"].tolist())

    filtered = [d for d in all_dates if date_from <= d <= date_to]
    return filtered


def save_output(dataframes, output_dir, fmt):
    """Save DataFrames to output directory as CSV and/or JSON."""
    os.makedirs(output_dir, exist_ok=True)

    for name, df in dataframes.items():
        if fmt in ("csv", "both"):
            path = os.path.join(output_dir, f"{name}.csv")
            df.to_csv(path, index=False)
            print(f"  Saved {path} ({len(df)} rows)")

        if fmt in ("json", "both"):
            path = os.path.join(output_dir, f"{name}.json")
            with open(path, "w") as f:
                json.dump(df.to_dict(orient="records"), f, indent=2)
            print(f"  Saved {path} ({len(df)} rows)")


def main():
    parser = argparse.ArgumentParser(
        prog="sgparl",
        description="Scrape Singapore Parliament Hansard speeches to local files.",
    )
    parser.add_argument(
        "--date", nargs="+", help="One or more sitting dates (YYYY-MM-DD)"
    )
    parser.add_argument("--from", dest="date_from", help="Start date for range (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", help="End date for range (YYYY-MM-DD)")
    parser.add_argument(
        "--output", default="data", help="Output directory (default: data)"
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)",
    )
    args = parser.parse_args()

    if not args.date and not (args.date_from and args.date_to):
        parser.error("Provide --date or both --from and --to")

    if (args.date_from and not args.date_to) or (args.date_to and not args.date_from):
        parser.error("Both --from and --to are required for date ranges")

    dates = resolve_dates(
        dates=args.date, date_from=args.date_from, date_to=args.date_to
    )

    if not dates:
        print("No sitting dates found for the given range.")
        sys.exit(0)

    print(f"Scraping {len(dates)} date(s): {', '.join(dates)}")

    all_sittings = []
    all_attendance = []
    all_topics = []
    all_speeches = []

    for date in dates:
        try:
            data = fetch(date)
            print(f"  [{date}] Parsing...")

            all_sittings.append(parse_sittings(data["metadata"]))
            all_attendance.append(parse_attendance(date, data["attendanceList"]))
            all_topics.append(parse_topics(date, data["takesSectionVOList"]))
            all_speeches.append(parse_speeches(date, data["takesSectionVOList"]))

            print(f"  [{date}] Done")

        except NoSittingError:
            print(f"  [{date}] No sitting found, skipping")
        except Exception as e:
            print(f"  [{date}] Error: {e}")

    if not all_sittings:
        print("No data scraped.")
        sys.exit(0)

    output = {
        "sittings": pd.concat(all_sittings, ignore_index=True),
        "attendance": pd.concat(all_attendance, ignore_index=True),
        "topics": pd.concat(all_topics, ignore_index=True),
        "speeches": pd.concat(all_speeches, ignore_index=True),
    }

    print(f"\nSaving to {args.output}/")
    save_output(output, args.output, args.fmt)
    print("Done!")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_cli.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sgparl/cli.py sgparl/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point with date resolution and file output"
```

---

### Task 6: Integration smoke test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

This test hits the real Parliament API for a known sitting date and verifies the full pipeline works end-to-end.

```python
# tests/test_integration.py
"""Integration test — hits the real Parliament API. Run with: pytest tests/test_integration.py -v -m integration"""
import pytest

from sgparl.api import fetch
from sgparl.parse import parse_sittings, parse_attendance, parse_topics, parse_speeches


@pytest.mark.integration
def test_full_pipeline_for_known_date():
    """Fetch and parse a known sitting date (8 Jan 2024) end-to-end."""
    date = "2024-01-08"
    data = fetch(date)

    sittings = parse_sittings(data["metadata"])
    assert len(sittings) == 1
    assert sittings["date"].iloc[0] == date

    attendance = parse_attendance(date, data["attendanceList"])
    assert len(attendance) > 0
    assert "member_name" in attendance.columns

    topics = parse_topics(date, data["takesSectionVOList"])
    assert len(topics) > 0

    speeches = parse_speeches(date, data["takesSectionVOList"])
    assert len(speeches) > 0
    assert speeches["num_words"].sum() > 0
    # No HTML tags in cleaned text
    for text in speeches["text"].head(10):
        assert "<p>" not in text
        assert "<strong>" not in text
```

- [ ] **Step 2: Configure pytest markers**

Add to `pyproject.toml` (create if not exists):

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: tests that hit real external APIs (deselect with '-m not integration')",
]
```

- [ ] **Step 3: Run unit tests (no network)**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/ -v -m "not integration"`
Expected: All unit tests PASS (roughly 24 tests)

- [ ] **Step 4: Run integration test (requires network)**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/test_integration.py -v -m integration`
Expected: 1 test PASS

- [ ] **Step 5: Run the actual CLI end-to-end**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m sgparl --date 2024-01-08 --output data --format both`
Expected output:
```
Scraping 1 date(s): 2024-01-08
Fetching: https://sprs.parl.gov.sg/search/getHansardReport/?sittingDate=08-01-2024
  [2024-01-08] Parsing...
  [2024-01-08] Done

Saving to data/
  Saved data/sittings.csv (1 rows)
  Saved data/sittings.json (1 rows)
  Saved data/attendance.csv (N rows)
  ...
Done!
```

Verify: `ls data/` should show `sittings.csv`, `sittings.json`, `attendance.csv`, `attendance.json`, `topics.csv`, `topics.json`, `speeches.csv`, `speeches.json`

- [ ] **Step 6: Commit**

```bash
git add tests/test_integration.py pyproject.toml
git commit -m "test: add integration smoke test and pytest config"
```

---

### Task 7: Cleanup — remove cloud pipeline files

**Files:**
- Delete: `main.py`, `extract_v1.py`, `transform_v1.py`, `Dockerfile`, `Makefile`, `nltk_req.py`
- Delete: `extract/`, `transform/`, `load/`, `utils/`, `sgparl_api/`, `schema/`
- Delete: `.github/workflows/docker-build-and-push.yaml`, `.pre-commit-config.yaml`, `.gcloudignore`
- Keep: `seeds/`, `sgparl/`, `tests/`, `docs/`, `README.md`, `LICENSE`, `notebooks/`, `resource-archive-html/`, `resource-archive-json/`, `resource-json/`, `resource-budget/`, `debug/`

- [ ] **Step 1: Remove cloud pipeline code**

```bash
cd /Users/wongpeiting/singapore-parliament-speeches
rm -f main.py extract_v1.py transform_v1.py Dockerfile Makefile nltk_req.py .gcloudignore .pre-commit-config.yaml
rm -rf extract/ transform/ load/ utils/ sgparl_api/ schema/ .github/
```

- [ ] **Step 2: Verify sgparl still works**

Run: `cd /Users/wongpeiting/singapore-parliament-speeches && python -m pytest tests/ -v -m "not integration"`
Expected: All unit tests still PASS

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove cloud pipeline code (BigQuery, GDrive, Docker, Telegram)"
```

---

### Task 8: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md with usage-focused content**

```markdown
# Singapore Parliament Speech Scraper

Scrape Singapore Parliament Hansard speeches into local CSV/JSON files.

Forked from [parleh-mate/singapore-parliament-speeches](https://github.com/parleh-mate/singapore-parliament-speeches) and stripped down to a lean local CLI tool.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Single sitting date
python -m sgparl --date 2024-01-08

# Multiple dates
python -m sgparl --date 2024-01-08 2024-02-05

# Date range (uses seeds/dates.csv to find known sitting dates)
python -m sgparl --from 2024-01-01 --to 2024-03-31

# Output options
python -m sgparl --date 2024-01-08 --output my-data/   # default: data/
python -m sgparl --date 2024-01-08 --format json        # csv (default), json, or both
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

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for local scraper usage"
```
