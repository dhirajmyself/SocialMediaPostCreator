# HealthPost Creator (free, offline)
Excel -> Instagram image (PNG) + caption (TXT). Python, Streamlit, Pandas, OpenPyXL, Pillow, SQLite. No paid API.

## Windows install
1. Install Python 3.10+ from python.org (tick "Add Python to PATH").
2. Unzip this folder, double-click **start.bat**. First run installs packages; the browser opens at http://localhost:8501.

## Use
Branding (set your page name first) -> Excel Library (check/upload content) -> Create Post (pick category, tip, template, download PNG + TXT) -> Bulk Generator (ZIP).

## Excel columns
ID, Category, Headline, Main content, Supporting tip, Source URL, Hashtags, Caption, CTA, Image style, Status (+ Review note).
Myth vs Fact rows: write `Myth: ... Fact: ...` in Main content. Re-run `python make_content.py` to rebuild the starter workbook.

## Optional local AI
Install Ollama, run `ollama pull llama3.2`, then tick "Polish caption with local Ollama" in Create Post. Falls back to templates if unavailable.

## Content safety
Starter facts are paraphrased from WHO/NHS pages (URL kept per row) and marked "Verify against source before publishing". Posts carry a general-information disclaimer. Do not add cure/guaranteed-result claims.

## Automation (v2)
- **Niche & News**: pick a preset or type any niche + keywords. Daily refresh pulls Google News RSS for those keywords plus any RSS feeds you add (needs internet).
- **30-Day Calendar**: 3 posts/day (times editable). Approve drafts (Status = Ready), build calendar, download all as ZIP.
- **Hook / Description / CTA** columns feed every caption: Hook, Description, question, Follow + Subscribe + Link in bio lines, source, hashtags.
- **Instagram**: official Graph API + free Cloudinary image host. Fill the Instagram page, tick auto-publish, run `autopilot.bat` (keeps PC on) or `python runner.py` from Task Scheduler.
- Without credentials, autopilot just prepares each due post (PNG + caption.txt) in `output/`.
- Requires a Business/Creator Instagram account linked to a Facebook Page. Tokens last ~60 days and need renewing. Keep approval ON for health content.
