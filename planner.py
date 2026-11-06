"""30-day content calendar stored in SQLite (history.db)."""
import os, sqlite3, datetime as dt
from itertools import zip_longest

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def con():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS calendar(id INTEGER PRIMARY KEY, date TEXT, time TEXT, content_id TEXT, "
              "headline TEXT, template TEXT, status TEXT, posted_at TEXT, media_id TEXT, error TEXT, UNIQUE(date,time))")
    return c


def interleave(records):
    """Round-robin across categories, newest records first."""
    groups = {}
    for r in reversed(records):
        groups.setdefault(r["Category"], []).append(r)
    return [r for row in zip_longest(*groups.values()) for r in row if r]


def fill_calendar(records, times, days=30, start=None, allowed=("Ready",), pick=None):
    """Create slots for `days` days x len(times) and assign unused records to open slots."""
    c, start = con(), start or dt.date.today()
    for i in range(days):
        for t in times:
            c.execute("INSERT OR IGNORE INTO calendar(date,time,status) VALUES(?,?, 'Needs content')",
                      ((start + dt.timedelta(days=i)).isoformat(), t))
    used = {r[0] for r in c.execute("SELECT content_id FROM calendar WHERE content_id IS NOT NULL")}
    cands = [r for r in interleave(records) if r["Status"] in allowed and r["ID"] not in used]
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    open_slots = c.execute("SELECT id FROM calendar WHERE status='Needs content' AND date||' '||time>=? "
                           "ORDER BY date,time", (now,)).fetchall()
    n = 0
    for (sid,), r in zip(open_slots, cands):
        c.execute("UPDATE calendar SET content_id=?,headline=?,template=?,status='Scheduled' WHERE id=?",
                  (r["ID"], r["Headline"], (pick(r) if pick else r.get("Image style", "")), sid))
        n += 1
    c.commit(); c.close()
    return n


def due(now=None):
    now = (now or dt.datetime.now()).strftime("%Y-%m-%d %H:%M")
    c = con()
    rows = c.execute("SELECT id,date,time,content_id,template FROM calendar WHERE status='Scheduled' "
                     "AND date||' '||time<=? ORDER BY date,time", (now,)).fetchall()
    c.close()
    return rows


def mark(sid, status, media_id="", error=""):
    c = con()
    c.execute("UPDATE calendar SET status=?,posted_at=?,media_id=?,error=? WHERE id=?",
              (status, dt.datetime.now().strftime("%Y-%m-%d %H:%M"), media_id, error[:300], sid))
    c.commit(); c.close()
