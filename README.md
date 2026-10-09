# MiniGT rare models price tracker

Static site live at https://minigt-prices.vercel.app — retail and resale prices (HKD, with original currency) for rare Mini GT 1:64 models.

## Layout
- `index.html`, `cars/`, `photos/`, `site.css`, `sitemap.xml`, `robots.txt`, `llms.txt`, `vercel.json` — the built site, deployed as-is to Vercel (no build step).
- `src/build_site.py` — generator: `python3 src/build_site.py <datadir with cars/*.json> <photosdir> <outdir>`
- `src/site.css` — stylesheet source.

Prices are refreshed weekly. Contact: minigt.prices@gmail.com
