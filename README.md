# MiniGT rare models price tracker

Retail and resale prices for rare Mini GT 1:64 diecast models, in Hong Kong dollars, matched on the exact catalogue number. SEO and GEO optimized.

Live site: https://minigt-prices.vercel.app

## What it shows
- **Retail:** the average price shops list for a new car, including sold-out listings (tagged "Sold out"). When no shop lists the exact code, the same car under another code is used and tagged "Close match".
- **Resale:** the range of secondary-market asking prices, mostly eBay and Carousell. Where none is verified, the page shows a "Contact us" button instead of a guess.
- One page per model, with every source linked, its status, the original price and currency, the FX rate used, and listings that were checked but not counted.

## How it works
- The listed cars live in a Postgres database (Neon, connected to the Vercel project as `DATABASE_URL`).
- `/`, `/cars/<code>`, `/sitemap.xml` and `/llms.txt` are rendered from the database by `api/site.py` and cached at Vercel's edge for an hour, so a database update shows on the site within the hour without a commit.
- Prices are refreshed weekly by an automated job, which writes each car to the database with `src/db.py import`.
- Photos, the stylesheet and the other static files are served from this repo as before.

## Database
Three tables: `cars` (one row per model: name, check date, resale range, notes, exchange rates, photo credit), `listings` (retail, close-match and resale rows, in display order) and `excluded_listings` (listings checked but not counted).

```
export DATABASE_URL=postgres://...
python3 src/db.py init                         # create the tables (safe to re-run)
python3 src/db.py import <data dir> --photos photos   # upsert every <data dir>/cars/<CODE>.json
python3 src/db.py export <data dir>            # dump the database back to JSON
```
- One JSON file per model, in the format of `data/cars/*.json`. Importing a car replaces all of its listings.
- `--prune` also deletes cars that are not in `<data dir>`.
- A new model also needs its photo committed to `photos/<code>.jpg`; a car whose photo is missing is stored without one.
- `data/` is the snapshot the database was seeded from (8 Nov 2026). The database, not `data/`, is what the site shows.

## Layout
- `api/site.py`: serves the pages from the database.
- `src/render.py`: the page templates, shared by the server and the static export.
- `src/db.py`: schema, import and export.
- `src/build_site.py`: static export of the whole site, from JSON or `--db`, for previews and diffs.
- `src/site.css`: the stylesheet source; keep `site.css` at the root identical to it.
- `photos/`, `site.css`, `robots.txt`, `og.jpg`, `favicon.svg`, `vercel.json`: static files.

## Running locally
```
pip install -r requirements.txt
python3 src/build_site.py data photos <output dir>     # static export from JSON
python3 src/build_site.py --db photos <output dir>     # static export from the database
```
- `<photos dir>` holds `<CODE>.jpg` or `<code>.jpg`.

## Matching rules
- Only the exact catalogue number counts, including its suffix (-L, -R, -BL, -MJ and so on).
- A "-CH" suffix is not treated as a chase; a car is a chase only when confirmed.
- Prices come only from pages that were actually opened. Any listing with an ambiguous currency is left out.

## Contact
minigt.prices@gmail.com

Not affiliated with Mini GT or TSM-Model. Some shop links are affiliate links.
