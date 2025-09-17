import requests, re, json, os
from datetime import datetime, timezone

BASE_URL = "https://virginia.campusdish.com/en/locationsandmenus/observatoryhilldiningroom/"

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

def main(dump_dir: str = "ohill_dumps", also_split_files: bool = False):
    os.makedirs(dump_dir, exist_ok=True)

    # base model straight from page
    base_model = get_model_from_html(BASE_URL)
    date_str = base_model.get("Date", "")
    location_id = str(base_model.get("LocationId", ""))
    periods = [(str(p["PeriodId"]), p.get("Name")) for p in base_model.get("Menu", {}).get("MenuPeriods", [])]

    period_payloads = {}
    for pid, pname in periods:
        try:
            payload = get_model_from_html(f"{BASE_URL}?periodId={pid}")
        except Exception:
            payload = None
        period_payloads[pid] = {"name": pname, "raw": payload}

        if also_split_files and payload:
            out_path = os.path.join(dump_dir, f"period_{pid}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

    combined = {
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z",
        "base_url": BASE_URL,
        "date": date_str,
        "location_id": location_id,
        "base_model_raw": base_model,
        "periods": period_payloads,
    }

    out_name = f"ohill_raw_{date_str.replace('/','-') or 'unknown'}.json"
    out_path = os.path.join(dump_dir, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    return combined

if __name__ == "__main__":
    main(also_split_files=True)