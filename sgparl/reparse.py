"""
Re-parse member_name from member_name_original in existing speech CSVs.

Use this after improving get_mp_name() in sgparl/utils.py — no rescraping needed.
The raw `member_name_original` column is preserved from the original scrape;
this script only regenerates the cleaned `member_name` column.

Usage:
    python -m sgparl.reparse                          # reparse data/all/speeches_all.csv
    python -m sgparl.reparse path/to/speeches.csv     # reparse a specific file
    python -m sgparl.reparse --all                    # reparse all speech CSVs in data/all/
"""

import sys
from pathlib import Path

import pandas as pd

from sgparl.utils import get_mp_name
from sgparl.enrich import resolve_role_titles, summarise_resolutions


def reparse(filepath):
    """Re-apply get_mp_name() and role-title resolution to a speech CSV."""
    filepath = Path(filepath)
    print(f"Loading {filepath}...")
    df = pd.read_csv(filepath, low_memory=False)

    if "member_name_original" not in df.columns:
        print(f"  Skipping — no member_name_original column")
        return

    old = df["member_name"].copy()
    df["member_name"] = df["member_name_original"].apply(get_mp_name)

    # Resolve role titles (PM, Chief Minister) to actual names by date
    df = resolve_role_titles(df)

    changed = (old.fillna("") != df["member_name"].fillna("")).sum()
    empty_before = (old.fillna("") == "").sum() + old.isna().sum()
    empty_after = (df["member_name"].fillna("") == "").sum() + df["member_name"].isna().sum()

    print(f"  Rows: {len(df):,}")
    print(f"  Names changed: {changed:,} ({changed/len(df)*100:.1f}%)")
    print(f"  Empty names: {empty_before:,} -> {empty_after:,}")
    print(f"  Unique speakers: {df['member_name'].nunique()}")
    summarise_resolutions(df)
    appt = df['is_appointment'].sum() if 'is_appointment' in df.columns else 0
    print(f"  Appointment-capacity speeches: {appt:,}")

    df.to_csv(filepath, index=False)
    print(f"  Saved {filepath}")
    return df


def main():
    data_dir = Path("data/all")

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Reparse component speech CSVs (skip speeches_all.csv — it gets rebuilt below)
        for f in sorted(data_dir.glob("speeches*.csv")):
            if f.name == "speeches_all.csv":
                continue
            reparse(f)
            print()
        # Also reparse pre2012_v2 if it exists
        pre2012_v2 = data_dir / "pre2012_v2" / "speeches.csv"
        if pre2012_v2.exists():
            reparse(pre2012_v2)
            print()

        # Rebuild speeches_all.csv from the two canonical sources
        print("Rebuilding speeches_all.csv...")
        sources = [
            data_dir / "pre2012_v2" / "speeches.csv",
            data_dir / "speeches_post2012.csv",
        ]
        parts = []
        for p in sources:
            if p.exists():
                parts.append(pd.read_csv(p, low_memory=False))
                print(f"  Loaded {p.relative_to(data_dir)}: {len(parts[-1]):,} rows")
        if parts:
            # Post-2012 takes priority for overlapping dates
            post_dates = set(parts[-1]["date"].unique()) if len(parts) > 1 else set()
            combined = pd.concat(
                [p[~p["date"].isin(post_dates)] for p in parts[:-1]] + [parts[-1]],
                ignore_index=True,
            ).sort_values("date").reset_index(drop=True)
            combined.to_csv(data_dir / "speeches_all.csv", index=False)
            print(f"  Saved speeches_all.csv: {len(combined):,} rows")
    elif len(sys.argv) > 1:
        reparse(sys.argv[1])
    else:
        reparse(data_dir / "speeches_all.csv")


if __name__ == "__main__":
    main()
