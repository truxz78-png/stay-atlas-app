import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://truxz78-png.github.io/stay-atlas-app/"
PAGES = {
    "index.html": ['href="privacy.html"', 'href="terms.html"', "mailto:soporte.stayatlas@gmail.com"],
    "app.html": ['href="privacy.html"', 'href="terms.html"'],
    "privacy.html": ['href="terms.html"', "The English version is the official one"],
    "terms.html": ['href="privacy.html"', "The English version is the official one"],
    "sitemap.xml": ["app.html", "privacy.html", "terms.html"],
}
LEGAL_PAGES = ["privacy.html", "terms.html"]
CORE = ["es", "pt", "fr", "zh-CN", "ar", "hi"]
OTHERS = ["de", "it", "ru", "ja", "ko", "tr", "nl", "pl", "uk", "ro", "el", "cs", "hu", "sv", "da", "fi", "no", "iw", "fa", "ur", "bn", "ta", "te", "mr", "gu", "id", "ms", "vi", "th", "tl", "sw", "am", "zu", "af", "ha", "yo", "ig", "sq", "sr", "hr", "bg", "sk"]
GROUP = datetime.date.today().isocalendar()[1] % 7
LANGS = CORE + OTHERS[GROUP * 6:(GROUP + 1) * 6]
NEG = re.compile(r"\b(?:not|no|never|nothing|none|neither|nor|without|cannot)\b|n't", re.I)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StayAtlasPageBot/1.0)"}
REPORT = "page_report.md"


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def translate(text, source, target):
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl="
           + source + "&tl=" + target + "&dt=t&q=" + urllib.parse.quote(text))
    for attempt in range(3):
        try:
            _, body = fetch(url)
            data = json.loads(body)
            return "".join(part[0] for part in data[0] if part and part[0])
        except Exception:
            time.sleep(3 * (attempt + 1))
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
    checked = 0
    untested = 0
    for page in LEGAL_PAGES:
        html = pages_html.get(page)
        if not html:
            continue
        sentences = [t for t in legal_paragraphs(html) if NEG.search(t)]
        for lang in LANGS:
            for text in sentences:
                original = len(NEG.findall(text))
                translated = translate(text, "en", lang)
                time.sleep(0.3)
                back = translate(translated, lang, "en") if translated else None
                time.sleep(0.3)
                if back is None:
                    untested += 1
                    continue
                checked += 1
                if len(NEG.findall(back)) < original:
                    problems.append(page + " [" + lang + "] a negation may be lost in translation."
                                    + "\n  - English: " + text + "\n  - Back-translated: " + back)
    lines.append("- Paragraph checks completed: " + str(checked) + " (" + str(len(LANGS)) + " languages: " + ", ".join(LANGS) + ")")
    lines.append("- Could not test (translation service busy): " + str(untested))

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
