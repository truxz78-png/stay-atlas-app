import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://truxz78-png.github.io/stay-atlas-app/"
PAGES = {
    "index.html": ['href="privacy.html"', 'href="terms.html"', "mailto:soporte.stayatlas@gmail.com", "translate_a/single", 'content="notranslate"'],
    "app.html": ['href="privacy.html"', 'href="terms.html"'],
    "privacy.html": ['href="terms.html"', "The English version is the official one", "translate_a/single", 'content="notranslate"'],
    "terms.html": ['href="privacy.html"', "The English version is the official one", "translate_a/single", 'content="notranslate"'],
    "sitemap.xml": ["app.html", "privacy.html", "terms.html"],
}
LEGAL_PAGES = ["privacy.html", "terms.html"]
CORE = ["es", "pt", "fr", "zh-CN", "ar", "hi"]
OTHERS = ["de", "it", "ru", "ja", "ko", "tr", "nl", "pl", "uk", "ro", "el", "cs", "hu", "sv", "da", "fi", "no", "iw", "fa", "ur", "bn", "ta", "te", "mr", "gu", "id", "ms", "vi", "th", "tl", "sw", "am", "zu", "af", "ha", "yo", "ig", "sq", "sr", "hr", "bg", "sk"]
GROUP = datetime.date.today().isocalendar()[1] % 7
LANGS = CORE + OTHERS[GROUP * 6:(GROUP + 1) * 6]
if "--legal" not in sys.argv:
    LANGS = []
NEG = re.compile(r"\b(?:not|no|never|nothing|none|neither|nor|without|cannot)\b|n't", re.I)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StayAtlasPageBot/1.0)"}
REPORT = "page_report.md"
TIME_BUDGET = 600
CHUNK_LIMIT = 700
LAST_ERROR = ""


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def translate(text, source, target):
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl="
           + source + "&tl=" + target + "&dt=t&q=" + urllib.parse.quote(text))
    for attempt in range(2):
        try:
            _, body = fetch(url, timeout=15)
            data = json.loads(body)
            return "".join(part[0] for part in data[0] if part and part[0])
        except Exception as exc:
            global LAST_ERROR
            LAST_ERROR = str(exc)[:200]
            time.sleep(2 * (attempt + 1))
    return None


def legal_paragraphs(html):
    start = html.find("<h1")
    end = html.find("This page may be translated automatically")
    if start == -1:
        start = 0
    if end == -1:
        end = len(html)
    texts = []
    for match in re.finditer(r"<p[^>]*>(.*?)</p>", html[start:end], re.S):
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", text).replace("&amp;", "&").strip()
        if text:
            texts.append(text)
    return texts


def make_chunks(texts):
    chunks, current, size = [], [], 0
    for text in texts:
        if current and size + len(text) > CHUNK_LIMIT:
            chunks.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        chunks.append(current)
    return chunks


def main():
    problems = []
    lines = ["## Pages"]
    pages_html = {}
    for page, required in PAGES.items():
        try:
            status, html = fetch(BASE + page)
        except Exception as exc:
            problems.append(page + ": could not open (" + str(exc) + ")")
            lines.append("- " + page + ": ERROR")
            continue
        pages_html[page] = html
        missing = [item for item in required if item not in html]
        if status != 200:
            problems.append(page + ": HTTP " + str(status))
        for item in missing:
            problems.append(page + ": missing " + item)
        lines.append("- " + page + ": " + ("OK" if status == 200 and not missing else "PROBLEM"))

    lines += ["", "## Legal translation check"]
    page_chunks = {}
    for page in LEGAL_PAGES:
        html = pages_html.get(page)
        if html:
            page_chunks[page] = make_chunks([t for t in legal_paragraphs(html) if NEG.search(t)])
    checked = 0
    untested = 0
    failures_in_a_row = 0
    deadline = time.time() + TIME_BUDGET
    for lang in LANGS:
        for page, chunks in page_chunks.items():
            for chunk in chunks:
                if time.time() > deadline:
                    untested += len(chunk)
                    continue
                translated = translate("\n".join(chunk), "en", lang)
                time.sleep(0.5)
                back = translate(translated, lang, "en") if translated else None
                time.sleep(0.5)
                if back is None:
                    untested += len(chunk)
                    failures_in_a_row += 1
                    if failures_in_a_row >= 3:
                        deadline = 0
                    continue
                failures_in_a_row = 0
                back_lines = [line.strip() for line in back.split("\n") if line.strip()]
                if len(back_lines) == len(chunk):
                    pairs = list(zip(chunk, back_lines))
                else:
                    pairs = [(" ".join(chunk), back)]
                for text, back_text in pairs:
                    if len(NEG.findall(back_text)) < len(NEG.findall(text)):
                        problems.append(page + " [" + lang + "] a negation may be lost in translation."
                                        + "\n  - English: " + text + "\n  - Back-translated: " + back_text)
                checked += len(chunk)
    lines.append("- Languages this week: " + (", ".join(LANGS) if LANGS else "not run here (run it from Termux with --legal after changing legal text)"))
    lines.append("- Paragraph checks completed: " + str(checked))
    lines.append("- Could not test (translation service busy or time limit): " + str(untested))
    if LAST_ERROR:
        lines.append("- Last translation error: " + LAST_ERROR)
    if checked == 0 and untested > 0:
        problems.append("Legal translation check could not run: the translation service did not answer.")

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    body = ["# Stay Atlas weekly page check - " + today, ""]
    if problems:
        body.append("**Result: " + str(len(problems)) + " problem(s) found. Please review.**")
    else:
        body.append("**Result: all checks passed.**")
    body += [""] + lines
    if problems:
        body += ["", "## Problems"] + ["- " + p for p in problems]
    body += ["", "This robot only checks and reports. It never changes the website."]
    report = "\n".join(body)
    if len(report) > 60000:
        report = report[:60000] + "\n\n(report cut: too long)"
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(report)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("# Stay Atlas weekly page check\n\n**The check itself crashed:** " + str(exc) + "\n")
        print("Crashed:", exc)
        sys.exit(1)
