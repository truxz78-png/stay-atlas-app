import sys
import json
import urllib.request

LANGUAGES = ["es", "pt", "fr", "ar", "hi", "zh-CN"]
SITE_URL = "https://truxz78-png.github.io/stay-atlas-app/"

def check_translate_api(lang):
    url = (
        "https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=en&tl=" + lang + "&dt=t&q=Hello"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = "".join(seg[0] for seg in data[0])
            if text.strip():
                print("OK (" + lang + "): " + text.strip())
                return True
            print("FAIL (" + lang + "): respuesta vacia")
            return False
    except Exception as e:
        print("FAIL (" + lang + "): " + str(e))
        return False

def check_script_present():
    try:
        with urllib.request.urlopen(SITE_URL, timeout=15) as resp:
            html = resp.read().decode("utf-8")
            if "translate_a/single" in html:
                print("OK: el script de traduccion sigue en la web")
                return True
            print("FAIL: el script de traduccion no esta en la web")
            return False
    except Exception as e:
        print("FAIL (no se pudo leer la web): " + str(e))
        return False

def main():
    ok = True
    for lang in LANGUAGES:
        if not check_translate_api(lang):
            ok = False
    if not check_script_present():
        ok = False
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
