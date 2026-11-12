"""Serves the site's pages from the Postgres car database.

vercel.json rewrites /, /cars/<code>, /sitemap.xml and /llms.txt here as ?p=index|car|sitemap|llms.
Pages are cached at Vercel's edge for an hour, then served stale while one request refreshes them.
Without DATABASE_URL (local runs), cars are read from DATA_DIR (default: data/).
"""
import os, sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import render, db

CACHE = "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400"
TYPES = {"index": "text/html", "car": "text/html", "sitemap": "application/xml", "llms": "text/plain"}


def load_cars():
    if os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL"):
        with db.connect() as conn:
            return db.load_cars(conn)
    if os.environ.get("VERCEL"):  # deployed without a database: fail loudly, never serve an empty site
        raise RuntimeError("DATABASE_URL is not set")
    return db.read_json_dir(os.environ.get("DATA_DIR") or os.path.join(ROOT, "data"))


def respond(page, code):
    """(status, content type, body) for one request."""
    if page not in TYPES:
        return 404, "text/plain", "Not found\n"
    cars, last_checked = render.prepare(load_cars())
    if page == "index":
        return 200, TYPES[page], render.index_page(cars, last_checked)
    if page == "sitemap":
        return 200, TYPES[page], render.sitemap_xml(cars, last_checked)
    if page == "llms":
        return 200, TYPES[page], render.llms_txt(cars, last_checked)
    car = next((c for c in cars if render.slug(c["code"]) == (code or "").lower()), None)
    if not car:
        return 404, "text/plain", "Not found\n"
    return 200, TYPES[page], render.car_page(car, last_checked)


class handler(BaseHTTPRequestHandler):
    def _serve(self, head=False):
        q = parse_qs(urlparse(self.path).query)
        try:
            status, ctype, body = respond(q.get("p", [""])[0], q.get("code", [""])[0])
            cache = CACHE if status == 200 else "public, max-age=0, s-maxage=300"
        except Exception as ex:  # database unreachable etc.: never cache an error
            print("render failed:", repr(ex), file=sys.stderr)
            status, ctype, body, cache = 500, "text/plain", "Temporarily unavailable, please retry.\n", "no-store"
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def do_GET(self):
        self._serve()

    def do_HEAD(self):
        self._serve(head=True)
