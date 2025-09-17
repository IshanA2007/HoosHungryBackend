import os
import re
import json
from datetime import datetime
import requests
from django.test import TestCase, skipUnlessDBFeature

# ⬇️ CHANGE THIS import to wherever your loader lives.
# e.g., from ..ingest import load_menu_data
from api.importers import load_menu_data

from api.models import (
    DiningHall, Day, Period, Station, MenuItem, Allergen, NutritionInfo
)

CAMPUSDISH = {
    "ohill": "https://virginia.campusdish.com/en/locationsandmenus/observatoryhilldiningroom/",
    "newcomb": "https://virginia.campusdish.com/en/locationsandmenus/freshfoodcompany/",
    "runk": "https://virginia.campusdish.com/en/locationsandmenus/runk/",
}

def _extract_model_json(html: str) -> dict:
    """
    CampusDish pages embed a big JS object like: `model: {...}`.
    We find 'model', then brace-match to extract the JSON, then json.loads it.
    """
    # Find 'model' key location (be generous about whitespace/punctuation)
    m = re.search(r'model\s*:\s*{', html)
    if not m:
        raise ValueError("Could not find embedded model JSON on page.")
    start = m.start() + html[m.start():].find('{')
    # Brace-match
    depth = 0
    i = start
    while i < len(html):
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    else:
        raise ValueError("Unterminated model JSON braces.")

    raw = html[start:end]

    # The object is JS, not strictly JSON; but CampusDish uses JSON-safe keys/values.
    # Remove trailing commas in arrays/objects if present (rare).
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    return json.loads(raw)

def _build_loader_payload(model: dict) -> tuple[dict, dict]:
    """
    Convert CampusDish model into the (data, hours) payload that load_menu_data expects.

    data = {
      "date": "MM/DD/YYYY",
      "periods": {
        "1421": {"name": "Breakfast", "raw": {"Menu": {"MenuStations": [...], "MenuProducts": [...]}}},
        ...
      }
    }

    hours = {
      "open_time": "00:00",
      "close_time": "23:59",
      "periods": {"1421": {"start_time": "00:00", "end_time": "23:59"}, ...}
    }
    """
    menu = model.get("Menu") or {}
    date_str = model.get("Date") or datetime.now().strftime("%m/%d/%Y")

    # Period list is typically present; each has Id + Name
    periods = {}
    hours_periods = {}

    # Some sites use "MenuPeriods"; if missing, we’ll derive period ids from stations/products and label generically.
    menu_periods = menu.get("MenuPeriods") or []
    if menu_periods:
        for p in menu_periods:
            pid = str(p.get("Id") or p.get("PeriodId") or "")
            pname = p.get("Name") or "Unknown"
            if not pid:
                continue
            periods[pid] = {"name": pname, "raw": {"Menu": {}}}
            # We don’t have reliable times in the embedded model -> use wide defaults to satisfy parse_time
            hours_periods[pid] = {"start_time": "00:00", "end_time": "23:59"}
    else:
        # Fallback: collect whatever PeriodId appears on stations/products
        periods_seen = set()
        for s in (menu.get("MenuStations") or []):
            if s.get("PeriodId"): periods_seen.add(str(s["PeriodId"]))
        for p in (menu.get("MenuProducts") or []):
            if p.get("PeriodId"): periods_seen.add(str(p["PeriodId"]))
        for pid in periods_seen:
            periods[pid] = {"name": f"Period {pid}", "raw": {"Menu": {}}}
            hours_periods[pid] = {"start_time": "00:00", "end_time": "23:59"}

    # Attach the station/product arrays to each period’s "raw.Menu"
    stations = menu.get("MenuStations") or []
    products = menu.get("MenuProducts") or []
    for pid, block in periods.items():
        block["raw"]["Menu"]["MenuStations"] = [s for s in stations if str(s.get("PeriodId")) == pid]
        # Products sometimes don’t carry PeriodId; in that case, include all and let your station map filter
        per_products = [p for p in products if str(p.get("PeriodId")) == pid] or products
        block["raw"]["Menu"]["MenuProducts"] = per_products

    data = {"date": date_str, "periods": periods}
    hours = {
        "open_time": "00:00",
        "close_time": "23:59",
        "periods": hours_periods,
    }
    return data, hours

def _fetch_and_build(hall_key: str):
    url = CAMPUSDISH[hall_key]
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    model = _extract_model_json(resp.text)
    return _build_loader_payload(model)


class LiveCampusDishIngestTests(TestCase):
    maxDiff = None

    def test_ingest_ohill_live(self):
        data, hours = _fetch_and_build("ohill")
        load_menu_data("ohill", data, hours)

        hall = DiningHall.objects.get(name="ohill")
        day = Day.objects.get(dining_hall=hall, date=datetime.strptime(data["date"], "%m/%d/%Y").date())

        # We should have at least one period, station, and menu item
        self.assertGreater(Period.objects.filter(day=day).count(), 0, "No periods ingested")
        stations = Station.objects.filter(period__day=day)
        self.assertGreater(stations.count(), 0, "No stations ingested")
        items = MenuItem.objects.filter(station__in=stations)
        self.assertGreater(items.count(), 0, "No menu items ingested")

        # If nutrition exists for any item, it should save decimals (not crash)
        # We don't assert counts because some live menus omit nutrition.
        if items.exists():
            any_item = items.first()
            # Nutrition OneToOne is optional, so only touch if present
            if hasattr(any_item, "nutrition_info"):
                n = any_item.nutrition_info
                # Sanity: attributes exist; not asserting values because live data varies
                _ = n.calories  # just access to ensure field is there

    def test_ingest_newcomb_live(self):
        data, hours = _fetch_and_build("newcomb")
        load_menu_data("newcomb", data, hours)
        self.assertTrue(DiningHall.objects.filter(name="newcomb").exists())

    def test_ingest_runk_live(self):
        data, hours = _fetch_and_build("runk")
        load_menu_data("runk", data, hours)
        self.assertTrue(DiningHall.objects.filter(name="runk").exists())