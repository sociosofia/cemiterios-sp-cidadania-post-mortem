#!/usr/bin/env python3
"""Executa a integração Seade com sessão HTTP compatível com o portal CKAN.

O repositório do Seade responde 403 a alguns agentes HTTP automatizados. Esta
camada preserva cookies, envia cabeçalhos usuais de navegador e produz erro com
URL e trecho da resposta, sem alterar a lógica estatística da rotina principal.
"""
from __future__ import annotations

import http.cookiejar
import urllib.error
import urllib.request

import fetch_seade_mortalidade as seade

HOME = "https://repositorio.seade.gov.br/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/json,text/plain,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": HOME,
    "Cache-Control": "no-cache",
}
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
SESSION_READY = False


def request_bytes(url: str, timeout: int = 240) -> tuple[bytes, dict[str, str], str]:
    global SESSION_READY
    if not SESSION_READY:
        try:
            OPENER.open(urllib.request.Request(HOME, headers=HEADERS), timeout=60).read(1)
        except Exception:
            # O aquecimento é auxiliar; a chamada do recurso produzirá o erro útil.
            pass
        SESSION_READY = True

    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with OPENER.open(request, timeout=timeout) as response:
            return response.read(), dict(response.headers.items()), response.geturl()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(800).decode("utf-8", errors="replace").replace("\n", " ")
        except Exception:
            body = ""
        raise RuntimeError(
            f"Falha HTTP {exc.code} ao acessar {url}; resposta={body!r}"
        ) from exc


seade.UA = HEADERS["User-Agent"]
seade.get = request_bytes

if __name__ == "__main__":
    raise SystemExit(seade.main())
