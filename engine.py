"""HealthPost Creator - image and caption engine (Pillow only, fully offline)."""
import io, re, json, zipfile, urllib.request
from PIL import Image, ImageDraw, ImageFont

SIZES = {"Portrait 1080x1350": (1080, 1350), "Square 1080x1080": (1080, 1080)}
TEMPLATES = ["Health Tip", "Motivational Quote", "Did You Know?", "Nutrition Facts",
             "Myth vs Fact", "Healthy Habits Checklist", "Step-by-Step Tips", "Wellness Reminder"]
FONTS = {"Modern (Segoe UI / Arial)": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"],
         "Elegant (Georgia)": ["georgia.ttf", "DejaVuSerif.ttf"],
         "Clean (Verdana)": ["verdana.ttf", "DejaVuSans.ttf"]}
BOLD = {"segoeui.ttf": "segoeuib.ttf", "arial.ttf": "arialbd.ttf", "georgia.ttf": "georgiab.ttf",
        "verdana.ttf": "verdanab.ttf", "DejaVuSans.ttf": "DejaVuSans-Bold.ttf",
        "DejaVuSerif.ttf": "DejaVuSerif-Bold.ttf"}
DISCLAIMER = "General information only - not medical advice."
DEFAULT_BRAND = {"page_name": "@yourpagename", "primary": "#2E7D5B", "secondary": "#F4B860",
                 "background": "#F6F3EA", "cta": "Follow | Subscribe | Link in bio",
                 "follow": "Follow {name} for daily updates", "subscribe": "Subscribe so you never miss a post",
                 "linkbio": "Link in bio", "hashtags": "", "disclaimer": DISCLAIMER,
                 "font": "Modern (Segoe UI / Arial)", "logo": None}


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def on(c):
    return (25, 35, 35) if lum(c) > 0.62 else (255, 255, 255)


def font(pref, size, bold=False):
    for n in FONTS.get(pref, FONTS["Modern (Segoe UI / Arial)"]):
        for name in ((BOLD.get(n, n),) if bold else (n,)):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
    return ImageFont.load_default(size)


def wrap(d, text, f, w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def fit(d, text, pref, w, h, maxs, mins=24, bold=False):
    """Largest font size where text fits the box; ellipsis only as last resort."""
    for s in range(maxs, mins - 1, -2):
        f = font(pref, s, bold)
        L = wrap(d, text, f, w)
        if len(L) * s * 1.28 <= h and all(d.textlength(l, font=f) <= w for l in L):
            return f, L, s
    f = font(pref, mins, bold)
    L = wrap(d, text, f, w)
    n = max(1, int(h / (mins * 1.28)))
    if len(L) > n:
        L = L[:n]
        L[-1] = L[-1].rstrip(" .,;") + "..."
    return f, L, mins


def split_items(text):
    return [p.strip()[0].upper() + p.strip()[1:] for p in re.split(r";\s*|(?<=[.!?])\s+", text or "") if p.strip()]


def render(rec, tpl, brand, size="Portrait 1080x1350"):
    b = {**DEFAULT_BRAND, **{k: v for k, v in brand.items() if v}}
    W, H = SIZES[size]
    P, S, BG = hexrgb(b["primary"]), hexrgb(b["secondary"]), hexrgb(b["background"])
    INK = (30, 42, 42) if lum(BG) > 0.5 else (240, 240, 240)
    F = b["font"]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((W - 380, -220, W + 140, 300), fill=S + (80,))
    d.ellipse((-220, H - 460, 260, H + 20), fill=P + (45,))
    d.ellipse((W - 230, H - 620, W + 120, H - 270), fill=S + (45,))
    m = 70

    def block(box, text, maxs, color, bold=False, align="left", va="top", mins=24):
        x, y, w, h = box
        f, L, s = fit(d, text, F, w, h, maxs, mins, bold)
        lh, tot = s * 1.28, len(L) * s * 1.28
        y0 = y if va == "top" else y + (h - tot) / 2
        for i, l in enumerate(L):
            lw = d.textlength(l, font=f)
            d.text((x + ((w - lw) / 2 if align == "center" else 0), y0 + i * lh), l, font=f, fill=color)

    def card(box, fill=(255, 255, 255, 235), r=36):
        x, y, w, h = box
        d.rounded_rectangle((x + 6, y + 10, x + w + 6, y + h + 10), r, fill=(0, 0, 0, 28))
        d.rounded_rectangle((x, y, x + w, y + h), r, fill=fill)

    def tipbox(box, tip):
        if not tip:
            return
        x, y, w, h = box
        d.rounded_rectangle((x, y, x + w, y + h), 30, fill=P)
        block((x + 36, y + 14, w - 72, h - 28), "Tip: " + tip, 40, on(P), va="mid", mins=22)

    # header: category pill + optional logo
    cat = (rec.get("Category") or "Wellness").upper()
    pf = font(F, 26, True)
    tw = d.textlength(cat, font=pf)
    d.rounded_rectangle((m, 70, m + tw + 50, 126), 28, fill=P)
    d.text((m + 25, 98), cat, font=pf, fill=on(P), anchor="lm")
    if b.get("logo"):
        try:
            lg = Image.open(io.BytesIO(b["logo"]) if isinstance(b["logo"], bytes) else b["logo"]).convert("RGBA")
            lg.thumbnail((120, 120))
            img.paste(lg, (W - m - lg.width, 60), lg)
        except Exception:
            pass
    # footer: name, CTA, disclaimer
    d.line((m, H - 170, W - m, H - 170), fill=P + (130,), width=3)
    d.text((m, H - 130), b["page_name"], font=font(F, 38, True), fill=P, anchor="lm")
    block((m, H - 108, W - 2 * m, 40), b["cta"], 30, INK, va="mid", mins=20)
    disc = brand.get("disclaimer", DISCLAIMER)
    if disc:
        d.text((W / 2, H - 38), disc, font=font(F, 22), fill=INK[:3] + (150,), anchor="mm")

    x, y, w, h = m, 165, W - 2 * m, H - 165 - 190
    head, main, tip = rec.get("Headline", ""), rec.get("Main content", ""), rec.get("Supporting tip", "")
    tp = 0.15 if tip else 0  # share of area reserved for tip
    th = int(h * 0.16) if tip else 0
    body_h = h - th - (24 if tip else 0)
    tipbox_at = (x, y + h - th, w, th)

    if tpl == "Motivational Quote":
        d.text((x, y - 30), "\u201C", font=font(F, 300, True), fill=S + (230,))
        block((x, y + 150, w, body_h - 250), main or head, 78, INK, bold=True, align="center", va="mid", mins=36)
        d.line((W / 2 - 70, y + body_h - 70, W / 2 + 70, y + body_h - 70), fill=P, width=6)
        block((x, y + body_h - 55, w, 55), head, 36, P, True, "center", "mid", 22)
    elif tpl == "Did You Know?":
        d.rounded_rectangle((x, y, x + w, y + 120), 36, fill=P)
        d.text((W / 2, y + 60), "DID YOU KNOW?", font=font(F, 62, True), fill=on(P), anchor="mm")
        hh = int(body_h * 0.2)
        block((x, y + 150, w, hh), head, 60, P, True, "center", "mid", 30)
        card((x, y + 160 + hh, w, body_h - hh - 160))
        block((x + 44, y + 180 + hh, w - 88, body_h - hh - 200), main, 56, INK, align="center", va="mid", mins=28)
    elif tpl in ("Nutrition Facts", "Healthy Habits Checklist", "Step-by-Step Tips"):
        items = split_items(main)
        if tpl != "Nutrition Facts" and tip and len(items) < 3:
            items += split_items(tip)
        items = (items or [main])[:6]
        hh = int(body_h * 0.2)
        block((x, y, w, hh), head, 70, P, True, va="mid", mins=34)
        bx = (x, y + hh + 10, w, body_h - hh - 10)
        card(bx)
        rh = min(bx[3] / len(items), 170)
        y0 = bx[1] + (bx[3] - rh * len(items)) / 2
        for i, t in enumerate(items):
            cy = y0 + i * rh + rh / 2
            mx = x + 62
            if tpl == "Nutrition Facts":
                d.ellipse((mx - 14, cy - 14, mx + 14, cy + 14), fill=S if i % 2 else P)
            elif tpl == "Step-by-Step Tips":
                d.ellipse((mx - 30, cy - 30, mx + 30, cy + 30), fill=P)
                d.text((mx, cy), str(i + 1), font=font(F, 34, True), fill=on(P), anchor="mm")
            else:
                d.rounded_rectangle((mx - 26, cy - 26, mx + 26, cy + 26), 10, outline=P, width=5)
                d.line((mx - 13, cy, mx - 3, cy + 12, mx + 15, cy - 12), fill=P, width=7, joint="curve")
            block((x + 120, y0 + i * rh + 6, w - 150, rh - 12), t, 44, INK, va="mid", mins=22)
        tipbox(tipbox_at, tip if tpl == "Nutrition Facts" or len(split_items(main)) >= 3 else "")
    elif tpl == "Myth vs Fact":
        mm = re.search(r"myth:\s*(.*?)\s*fact:\s*(.*)", main, re.I | re.S)
        myth, fact = (mm.group(1), mm.group(2)) if mm else ("", main)
        ph = (body_h - 20) // 2 if myth else body_h
        ypos = y
        for label, text, fill, txt in ([("MYTH", myth, (196, 84, 84), (255, 255, 255))] if myth else []) + \
                [("FACT", fact, P, on(P))]:
            d.rounded_rectangle((x, ypos, x + w, ypos + ph), 36, fill=fill)
            d.text((x + 44, ypos + 50), label, font=font(F, 44, True), fill=txt, anchor="lm")
            block((x + 44, ypos + 90, w - 88, ph - 120), text, 50, txt, va="mid", mins=24)
            ypos += ph + 20
        tipbox(tipbox_at, tip)
    elif tpl == "Wellness Reminder":
        d.text((W / 2, y + 30), "WELLNESS REMINDER", font=font(F, 34, True), fill=P, anchor="mm")
        hh = int(body_h * 0.36)
        block((x, y + 80, w, hh), head, 88, INK, True, "center", "mid", 40)
        d.line((W / 2 - 80, y + 100 + hh, W / 2 + 80, y + 100 + hh), fill=S, width=8)
        block((x + 30, y + 130 + hh, w - 60, body_h - hh - 130), main, 52, INK, align="center", va="mid", mins=26)
        tipbox(tipbox_at, tip)
    else:  # Health Tip
        hh = int(body_h * 0.27)
        block((x, y, w, hh), head, 88, P, True, va="mid", mins=40)
        card((x, y + hh + 10, w, body_h - hh - 10))
        block((x + 44, y + hh + 40, w - 88, body_h - hh - 70), main, 54, INK, va="mid", mins=26)
        tipbox(tipbox_at, tip)
    return img


def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------- captions ----------------
HOOKS = {"Nutrition": "\U0001F957 Good nutrition starts with simple everyday choices!",
         "Fitness": "\U0001F3C3 Every bit of movement counts!",
         "Weight Management": "\U0001F33F Small habits, meaningful progress!",
         "Mental Wellness": "\U0001F9D8 Your mind deserves care too.",
         "Sleep": "\U0001F319 Better days often start with better nights.",
         "Hydration": "\U0001F4A7 Hydration made simple!",
         "Women's Wellness": "\U0001F338 Looking after yourself is never selfish.",
         "Healthy Habits": "\u2728 Little habits, big difference over time!",
         "Health Facts": "\U0001F4A1 Did you know?",
         "Motivational Quotes": "\U0001F4AA A little motivation for today!"}
QUESTIONS = {"Nutrition": "What is one healthy food you enjoy eating?",
             "Fitness": "How do you like to move your body?",
             "Sleep": "What helps you wind down at night?",
             "Hydration": "How many glasses of water have you had today?",
             "Mental Wellness": "What helps you feel calm and balanced?"}
DEF_TAGS = {"Nutrition": "#Nutrition #HealthyEating #BalancedDiet", "Fitness": "#Fitness #StayActive #Movement",
            "Weight Management": "#HealthyWeight #HealthyHabits #Lifestyle", "Sleep": "#Sleep #SleepHygiene #RestWell",
            "Hydration": "#Hydration #DrinkWater #HealthyHabits", "Mental Wellness": "#MentalWellness #Mindfulness #SelfCare",
            "Women's Wellness": "#WomensHealth #Wellness #SelfCare", "Healthy Habits": "#HealthyHabits #DailyHabits #Wellbeing",
            "Health Facts": "#HealthFacts #HealthEducation #DidYouKnow", "Motivational Quotes": "#Motivation #WellnessJourney #Mindset"}


def make_caption(rec, brand):
    b = {**DEFAULT_BRAND, **{k: v for k, v in brand.items() if v}}
    cat = rec.get("Category", "")
    hook = rec.get("Hook") or HOOKS.get(cat, "\u2728 Today's update for you!")
    parts = [hook, "", rec.get("Description") or rec.get("Caption") or rec.get("Main content", "")]
    if rec.get("Supporting tip"):
        parts += ["", "\U0001F4A1 " + rec["Supporting tip"]]
    old, rc = "Follow for more health tips | Link in bio", (rec.get("CTA") or "").strip()
    cta = [rc] if rc and rc != old else [f"\U0001F449 {b['follow'].format(name=b['page_name'])}",
                                          f"\U0001F514 {b['subscribe']}", f"\U0001F517 {b['linkbio']}"]
    parts += ["", QUESTIONS.get(cat, "What do you think? Tell us in the comments \U0001F447"), "",
              "\u2764\ufe0f Save this post and share it with someone who needs it.", ""] + cta
    disc = brand.get("disclaimer", DISCLAIMER)
    if disc:
        parts += ["", disc]
    src = rec.get("Source URL", "")
    if src and not src.startswith("Original"):
        parts += ["", "Source: " + src]
    parts += ["", rec.get("Hashtags") or DEF_TAGS.get(cat) or b["hashtags"] or "#Wellness"]
    return "\n".join(parts)


def ollama_improve(caption, model="llama3.2", host="http://localhost:11434"):
    """Optional local AI polish. Returns None if Ollama is unavailable."""
    prompt = ("Improve the tone of this Instagram caption. Keep every fact, the source line, the disclaimer, "
              "hashtags and CTA unchanged. Do not add medical claims. Return only the caption.\n\n" + caption)
    try:
        req = urllib.request.Request(host + "/api/generate", method="POST",
                                     data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())["response"].strip() or None
    except Exception:
        return None


def pick_template(rec, override=None):
    if override:
        return override
    s = (rec.get("Image style") or "").lower()
    return next((t for t in TEMPLATES if t.lower() == s or t.lower().startswith(s[:6]) and s), "Health Tip")


def build_zip(records, brand, size, override=None, progress=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, rec in enumerate(records):
            name = f"{str(rec.get('ID', i + 1)).replace('/', '-')}"
            z.writestr(name + ".png", png_bytes(render(rec, pick_template(rec, override), brand, size)))
            z.writestr(name + ".txt", make_caption(rec, brand))
            if progress:
                progress((i + 1) / len(records))
    return buf.getvalue()
