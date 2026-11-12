#!/usr/bin/env python3
"""Static export of the MiniGT rare models price tracker.

The live site renders pages from the database (api/site.py). This writes the same pages as files,
for previews, diffs against the live site, or a fallback deploy.

  python src/build_site.py <data dir | --db> <photos dir> <output dir>

<data dir> holds cars/<CODE>.json; --db reads the cars from DATABASE_URL instead.
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render
from db import read_json_dir

SRC, PHOTOS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

if SRC == "--db":
    import db
    with db.connect() as conn:
        cars = db.load_cars(conn)
else:
    cars = read_json_dir(SRC)
cars, last_checked = render.prepare(cars)

def write(rel, text):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

os.makedirs(OUT, exist_ok=True)
for sub in ("cars", "photos"):
    shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
os.makedirs(os.path.join(OUT, "photos"))
write("site.css", render.CSS)

# photos: <CODE>.jpg or <code>.jpg in the photos dir; a car without one is shown without a photo
for c in cars:
    src = next((p for p in (os.path.join(PHOTOS, n + ".jpg") for n in (c["code"], render.slug(c["code"])))
                if os.path.exists(p)), None)
    if src: shutil.copy(src, os.path.join(OUT, "photos", render.slug(c["code"]) + ".jpg"))
    else: c.pop("photo", None)

for c in cars:
    write(os.path.join("cars", render.slug(c["code"]), "index.html"), render.car_page(c, last_checked))
write("index.html", render.index_page(cars, last_checked))
write("robots.txt", render.robots_txt())
write("sitemap.xml", render.sitemap_xml(cars, last_checked))
write("llms.txt", render.llms_txt(cars, last_checked))
if not os.path.exists(os.path.join(OUT, "favicon.svg")):  # keep the repo's own favicon
    write("favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#1b4f8a"/><text x="32" y="42" font-family="Arial,sans-serif" font-size="26" font-weight="700" fill="#fff" text-anchor="middle">GT</text></svg>')
print("built", len(cars), "cars ->", OUT)
