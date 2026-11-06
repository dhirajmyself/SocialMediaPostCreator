import os, io, json, sqlite3, datetime
import pandas as pd
import streamlit as st
import runner, niche, planner, publisher
from runner import clean, COLS
from engine import (SIZES, TEMPLATES, FONTS, DEFAULT_BRAND, render, png_bytes, make_caption,
                    ollama_improve, pick_template, build_zip)

BASE = os.path.dirname(os.path.abspath(__file__))
XLSX, BRAND_F, LOGO_F, DB = (os.path.join(BASE, n) for n in
                             ("Health_Content.xlsx", "brand.json", "brand_logo.png", "history.db"))

st.set_page_config("HealthPost Creator", "\U0001F33F", layout="wide")
st.markdown("<style>.stApp{background:#F7F5EE}h1,h2,h3{color:#2E7D5B}</style>", unsafe_allow_html=True)


# ---------- helpers ----------
def load_brand():
    b = dict(DEFAULT_BRAND)
    if os.path.exists(BRAND_F):
        b.update(json.load(open(BRAND_F)))
    b["logo"] = open(LOGO_F, "rb").read() if os.path.exists(LOGO_F) else None
    return b


def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, ts TEXT, content_id TEXT, "
              "headline TEXT, template TEXT, size TEXT)")
    return c


def log(rows):
    c = db()
    c.executemany("INSERT INTO history(ts,content_id,headline,template,size) VALUES(?,?,?,?,?)",
                  [(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), *r) for r in rows])
    c.commit(); c.close()


if "df" not in st.session_state:
    st.session_state.df = clean(pd.read_excel(XLSX)) if os.path.exists(XLSX) else pd.DataFrame(columns=COLS)
if "brand" not in st.session_state:
    st.session_state.brand = load_brand()
df, brand = st.session_state.df, st.session_state.brand
recs = lambda d: d.to_dict("records")

st.sidebar.title("\U0001F33F HealthPost Creator")
page = st.sidebar.radio("Menu", ["Dashboard", "Niche & News", "Excel Library", "30-Day Calendar", "Instagram",
                                 "Create Post", "Bulk Generator", "Branding", "History"])
st.sidebar.caption("Free & offline. General information only - verify facts against sources before posting.")

# ---------- pages ----------
if page == "Dashboard":
    st.title("Dashboard")
    c = db(); n = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]; c.close()
    a, b, d_ = st.columns(3)
    a.metric("Content records", len(df)); b.metric("Ready to post", int((df["Status"] == "Ready").sum()))
    d_.metric("Posts generated", n)
    if len(df):
        st.subheader("Records by category")
        st.bar_chart(df["Category"].value_counts())
    st.info("Start with **Excel Library** to check your content, then **Create Post**.")

elif page == "Niche & News":
    st.title("Niche & Daily News")
    s = niche.load_settings()
    p = st.selectbox("Start from a preset", list(niche.PRESETS), index=list(niche.PRESETS).index(s["preset"]) if s["preset"] in niche.PRESETS else 0)
    if p != s["preset"]:
        s.update(niche.PRESETS[p]); s["preset"] = p; s["niche"] = p if p != "Custom" else s["niche"]
    s["niche"] = st.text_input("Niche name (shown on posts)", s["niche"])
    s["keywords"] = [x.strip() for x in st.text_area("Keywords - one per line (auto-searched on Google News; works for ANY niche)", "\n".join(s["keywords"])).splitlines() if x.strip()]
    s["feeds"] = [x.strip() for x in st.text_area("Extra RSS feed URLs - one per line (magazines, blogs, news)", "\n".join(s["feeds"])).splitlines() if x.strip()]
    s["hashtags"] = st.text_input("Hashtags for news posts", s["hashtags"])
    s["times"] = [x.strip() for x in st.text_input("Posting times (HH:MM, comma separated)", ", ".join(s["times"])).split(",") if x.strip()]
    c1, c2 = st.columns(2)
    s["max_age_days"] = c1.number_input("Ignore news older than (days)", 1, 14, int(s["max_age_days"]))
    s["max_new_per_run"] = c2.number_input("Max new items per refresh", 1, 50, int(s["max_new_per_run"]))
    s["require_approval"] = st.checkbox("Require my approval (Status = Ready) before a post is scheduled - recommended", s["require_approval"])
    if st.button("Save niche settings"):
        niche.save_settings(s); st.success("Saved.")
    if st.button("Refresh news now"):
        niche.save_settings(s)
        with st.spinner("Collecting news..."):
            nd, added, errs = runner.refresh_news(s, st.session_state.df)
        if added:
            nd.to_excel(runner.XLSX, index=False); st.session_state.df = nd
        st.success(f"{added} new items added to the library as {'Draft' if s['require_approval'] else 'Ready'}.")
        if errs:
            st.warning("Some feeds failed (check internet / URL): " + "; ".join(errs[:5]))
    st.caption("News posts use the headline and a short summary with the source credited; always verify facts at the source link.")

elif page == "30-Day Calendar":
    st.title("30-Day Calendar")
    s = niche.load_settings()
    st.write(f"{len(s['times'])} posts/day at {', '.join(s['times'])}")
    n_draft = int(((df["Status"] == "Draft") & (df["Review note"].str.startswith("Auto-collected"))).sum())
    if n_draft and st.button(f"Approve {n_draft} auto-collected drafts (I checked the sources)"):
        m = (df["Status"] == "Draft") & df["Review note"].str.startswith("Auto-collected")
        st.session_state.df.loc[m, "Status"] = "Ready"; st.session_state.df.to_excel(runner.XLSX, index=False); st.rerun()
    if st.button("Build / extend 30-day calendar"):
        k = planner.fill_calendar(recs(df), s["times"], 30, allowed=runner.allowed(s), pick=pick_template)
        st.success(f"{k} slots filled.")
    c = planner.con(); cal = pd.read_sql("SELECT date,time,content_id,headline,template,status,error FROM calendar ORDER BY date,time", c); c.close()
    if cal.empty:
        st.info("No calendar yet. Approve some content (Status = Ready) then build it.")
    else:
        st.dataframe(cal, width="stretch", height=450)
        st.caption("Needs content = no approved item available yet; the daily refresh fills these.")
        sched = df[df["ID"].isin(cal.loc[cal.status == "Scheduled", "content_id"])]
        if len(sched) and st.button("Build ZIP of all scheduled posts"):
            st.session_state.calzip = build_zip(recs(sched), brand, "Portrait 1080x1350")
        if "calzip" in st.session_state:
            st.download_button("Download scheduled posts ZIP", st.session_state.calzip, "calendar_posts.zip")

elif page == "Instagram":
    st.title("Instagram Auto-Publishing")
    s = niche.load_settings()
    st.warning("Posts go live through the official Instagram API. With approval OFF, unreviewed news can be published - for health content keep approval ON.")
    s["ig_user_id"] = st.text_input("Instagram Business account ID", s["ig_user_id"])
    s["ig_token"] = st.text_input("Long-lived access token", s["ig_token"], type="password")
    s["cloud_name"] = st.text_input("Cloudinary cloud name (free image host)", s["cloud_name"])
    s["cloud_key"] = st.text_input("Cloudinary API key", s["cloud_key"])
    s["cloud_secret"] = st.text_input("Cloudinary API secret", s["cloud_secret"], type="password")
    s["auto_publish"] = st.checkbox("Auto-publish due posts (otherwise they are only prepared in the output/ folder)", s["auto_publish"])
    c1, c2, c3 = st.columns(3)
    if c1.button("Save"):
        niche.save_settings(s); st.success("Saved locally in settings.json")
    if c2.button("Test Instagram connection"):
        try:
            st.success("Connected as @" + publisher.ig_test(s))
        except Exception as e:
            st.error(str(e)[:300])
    if c3.button("Run autopilot once now"):
        niche.save_settings(s); out = []
        runner.run_once(brand, out.append); st.code("\n".join(out))
    with st.expander("One-time setup (about 20 minutes)"):
        st.markdown("""1. Instagram must be a **Business or Creator** account linked to a **Facebook Page**.
2. At developers.facebook.com create an app, add **Instagram Graph API**, and generate a token with `instagram_basic` and `instagram_content_publish` (convert it to a long-lived token; it lasts ~60 days, so renew it).
3. Copy your Instagram Business account ID.
4. Create a free Cloudinary account and copy cloud name, API key and secret.
5. For hands-free posting run **autopilot.bat** and leave the PC on (or schedule it in Windows Task Scheduler).""")

elif page == "Excel Library":
    st.title("Excel Content Library")
    up = st.file_uploader("Upload an updated Health_Content.xlsx", type=["xlsx"])
    if up is not None and st.button("Load this file"):
        try:
            st.session_state.df = clean(pd.read_excel(up))
            st.success(f"Loaded {len(st.session_state.df)} records."); st.rerun()
        except Exception as e:
            st.error(f"Could not read that file: {e}")
    edited = st.data_editor(df, num_rows="dynamic", width="stretch", height=450)
    c1, c2 = st.columns(2)
    if c1.button("Save changes to Health_Content.xlsx"):
        try:
            st.session_state.df = clean(edited); st.session_state.df.to_excel(XLSX, index=False)
            st.success("Saved.")
        except Exception as e:
            st.error(str(e))
    buf = io.BytesIO(); edited.to_excel(buf, index=False)
    c2.download_button("Download current Excel", buf.getvalue(), "Health_Content.xlsx")

elif page == "Create Post":
    st.title("Create a Post")
    if df.empty:
        st.warning("No content loaded. Use Excel Library."); st.stop()
    c1, c2, c3 = st.columns(3)
    cat = c1.selectbox("Category", sorted(df["Category"].unique()))
    sub = df[df["Category"] == cat]
    pick = c2.selectbox("Content", sub.index, format_func=lambda i: f"{sub.loc[i, 'ID']} - {sub.loc[i, 'Headline']}")
    rec = sub.loc[pick].to_dict()
    tpl = c3.selectbox("Template", TEMPLATES, index=TEMPLATES.index(pick_template(rec)))
    size = st.radio("Size", list(SIZES), horizontal=True)
    if rec.get("Review note"):
        st.caption("\u26A0\uFE0F " + rec["Review note"])
    img = render(rec, tpl, brand, size)
    left, right = st.columns([1, 1])
    left.image(img, width="stretch")
    cap = make_caption(rec, brand)
    if right.checkbox("Polish caption with local Ollama (optional)"):
        with st.spinner("Asking Ollama..."):
            better = ollama_improve(cap)
        if better:
            cap = better
        else:
            right.warning("Ollama not reachable - using the standard caption.")
    cap = right.text_area("Caption (editable)", cap, height=420, key=f"cap_{rec['ID']}_{hash(cap)}")
    pngb = png_bytes(img)
    if right.download_button("Download PNG", pngb, f"{rec['ID']}.png", "image/png"):
        log([(rec["ID"], rec["Headline"], tpl, size)])
    right.download_button("Download caption (TXT)", cap, f"{rec['ID']}.txt")

elif page == "Bulk Generator":
    st.title("Bulk Generator")
    cats = st.multiselect("Categories", sorted(df["Category"].unique()), default=list(df["Category"].unique()))
    stat = st.multiselect("Status", ["Draft", "Ready", "Published"], default=["Draft", "Ready"])
    sel = df[df["Category"].isin(cats) & df["Status"].isin(stat)]
    st.write(f"{len(sel)} records selected")
    mode = st.selectbox("Template", ["Use each record's Image style"] + TEMPLATES)
    size = st.radio("Size", list(SIZES), horizontal=True)
    limit = st.number_input("Max posts", 1, 500, min(20, max(len(sel), 1)))
    if st.button("Generate ZIP", disabled=sel.empty):
        bar = st.progress(0.0)
        z = build_zip(recs(sel.head(int(limit))), brand, size, None if mode.startswith("Use") else mode, bar.progress)
        st.session_state.zip = z
        log([(r["ID"], r["Headline"], mode, size) for r in recs(sel.head(int(limit)))])
    if "zip" in st.session_state:
        st.success("Ready.")
        st.download_button("Download ZIP (images + captions)", st.session_state.zip, "healthposts.zip", "application/zip")

elif page == "Branding":
    st.title("Branding")
    b = dict(brand)
    b["page_name"] = st.text_input("Instagram page name", b["page_name"])
    c1, c2, c3 = st.columns(3)
    b["primary"] = c1.color_picker("Primary colour", b["primary"])
    b["secondary"] = c2.color_picker("Secondary colour", b["secondary"])
    b["background"] = c3.color_picker("Background colour", b["background"])
    b["cta"] = st.text_input("Image footer CTA", b["cta"])
    b["follow"] = st.text_input("Caption: Follow line ({name} = page name)", b["follow"])
    b["subscribe"] = st.text_input("Caption: Subscribe line", b["subscribe"])
    b["linkbio"] = st.text_input("Caption: Link in bio line", b["linkbio"])
    b["disclaimer"] = st.text_input("Disclaimer on images/captions (blank = none)", b["disclaimer"])
    b["font"] = st.selectbox("Font", list(FONTS), index=list(FONTS).index(b["font"]) if b["font"] in FONTS else 0)
    logo = st.file_uploader("Logo (optional, PNG with transparency works best)", type=["png", "jpg", "jpeg"])
    if st.button("Save branding"):
        if logo is not None:
            open(LOGO_F, "wb").write(logo.getvalue())
        json.dump({k: v for k, v in b.items() if k != "logo"}, open(BRAND_F, "w"))
        st.session_state.brand = load_brand(); st.success("Saved."); st.rerun()
    st.image(png_bytes(render({"Category": "Preview", "Headline": "Brand Preview", "Main content":
                               "This is how your colours, name and call to action look on a post.",
                               "Supporting tip": "Save to apply."}, "Health Tip", b)), width=360)

else:
    st.title("Generated Post History")
    c = db(); h = pd.read_sql("SELECT ts, content_id, headline, template, size FROM history ORDER BY id DESC", c); c.close()
    st.dataframe(h, width="stretch")
