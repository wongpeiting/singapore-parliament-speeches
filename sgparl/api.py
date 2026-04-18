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


def check_sitting(date):
    """Check if a date has a parliamentary sitting. Returns True/False.

    Does not raise on 500 errors — just returns False.
    """
    date_ddmmyyyy = _to_ddmmyyyy(date)
    url = f"https://sprs.parl.gov.sg/search/getHansardReport/?sittingDate={date_ddmmyyyy}"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return False
        data = response.json()
        return bool(data and "metadata" in data)
    except Exception:
        return False


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
