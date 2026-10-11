#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wattsplaying-stuur: "Stuur naar auto"-doorgeefluik.

De auto vraagt een korte koppelcode aan en vraagt die elke paar seconden
op; een telefoon die de code kent kan er een link in leggen. Alles staat
alleen in het geheugen en verloopt vanzelf - na een herstart is alles weg,
en dat is de bedoeling. Er wordt nooit iets opgehaald: de server bewaart
alleen de tekst van de link, de auto opent hem zelf.

Luistert alleen op 127.0.0.1; nginx zet /api/stuur/ hiernaartoe door.
"""
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PORT = 8099
ALFABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # geen 0/O, 1/I/L
CODE_LEN = 6
TTL = 10 * 60          # sessie vervalt 10 min na de laatste poll van de auto
MAX_SESSIES = 300
MAX_WACHTRIJ = 5
MAX_URL = 2000
MAX_TITEL = 200
MAX_BODY = 4096

_lock = threading.Lock()
_sessies = {}          # code -> {"gezien": t, "items": [...]}
_CODE_RE = re.compile(r"^[%s]{%d}$" % (ALFABET, CODE_LEN))


def _opruimen(nu):
    for c in [c for c, s in _sessies.items() if nu - s["gezien"] > TTL]:
        del _sessies[c]
    # ponytail: oudste eruit bij overloop; per-IP limiet als iemand dit ooit misbruikt
    while len(_sessies) >= MAX_SESSIES:
        del _sessies[min(_sessies, key=lambda c: _sessies[c]["gezien"])]


def nieuwe_sessie():
    nu = time.time()
    with _lock:
        _opruimen(nu)
        while True:
            code = "".join(secrets.choice(ALFABET) for _ in range(CODE_LEN))
            if code not in _sessies:
                break
        _sessies[code] = {"gezien": nu, "items": []}
    return code


def ophalen(code):
    """Auto pollt: geeft wachtende items terug en leegt de wachtrij."""
    nu = time.time()
    with _lock:
        _opruimen(nu)
        s = _sessies.get(code)
        if s is None:
            return None
        s["gezien"] = nu
        items, s["items"] = s["items"], []
    return items


def check_url(url):
    if not isinstance(url, str) or not url or len(url) > MAX_URL:
        raise ValueError("ongeldige link")
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("alleen http(s)-links")
    return url


def plaatsen(code, url, titel):
    url = check_url(url)
    titel = titel.strip()[:MAX_TITEL] if isinstance(titel, str) else ""
    with _lock:
        s = _sessies.get(code)
        if s is None or time.time() - s["gezien"] > TTL:
            return False
        s["items"] = (s["items"] + [{"url": url, "titel": titel, "t": int(time.time())}])[-MAX_WACHTRIJ:]
    return True


class Handler(BaseHTTPRequestHandler):
    server_version = "wattsplaying-stuur/1.0"

    def log_message(self, fmt, *args):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _code(self):
        parts = urlsplit(self.path).path.split("/")   # ['', 'api', 'stuur', X]
        if len(parts) != 4 or parts[1:3] != ["api", "stuur"]:
            return None
        return parts[3].upper()

    def do_GET(self):
        code = self._code()
        if not code or not _CODE_RE.match(code):
            return self._json(404, {"error": "onbekende code"})
        items = ophalen(code)
        if items is None:
            return self._json(404, {"error": "code verlopen"})
        return self._json(200, {"items": items})

    def do_POST(self):
        code = self._code()
        if code == "NIEUW":
            return self._json(200, {"code": nieuwe_sessie(), "ttl": TTL})
        if not code or not _CODE_RE.match(code):
            return self._json(404, {"error": "onbekende code"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._json(400, {"error": "ongeldige aanvraag"})
        try:
            data = json.loads(self.rfile.read(n))
            ok = plaatsen(code, data.get("url"), data.get("titel", ""))
        except (ValueError, AttributeError) as e:
            return self._json(400, {"error": str(e) or "ongeldige aanvraag"})
        if not ok:
            return self._json(404, {"error": "code verlopen"})
        return self._json(200, {"ok": True})


def _zelftest():
    c = nieuwe_sessie()
    assert _CODE_RE.match(c)
    assert ophalen(c) == []
    assert plaatsen(c, "https://youtu.be/x", "Video")
    assert [i["url"] for i in ophalen(c)] == ["https://youtu.be/x"]
    assert ophalen(c) == []                       # wachtrij is geleegd
    for bad in ("javascript:alert(1)", "file:///etc/passwd", "", "x" * 3000, None):
        try:
            plaatsen(c, bad, "")
            raise AssertionError("geaccepteerd: %r" % (bad,))
        except ValueError:
            pass
    assert not plaatsen("ZZZZZZ", "https://a.nl", "")
    _sessies[c]["gezien"] -= TTL + 1
    assert ophalen(c) is None                     # verlopen
    print("zelftest ok")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        _zelftest()
    else:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
