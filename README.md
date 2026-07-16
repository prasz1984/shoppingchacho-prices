# ShoppingChacho — Preisscraper

Automatische tägliche Preisaktualisierung für Mercadona und Lidl via GitHub Actions.

## Einrichtung (10 Minuten)

### Schritt 1 — Repository erstellen
1. GitHub.com öffnen → **"New repository"**
2. Name: `shoppingchacho-prices`
3. **Public** auswählen (damit die App die Preise lesen kann)
4. **"Create repository"** klicken

### Schritt 2 — Dateien hochladen
Diese drei Ordner/Dateien in dein Repository laden:
```
.github/workflows/scrape.yml   ← GitHub Actions Workflow
scraper/scrape.py              ← Python Scraper
data/prices.json               ← Ausgabedatei (leer zum Start)
```

Am einfachsten: Alle Dateien per Drag & Drop auf GitHub hochladen.

### Schritt 3 — GitHub Actions aktivieren
1. In deinem Repo auf **"Actions"** klicken
2. **"I understand my workflows, go ahead and enable them"** klicken
3. Links auf **"ShoppingChacho Preise aktualisieren"** klicken
4. **"Run workflow"** → **"Run workflow"** für ersten Test

### Schritt 4 — App verbinden
Die `prices.json` Datei ist dann unter dieser URL erreichbar:
```
https://raw.githubusercontent.com/DEIN-USERNAME/shoppingchacho-prices/main/data/prices.json
```
→ Diese URL in die App eintragen (siehe App-Anleitung unten)

### Schritt 5 — App anpassen
In der `ShoppingChacho_Beta.html` Datei diese Zeile suchen:
```javascript
var PRICES_URL = '';
```
Und die URL von Schritt 4 eintragen:
```javascript
var PRICES_URL = 'https://raw.githubusercontent.com/DEIN-USERNAME/shoppingchacho-prices/main/data/prices.json';
```

## Zeitplan
| Wann | Was |
|------|-----|
| Täglich 09:00 Uhr | Alle Mercadona-Preise |
| Montags 08:00 Uhr | Lidl-Wochenangebote |
| Manuell | Jederzeit über "Run workflow" |

## Kosten
| Service | Kosten |
|---------|--------|
| GitHub Actions | 0€ (2.000 Min/Monat frei) |
| GitHub Repository | 0€ |
| Scraping | 0€ |
| **Gesamt** | **0€** |

## Manuell ausführen
Wenn du sofort aktualisieren willst:
1. GitHub → dein Repo → **Actions**
2. **"ShoppingChacho Preise aktualisieren"**
3. **"Run workflow"**

## Troubleshooting
- **Workflow schlägt fehl**: Unter Actions → Run → Logs nachschauen
- **Mercadona blockiert**: Wartezeit im Script erhöhen (Zeile `time.sleep(0.5)`)
- **Lidl nicht erreichbar**: Fallback-Preise werden automatisch genutzt
