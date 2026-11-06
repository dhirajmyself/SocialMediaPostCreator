"""Autopilot: refresh news -> keep 30-day calendar full -> prepare/publish due posts.
Run once:  python runner.py      Keep running:  python runner.py --loop"""
import os, sys, time, datetime as dt
import pandas as pd
import niche, planner, publisher
from engine import render, png_bytes, make_caption, pick_template

BASE = os.path.dirname(os.path.abspath(__file__))
XLSX, OUT = os.path.join(BASE, "Health_Content.xlsx"), os.path.join(BASE, "output")
COLS = ["ID", "Category", "Headline", "Hook", "Main content", "Description", "Supporting tip", "Source URL",
        "Hashtags", "Caption", "CTA", "Image style", "Status", "Review note"]
ALIASES = {"main content": "Main content", "supporting tip": "Supporting tip", "source": "Source URL",
           "source url": "Source URL", "image style": "Image style", "review note": "Review note"}


def clean(df):
    df = df.rename(columns={c: ALIASES.get(str(c).strip().lower(), str(c).strip()) for c in df.columns})
    miss = [c for c in ("Headline", "Main content") if c not in df.columns]
    if miss:
        raise ValueError("Missing required column(s): " + ", ".join(miss))
    for c in COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLS].fillna("").astype(str)
    df = df[df["Headline"].str.strip() != ""].reset_index(drop=True)
    blank = df["ID"].str.strip() == ""
    df.loc[blank, "ID"] = [f"HP{i + 1:03d}" for i in df.index[blank]]
    return df


def load_df():
    return clean(pd.read_excel(XLSX)) if os.path.exists(XLSX) else pd.DataFrame(columns=COLS)


def refresh_news(s, df):
    items, errs = niche.fetch_all(s)
    seen = set(df["Source URL"]) | set(df["Headline"].str.lower())
    new = []
    for it in items:
        r = niche.to_record(it, s)
        if r["Source URL"] in seen or r["Headline"].lower() in seen or r["ID"] in set(df["ID"]):
            continue
        seen |= {r["Source URL"], r["Headline"].lower()}
        new.append(r)
        if len(new) >= s["max_new_per_run"]:
            break
    return (pd.concat([df, pd.DataFrame(new)], ignore_index=True) if new else df), len(new), errs


def allowed(s):
    return ("Ready",) if s["require_approval"] else ("Ready", "Draft")


def run_once(brand=None, log=print):
    s = niche.load_settings()
    brand = brand if brand is not None else load_brand()
    df = load_df()
    df, added, errs = refresh_news(s, df)
    log(f"News: +{added} new, {len(errs)} feed errors {errs[:2]}")
    if added:
        df.to_excel(XLSX, index=False)
    n = planner.fill_calendar(df.to_dict("records"), s["times"], 30, allowed=allowed(s),
                              pick=lambda r: pick_template(r))
    log(f"Calendar: {n} slots filled")
    by_id = {r["ID"]: r for r in df.to_dict("records")}
    live = s["auto_publish"] and publisher.configured(s)
    done = 0
    for sid, d, t, cid, tpl in planner.due()[:3]:
        if dt.datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M") < dt.datetime.now() - dt.timedelta(hours=24):
            planner.mark(sid, "Missed"); continue
        rec = by_id.get(cid)
        if rec is None:
            planner.mark(sid, "Failed", error="content row not found"); continue
        try:
            img, cap = render(rec, tpl or pick_template(rec), brand), make_caption(rec, brand)
            folder = os.path.join(OUT, f"{d}_{t.replace(':', '')}_{cid}")
            os.makedirs(folder, exist_ok=True)
            open(os.path.join(folder, "post.png"), "wb").write(png_bytes(img))
            open(os.path.join(folder, "caption.txt"), "w", encoding="utf-8").write(cap)
            if live:
                url = publisher.cloud_upload(publisher.jpg_bytes(img), f"hp_{cid}_{int(time.time())}", s)
                mid = publisher.ig_publish(url, cap, s)
                planner.mark(sid, "Published", mid)
                df.loc[df["ID"] == cid, "Status"] = "Published"
            else:
                planner.mark(sid, "Prepared")
            done += 1
        except Exception as e:
            planner.mark(sid, "Failed", error=str(e)); log(f"FAILED {cid}: {e}")
    if done and live:
        df.to_excel(XLSX, index=False)
    log(f"Posts handled: {done} ({'published to Instagram' if live else 'prepared in output/ folder'})")
    return done


def load_brand():
    import json
    from engine import DEFAULT_BRAND
    b, f, lg = dict(DEFAULT_BRAND), os.path.join(BASE, "brand.json"), os.path.join(BASE, "brand_logo.png")
    if os.path.exists(f):
        b.update(json.load(open(f)))
    b["logo"] = open(lg, "rb").read() if os.path.exists(lg) else None
    return b


if __name__ == "__main__":
    while True:
        run_once()
        if "--loop" not in sys.argv:
            break
        time.sleep(600)
