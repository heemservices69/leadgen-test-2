"""Google Sheets output via a service account (gspread)."""
import threading, time
from collections import deque
import gspread, pandas as pd
import config

MAX_REQUESTS_PER_MINUTE = 250  # separate cap for reads and for writes (per project)


class RateLimiter:
    """Sliding-window limiter: blocks until a request is allowed within `limit` per `window` seconds."""
    def __init__(self, limit=MAX_REQUESTS_PER_MINUTE, window=60.0):
        self.limit, self.window = limit, window
        self.calls, self.lock = deque(), threading.Lock()

    def wait(self):
        while True:
            with self.lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] >= self.window:
                    self.calls.popleft()
                if len(self.calls) < self.limit:
                    self.calls.append(now)
                    return
                sleep_for = self.window - (now - self.calls[0])
            time.sleep(max(sleep_for, 0.01))


# Module-level so the cap is shared by every push() in this app instance (one project / service account).
_reads = RateLimiter()
_writes = RateLimiter()

COLUMNS = ["name", "category", "city", "phone", "email", "website", "facebook", "instagram",
           "linkedin", "address", "maps_link", "ai_score", "best_service", "ai_reason",
           "pitch", "source", "status"]

def push(df: pd.DataFrame, sheet_id: str, tab: str = "Leads") -> int:
    gc = gspread.service_account_from_dict(config.service_account_info())
    _reads.wait()
    sh = gc.open_by_key(sheet_id)
    try:
        _reads.wait()
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        _writes.wait()
        ws = sh.add_worksheet(tab, rows=1000, cols=len(COLUMNS))
    _reads.wait()
    if not ws.get_all_values():
        _writes.wait()
        ws.append_row(COLUMNS)
    _reads.wait()
    existing = ws.get_all_records()
    seen = {(r.get("name", "").lower(), str(r.get("phone", ""))) for r in existing}
    rows = []
    for _, r in df.iterrows():
        k = (str(r.get("name", "")).lower(), str(r.get("phone", "")))
        if k in seen:
            continue
        rows.append([str(r.get(c, "") if pd.notna(r.get(c, "")) else "") for c in COLUMNS[:-1]] + ["New"])
    if rows:
        _writes.wait()
        ws.append_rows(rows, value_input_option="USER_ENTERED")
    return len(rows)
