"""Niche settings + daily news collection (RSS / Google News RSS, stdlib only, free)."""
import os, re, json, html, hashlib, datetime as dt, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_F = os.path.join(BASE, "settings.json")
UA = {"User-Agent": "Mozilla/5.0 (HealthPostCreator)"}

PRESETS = {
    "Health & Wellness": {"keywords": ["health tips", "nutrition", "sleep and wellbeing", "exercise and fitness"],
                          "feeds": ["http://feeds.bbci.co.uk/news/health/rss.xml",
                                    "https://www.sciencedaily.com/rss/health_medicine.xml",
                                    "https://www.who.int/rss-feeds/news-english.xml"],
                          "hashtags": "#HealthNews #Wellness #HealthyLifestyle #HealthTips"},
    "Fitness": {"keywords": ["fitness", "strength training", "running"], "feeds": [],
                "hashtags": "#Fitness #Workout #StayActive"},
    "Technology / AI": {"keywords": ["artificial intelligence", "consumer gadgets"],
                        "feeds": ["http://feeds.bbci.co.uk/news/technology/rss.xml", "https://techcrunch.com/feed/"],
                        "hashtags": "#Tech #AI #Innovation"},
    "Personal Finance": {"keywords": ["personal finance", "saving money"],
                         "feeds": ["http://feeds.bbci.co.uk/news/business/rss.xml"],
                         "hashtags": "#PersonalFinance #Money #Savings"},
    "Travel": {"keywords": ["travel tips", "best destinations"], "feeds": [], "hashtags": "#Travel #TravelTips #Wanderlust"},
    "Custom": {"keywords": [], "feeds": [], "hashtags": ""},
}
DEFAULTS = {"niche": "Health & Wellness", "preset": "Health & Wellness", **PRESETS["Health & Wellness"],
            "locale": "hl=en-IN&gl=IN&ceid=IN:en", "times": ["08:00", "13:00", "19:00"],
            "max_age_days": 3, "max_new_per_run": 15, "require_approval": True, "auto_publish": False,
            "ig_user_id": "", "ig_token": "", "cloud_name": "", "cloud_key": "", "cloud_secret": ""}
HOOKS = ["Here's what's making headlines in {niche} \U0001F447", "Quick {niche} update you shouldn't miss:",
         "Did you see this in {niche} news?", "Today's {niche} news in 30 seconds \u23F1\uFE0F",
         "Worth knowing today \U0001F4A1"]
STYLES = ["Did You Know?", "Health Tip", "Wellness Reminder"]


def load_settings():
    s = dict(DEFAULTS)
    if os.path.exists(SETTINGS_F):
        s.update(json.load(open(SETTINGS_F, encoding="utf-8")))
    return s


def save_settings(s):
    json.dump(s, open(SETTINGS_F, "w", encoding="utf-8"), indent=2)


def google_news_url(q, locale):
    return "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:2d") + "&" + locale


def _txt(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
    return ""


def strip_html(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def parse_feed(data):
    """Parse RSS 2.0 or Atom bytes into [{title, link, summary, publisher, date}]."""
    root, out = ET.fromstring(data), []
    A = "{http://www.w3.org/2005/Atom}"
    for it in list(root.iter("item")) + list(root.iter(A + "entry")):
        link = _txt(it, "link")
        if not link and it.find(A + "link") is not None:
            link = it.find(A + "link").get("href", "")
        raw = _txt(it, "pubDate", A + "published", A + "updated")
        try:
            date = parsedate_to_datetime(raw) if "," in raw else dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            date = None
        out.append({"title": strip_html(_txt(it, "title", A + "title")), "link": link,
                    "summary": strip_html(_txt(it, "description", A + "summary", A + "content")),
                    "publisher": strip_html(_txt(it, "source")), "date": date})
    return out


def fetch_all(s):
    feeds = list(s["feeds"]) + [google_news_url(k, s["locale"]) for k in s["keywords"]]
    items, errors = [], []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=s["max_age_days"])
    for u in feeds:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r:
                for it in parse_feed(r.read()):
                    d = it["date"]
                    if d is not None and d.tzinfo is None:
                        d = d.replace(tzinfo=dt.timezone.utc)
                    if it["title"] and it["link"] and (d is None or d >= cutoff):
                        items.append(it)
        except Exception as e:
            errors.append(f"{u[:60]}: {type(e).__name__}")
    return items, errors


def to_record(it, s):
    title, pub = it["title"], it["publisher"]
    if " - " in title:  # Google News appends the publisher
        title, p2 = title.rsplit(" - ", 1)
        pub = pub or p2
    pub = pub or urllib.parse.urlparse(it["link"]).netloc.replace("www.", "")
    summ = it["summary"]
    if summ.lower().startswith(title.lower()[:40]) or len(summ) < 40:
        summ = ""
    first = re.split(r"(?<=[.!?])\s", summ)[0][:200] if summ else ""
    n = int(hashlib.md5(it["link"].encode()).hexdigest(), 16)
    tag = s["hashtags"] or "#" + re.sub(r"\W+", "", s["niche"].title())
    return {"ID": "N" + hashlib.md5(it["link"].encode()).hexdigest()[:7], "Category": s["niche"],
            "Headline": title[:110], "Hook": HOOKS[n % len(HOOKS)].format(niche=s["niche"]),
            "Main content": first or title, "Description": f"{first or title}\n\nVia {pub}.",
            "Supporting tip": "", "Source URL": it["link"], "Hashtags": tag, "Caption": "", "CTA": "",
            "Image style": STYLES[n % len(STYLES)], "Status": "Draft" if s["require_approval"] else "Ready",
            "Review note": "Auto-collected news - check the facts at the source link before approving"}
