#!/usr/bin/env python3
"""Postgres storage for the car data.

Library: load_cars(conn) returns cars in the cars/<CODE>.json format that render.py takes.
CLI (needs DATABASE_URL):
  python src/db.py init                                   create the tables (safe to re-run)
  python src/db.py import <data dir> [--photos DIR] [--prune]
        upsert every <data dir>/cars/*.json; with --photos, a car whose <CODE>.jpg is missing
        there is stored without a photo; --prune deletes cars that are not in <data dir>
  python src/db.py export <data dir>                      write the database back out as JSON
"""
import glob, json, os, sys
from decimal import Decimal

SCHEMA = """
CREATE TABLE IF NOT EXISTS cars (
  code              text PRIMARY KEY,
  name              text NOT NULL,
  checked_at        text,
  fx                text,
  notes             text,
  resale_note       text,
  resale_low        numeric,
  resale_high       numeric,
  resale_label      text,
  has_photo         boolean NOT NULL DEFAULT false,
  photo_caption     text,
  photo_source      text,
  photo_source_url  text,
  photo_is_box      boolean NOT NULL DEFAULT false,
  updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS listings (
  id        bigserial PRIMARY KEY,
  car_code  text NOT NULL REFERENCES cars(code) ON DELETE CASCADE ON UPDATE CASCADE,
  kind      text NOT NULL CHECK (kind IN ('retail', 'retail_close', 'resale')),
  position  int  NOT NULL,
  shop      text,
  price     text,
  hkd       numeric,
  status    text,
  url       text,
  UNIQUE (car_code, kind, position)
);
CREATE TABLE IF NOT EXISTS excluded_listings (
  id        bigserial PRIMARY KEY,
  car_code  text NOT NULL REFERENCES cars(code) ON DELETE CASCADE ON UPDATE CASCADE,
  position  int  NOT NULL,
  label     text,
  url       text,
  reason    text,
  UNIQUE (car_code, position)
);
"""

KINDS = {"retail": "retail", "retailClose": "retail_close", "resale": "resale"}


def _load_dotenv():
    """Local runs: read DATABASE_URL from the repo's .env (gitignored) when it isn't in the environment."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.environ.get("DATABASE_URL") or not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            k, sep, v = line.strip().partition("=")
            if sep and k.strip() in ("DATABASE_URL", "POSTGRES_URL") and not os.environ.get(k.strip()):
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def connect():
    import psycopg
    _load_dotenv()
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url, autocommit=False)


def _num(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() and "." not in str(v) else float(v)
    return v


def _put(d, k, v):
    if v is not None:
        d[k] = v


def load_cars(conn, code=None):
    """All cars (or the one whose code matches case-insensitively) in the JSON format render.py uses."""
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        where, args = ("WHERE lower(code) = lower(%s)", [code]) if code else ("", [])
        cur.execute(f"SELECT * FROM cars {where} ORDER BY code", args)
        cars = {}
        for r in cur.fetchall():
            c = {"code": r["code"], "name": r["name"]}
            _put(c, "checkedAt", r["checked_at"])
            if r["has_photo"]:
                p = {"isBox": r["photo_is_box"]}
                _put(p, "caption", r["photo_caption"])
                _put(p, "source", r["photo_source"])
                _put(p, "sourceUrl", r["photo_source_url"])
                c["photo"] = p
            if r["resale_low"] is not None:
                c["resaleRange"] = {"low": _num(r["resale_low"]), "high": _num(r["resale_high"]),
                                    "label": r["resale_label"] or ""}
            _put(c, "resaleNote", r["resale_note"])
            _put(c, "notes", r["notes"])
            _put(c, "fx", r["fx"])
            cars[r["code"]] = c
        if not cars:
            return []
        codes = list(cars)
        cur.execute("SELECT * FROM listings WHERE car_code = ANY(%s) ORDER BY car_code, kind, position", [codes])
        back = {v: k for k, v in KINDS.items()}
        for r in cur.fetchall():
            cars[r["car_code"]].setdefault(back[r["kind"]], []).append({
                "shop": r["shop"], "price": r["price"], "hkd": _num(r["hkd"]),
                "status": r["status"], "url": r["url"]})
        cur.execute("SELECT * FROM excluded_listings WHERE car_code = ANY(%s) ORDER BY car_code, position", [codes])
        for r in cur.fetchall():
            x = {"label": r["label"]}
            _put(x, "url", r["url"])
            x["reason"] = r["reason"]
            cars[r["car_code"]].setdefault("excluded", []).append(x)
    return list(cars.values())


def upsert_car(cur, c):
    p = c.get("photo") or None
    rr = c.get("resaleRange") or {}
    cur.execute("""
      INSERT INTO cars (code, name, checked_at, fx, notes, resale_note, resale_low, resale_high, resale_label,
                        has_photo, photo_caption, photo_source, photo_source_url, photo_is_box, updated_at)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
      ON CONFLICT (code) DO UPDATE SET
        name=EXCLUDED.name, checked_at=EXCLUDED.checked_at, fx=EXCLUDED.fx, notes=EXCLUDED.notes,
        resale_note=EXCLUDED.resale_note, resale_low=EXCLUDED.resale_low, resale_high=EXCLUDED.resale_high,
        resale_label=EXCLUDED.resale_label, has_photo=EXCLUDED.has_photo, photo_caption=EXCLUDED.photo_caption,
        photo_source=EXCLUDED.photo_source, photo_source_url=EXCLUDED.photo_source_url,
        photo_is_box=EXCLUDED.photo_is_box, updated_at=now()""",
        [c["code"], c["name"], c.get("checkedAt"), c.get("fx"), c.get("notes"), c.get("resaleNote"),
         rr.get("low"), rr.get("high"), rr.get("label"),
         p is not None, (p or {}).get("caption"), (p or {}).get("source"), (p or {}).get("sourceUrl"),
         bool((p or {}).get("isBox"))])
    cur.execute("DELETE FROM listings WHERE car_code = %s", [c["code"]])
    cur.execute("DELETE FROM excluded_listings WHERE car_code = %s", [c["code"]])
    for key, kind in KINDS.items():
        for i, r in enumerate(c.get(key) or []):
            hkd = r.get("hkd") if isinstance(r.get("hkd"), (int, float)) else None
            cur.execute("INSERT INTO listings (car_code, kind, position, shop, price, hkd, status, url) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        [c["code"], kind, i, r.get("shop"), r.get("price"), hkd, r.get("status"), r.get("url")])
    for i, x in enumerate(c.get("excluded") or []):
        cur.execute("INSERT INTO excluded_listings (car_code, position, label, url, reason) VALUES (%s,%s,%s,%s,%s)",
                    [c["code"], i, x.get("label"), x.get("url"), x.get("reason")])


def read_json_dir(src):
    cars = []
    for f in sorted(glob.glob(os.path.join(src, "cars", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            c = json.load(fh)
        if c.get("code"):
            cars.append(c)
    return cars


def main(argv):
    if not argv or argv[0] not in ("init", "import", "export"):
        print(__doc__); return 2
    cmd = argv[0]
    with connect() as conn:
        if cmd == "init":
            conn.execute(SCHEMA)
            print("schema ready")
        elif cmd == "import":
            src = argv[1]
            photos = argv[argv.index("--photos") + 1] if "--photos" in argv else None
            cars = read_json_dir(src)
            if not cars:
                raise SystemExit(f"no cars/*.json in {src}; nothing imported")
            with conn.cursor() as cur:
                for c in cars:
                    if photos and not any(os.path.exists(os.path.join(photos, n + ".jpg"))
                                          for n in (c["code"], c["code"].lower())):
                        c.pop("photo", None)
                        print(f"warning: no photo for {c['code']}, stored without one")
                    upsert_car(cur, c)
                if "--prune" in argv:
                    cur.execute("DELETE FROM cars WHERE NOT (code = ANY(%s)) RETURNING code", [[c["code"] for c in cars]])
                    for (code,) in cur.fetchall():
                        print("removed", code)
            print("imported", len(cars), "cars")
        elif cmd == "export":
            out = os.path.join(argv[1], "cars")
            os.makedirs(out, exist_ok=True)
            cars = load_cars(conn)
            for c in cars:
                with open(os.path.join(out, c["code"] + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(c, fh, ensure_ascii=False, indent=2); fh.write("\n")
            print("exported", len(cars), "cars ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
