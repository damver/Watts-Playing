#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wattsplaying-news: stateless, veilige RSS-proxy.

Luistert alleen op 127.0.0.1; nginx zet /api/ hiernaartoe door. Bewaart
niets zelf — de lijst met bronnen (ingebouwd + zelf toegevoegd) en de
verborgen/zichtbaar-status leven in localStorage van de browser, net als
bij de tegels. Dit ding doet alleen de fetch die de browser zelf niet
mag doen (geen CORS-koptekst op de meeste nieuwsfeeds), met een SSRF-check
zodat het niet als open doorgeefluik naar het interne netwerk kan worden
misbruikt.
"""
import ipaddress
import socket
import ssl
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

PORT = 8098
TIMEOUT = 12
MAX_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 4
UA = "WattsPlaying/1.0"


def is_public_ip(ip_str):
    ip = ipaddress.ip_address(ip_str)
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def assert_safe_url(url):
    """Weigert alles behalve http(s) naar een publiek, niet-lokaal adres."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("alleen http/https")
    host = parts.hostname
    if not host:
        raise ValueError("geen host in url")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("host niet op te lossen: %s" % e)
    if not infos:
        raise ValueError("host niet op te lossen")
    for info in infos:
        ip = info[4][0]
        if not is_public_ip(ip):
            raise ValueError("wijst naar een lokaal/privé-adres, dat mag niet")


def fetch_feed(url, redirects_left=MAX_REDIRECTS):
    assert_safe_url(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read(MAX_BYTES + 1)
            ctype = resp.headers.get("Content-Type", "application/xml")
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and redirects_left > 0:
            loc = e.headers.get("Location")
            if loc:
                return fetch_feed(loc, redirects_left - 1)
        raise
    if len(body) > MAX_BYTES:
        raise ValueError("feed is te groot")
    return body, ctype


class Handler(BaseHTTPRequestHandler):
    server_version = "wattsplaying-news/2.0"

    def log_message(self, fmt, *args):
        pass  # rustig in de systemd-journal houden

    def _json(self, code, payload):
        import json
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path != "/api/rss":
            return self._json(404, {"error": "onbekend pad"})
        qs = parse_qs(parts.query)
        url = (qs.get("url") or [""])[0]
        if not url:
            return self._json(400, {"error": "url-parameter ontbreekt"})
        try:
            body, ctype = fetch_feed(url)
        except Exception as e:  # noqa: BLE001 - naar de gebruiker toe is elke fout gelijk
            return self._json(502, {"error": "ophalen mislukte: %s" % e})
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()
