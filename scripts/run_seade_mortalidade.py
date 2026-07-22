#!/usr/bin/env python3
"""Executa a integração Seade pela API CKAN, com download como contingência.

O Cloudflare do repositório bloqueia os arquivos ``/download/`` em alguns
ambientes automatizados. Para recursos carregados no CKAN DataStore, esta
camada pagina os registros pela Action API e reconstrói um CSV equivalente.
"""
from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import fetch_seade_mortalidade as seade

HOME = "https://repositorio.seade.gov.br/"
DATASTORE = HOME + "api/3/action/datastore_search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0 Safari/537.36"
    ),
    "Accept": "application/json,text/csv,text/plain,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": HOME,
    "Cache-Control": "no-cache",
}
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
SESSION_READY = False


def http_bytes(url: str, timeout: int = 240) -> tuple[bytes, dict[str, str], str]:
    global SESSION_READY
    if not SESSION_READY:
        try:
            OPENER.open(urllib.request.Request(HOME, headers=HEADERS), timeout=60).read(1)
        except Exception:
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


def datastore_page(resource_id: str, limit: int, offset: int) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {"resource_id": resource_id, "limit": limit, "offset": offset}
    )
    raw, _, _ = http_bytes(f"{DATASTORE}?{query}", timeout=240)
    payload = json.loads(raw.decode("utf-8"))
    if not payload.get("success"):
        raise RuntimeError(f"DataStore respondeu sem sucesso para {resource_id}")
    return payload["result"]


def datastore_csv(resource_id: str) -> tuple[bytes, dict[str, str], str]:
    first = datastore_page(resource_id, limit=5000, offset=0)
    fields = [
        field["id"]
        for field in first.get("fields", [])
        if field.get("id") != "_id"
    ]
    if not fields:
        raise RuntimeError(f"DataStore sem campos para {resource_id}")

    total = int(first.get("total", 0))
    records = list(first.get("records", []))
    offset = len(records)
    while offset < total:
        page = datastore_page(resource_id, limit=5000, offset=offset)
        batch = page.get("records", [])
        if not batch:
            raise RuntimeError(
                f"Paginação interrompida no recurso {resource_id}: {offset}/{total}"
            )
        records.extend(batch)
        offset += len(batch)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter=";",
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for record in records:
        writer.writerow({field: record.get(field) for field in fields})

    endpoint = f"{DATASTORE}?resource_id={resource_id}"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "X-Seade-Acquisition": "CKAN-DataStore",
        "X-Seade-Resource-Id": resource_id,
        "X-Seade-Record-Count": str(len(records)),
    }
    return output.getvalue().encode("utf-8"), headers, endpoint


def request_bytes(url: str, timeout: int = 240) -> tuple[bytes, dict[str, str], str]:
    match = re.search(r"/resource/([0-9a-f-]{36})/download/", url, flags=re.I)
    datastore_error: Exception | None = None
    if match:
        try:
            return datastore_csv(match.group(1))
        except Exception as exc:
            datastore_error = exc

    try:
        return http_bytes(url, timeout=timeout)
    except Exception as download_error:
        if datastore_error is not None:
            raise RuntimeError(
                f"DataStore indisponível ({datastore_error}); "
                f"download direto também falhou ({download_error})"
            ) from download_error
        raise


seade.UA = HEADERS["User-Agent"]
seade.get = request_bytes

if __name__ == "__main__":
    raise SystemExit(seade.main())
