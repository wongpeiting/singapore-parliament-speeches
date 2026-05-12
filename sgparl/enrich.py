"""
Post-processing enrichment for parliamentary speech data.

Resolves role titles ("The Prime Minister", "The Chairman") to actual names
based on date, and flags speeches made in an appointment capacity.
"""

import re
import pandas as pd


# --- Role-to-name mappings by date ---

# Singapore Prime Ministers
PM_TERMS = [
    ('1959-06-05', '1990-11-27', 'Lee Kuan Yew'),
    ('1990-11-28', '2004-08-11', 'Goh Chok Tong'),
    ('2004-08-12', '2024-05-14', 'Lee Hsien Loong'),
    ('2024-05-15', '2099-12-31', 'Lawrence Wong'),
]

# Singapore Chief Ministers (pre-independence)
CM_TERMS = [
    ('1955-04-06', '1956-06-07', 'D. S. Marshall'),
    ('1956-06-08', '1959-06-03', 'Lim Yew Hock'),
]

# Speakers of Parliament
# Gaps in 1963-64 and 1966-68 are genuine — Parliament was dissolved between terms.
SPEAKER_TERMS = [
    ('1955-04-22', '1963-09-20', 'G. E. N. Oehlers'),
    ('1964-12-08', '1966-12-06', 'A. P. Rajah'),
    ('1968-05-06', '1970-05-18', 'Punch Coomaraswamy'),
    ('1970-08-10', '1989-01-08', 'Yeoh Ghim Seng'),
    ('1989-01-09', '2002-03-24', 'Tan Soo Khoon'),
    ('2002-11-25', '2011-10-09', 'Abdullah Tarmugi'),
    ('2011-10-10', '2012-12-12', 'Michael Palmer'),
    ('2013-01-14', '2017-09-10', 'Halimah Yacob'),
    ('2017-09-11', '2023-07-17', 'Tan Chuan-Jin'),
    ('2023-08-02', '2099-12-31', 'Seah Kian Peng'),
]


def _lookup_by_date(date_str, terms):
    """Find the name for a role title on a given date."""
    for start, end, name in terms:
        if start <= date_str <= end:
            return name
    return None


def resolve_role_titles(df):
    """Resolve role titles to actual names and flag appointment-capacity speeches.

    Adds/updates columns:
    - member_name: filled in from role title where previously empty
    - is_appointment: True if the speech was made in an official appointment
      capacity (PM, Speaker, Chairman, etc.) rather than as a regular MP.
      These can be filtered out for backbench activity analysis.

    Does NOT modify member_name_original (preserving the raw Hansard text).
    """
    df = df.copy()

    if 'is_appointment' not in df.columns:
        df['is_appointment'] = False

    # --- Prime Minister ---
    pm_mask = (
        df['member_name_original'].str.match(r'^The Prime Minister\s*$', na=False) &
        (df['member_name'].fillna('') == '')
    )
    if pm_mask.any():
        df.loc[pm_mask, 'member_name'] = df.loc[pm_mask, 'date'].apply(
            lambda d: _lookup_by_date(d, PM_TERMS) or ''
        )
        df.loc[pm_mask, 'is_appointment'] = True

    # Also flag PM speeches that already have a name parsed
    pm_titled = df['member_name_original'].str.startswith('The Prime Minister', na=False)
    df.loc[pm_titled, 'is_appointment'] = True

    # --- Chief Minister (pre-independence) ---
    cm_mask = (
        df['member_name_original'].str.match(r'^The Chief Minister\s*$', na=False) &
        (df['member_name'].fillna('') == '')
    )
    if cm_mask.any():
        df.loc[cm_mask, 'member_name'] = df.loc[cm_mask, 'date'].apply(
            lambda d: _lookup_by_date(d, CM_TERMS) or ''
        )
        df.loc[cm_mask, 'is_appointment'] = True

    cm_titled = df['member_name_original'].str.startswith('The Chief Minister', na=False)
    df.loc[cm_titled, 'is_appointment'] = True

    # --- Deputy Prime Minister ---
    dpm_titled = df['member_name_original'].str.startswith('The Deputy Prime Minister', na=False)
    df.loc[dpm_titled, 'is_appointment'] = True

    # --- All ministerial speeches ---
    minister_mask = df['member_name_original'].str.contains(
        r'Minister|Parliamentary Secretary', case=False, na=False
    )
    df.loc[minister_mask, 'is_appointment'] = True

    # --- Chairing speeches (unified detection for both pipelines) ---
    # Deputy Speaker / Speaker procedural utterances and Chairman during
    # Committee proceedings. These inflate MP word counts if not filtered.
    if 'is_chairing' not in df.columns:
        df['is_chairing'] = False
    chairing_mask = df['member_name_original'].str.contains(
        r'\[Deputy Speaker.*in the Chair\]|\[Speaker.*in the Chair\]'
        r'|^Deputy Speaker\b|^The (?:Deputy )?Chairman\s*:?\s*$',
        case=False, na=False, regex=True,
    )
    df.loc[chairing_mask, 'is_chairing'] = True

    # Chairman speeches are also appointment-capacity
    chairman_mask = df['member_name_original'].str.match(
        r'^The (?:Deputy )?Chairman\s*:?\s*$', na=False
    )
    df.loc[chairman_mask, 'is_appointment'] = True

    # --- Speaker (when "Mr Speaker" is the speaker, not the addressee) ---
    # "Speaker" as member_name is already handled — these are procedural.
    # Flag any remaining Speaker-role speeches.
    speaker_mask = (df['member_name'].fillna('') == 'Speaker')
    df.loc[speaker_mask, 'is_appointment'] = True

    # --- Anonymous interjections and non-speech entries ---
    # "An hon. Member", "Some hon. Members", "Hon. Members" = unattributed
    # shouts from the chamber ("No!", "Hear, hear!"). Not real speeches.
    # "ADJOURNMENT", "(Motion)", "(Business Motion)" = procedural markers
    # that the HTML parser picked up as speeches.
    noise_mask = df['member_name_original'].str.match(
        r'^(An |Some )?[Hh]on\.?\s*Members?$|^ADJOURNMENT|^\(.*\)$|^ASSENTS TO'
        r'|^ANNUAL BUDGET|^SUPPLY BILL|^ORDER OF BUSINESS'
        r'|^BILLS?\s*$|^MOTIONS?\s*$|^PAPERS?\s*$|^DRAFT |^PROFESSIONAL '
        r'|^Vernacular Speeches$',
        na=False,
    )
    # Also flag all-caps entries with 2+ words as noise (bill/section titles
    # like "HEALTHCARE SERVICES BILL", "ROAD TRAFFIC (AMENDMENT) BILL")
    allcaps_mask = df['member_name_original'].str.match(
        r'^[A-Z][A-Z\s()\-,]+$', na=False
    ) & (df['member_name_original'].str.split().str.len() >= 2)
    # Procedural text with no speaker: bill summaries, motions, resolutions.
    # These have empty member_name_original and text like "[() Order for
    # Second Reading read. ()]" or bill descriptions starting with "to amend".
    if 'text' in df.columns:
        procedural_mask = (
            (df['member_name_original'].fillna('') == '') &
            (df['member_name'].fillna('') == '') &
            df['text'].str.match(
                r'^\[?\(?|^"to |^The following|^The President|^Resolved|^Order for',
                na=False,
            )
        )
    else:
        procedural_mask = pd.Series(False, index=df.index)
    # Short fragments that are clearly parser artifacts, not speaker names
    # (e.g. "33%", "When", "Information)")
    artifact_mask = (
        (df['member_name'].fillna('') == '') &
        (df['member_name_original'].str.len() <= 5) &
        (df['member_name_original'].fillna('') != '')
    )

    if 'is_noise' not in df.columns:
        df['is_noise'] = False
    df.loc[noise_mask, 'is_noise'] = True
    df.loc[allcaps_mask, 'is_noise'] = True
    df.loc[procedural_mask, 'is_noise'] = True
    df.loc[artifact_mask, 'is_noise'] = True

    return df


def summarise_resolutions(df):
    """Print summary of role title resolutions."""
    pm_resolved = (
        df['member_name_original'].str.match(r'^The Prime Minister\s*$', na=False) &
        (df['member_name'].fillna('') != '')
    ).sum()
    cm_resolved = (
        df['member_name_original'].str.match(r'^The Chief Minister\s*$', na=False) &
        (df['member_name'].fillna('') != '')
    ).sum()
    appt_count = df['is_appointment'].sum() if 'is_appointment' in df.columns else 0

    print(f"  'The Prime Minister' -> named: {pm_resolved}")
    print(f"  'The Chief Minister' -> named: {cm_resolved}")
    print(f"  Total appointment-capacity speeches: {appt_count:,}")
