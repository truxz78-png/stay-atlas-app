import json
import socket
import sys
import urllib.error
import urllib.request

LINKS_FILE = "links.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}
BROKEN_CODES = (404, 410)


def check_url(url):
    """Devuelve ('ok', motivo), ('dudoso', motivo) o ('roto', motivo).
    Solo 'roto' cuenta como fallo: 404, 410 o el sitio no existe."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return "ok", "status " + str(resp.status)
        except urllib.error.HTTPError as e:
            if e.code in BROKEN_CODES:
                return "roto", "status " + str(e.code)
            if e.code == 405 and method == "HEAD":
                continue
            if e.code < 400:
                return "ok", "status " + str(e.code)
            if e.code in (403, 429, 999) or e.code >= 500:
                return "dudoso", "status " + str(e.code) + " (antibot, freno o servidor ocupado)"
            return "ok", "status " + str(e.code)
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.gaierror):
                return "roto", "el sitio no existe (" + str(e.reason) + ")"
            return "dudoso", "sin respuesta (" + str(e.reason) + ")"
        except Exception as e:
            return "dudoso", "sitio lento o sin respuesta (" + str(e) + ")"
    return "dudoso", "no respondio a HEAD ni a GET"


def main():
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    auto_switch = data.get("settings", {}).get("auto_switch", False)
    broken, doubtful, notes = [], [], []
    changed = False

    for key, link in data["links"].items():
        name = link["name"]
        if link.get("solo_pais"):
            notes.append(f"- {name}: solo funciona en {link['solo_pais']}; no se puede probar desde EE. UU. y nunca se cambia solo.")
            continue

        status, reason = check_url(link["principal"])

        if status == "ok":
            if link.get("consecutive_failures", 0) != 0:
                link["consecutive_failures"] = 0
                changed = True
            if link.get("active") != "principal":
                notes.append(f"- {name}: el enlace principal funciona; esta activo '{link.get('active')}'. Revisar a mano.")
            continue

        if status == "dudoso":
            doubtful.append(f"- {name}: DUDOSO, {reason}. No se cambia nada.")
            continue

        link["consecutive_failures"] = link.get("consecutive_failures", 0) + 1
        changed = True
        broken.append(f"- {name}: ROTO #{link['consecutive_failures']} ({reason}).")
        if link["consecutive_failures"] >= 2:
            if not link.get("respaldo"):
                broken.append(f"  -> {name} no tiene enlace de respaldo configurado.")
            elif auto_switch and link.get("active") == "principal":
                link["active"] = "respaldo"
                broken.append(f"  -> Cambiado al enlace de respaldo de {name}.")
            elif not auto_switch:
                broken.append(f"  -> (modo solo reportar) se cambiaria al respaldo de {name}.")

    if changed:
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if broken:
        print("ENLACES ROTOS DE VERDAD (404, 410 o sitio inexistente):")
        print("\n".join(broken))
    if doubtful:
        print("DUDOSOS (lentos, antibots o frenos; se vuelven a probar la proxima semana):")
        print("\n".join(doubtful))
    if notes:
        print("NOTAS:")
        print("\n".join(notes))
    if not broken:
        print("Ningun enlace roto de verdad.")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
