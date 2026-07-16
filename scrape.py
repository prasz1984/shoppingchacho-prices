#!/usr/bin/env python3
"""
ShoppingChacho Scraper
Scrapt täglich Preise von Mercadona und Lidl.
Läuft kostenlos via GitHub Actions.
"""

import json, time, datetime, os, re
import urllib.request, urllib.error

OUTPUT_FILE = "data/prices.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json, text/html",
    "Accept-Language": "es-ES,es;q=0.9",
}

# ── Produktkategorien die wir von Mercadona scrapen ──────────────
# IDs aus tienda.mercadona.es/categories/<ID>
MERCADONA_CATEGORIES = {
    "aceites":    [112],   # Aceites
    "lacteos":    [120],   # Lácteos
    "pan":        [136],   # Pan, arroz, pasta
    "verduras":   [150],   # Verduras y frutas
    "bebidas":    [160],   # Bebidas
    "carne":      [170],   # Carne y pescado
    "drogueria":  [220],   # Droguería
    "higiene":    [230],   # Higiene personal
    "congelados": [210],   # Congelados
}

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  Fehler bei {url}: {e} (Versuch {attempt+1}/{retries})")
            time.sleep(2 ** attempt)
    return None

def fetch_html(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            print(f"  Fehler bei {url}: {e} (Versuch {attempt+1}/{retries})")
            time.sleep(2 ** attempt)
    return None

# ─────────────────────────────────────────────────────────────────
# MERCADONA
# Offizielle (inoffizielle) JSON-API — sehr stabil
# ─────────────────────────────────────────────────────────────────
def scrape_mercadona():
    print("\n── Mercadona ────────────────────────────────────────────")
    products = []

    for cat_name, cat_ids in MERCADONA_CATEGORIES.items():
        for cat_id in cat_ids:
            url = f"https://tienda.mercadona.es/api/categories/{cat_id}/?lang=es&wh=vlc1"
            print(f"  Kategorie {cat_name} (ID {cat_id})...")
            data = fetch_json(url)
            if not data:
                print(f"  ⚠ Keine Daten für {cat_name}")
                continue

            # Mercadona gibt subcategories zurück
            categories = data.get("results", {}).get("categories", [])
            if not categories:
                # manchmal direkt products
                categories = [data.get("results", {})]

            for subcat in categories:
                for product in subcat.get("products", []):
                    try:
                        price_info = product.get("price_instructions", {})
                        price = float(price_info.get("unit_price", 0))
                        if price <= 0:
                            continue

                        # Einheitspreis / Menge
                        bulk_price = price_info.get("bulk_price")
                        size_format = price_info.get("size_format", "")
                        unit_name = price_info.get("unit_name", "ud")
                        reference_price = price_info.get("reference_price")
                        reference_format = price_info.get("reference_format", "")

                        # Vorheriger Preis (falls Angebot)
                        previous_price = None
                        if price_info.get("previous_unit_price"):
                            try:
                                previous_price = float(price_info["previous_unit_price"])
                            except:
                                pass

                        products.append({
                            "id":         str(product.get("id", "")),
                            "name":       product.get("display_name", ""),
                            "chain":      "Mercadona",
                            "cat":        cat_name,
                            "price":      round(price, 2),
                            "oldPrice":   round(previous_price, 2) if previous_price else None,
                            "unit":       unit_name,
                            "sizeFormat": size_format,
                            "refPrice":   reference_price,
                            "refFormat":  reference_format,
                            "barcode":    product.get("ean", ""),
                            "thumbnail":  product.get("thumbnail", ""),
                            "offer":      previous_price is not None and previous_price > price,
                        })
                    except Exception as e:
                        print(f"    Fehler bei Produkt: {e}")
                        continue

            time.sleep(0.5)  # höflich zum Server

    print(f"  ✓ {len(products)} Mercadona-Produkte")
    return products


# ─────────────────────────────────────────────────────────────────
# LIDL — Wochenangebote via JSON-Feed
# ─────────────────────────────────────────────────────────────────
def scrape_lidl():
    print("\n── Lidl ─────────────────────────────────────────────────")
    products = []

    # Lidl hat einen öffentlichen Angebots-Feed
    url = "https://www.lidl.es/api/offers"
    data = fetch_json(url)

    if not data:
        # Fallback: Statische Lidl-Stammpreise (werden manuell gepflegt)
        print("  Lidl API nicht erreichbar — nutze Fallback-Preise")
        return get_lidl_fallback()

    try:
        offers = data.get("offers", data if isinstance(data, list) else [])
        for item in offers[:100]:  # max 100 Angebote
            name  = item.get("name") or item.get("title", "")
            price = item.get("price") or item.get("currentPrice", 0)
            if not name or not price:
                continue
            try:
                price = float(str(price).replace(",", "."))
            except:
                continue

            products.append({
                "id":       f"lidl_{item.get('id', name[:8])}",
                "name":     name,
                "chain":    "Lidl",
                "cat":      map_lidl_category(name),
                "price":    round(price, 2),
                "oldPrice": None,
                "offer":    True,
                "barcode":  "",
                "thumbnail": item.get("image", ""),
            })
    except Exception as e:
        print(f"  Fehler beim Parsen: {e}")
        return get_lidl_fallback()

    if not products:
        return get_lidl_fallback()

    print(f"  ✓ {len(products)} Lidl-Angebote")
    return products


def map_lidl_category(name):
    """Ordnet Lidl-Produkte einer Kategorie zu."""
    name_l = name.lower()
    if any(x in name_l for x in ["aceite", "oliva", "girasol"]):    return "aceites"
    if any(x in name_l for x in ["leche", "yogur", "queso", "mantequilla"]): return "lacteos"
    if any(x in name_l for x in ["pan", "arroz", "pasta", "cereales"]):      return "pan"
    if any(x in name_l for x in ["fruta", "verdura", "patata", "tomate"]):   return "verduras"
    if any(x in name_l for x in ["agua", "zumo", "refresco", "cerveza"]):    return "bebidas"
    if any(x in name_l for x in ["pollo", "carne", "atun", "pescado"]):      return "carne"
    if any(x in name_l for x in ["papel", "detergente", "suavizante", "lejia", "limpieza"]): return "drogueria"
    if any(x in name_l for x in ["champu", "gel", "dentifrico", "higiene"]): return "higiene"
    if any(x in name_l for x in ["congelad", "pizza", "helado"]):            return "congelados"
    return "otros"


def get_lidl_fallback():
    """Feste Lidl-Stammpreise als Fallback wenn API nicht erreichbar."""
    return [
        {"id":"lidl_leche",   "name":"Leche entera Milbona 1L",        "chain":"Lidl","cat":"lacteos",   "price":0.79, "oldPrice":None,"offer":False,"barcode":"20319895","thumbnail":""},
        {"id":"lidl_aceite",  "name":"Aceite oliva virgen extra 1L",    "chain":"Lidl","cat":"aceites",   "price":4.29, "oldPrice":None,"offer":False,"barcode":"20374185","thumbnail":""},
        {"id":"lidl_pan",     "name":"Pan de molde 500g",               "chain":"Lidl","cat":"pan",       "price":0.79, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_agua",    "name":"Agua mineral 6x1.5L",             "chain":"Lidl","cat":"bebidas",   "price":2.29, "oldPrice":None,"offer":True, "barcode":"","thumbnail":""},
        {"id":"lidl_papel16", "name":"Papel higienico original x16",    "chain":"Lidl","cat":"drogueria", "price":6.99, "oldPrice":None,"offer":False,"barcode":"20374191","thumbnail":""},
        {"id":"lidl_deterg",  "name":"Detergente liquido 50 lavados",   "chain":"Lidl","cat":"drogueria", "price":5.49, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_suav",    "name":"Suavizante Formil 80 dosis",      "chain":"Lidl","cat":"drogueria", "price":2.99, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_gel",     "name":"Gel de bano Cien 1L",             "chain":"Lidl","cat":"higiene",   "price":1.49, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_champu",  "name":"Champu Cien 300ml",               "chain":"Lidl","cat":"higiene",   "price":0.99, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_pizza",   "name":"Pizza margarita Italiamo",        "chain":"Lidl","cat":"congelados","price":1.79, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_helado",  "name":"Helado vainilla 1L",              "chain":"Lidl","cat":"congelados","price":1.99, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_yogur",   "name":"Yogur Milbona natural x8",        "chain":"Lidl","cat":"lacteos",   "price":1.29, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_arroz",   "name":"Arroz redondo 1kg",               "chain":"Lidl","cat":"pan",       "price":0.89, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_pasta",   "name":"Espaguetis 500g",                 "chain":"Lidl","cat":"pan",       "price":0.45, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_pollo",   "name":"Pechuga de pollo 1kg",            "chain":"Lidl","cat":"carne",     "price":4.99, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
        {"id":"lidl_cocina",  "name":"Papel cocina 2 rollos",           "chain":"Lidl","cat":"drogueria", "price":1.09, "oldPrice":None,"offer":False,"barcode":"","thumbnail":""},
    ]


# ─────────────────────────────────────────────────────────────────
# HAUPTFUNKTION
# ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("ShoppingChacho Scraper — " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 55)

    all_products = []

    # Mercadona scrapen
    try:
        mercadona = scrape_mercadona()
        all_products.extend(mercadona)
    except Exception as e:
        print(f"Mercadona Fehler: {e}")

    # Lidl scrapen
    try:
        lidl = scrape_lidl()
        all_products.extend(lidl)
    except Exception as e:
        print(f"Lidl Fehler: {e}")

    if not all_products:
        print("\n⚠ Keine Produkte gefunden — Scraping fehlgeschlagen")
        return 1

    # Barcode-Index aufbauen
    barcode_index = {}
    for p in all_products:
        if p.get("barcode"):
            barcode_index[p["barcode"]] = p.get("id", "")

    output = {
        "updated":       datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_human": datetime.datetime.now().strftime("%d.%m.%Y %H:%M Uhr"),
        "product_count": len(all_products),
        "products":      all_products,
        "barcodeIndex":  barcode_index,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 55}")
    print(f"✓ Fertig! {len(all_products)} Produkte gespeichert")
    print(f"✓ Ausgabe: {OUTPUT_FILE}")
    print(f"{'=' * 55}")
    return 0


if __name__ == "__main__":
    exit(main())
