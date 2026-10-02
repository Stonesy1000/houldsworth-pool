"""Weekly pull: reads scraper/urls.txt, saves every table to data/latest.json."""
import io, json, sys, time, datetime, pathlib
import requests
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELAY_SECONDS = 6
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/129 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-GB,en;q=0.9"}

def flat(col):
    if isinstance(col, tuple):
        return " ".join(str(c) for c in col if "Unnamed" not in str(c)).strip()
    return "" if "Unnamed" in str(col) else str(col)

lines = [l.strip() for l in (ROOT / "scraper/urls.txt").read_text().splitlines()
         if l.strip() and not l.strip().startswith("#")]

pages, failed = [], 0
for i, line in enumerate(lines, 1):
    label, url = (p.strip() for p in line.split("|", 1)) if "|" in line else (f"Page {i}", line)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(f"{label}: HTTP {r.status_code}, {len(r.text)} chars")
        r.raise_for_status()
        if not r.text.strip():
            raise ValueError(f"Blank page returned (HTTP {r.status_code}) - site may be refusing cloud servers")
        try:
            found = pd.read_html(io.StringIO(r.text))
        except ValueError:
            found = []
    except Exception as e:
        failed += 1
        print(f"FAILED {label}: {e}")
        pages.append({"label": label, "url": url, "error": str(e)[:200], "tables": []})
        continue
    tables = [{"columns": [flat(c) for c in df.columns],
               "rows": df.fillna("").astype(str).values.tolist()} for df in found]
    pages.append({"label": label, "url": url, "tables": tables})
    print(f"OK {label}: {len(tables)} table(s)")
    time.sleep(DELAY_SECONDS)

if lines and failed == len(lines):
    print("Every page failed - keeping last week's data.")
    sys.exit(1)

out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
       "pages": pages, "failed": failed}
(ROOT / "data/latest.json").write_text(json.dumps(out, ensure_ascii=False))
print(f"Saved {len(pages)} page(s), {failed} failed.")
