import requests, re, json, os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


URL_MAP = {
    "ohill":   "https://virginia.campusdish.com/en/locationsandmenus/observatoryhilldiningroom/",
    "newcomb": "https://virginia.campusdish.com/en/locationsandmenus/freshfoodcompany/",
    "runk":    "https://virginia.campusdish.com/en/locationsandmenus/runk/",
}

NY_TZ = ZoneInfo("America/New_York")

def get_model_from_html(url: str):
    """Fetch the page and extract the JSON object assigned to model:"""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html = r.text

    # non-greedy match for 'model: { ... }' block
    m = re.search(r'model\s*:\s*({.*})', html, re.DOTALL)
    if not m:
        raise RuntimeError("Could not find 'model:' in page")
    obj_text = m.group(1)

    # trim up to the matching closing brace by counting
    depth = 0
    for i, c in enumerate(obj_text):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                obj_text = obj_text[:i+1]
                break

    return json.loads(obj_text)

def get_menu_data(hall_name: str):
 
    url = URL_MAP.get(hall_name)
    if not url:
        raise ValueError(f"Unknown hall name: {hall_name}")
    # base model straight from page
    base_model = get_model_from_html(url)
    date_str = base_model.get("Date", "")
    location_id = str(base_model.get("LocationId", ""))
    periods = [(str(p["PeriodId"]), p.get("Name")) for p in base_model.get("Menu", {}).get("MenuPeriods", [])]

    period_payloads = {}
    for pid, pname in periods:
        try:
            payload = get_model_from_html(f"{url}?periodId={pid}")
        except Exception:
            payload = None
        period_payloads[pid] = {"name": pname, "raw": payload}

    combined = {
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z",
        "base_url": url,
        "date": date_str,
        "location_id": location_id,
        "base_model_raw": base_model,
        "periods": period_payloads,
    }
    return combined

# TIME SCRAPER:


def _extract_hours_blob(html: str) -> list[dict]:
    """
    Finds: currentHoursOfOperations = JSON.parse('[...]');
    Returns a Python list of dicts.
    """
    m = re.search(
        r"currentHoursOfOperations\s*=\s*JSON\.parse\('(?P<blob>\[.*?\])'\)",
        html, re.DOTALL
    )
    if not m:
        raise RuntimeError("Hours JSON not found on page")
    blob = m.group("blob")
    return json.loads(blob)


def _js_dow_for(date_obj: datetime) -> int:
    """
    CampusDish WeekDay: 0=Sun..6=Sat.
    Python weekday(): 0=Mon..6=Sun.
    """
    py = date_obj.weekday()        # Mon=0
    return (py + 1) % 7            # Sun=0


def _parse_local(ts: str) -> datetime:
    # Example: "2025-09-17T08:00:00" (no TZ)
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=NY_TZ)


def _fmt_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def get_hours(hall_name: str) -> dict:
    """
    Returns:
    {
      "open_time": "HH:MM",
      "close_time": "HH:MM",
      "periods": {
         "1421": {"start_time": "HH:MM", "end_time": "HH:MM"},
         ...
      }
    }
    (If closed today: open/close both "00:00" and periods empty.)
    """
    url = URL_MAP.get(hall_name.lower())
    if not url:
        raise ValueError(f"Unknown hall: {hall_name}. Options: {', '.join(URL_MAP)}")

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    blob = _extract_hours_blob(r.text)

    today_local = datetime.now(NY_TZ)
    js_dow = _js_dow_for(today_local)

    # Filter to today's, skip closed blocks
    todays = [h for h in blob if h.get("WeekDay") == js_dow and not h.get("IsClosed")]

    if not todays:
        return {"open_time": "00:00", "close_time": "00:00", "periods": {}}

    # Day bounds
    starts = [_parse_local(h["LocalStartTime"]) for h in todays]
    ends   = [_parse_local(h["LocalEndTime"])   for h in todays]
    day_open  = min(starts)
    day_close = max(ends)

    # Aggregate by MealPeriodId (some periods appear multiple slices)
    by_meal: dict[str, tuple[datetime, datetime]] = {}
    for h in todays:
        pid = str(h.get("MealPeriodId"))
        s = _parse_local(h["LocalStartTime"])
        e = _parse_local(h["LocalEndTime"])
        if pid in by_meal:
            cur_s, cur_e = by_meal[pid]
            by_meal[pid] = (min(cur_s, s), max(cur_e, e))
        else:
            by_meal[pid] = (s, e)

    periods_out = {
        pid: {"start_time": _fmt_hhmm(s), "end_time": _fmt_hhmm(e)}
        for pid, (s, e) in by_meal.items()
    }

    return {
        "open_time": _fmt_hhmm(day_open),
        "close_time": _fmt_hhmm(day_close),
        "periods": periods_out,
    }


if __name__ == "__main__":
    print(str(get_menu_data("ohill"))[0:500])
    print(json.dumps(get_hours("ohill"), indent=4))