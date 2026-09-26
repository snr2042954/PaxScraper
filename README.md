# PAX Scraper

Self-hosted IKEA price and Second Chance tracker for a custom PAX wardrobe build.

PAX Scraper monitors a fixed list of IKEA products, stores normal retail price changes, scans IKEA's **Second Chance / Tweedekanshoek** inventory, and sends Pushover notifications when something interesting happens.

The application runs as a FastAPI web app with a SQLite database and is designed to run continuously in Docker on a home server.

---

## Features

- Track a fixed list of IKEA products from `products.yaml`
- Scrape current IKEA retail prices
- Store price history in SQLite
- Only store a new normal-price observation when the price actually changes
- Detect both retail price increases and decreases
- Send Pushover notifications for significant retail price changes
- Scan IKEA Second Chance / Tweedekanshoek inventory
- Match Second Chance offers directly by IKEA article number
- Scan multiple IKEA stores
- Automatically resolve IKEA store names to store IDs
- Track currently active Second Chance offers
- Automatically mark disappeared Second Chance offers as inactive
- Avoid duplicate Second Chance notifications using IKEA offer UUIDs
- Show active Second Chance matches on the dashboard
- Manual **Scan now** button scans both retail prices and Second Chance inventory
- Automatic scheduled scans
- Persistent SQLite database
- Docker deployment
- Tailscale-compatible server setup

---

## Architecture

```text
                         FastAPI
                         main.py
                        /       \
                       /         \
              Dashboard          Scan now
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
            Normal price scan          Second Chance scan
                    |                           |
                    v                           v
                ikea.py                 second_hand.py
                    |                           |
                    v                           v
            IKEA product pages         IKEA Circular API
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                               SQLite
                                  |
                       +----------+----------+
                       |                     |
                       v                     v
                 Price history       Active second-hand
                                           offers
                                  |
                                  v
                               Pushover
```

Automatic scheduling is handled by APScheduler.

Normal IKEA prices and Second Chance inventory intentionally use separate scanners because they represent different types of events.

---

## Project Structure

```text
PaxScraper/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── notifier.py
│   │   ├── price_checker.py
│   │   ├── scanner.py
│   │   └── second_hand_scanner.py
│   │
│   ├── templates/
│   │   └── dashboard.html
│   │
│   ├── static/
│   │   └── favicon.png
│   │
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── ikea.py
│   ├── main.py
│   ├── models.py
│   ├── scheduler.py
│   └── second_hand.py
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

---

# Product Configuration

Products are configured in:

```text
products.yaml
```

Each tracked product contains:

- IKEA product URL
- quantity needed
- optional target price

Example:

```yaml
products:

  # PAX basiselement kledingkast, 100x58x236 cm
  - url: "https://www.ikea.com/nl/nl/p/-20458205/"
    quantity_needed: 1
    target_price:

  # KOMPLEMENT zachtsluitende scharnier
  - url: "https://www.ikea.com/nl/nl/p/-30214504/"
    quantity_needed: 3
    target_price:
```

The IKEA article number is automatically extracted from the URL.

Product names are retrieved from IKEA and stored in the database.

---

# Second Chance Configuration

The same `products.yaml` file also controls IKEA Second Chance scanning.

Example:

```yaml
second_hand:
  enabled: true
  scan_interval_hours: 1
  min_discount_percent: 10

  stores:
    # - amersfoort
    # - amsterdam
    # - barendrecht
    - breda
    # - delft
    - duiven
    - eindhoven
    # - groningen
    # - haarlem
    - heerlen
    # - hengelo
    # - utrecht
    # - zwolle
```

For the current setup, the nearby stores around Eindhoven are enabled:

```text
Eindhoven
Breda
Duiven
Heerlen
```

Other stores can be enabled simply by uncommenting them.

---

# IKEA Store Discovery

Second Chance inventory uses IKEA internal store IDs.

For example:

```text
Eindhoven → 087
Duiven    → 272
Breda     → 403
```

These IDs are **not hard-coded** in `products.yaml`.

PAX Scraper resolves them automatically from IKEA's store metadata:

```text
https://www.ikea.com/nl/nl/meta-data/informera/stores-suggested.json
```

The application uses the IKEA `displayName` field to map a configured store name such as:

```text
eindhoven
```

to the corresponding IKEA business unit ID.

Only entries classified as:

```text
STORE
```

are used.

This intentionally excludes locations such as Plan and Order Points.

---

# Second Chance API

Second Chance / Tweedekanshoek inventory is loaded from IKEA's Circular API:

```text
https://web-api.ikea.com/circular/circular-asis/offers/grouped/search
```

Example request:

```text
https://web-api.ikea.com/circular/circular-asis/offers/grouped/search?languageCode=nl&size=32&storeIds=087&page=0
```

Parameters:

```text
languageCode=nl
size=32
storeIds=087
page=0
```

The API uses pagination.

For example, if a store returns:

```json
{
  "size": 32,
  "totalElements": 433,
  "totalPages": 14
}
```

PAX Scraper requests:

```text
page=0
page=1
page=2
...
page=13
```

The page size should remain:

```text
32
```

because IKEA returned a `400 Bad Request` when tested with `size=100`.

---

# Second Chance Matching

Second Chance offers include IKEA article numbers directly.

Example structure:

```json
{
  "articleNumbers": [
    "00395351"
  ],
  "storeId": "087",
  "title": "NYTTIG FIL 650",
  "originalPrice": 45.0,
  "minPrice": 9.99,
  "offers": [
    {
      "offerUuid": "...",
      "price": 9.99,
      "productConditionTitle": "Zo goed als nieuw",
      "reasonDiscount": "Klantenretour"
    }
  ]
}
```

PAX Scraper compares:

```text
Second Chance article number
```

against:

```text
tracked IKEA article numbers from products.yaml
```

This means fuzzy product-name matching is not necessary.

---

# Second Chance Discount Calculation

For each matching offer:

```text
discount percentage =
(original price - second-hand price)
/
original price
*
100
```

Example:

```text
Original price:      €105
Second Chance price: €59
```

Result:

```text
43.8% cheaper
```

Notifications are only sent when the discount is at least:

```yaml
min_discount_percent: 10
```

---

# Second Chance Conditions

The IKEA Circular API provides additional information for each offer.

This may include:

```text
productConditionCode
productConditionTitle
productConditionDescription
reasonDiscount
additionalInfo
```

Possible examples include:

```text
Nieuw
Zo goed als nieuw
Goed
Redelijk
```

Reasons can include:

```text
Klantenretour
Gebruikersschade
Model uit de showroom
Uit productie genomen product
```

This information is included in notifications and can also be displayed on the dashboard.

---

# Active Second Chance Offers

Second Chance inventory behaves differently from regular IKEA pricing.

A normal IKEA product has one current retail price.

A Second Chance product may:

- appear suddenly
- have multiple offers
- have different prices
- exist at multiple stores
- disappear after someone buys or reserves it

Because of this, Second Chance listings are stored separately.

The database keeps information such as:

```text
offer_uuid
article_number
store_id
store_name
title
description
original_price
price
condition_code
condition_title
reason_discount
additional_info
active
first_seen_at
last_seen_at
notified_at
```

---

# Offer Lifecycle

When a Second Chance offer appears:

```text
active = true
```

During every scan, its:

```text
last_seen_at
```

timestamp is updated.

If the same offer disappears from IKEA's current inventory:

```text
active = false
```

This causes it to automatically disappear from the dashboard.

---

# Duplicate Notification Prevention

Each IKEA Second Chance offer contains a unique:

```text
offerUuid
```

This UUID is used to prevent notification spam.

Example flow:

```text
Hour 1
New PAX offer appears
→ notify

Hour 2
Same offerUuid still exists
→ no notification

Hour 3
Same offerUuid still exists
→ no notification

Hour 5
Different PAX appears
→ new offerUuid
→ notify
```

The database stores:

```text
notified_at
```

after a successful Pushover notification.

---

# Normal IKEA Price Tracking

Normal IKEA retail prices are retrieved directly from product pages.

Example:

```text
https://www.ikea.com/nl/nl/p/-20458205/
```

IKEA redirects this to the canonical product URL.

The scraper extracts product information from JSON-LD embedded in the page.

Stored information includes:

```text
article number
product name
URL
current price
```

---

# Price History

Price history is stored in SQLite.

The application intentionally **does not store an observation every scan**.

If a product remains:

```text
€105
```

for 30 scans, only one price record exists.

If it changes:

```text
€105
→ €95
→ €105
```

three observations exist.

This keeps the database small while preserving the full history of meaningful price changes.

---

# Retail Price Notifications

Retail price notifications use a percentage threshold configured in `.env`.

Example:

```env
PRICE_CHANGE_THRESHOLD_PERCENT=5
```

The scanner calculates:

```text
(current price - previous price)
/
previous price
*
100
```

The current implementation can notify on changes larger than the configured percentage.

If desired, this can be restricted to price drops only by changing the condition to:

```python
if percentage_change < -PRICE_CHANGE_THRESHOLD_PERCENT:
```

---

# Pushover Notifications

PAX Scraper supports Pushover notifications.

Required `.env` values:

```env
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token
PRICE_CHANGE_THRESHOLD_PERCENT=5
```

Do not commit `.env` to Git.

---

## Retail Price Notification Example

```text
PRICE DROP: PAX Basiselement kledingkast

PAX Basiselement kledingkast
Article: 20458205

€105.00 → €95.00
-9.5%
```

---

## Second Chance Notification Example

```text
Second Chance: PAX Basiselement kledingkast

PAX Basiselement kledingkast
100x58x236 cm

Article: 20458205
Store: Eindhoven

Retail: €105.00
Second Chance: €59.00
Discount: 43.8%

Condition: Zo goed als nieuw
Reason: Klantenretour
```

The notification also contains a link to the corresponding IKEA Second Chance store page.

---

# Dashboard

The dashboard is available at:

```text
http://127.0.0.1:8013
```

or on the server through the configured Tailscale address.

The dashboard shows:

- product name
- IKEA article number
- current retail price
- best active Second Chance offer
- previous retail price
- retail price change
- quantity needed
- target price
- last retail price change

---

# Second Chance Dashboard Column

When an active Second Chance offer exists, the dashboard displays something like:

```text
€59.00   -43.8%
Eindhoven
Zo goed als nieuw
Klantenretour
```

If multiple active offers exist for the same tracked product, the dashboard:

- shows the cheapest active offer
- shows the number of active offers

Example:

```text
€59.00   -43.8%
Eindhoven
Zo goed als nieuw
3 active offers
```

Clicking the offer opens the corresponding IKEA Second Chance page.

---

# Dashboard Summary Cards

The dashboard includes summary cards for:

```text
Tracked products
Products scanned
Price drops
Second Chance matches
Units needed
```

`Second Chance matches` counts tracked products that currently have at least one active Second Chance offer.

---

# Manual Scanning

The dashboard contains a:

```text
Scan now
```

button.

This performs both scans:

```text
Scan now
   |
   +--> normal IKEA retail scan
   |
   +--> Second Chance inventory scan
   |
   +--> refresh dashboard
```

The route is:

```text
POST /scan
```

After both scans finish, the browser is redirected back to the dashboard.

---

# Automatic Scheduling

PAX Scraper uses APScheduler.

Normal retail price scans run every:

```text
6 hours
```

Second Chance scans are configured separately.

Example:

```yaml
second_hand:
  scan_interval_hours: 1
```

So the default intended schedule is:

```text
Normal IKEA prices:
every 6 hours

Second Chance:
every 1 hour
```

Second Chance is scanned more frequently because listings can disappear quickly.

---

# Logging

Application logs include successful scans.

Example:

```text
Starting IKEA price scan for 20 products

SCAN OK | 20458205 | PAX Basiselement kledingkast | €105.00 | unchanged

IKEA price scan finished | successful=20 failed=0
```

Second Chance logs look like:

```text
Starting Second Chance scan | stores=4 tracked_articles=20

SECOND HAND STORE OK | eindhoven | offers=433 matches=0

Second Chance scan finished | matches=0 notifications=0
```

When a tracked offer is found:

```text
SECOND HAND MATCH |
eindhoven |
20458205 |
€105.00 -> €59.00 |
43.8%
```

When an offer disappears:

```text
SECOND HAND GONE |
eindhoven |
20458205 |
<offer UUID>
```

---

# HTTP Logging

Because root logging is configured at `INFO`, HTTPX may log every network request.

Example:

```text
HTTP Request: GET https://www.ikea.com/... "HTTP/1.1 200 OK"
```

If cleaner logs are desired, add:

```python
logging.getLogger("httpx").setLevel(logging.WARNING)
```

Optionally APScheduler logging can also be reduced:

```python
logging.getLogger("apscheduler").setLevel(logging.WARNING)
```

---

# Database

The database uses SQLite:

```text
data/ikea.db
```

The Docker container mounts:

```text
./data:/app/data
```

so the database survives container rebuilds.

---

## Main Tables

The application uses tables for:

```text
product_metadata
price_observations
second_hand_offers
```

Earlier development versions may also contain:

```text
seen_second_hand_offers
```

This older table can remain in the SQLite database without causing problems even if it is no longer used.

---

# Local Development

## Clone the repository

```powershell
git clone https://github.com/snr2042954/PaxScraper.git
cd PaxScraper
```

---

## Create a virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

## Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Start the application

```powershell
uvicorn app.main:app --reload --port 8013
```

Open:

```text
http://127.0.0.1:8013
```

Because `--reload` is enabled, saving Python files automatically restarts the local development server.

---

# Test the Normal Scanner Directly

```powershell
python -c "import asyncio; from app.services.scanner import scan_all_products; asyncio.run(scan_all_products())"
```

---

# Test the Second Chance Scanner Directly

```powershell
python -c "import asyncio; from app.services.second_hand_scanner import scan_second_hand; asyncio.run(scan_second_hand())"
```

---

# Test IKEA Store Resolution

Example:

```powershell
python -c "import asyncio; from app.second_hand import resolve_store_ids; print(asyncio.run(resolve_store_ids(['eindhoven','breda','duiven','heerlen'])))"
```

Expected result:

```text
{
    'eindhoven': '087',
    'breda': '403',
    'duiven': '272',
    'heerlen': '089'
}
```

---

# Known Dutch IKEA Store IDs

The current IKEA store metadata includes:

```text
Amersfoort   415
Amsterdam    088
Barendrecht  274
Breda        403
Delft        151
Duiven       272
Eindhoven    087
Groningen    404
Haarlem      378
Heerlen      089
Hengelo      312
Utrecht      270
Zwolle       391
```

These are resolved automatically by the application and do not need to be placed in `products.yaml`.

IKEA Leeuwarden is classified as:

```text
PAOP
```

rather than:

```text
STORE
```

and is therefore excluded from normal Second Chance store scanning.

---

# Pushover Test

To test Pushover directly:

```powershell
python -c "import asyncio; from app.services.notifier import send_pushover_notification; asyncio.run(send_pushover_notification('PAX Scraper Test', 'Pushover notifications are working.'))"
```

---

# Docker

## Dockerfile

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

# Docker Compose

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

---

# Local `.env`

Example:

```env
PORT=8013
BIND_IP=0.0.0.0

PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token

PRICE_CHANGE_THRESHOLD_PERCENT=5
```

---

# Server `.env`

On the server, `BIND_IP` can be set to the Tailscale IP.

Example:

```env
PORT=8013
BIND_IP=100.x.x.x

PUSHOVER_USER_KEY=your_user_key
PUSHOVER_API_TOKEN=your_api_token

PRICE_CHANGE_THRESHOLD_PERCENT=5
```

This makes the dashboard accessible through Tailscale without exposing the service publicly.

---

# Docker Ignore

A typical `.dockerignore` should include:

```text
.venv
__pycache__
*.pyc
.git
.env
data
```

The `data` directory is mounted separately at runtime.

---

# Git Ignore

A typical `.gitignore` should include:

```text
.venv/
__pycache__/
*.pyc
.env
data/ikea.db
```

Do not commit:

```text
.env
```

because it contains Pushover secrets and deployment configuration.

---

# Home Server Deployment

The application runs on:

```text
~/Docker/paxscraper
```

on the home server.

Example SSH workflow:

```bash
ssh doerak@doerak-server
```

Then:

```bash
cd ~/Docker/paxscraper
```

---

# Initial Clone

```bash
cd ~/Docker

git clone https://github.com/snr2042954/PaxScraper.git paxscraper
```

---

# Updating the Server

Pull the latest code:

```bash
cd ~/Docker/paxscraper

git pull
```

A source-code update also requires rebuilding the Docker image.

The normal `up` helper only starts the existing image and does **not** rebuild it.

---

# Docker Helper Commands

The server uses helper scripts in:

```text
~/Docker/.commands
```

---

## `up`

The existing `up` script:

```bash
#!/bin/bash

for project in "$@"; do
  echo "Starting $project..."

  docker compose \
    --env-file ../.env \
    --env-file "../$project/.env" \
    -f "../$project/docker-compose.yml" \
    up -d
done
```

Use this when no source code changed:

```bash
cd ~/Docker/.commands

./up paxscraper
```

---

## `build`

For code updates, use:

```bash
#!/bin/bash

for project in "$@"; do

  echo "Building and starting $project..."

  docker compose \
    --env-file ../.env \
    --env-file "../$project/.env" \
    -f "../$project/docker-compose.yml" \
    up -d --build

done
```

Save as:

```text
~/Docker/.commands/build
```

Make executable:

```bash
chmod +x ~/Docker/.commands/build
```

Run:

```bash
cd ~/Docker/.commands

./build paxscraper
```

---

# Recommended Server Update Workflow

After pushing changes from the development machine:

```bash
cd ~/Docker/paxscraper

git pull

cd ../.commands

./build paxscraper
```

For a normal restart without code changes:

```bash
cd ~/Docker/.commands

./up paxscraper
```

---

# Docker Logs

View live logs:

```bash
docker logs -f paxscraper
```

View recent logs:

```bash
docker logs paxscraper
```

Successful startup should include something similar to:

```text
Scheduler started | normal prices every 6h | Second Chance every 1h

PAX Scraper started

Uvicorn running on http://0.0.0.0:8013
```

---

# Git Workflow

On the local development machine:

```powershell
git status
git add .
git commit -m "Update PAX scraper"
git push
```

Then on the server:

```bash
cd ~/Docker/paxscraper

git pull
```

and rebuild:

```bash
cd ~/Docker/.commands

./build paxscraper
```

---

# Server-Side Local Changes

If a server-side modification blocks `git pull`:

```bash
git stash
git pull
git stash pop
```

If the stashed server modification is no longer required:

```bash
git stash drop
```

To exit the Git pager:

```text
q
```

---

# Current Tracked Products

The project currently tracks 20 IKEA products.

```text
1. FIXA Boormal
   Article: 90323393
   Quantity: 1

2. PAX basiselement kledingkast
   Article: 20458205
   Quantity: 1

3. KOMPLEMENT zachtsluitende scharnier
   Article: 30214504
   Quantity: 3

4. FLISBERGET deur
   Article: 60344735
   Quantity: 3

5. KOMPLEMENT plank 100x58
   Article: 60509142
   Quantity: 2

6. KOMPLEMENT kledingroede 100
   Article: 80256940
   Quantity: 1

7. KOMPLEMENT uittrekbare spiegel
   Article: 50623874
   Quantity: 1

8. PAX middenelement
   Article: 30603829
   Quantity: 1

9. PAX basiselement kledingkast 50x58x236
   Article: 30458219
   Quantity: 1

10. KOMPLEMENT plank 50x58
    Article: 90509145
    Quantity: 4

11. KOMPLEMENT kledingroede 50
    Article: 40256942
    Quantity: 1

12. PAX eindelement
    Article: 70603851
    Quantity: 1

13. SKUBB opbergtas 90x53x19
    Article: 50591062
    Quantity: 1

14. SKUBB bak 31x55x33
    Article: 60290370
    Quantity: 2

15. SKUBB opbergtas 43x53x19
    Article: 60591052
    Quantity: 1

16. ÖVERSIDAN LED-strip 96 cm
    Article: 00589556
    Quantity: 1

17. ÖVERSIDAN LED-strip 46 cm
    Article: 30589098
    Quantity: 1

18. TRÅDFRI driver 10 W
    Article: 50356187
    Quantity: 1

19. FÖRNIMMA aansluitsnoer 3.5 m
    Article: 50446881
    Quantity: 1

20. ENERYDA handgreep 112 mm
    Article: 70347516
    Quantity: 2
```

---

# Current Observed Retail Prices

At the latest known successful scan:

```text
FIXA                         €1.49
PAX 20458205               €105.00
KOMPLEMENT hinges           €16.00
FLISBERGET                  €70.00
KOMPLEMENT shelf 100        €12.00
KOMPLEMENT rail 100         €10.00
KOMPLEMENT mirror           €40.00
PAX middle                 €120.00
PAX 30458219                €90.00
KOMPLEMENT shelf 50          €6.00
KOMPLEMENT rail 50           €5.00
PAX end                     €75.00
SKUBB bag                    €9.99
SKUBB box                   €17.99
SKUBB bag                    €6.99
ÖVERSIDAN 96                €29.99
ÖVERSIDAN 46                €19.99
TRÅDFRI                     €12.00
FÖRNIMMA                     €3.00
ENERYDA                     €11.00
```

These values are not hard-coded into the application and will change automatically when IKEA changes its retail prices.

---

# Favicon

The web app uses:

```text
app/static/favicon.png
```

and the dashboard references it using:

```html
<link
    rel="icon"
    type="image/png"
    href="/static/favicon.png"
>
```

---

# Notes

The normal retail scanner and the Second Chance scanner intentionally solve two different problems.

The retail scanner asks:

```text
Did IKEA change the normal price?
```

The Second Chance scanner asks:

```text
Is an item I need available cheaply somewhere right now?
```

Together they make it possible to gradually purchase a PAX wardrobe build when individual components become cheaper through either normal price changes or Second Chance inventory.

---

# License

Personal project.

No affiliation with IKEA.

IKEA product names, trademarks, URLs, and related data belong to IKEA and their respective owners.