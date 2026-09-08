# PAX Scraper

A small self-hosted Python application for tracking IKEA product prices over time.

The project was built primarily to monitor the individual components of an IKEA PAX wardrobe and detect when one of those components becomes cheaper.

Instead of relying on IKEA explicitly marking a product as being on sale, the application stores observed prices and compares each new price against the previously recorded price.

## How it works

The application reads a list of IKEA product URLs from `products.yaml`.

For each product it:

1. Fetches the IKEA product page.
2. Extracts the article number, product name, and current price.
3. Looks up the most recently stored price in SQLite.
4. Compares the current price to the previous price.
5. Stores a new observation only when the price changes.
6. Reports whether the price increased or decreased.
7. Optionally checks whether a configured target price has been reached.

This means the database acts as a price-change history rather than a log of every polling attempt.

Example:

```text
€105
  ↓
€80
  ↓
€105
  ↓
€95
```

## Project structure

```text
PaxScraper/
├── app/
│   ├── jobs/
│   │   ├── __init__.py
│   │   └── scan_products.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── price_checker.py
│   │
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── ikea.py
│   ├── main.py
│   └── models.py
│
├── data/
│   └── ikea.db
│
├── products.yaml
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+
- Internet access
- IKEA.nl product URLs

Install dependencies with:

```bash
pip install -r requirements.txt
```

The project currently uses:

```text
fastapi
uvicorn[standard]
httpx
beautifulsoup4
sqlalchemy
python-dotenv
pyyaml
```

## Configuration

Products are configured in `products.yaml`.

Example:

```yaml
products:

  # PAX wardrobe frame, 100x58x236 cm
  - url: "https://www.ikea.com/nl/nl/p/-20458205/"
    quantity_needed: 1
    target_price:

  # KOMPLEMENT shelf, 100x58 cm
  - url: "https://www.ikea.com/nl/nl/p/-60509142/"
    quantity_needed: 2
    target_price:
```

### Fields

#### `url`

The IKEA product URL.

The application derives the following information from the IKEA product page:

- Article number
- Product name
- Current price

#### `quantity_needed`

The number of units required for the final wardrobe configuration.

Example:

```yaml
quantity_needed: 3
```

This does not currently affect price detection, but is included for future procurement logic.

#### `target_price`

Optional target price.

Leave it empty:

```yaml
target_price:
```

Or specify a value:

```yaml
target_price: 75.00
```

If the current IKEA price is equal to or below the configured target price, the scanner reports:

```text
TARGET PRICE REACHED
```

## Running the scanner

From the project root:

```bash
python -m app.jobs.scan_products
```

## First run

On the first run, each product creates a baseline price observation.

Example:

```text
Scanning 2 product(s)...

PAX wardrobe frame
Article: 20458205
Needed:  1
Baseline stored: €105.00
```

## Unchanged prices

If a product still has the same price:

```text
PAX wardrobe frame
Article: 20458205
Needed:  1
Price unchanged: €105.00
```

No additional database row is stored.

This keeps the database focused on actual price changes rather than every scan.

## Price drops

If IKEA lowers the price:

```text
PAX wardrobe frame
Article: 20458205
Needed:  1
Previous: €105.00
Current:  €80.00
Change:   €-25.00 (-23.8%)

PRICE DROP
```

The new price is stored in the database.

## Price increases

Price increases are also stored.

Example:

```text
Previous: €80.00
Current:  €105.00
Change:   €+25.00 (+31.2%)

Price increased.
```

Tracking both increases and decreases gives an accurate history of the product price.

## Database

Price observations are stored in:

```text
data/ikea.db
```

The SQLite database stores price changes per IKEA article number.

Conceptually:

```text
article_number | price  | checked_at
---------------|--------|-------------------------
20458205       | 105.00 | 2026-09-08 20:00:00
20458205       |  80.00 | 2026-09-21 08:00:00
20458205       | 105.00 | 2026-10-03 08:00:00
```

Repeated scans at the same price are not stored.

## Adding products

To track another IKEA product, add it to `products.yaml`.

Example:

```yaml
# KOMPLEMENT clothes rail, 50 cm
- url: "https://www.ikea.com/nl/nl/p/-40256942/"
  quantity_needed: 1
  target_price:
```

The next scan will automatically:

1. Fetch the product.
2. Extract its article number and name.
3. Read the current price.
4. Store the first observed price as its baseline.

No Python changes are required when adding products.

## Development

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the scanner:

```bash
python -m app.jobs.scan_products
```

## Git

Runtime and secret files should not be committed.

A typical `.gitignore` includes:

```gitignore
.venv/
.env
__pycache__/
*.pyc
data/*.db
```

The `products.yaml` file can be committed so the list of tracked wardrobe components is version controlled.

## Current architecture

```text
products.yaml
      │
      ▼
  config.py
      │
      ▼
scan_products.py
      │
      ▼
   ikea.py
      │
      ▼
IKEA product pages
      │
      ▼
price_checker.py
      │
      ▼
   SQLite
```

## Planned features

Possible future additions:

- Scheduled automatic scans
- Telegram notifications
- Email notifications
- Web dashboard
- Price-history charts
- Mark products as already purchased
- Track quantity owned versus quantity needed
- Calculate total wardrobe savings
- Track product availability
- Track IKEA Second Chance products
- Docker deployment
- Run continuously on a home server

## Goal

The long-term goal is to turn a complete IKEA PAX design into a personal procurement tracker.

Instead of buying the full wardrobe at retail price immediately, individual components can be purchased over time whenever their price drops.

The application keeps track of the historical prices so that buying decisions are based on actual observed price changes rather than IKEA sale labels.