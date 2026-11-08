import json
import sys
import time
import urllib.error
import urllib.request

LANGUAGES = ["es", "ar", "zh-CN"]
BASE = "https://truxz78-png.github.io/stay-atlas-app/"
PAGES = ["index.html", "privacy.html", "terms.html"]
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


def check_translator(lang):
    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=en&tl=" + lang + "&dt=t&q=Hello")
    try:
        data = json.loads(fetch(url))
        text = "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
        if text:
            print("OK (" + lang + "): " + text)
            return "ok"
        print("FAIL (" + lang + "): respuesta vacia")
        return "fail"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("OCUPADO (" + lang + "): Google frena al servidor de GitHub (429). No es un error de la pagina.")
            return "busy"
        print("FAIL (" + lang + "): HTTP " + str(e.code))
        return "fail"
    except Exception as e:
        print("FAIL (" + lang + "): " + str(e))
        return "fail"


def main():
    problems = 0
    for page in PAGES:
        try:
            html = fetch(BASE + page)
            if "translate_a/single" in html and 'content="notranslate"' in html:
                print("OK: " + page + " tiene el traductor")
            else:
                print("FAIL: a " + page + " le falta el traductor o la etiqueta notranslate")
                problems += 1
        except Exception as e:
            print("FAIL (no se pudo abrir " + page + "): " + str(e))
            problems += 1

    results = []
    for lang in LANGUAGES:
        results.append(check_translator(lang))
        if results[-1] == "ok":
            break
        time.sleep(5)
    if "ok" in results:
        print("OK: el traductor responde")
    elif "fail" in results:
        print("FAIL: el traductor dio un error real")
        problems += 1
    else:
        print("AVISO: Google estaba ocupado con GitHub y no se pudo probar hoy. Se vuelve a probar manana.")

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
