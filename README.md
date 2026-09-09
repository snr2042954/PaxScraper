# PAX Scraper

A small self-hosted Python application for tracking IKEA product prices over time.

The project was built primarily to monitor the individual components of an IKEA PAX wardrobe and detect when one of those components becomes meaningfully cheaper.

Instead of relying on IKEA explicitly marking a product as being on sale, the application stores observed prices and compares each new price against the previously recorded price.

The app includes:

- a FastAPI web dashboard
- automatic scans every 6 hours
- manual scans from the dashboard
- SQLite price history
- Pushover notifications for significant price changes
- Docker deployment for a home server
- Tailscale-friendly port binding

---

## How it works

The application reads a list of IKEA product URLs from `products.yaml`.

For each product it:

1. Fetches the IKEA product page.
2. Extracts the article number, product name, and current price.
3. Looks up the most recently stored price in SQLite.
4. Compares the current price to the previous price.
5. Stores a new observation only when the price changes.
6. Logs the result of every scan.
7. Sends a Pushover notification if the configured price-change threshold is exceeded.

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

Repeated scans at the same price are not stored.

---

## Architecture

```text
                         main.py
                        /       \
                       /         \
              dashboard           Scan button
                                  |
                                  v
scheduler.py ------------> services/scanner.py
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
                ikea.py              services/price_checker.py
                                                |
                                                v
                                             SQLite

                                  |
                                  v
                         services/notifier.py
                                  |
                                  v
                              Pushover


products.yaml --> config.py --> scanner.py
```

The application is intentionally split into small components:

- `main.py` handles the web application and routes.
- `scheduler.py` triggers automatic scans.
- `scanner.py` coordinates full product scans.
- `ikea.py` fetches and parses IKEA product pages.
- `price_checker.py` compares and stores prices.
- `notifier.py` sends Pushover notifications.
- `config.py` reads `products.yaml`.
- `models.py` defines the database tables.
- `db.py` configures SQLite and SQLAlchemy.

---

## Project structure

```text
PaxScraper/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── notifier.py
│   │   ├── price_checker.py
│   │   └── scanner.py
│   │
│   ├── templates/
│   │   └── dashboard.html
│   │
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── ikea.py
│   ├── main.py
│   ├── models.py
│   └── scheduler.py
│
├── data/
│   └── ikea.db
│
├── .dockerignore
├── .env
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── products.yaml
├── README.md
└── requirements.txt
```

The old `app/jobs/` folder is no longer required. Both scheduled scans and manual dashboard scans now use the shared logic in:

```text
app/services/scanner.py
```

---

## Requirements

- Python 3.10+
- Docker for deployment
- Internet access
- IKEA.nl product URLs
- Optional Pushover account for notifications

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

The project currently uses packages such as:

```text
fastapi
uvicorn[standard]
httpx
beautifulsoup4
sqlalchemy
python-dotenv
pyyaml
jinja2
apscheduler
```

---

## Product configuration

Products are configured in:

```text
products.yaml
```

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

The application derives the following information from the product page:

- article number
- product name
- current price

#### `quantity_needed`

The number of units required for the final wardrobe configuration.

Example:

```yaml
quantity_needed: 3
```

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

---

## Environment configuration

Secrets and runtime configuration are stored in `.env`.

Example:

```env
PORT=8013
BIND_IP=0.0.0.0

PUSHOVER_USER_KEY=your_user_key_here
PUSHOVER_API_TOKEN=your_application_token_here

PRICE_CHANGE_THRESHOLD_PERCENT=5
```

For a home server using Tailscale, set `BIND_IP` to the server's Tailscale address:

```env
PORT=8013
BIND_IP=100.x.y.z
```

Then the dashboard is available at:

```text
http://100.x.y.z:8013
```

Keep `.env` out of Git.

---

## Price-change notifications

Pushover notifications are sent when the percentage price change exceeds the configured threshold.

Example:

```env
PRICE_CHANGE_THRESHOLD_PERCENT=5
```

If a product changes from:

```text
€105 → €98
```

the percentage change is roughly:

```text
-6.7%
```

and a notification is sent.

The notification includes:

- product name
- article number
- previous price
- current price
- percentage change
- link to the IKEA product page

By default, the current implementation can notify for both increases and decreases if the absolute percentage change exceeds the threshold.

If desired, this can be changed so only price drops trigger notifications.

---

## Database

Price observations are stored in:

```text
data/ikea.db
```

The SQLite database stores only actual price changes.

Conceptually:

```text
article_number | price  | checked_at
---------------|--------|-------------------------
20458205       | 105.00 | 2026-09-08 20:00:00
20458205       |  80.00 | 2026-09-21 08:00:00
20458205       | 105.00 | 2026-10-03 08:00:00
```

If the price is unchanged during a scan, no new row is added.

Product metadata such as product name and URL is also stored separately in SQLite.

---

## Web dashboard

Start the application locally with:

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The dashboard shows:

- tracked products
- product name
- IKEA article number
- current price
- previous price
- percentage change
- quantity needed
- optional target price
- last recorded price change

The dashboard also includes a:

```text
Scan prices
```

button for manually triggering a full scan.

---

## Automatic scans

The scheduler starts with the FastAPI application.

It runs a full scan every:

```text
6 hours
```

Both automatic scans and manual dashboard scans call the same function:

```text
app/services/scanner.py
```

This avoids duplicated scanning logic.

---

## Logging

All scan activity is written to standard output.

When running in Docker, view logs with:

```bash
docker logs paxscraper
```

Follow logs live with:

```bash
docker logs -f paxscraper
```

Example output:

```text
2026-09-09 18:00:00 | INFO | paxscraper | Starting IKEA price scan for 20 products
2026-09-09 18:00:01 | INFO | paxscraper | SCAN OK | 20458205 | PAX wardrobe frame | €105.00 | unchanged
2026-09-09 18:00:02 | INFO | paxscraper | SCAN OK | 30214504 | KOMPLEMENT hinge | €16.00 | unchanged
2026-09-09 18:00:03 | INFO | paxscraper | SCAN OK | 60344735 | FLISBERGET door | €70.00 -> €59.00 | -15.71%
2026-09-09 18:00:03 | INFO | paxscraper | PUSHOVER SENT | 60344735 | -15.71%
2026-09-09 18:00:19 | INFO | paxscraper | IKEA price scan finished | successful=20 failed=0
```

Failures are logged individually so one broken product page does not prevent the rest of the products from being scanned.

---

## Docker deployment

Build and run with:

```bash
docker compose up -d --build
```

Check the container:

```bash
docker compose ps
```

View logs:

```bash
docker logs -f paxscraper
```

---

## Dockerfile

The application container runs Uvicorn on port `8013`.

Example:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8013"]
```

---

## Docker Compose

Example:

```yaml
services:
  paxscraper:
    build: .
    container_name: paxscraper

    restart: unless-stopped

    ports:
      - "${BIND_IP:-0.0.0.0}:${PORT:-8013}:${PORT:-8013}"

    env_file:
      - .env

    volumes:
      - ./data:/app/data
      - ./products.yaml:/app/products.yaml:ro

    environment:
      - TZ=Europe/Amsterdam
```

This allows the same Compose file to be used locally and on the server.

Locally:

```env
PORT=8013
BIND_IP=0.0.0.0
```

On the server:

```env
PORT=8013
BIND_IP=100.x.y.z
```

---

## Updating the server

The repository only needs to be cloned once.

After pushing changes to GitHub:

```bash
cd ~/Docker/paxscraper
git pull
docker compose up -d --build
```

`git pull` only updates the repository in the current directory.

It does not affect unrelated Docker projects.

---

## Git

A typical `.gitignore` should include:

```gitignore
.venv/
.env

__pycache__/
*.pyc

data/*.db
```

A typical `.dockerignore` should include:

```text
.venv
.git
.gitignore
__pycache__
*.pyc
data/*.db
.env
```

The SQLite database is runtime state and should not normally be committed.

The `products.yaml` file can be committed so the tracked wardrobe components are version controlled.

---

## Development workflow

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

Run locally:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## Current application flow

```text
products.yaml
      |
      v
   config.py
      |
      v
services/scanner.py
      |
      +----------------------+
      |                      |
      v                      v
   ikea.py          price_checker.py
      |                      |
      v                      v
IKEA product pages         SQLite

      |
      v
  notifier.py
      |
      v
   Pushover
```

The scanner can be triggered by:

```text
scheduler.py
```

or:

```text
main.py
```

through the dashboard's manual scan button.

---

## Goal

The long-term goal is to turn a complete IKEA PAX design into a personal procurement tracker.

Instead of buying the entire wardrobe at retail price immediately, individual components can be purchased over time whenever their price drops.

The application keeps track of historical prices so buying decisions are based on actual observed price changes rather than IKEA sale labels.

Future additions could include:

- price-history charts
- quantity owned versus quantity needed
- total savings calculations
- availability tracking
- IKEA Second Chance tracking
- product purchase status
- richer dashboard filters
- product-level history pages