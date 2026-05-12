"""
Scrape pre-2012 Singapore Parliament data using getHansardReport.

This endpoint returns the full sitting report as raw HTML in htmlFullContent,
including all topics and the attendance list.

Uses HTML comments (<!-- MP_NAME:Name -->) as primary speaker source (works
across all decades), with bold tags as fallback for older documents.

Output: data/all/pre2012_v2/
  speeches.csv, topics.csv, attendance.csv, sittings.csv

Usage:
    python -m sgparl.pre2012
"""

import json
import re
import time
import random
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from sgparl.utils import (
    get_mp_name, count_words_and_characters,
    calc_number_of_sentences, calc_number_of_syllables,
)

BASE_URL = "https://sprs.parl.gov.sg/search"
OUTPUT_DIR = Path("data/all/pre2012_v2")
CHECKPOINT = OUTPUT_DIR / ".checkpoint.json"


def load_checkpoint():
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {"done": []}


def save_checkpoint(state):
    CHECKPOINT.write_text(json.dumps(state))


def fetch_full_report(date_ddmmyyyy):
    """Fetch the full sitting report for a pre-2012 date."""
    url = f"{BASE_URL}/getHansardReport/?sittingDate={date_ddmmyyyy}"
    r = requests.get(url, timeout=60)
    data = r.json()
    html = data.get("htmlFullContent", "") or ""
    return html, data


def parse_attendance(html):
    """Extract PRESENT and ABSENT MPs from the full report HTML."""
    text = BeautifulSoup(html, "html.parser").get_text()
    records = []

    if "PRESENT" not in text:
        return records

    present_idx = text.index("PRESENT")
    absent_idx = text.index("ABSENT") if "ABSENT" in text else len(text)

    present_block = text[present_idx:absent_idx]
    absent_block = text[absent_idx:absent_idx + 2000] if "ABSENT" in text else ""

    name_pattern = re.compile(
        r"(?:Mr|Mrs|Ms|Mdm|Dr|Prof|Assoc\.?\s*Prof\.?|Er|BG|RAdm|Madam|Encik|Tun|Maj)\s+"
        r"([^.(]+?)(?:\s*\()",
        re.IGNORECASE,
    )

    for name_match in name_pattern.finditer(present_block):
        name = name_match.group(1).strip()
        if name and len(name) > 2 and name != "SPEAKER":
            records.append({"member_name": get_mp_name("Mr " + name) or name, "is_present": True})

    for name_match in name_pattern.finditer(absent_block):
        name = name_match.group(1).strip()
        if name and len(name) > 2 and name != "SPEAKER":
            records.append({"member_name": get_mp_name("Mr " + name) or name, "is_present": False})

    return records


def parse_sitting_metadata(html):
    """Extract sitting metadata from HTML meta tags."""
    soup = BeautifulSoup(html[:5000], "html.parser")
    metas = {m.get("name", ""): m.get("content", "") for m in soup.find_all("meta") if m.get("name")}
    return {
        "parliament": int(metas.get("Parl_No", 0)) if metas.get("Parl_No") else None,
        "session": int(metas.get("Sess_No", 0)) if metas.get("Sess_No") else None,
        "volume": int(metas.get("Vol_No", 0)) if metas.get("Vol_No") else None,
    }


def parse_topics_and_speeches(html, date):
    """Parse all topics and speeches from the full report HTML."""
    blocks = html.split("<html>")

    all_topics = []
    all_speeches = []
    topic_order = 0

    for block in blocks:
        if len(block) < 100:
            continue

        block_html = "<html>" + block
        soup = BeautifulSoup(block_html, "html.parser")

        metas = {m.get("name", ""): m.get("content", "") for m in soup.find_all("meta") if m.get("name")}
        title = metas.get("Title", "")
        section = metas.get("Sect_Name", "")

        # Skip header/attendance blocks (no Title)
        if not title and not section:
            body = soup.find("body")
            if not body:
                continue
            bold_tags = [b.get_text(strip=True) for b in body.find_all("b") if len(b.get_text(strip=True)) > 5]
            if not bold_tags:
                continue
            title = bold_tags[0] if bold_tags else "Unknown"

        topic_order += 1
        topic_id = f"{date}-T-{topic_order:03d}"

        section_type = ""
        if section:
            section_map = {
                "ORAL ANSWERS TO QUESTIONS": "OA",
                "WRITTEN ANSWERS TO QUESTIONS": "WA",
                "BILLS": "BI",
                "MOTIONS": "MO",
                "MINISTERIAL STATEMENTS": "MI",
                "BUDGET": "BU",
            }
            for key, val in section_map.items():
                if key in section.upper():
                    section_type = val
                    break
            if not section_type:
                section_type = section[:2].upper()

        all_topics.append({
            "topic_id": topic_id,
            "date": date,
            "topic_order": topic_order,
            "title": title[:200],
            "section_type": section_type,
        })

        body = soup.find("body")
        if not body:
            continue

        body_html = str(body)

        # Strategy: use HTML comments as primary speaker source (works all eras),
        # fall back to bold tags for blocks without comments.
        # Pre-2005 format: <!-- Speaker Name -->
        # Post-2005 format: <!-- MP_NAME:Speaker Name -->
        comment_pattern = re.compile(
            r'<!--\s*(?:MP_NAME:)?\s*'
            r'((?:The (?:Minister|Deputy|Senior|Prime|Chief|Acting|Parliamentary)[^-]{5,120}|'
            r'(?:Mr|Mrs|Ms|Mdm|Dr|Prof|Er|BG|Madam|Encik|Inche|Tun|Haji|Maj|Assoc)[^-]{3,80}|'
            r'Mr Speaker))'
            r'\s*-->'
        )
        bold_pattern = re.compile(
            r"<b>((?:The (?:Minister|Deputy|Senior|Prime|Chief|Acting|Parliamentary)[^<]{5,80}|"
            r"(?:Mr|Mrs|Ms|Mdm|Dr|Prof|Er|BG|Madam|Encik|Tun|Haji|Maj|Assoc)\s*\.?\s*"
            r"[\w\s.'\u2019-]{3,60}(?:\([^)]+\))?))\s*:?\s*</b>",
            re.IGNORECASE,
        )

        # Try comments first; if none found, fall back to bold tags
        comment_splits = list(comment_pattern.finditer(body_html))
        bold_splits = list(bold_pattern.finditer(body_html))
        splits = comment_splits if comment_splits else bold_splits

        for i, match in enumerate(splits):
            speaker_raw = match.group(1).strip().rstrip(":")
            if not speaker_raw:
                continue
            start = match.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(body_html)
            segment = body_html[start:end]

            segment_text = BeautifulSoup(segment, "html.parser").get_text(" ", strip=True)
            segment_text = re.sub(r"\s+", " ", segment_text).strip()
            segment_text = re.sub(r"Column:\s*\d+", "", segment_text).strip()

            if len(segment_text) < 3:
                continue

            parsed_name = get_mp_name(speaker_raw)
            wc = count_words_and_characters(segment_text)

            all_speeches.append({
                "date": date,
                "speech_id": f"{topic_id}-S-{i+1:05d}",
                "topic_id": topic_id,
                "speech_order": i + 1,
                "member_name_original": speaker_raw,
                "member_name": parsed_name,
                "text": segment_text,
                "num_words": wc[0],
                "num_characters": wc[1],
                "num_sentences": calc_number_of_sentences(segment_text),
                "num_syllables": calc_number_of_syllables(segment_text),
                "is_chairing": False,
                "is_appointment": False,
                "is_noise": False,
            })

    return all_topics, all_speeches


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dates_df = pd.read_csv(Path("seeds/dates.csv"))
    pre2012_dates = sorted(
        dates_df[dates_df["Version"] == 1]["Sitting_Date"].tolist(),
        reverse=True,
    )
    print(f"Pre-2012 sitting dates: {len(pre2012_dates)}", flush=True)

    state = load_checkpoint()
    done = set(state["done"])
    remaining = [d for d in pre2012_dates if d not in done]
    print(f"Done: {len(done)}, Remaining: {len(remaining)}", flush=True)

    speeches_file = OUTPUT_DIR / "speeches.csv"
    topics_file = OUTPUT_DIR / "topics.csv"
    attendance_file = OUTPUT_DIR / "attendance.csv"
    sittings_file = OUTPUT_DIR / "sittings.csv"

    speeches_header = not speeches_file.exists()
    topics_header = not topics_file.exists()
    att_header = not attendance_file.exists()
    sit_header = not sittings_file.exists()

    total_speeches = 0
    total_topics = 0

    for i, date in enumerate(remaining):
        parts = date.split("-")
        date_ddmmyyyy = f"{parts[2]}-{parts[1]}-{parts[0]}"

        try:
            html, raw_data = fetch_full_report(date_ddmmyyyy)

            if not html or len(html) < 100:
                done.add(date)
                continue

            metadata = parse_sitting_metadata(html)
            att_records = parse_attendance(html)
            topics, speeches = parse_topics_and_speeches(html, date)

            if speeches:
                cols = [
                    "date", "speech_id", "topic_id", "speech_order",
                    "member_name_original", "member_name", "text",
                    "num_words", "num_characters", "num_sentences",
                    "num_syllables", "is_chairing", "is_appointment", "is_noise",
                ]
                pd.DataFrame(speeches)[cols].to_csv(
                    speeches_file, mode="a", header=speeches_header, index=False
                )
                speeches_header = False

            if topics:
                pd.DataFrame(topics).to_csv(
                    topics_file, mode="a", header=topics_header, index=False
                )
                topics_header = False

            if att_records:
                att_df = pd.DataFrame(att_records)
                att_df["date"] = date
                att_df.to_csv(
                    attendance_file, mode="a", header=att_header, index=False
                )
                att_header = False

            sit_row = {
                "date": date,
                "parliament": metadata.get("parliament"),
                "session": metadata.get("session"),
                "volume": metadata.get("volume"),
            }
            pd.DataFrame([sit_row]).to_csv(
                sittings_file, mode="a", header=sit_header, index=False
            )
            sit_header = False

            total_speeches += len(speeches)
            total_topics += len(topics)
            done.add(date)

            if (i + 1) % 20 == 0:
                state = {"done": sorted(done)}
                save_checkpoint(state)
                print(
                    f"  [{i+1}/{len(remaining)}] {date}: {len(topics)} topics, "
                    f"{len(speeches)} speeches, {len(att_records)} attendance | "
                    f"cumulative: {total_speeches:,} speeches",
                    flush=True,
                )

            time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            print(f"  [{i+1}/{len(remaining)}] {date}: ERROR - {e}", flush=True)

    state = {"done": sorted(done)}
    save_checkpoint(state)
    print(f"\nDone! {total_speeches:,} speeches, {total_topics:,} topics", flush=True)


if __name__ == "__main__":
    main()
