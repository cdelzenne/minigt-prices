# MiniGT rare models price tracker

Retail and resale prices for rare Mini GT 1:64 diecast models, in Hong Kong dollars, matched on the exact catalogue number.

Live site: https://minigt-prices.vercel.app

## What it shows
- **Retail:** the average price shops list for a new car, including sold-out listings (tagged "Sold out"). When no shop lists the exact code, the same car under another code is used and tagged "Close match".
- **Resale:** the range of secondary-market asking prices, mostly eBay and Carousell. Where none is verified, the page shows a "Contact us" button instead of a guess.
- One page per model, with every source linked, its status, the original price and currency, the FX rate used, and listings that were checked but not counted.

## How it works
- Prices are kept in a private tracker and refreshed weekly by an automated job.
- The job rebuilds the static site with `src/build_site.py`, commits it here and pushes to `main`.
- Vercel deploys every push to `main` as-is; there is no build step on Vercel.

## Layout
- `index.html`, `cars/<code>/`, `photos/`, `site.css`, `sitemap.xml`, `robots.txt`, `llms.txt`, `vercel.json`, `og.jpg`, `favicon.svg`: the built site.
- `src/build_site.py`: the generator.
- `src/site.css`: the stylesheet source, copied to the root on each build.

## Building locally
```
python3 src/build_site.py <data dir> <photos dir> <output dir>
```
- `<data dir>` holds `cars/<CODE>.json`, one file per model.
- `<photos dir>` holds `<CODE>.jpg`.
- To regenerate the site in place, use the repo root as the output dir.

## Matching rules
- Only the exact catalogue number counts, including its suffix (-L, -R, -BL, -MJ and so on).
- A "-CH" suffix is not treated as a chase; a car is a chase only when confirmed.
- Prices come only from pages that were actually opened. Any listing with an ambiguous currency is left out.

## Contact
minigt.prices@gmail.com

Not affiliated with Mini GT or TSM-Model. Some shop links are affiliate links.
