"""Atualiza categorias oficiais e descrições de fragrância do catálogo Avatim."""
from __future__ import annotations

import csv
import re
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, local
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www.avatim.com.br"
PRODUCTS_PATH = Path("data/produtos_avatim.csv")
FRAGRANCES_PATH = Path("data/fragrancias_avatim.csv")
MIN_INTERVAL = 0.4  # no máximo 2,5 requisições/s em toda a execução
OFFICIAL_CATEGORIES = {
    "corpo": "Corpo", "ambiente": "Ambiente", "kits": "Kits", "acessorios": "Acessórios",
    "homem": "Homem", "lancamentos": "Lançamentos", "refis": "Refis",
}
last_request = 0.0
rate_lock = Lock()
thread_local = local()


def clean(value: str | None) -> str:
    return " ".join((value or "").split())


def canonical(url: str) -> str:
    parts = urlsplit(urljoin(BASE_URL, url))
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=False)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), query, ""))


def session() -> requests.Session:
    client = requests.Session()
    client.headers.update({"User-Agent": "Mozilla/5.0 (compatible; AvatimCatalogUpdater/1.0)", "Accept-Language": "pt-BR,pt;q=0.9"})
    client.mount("https://", HTTPAdapter(max_retries=Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))))
    return client


def worker_session() -> requests.Session:
    if not hasattr(thread_local, "client"):
        thread_local.client = session()
    return thread_local.client


def get_html(client: requests.Session, url: str) -> str:
    global last_request
    with rate_lock:
        remaining = MIN_INTERVAL - (time.monotonic() - last_request)
        if remaining > 0:
            time.sleep(remaining)
        last_request = time.monotonic()
    response = client.get(url, timeout=(15, 45))
    response.raise_for_status()
    return response.text


def category_urls(client: requests.Session, slug: str) -> set[str]:
    pending = deque([f"{BASE_URL}/todos-os-produtos/{slug}"])
    pages: set[str] = set()
    products: set[str] = set()
    while pending:
        page = canonical(pending.popleft())
        if page in pages:
            continue
        soup = BeautifulSoup(get_html(client, page), "html.parser")
        pages.add(page)
        for block in soup.select("[data-product-box]"):
            link = block.select_one('a[href*="/produto/"]')
            if link and link.get("href"):
                products.add(canonical(link["href"]))
        for link in soup.select(".pagination a[href]"):
            next_page = canonical(link["href"])
            if f"/todos-os-produtos/{slug}" in next_page and next_page not in pages:
                pending.append(next_page)
    return products


def product_fragrance(url: str) -> tuple[str, str]:
    soup = BeautifulSoup(get_html(worker_session(), url), "html.parser")
    tabs = [clean(tab.get_text(" ", strip=True)).casefold() for tab in soup.select("[data-desc-tab]")]
    contents = soup.select("[data-desc-content]")
    fragrance_text = ""
    if "sobre a fragrância" in tabs:
        fragrance_text = clean(contents[tabs.index("sobre a fragrância")].get_text(" ", strip=True))
    info_index = tabs.index("mais informações") if "mais informações" in tabs else -1
    fragrance = ""
    if info_index >= 0:
        info = clean(contents[info_index].get_text(" ", strip=True))
        found = re.search(r"FRAGRÂNCIA\s*:\s*(.*?)(?=\s+(?:FAMÍLIA OLFATIVA|REFIL|COMPOSIÇÃO|PIRÂMIDE OLFATIVA)\s*:|$)", info, re.I)
        if found:
            fragrance = clean(found.group(1))
    return fragrance, fragrance_text


def main() -> None:
    collected_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with PRODUCTS_PATH.open(encoding="utf-8-sig", newline="") as file:
        products = list(csv.DictReader(file))
    client = session()
    category_map: defaultdict[str, set[str]] = defaultdict(set)
    for slug, title in OFFICIAL_CATEGORIES.items():
        for url in category_urls(client, slug):
            category_map[url].add(title)
        print(f"Categoria mapeada: {title}")

    fragrance_rows: list[dict[str, str]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(product_fragrance, row["url"]): row for row in products}
        for position, future in enumerate(as_completed(futures), start=1):
            row = futures[future]
            try:
                fragrance, about = future.result()
            except Exception as exc:
                fragrance, about = "", ""
                errors.append(f"{row['url']}\t{type(exc).__name__}: {exc}")
            row["categoria"] = "; ".join(sorted(category_map.get(canonical(row["url"]), set())))
            row["fragrancia"] = fragrance
            fragrance_rows.append({
                "identificador": row["identificador"], "url": row["url"], "nome": row["nome"],
                "fragrancia": fragrance, "sobre_a_fragancia": about, "coletado_em": collected_at,
            })
            if position % 50 == 0:
                print(f"Fragrâncias processadas: {position}/{len(products)}")

    product_fields = [
        "identificador", "nome", "url", "descricao_apresentacao", "sobre_o_produto", "como_usar",
        "linha", "categoria", "fragrancia", "preco_atual_reais", "preco_anterior_reais", "disponibilidade",
        "url_imagem_principal", "coletado_em",
    ]
    with PRODUCTS_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=product_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(products)
    with FRAGRANCES_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["identificador", "url", "nome", "fragrancia", "sobre_a_fragancia", "coletado_em"])
        writer.writeheader()
        writer.writerows(sorted(fragrance_rows, key=lambda row: row["url"]))
    print({"produtos": len(products), "categorias_vazias": sum(not row["categoria"] for row in products), "fragrancias": sum(bool(row["fragrancia"]) for row in fragrance_rows), "textos_sobre_fragrancia": sum(bool(row["sobre_a_fragancia"]) for row in fragrance_rows), "erros": len(errors)})


if __name__ == "__main__":
    main()
