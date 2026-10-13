import json
import sys
import urllib.request
import urllib.error

LINKS_FILE = "links.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StayAtlasLinkBot/1.0)"}


def check_url(url):
    """Devuelve ('ok', None), ('bloqueado', motivo) o ('fallo', motivo)."""
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status < 400:
                return "ok", None
            return "fallo", "status " + str(resp.status)
    except urllib.error.HTTPError as e:
        if e.code == 403 or e.code == 999:
            return "bloqueado", "status " + str(e.code)
        if e.code < 500 and e.code != 404:
            return "ok", None
        return "fallo", "status " + str(e.code)
    except Exception as e:
        return "fallo", str(e)


def main():
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    auto_switch = data.get("settings", {}).get("auto_switch", False)
    report_lines = []
    changed = False

    for key, link in data["links"].items():
        status, reason = check_url(link["principal"])

        if status == "bloqueado":
            report_lines.append(f"- {link['name']}: el sitio bloquea revisiones automaticas ({reason}), se ignora.")
            continue

        if status == "ok":
            if link.get("consecutive_failures", 0) != 0:
                link["consecutive_failures"] = 0
                changed = True
            if link.get("active") == "respaldo":
                if auto_switch:
                    link["active"] = "principal"
                    changed = True
                    report_lines.append(f"- {link['name']}: el enlace principal se recupero, vuelve a quedar activo.")
                else:
                    report_lines.append(f"- {link['name']}: el enlace principal ya funciona de nuevo (modo solo reportar, no se cambio).")
            continue

        # status == "fallo"
        link["consecutive_failures"] = link.get("consecutive_failures", 0) + 1
        changed = True
        report_lines.append(f"- {link['name']}: fallo #{link['consecutive_failures']} ({reason}).")

        if link["consecutive_failures"] >= 2:
            if link.get("respaldo"):
                if auto_switch and link.get("active") != "respaldo":
                    link["active"] = "respaldo"
                    report_lines.append(f"  -> Cambiado al enlace de respaldo de {link['name']}.")
                elif not auto_switch:
                    report_lines.append(f"  -> (modo solo reportar) se cambiaria al respaldo de {link['name']}.")
            else:
                report_lines.append(f"  -> {link['name']} no tiene enlace de respaldo configurado.")

    if changed:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if report_lines:
        print("PROBLEMAS ENCONTRADOS:")
        print("\n".join(report_lines))
        sys.exit(1)
    else:
        print("Todos los enlaces de socios estan funcionando bien.")


if __name__ == "__main__":
    main()
