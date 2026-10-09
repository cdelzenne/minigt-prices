#!/usr/bin/env python3
"""Build the public static site for the MiniGT rare models price tracker."""
import json, glob, os, shutil, html, re, sys, datetime

SRC = sys.argv[1]          # dir with cars/*.json
PHOTOS = sys.argv[2]       # dir with <code>.jpg
OUT = sys.argv[3]
BASE = "https://minigt-prices.vercel.app"
SITE = "MiniGT rare models price tracker"
TODAY = datetime.date.today().isoformat()

SOLD = re.compile(r"sold out|discontinued|no longer|out of stock", re.I)
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
def fmt(n): return "HK$" + f"{n:,.2f}"
def slug(code): return code.lower()
def safe_url(u):
    u = str(u or "")
    return u if u.startswith("https://") or u.startswith("http://") else ""

cars = [json.load(open(f)) for f in glob.glob(os.path.join(SRC, "cars", "*.json"))]
cars = [c for c in cars if c.get("code")]
cars.sort(key=lambda c: c["code"])
last_checked = max((c.get("checkedAt") or "") for c in cars)

def retail_info(c):
    rows = [r for r in (c.get("retail") or []) if isinstance(r.get("hkd"), (int, float))]
    close = False
    if not rows:
        rows = [r for r in (c.get("retailClose") or []) if isinstance(r.get("hkd"), (int, float))]
        close = True
    if not rows:
        return None
    vals = [r["hkd"] for r in rows]
    sold = sum(1 for r in rows if SOLD.search(r.get("status") or ""))
    return dict(avg=sum(vals)/len(vals), low=min(vals), high=max(vals), n=len(rows),
                sold=sold, all_sold=(sold == len(rows)), close=close, rows=rows)

def resale_info(c):
    r = c.get("resaleRange")
    if not r or r.get("low") is None: return None
    return r

def retail_html(ri):
    if not ri: return '<span class="q">No price found</span>'
    tags = ('<span class="tag close">Close match</span>' if ri["close"] else "") + \
           ('<span class="tag sold">Sold out</span>' if ri["all_sold"] else "")
    lbl = "1 listing" if ri["n"] == 1 else f"avg of {ri['n']}"
    if not ri["all_sold"] and ri["sold"]: lbl += f" · {ri['sold']} sold out"
    return f'{fmt(ri["avg"])}<small>{tags}{e(lbl)}</small>'

def resale_html(r):
    if not r: return '<button type="button" class="contact" data-u="minigt.prices" data-d="gmail.com" aria-label="Contact us about this model">Contact us</button>'
    a, b = r["low"], r["high"]
    txt = fmt(a) if a == b else f"{fmt(a)}–{fmt(b)[3:]}"
    return f'{txt}<small>{e(r.get("label",""))}</small>'

def pill(s):
    t = (s or "").lower()
    if re.search(r"in stock|available|active", t) and not re.search(r"no longer|not ", t): cls = "ok"
    elif SOLD.search(t): cls = "warn"
    else: cls = "na"
    return f'<span class="pill {cls}">{e(s or "unknown")}</span>'

def src_table(rows):
    if not rows: return ""
    body = "".join(
        f'<tr><td data-l="Source">{e(r.get("shop"))}</td><td data-l="Listed" class="num">{e(r.get("price"))}</td>'
        f'<td data-l="HKD" class="num">{fmt(r["hkd"]) if isinstance(r.get("hkd"),(int,float)) else "–"}</td>'
        f'<td data-l="Status">{pill(r.get("status"))}</td>'
        f'<td data-l="Page"><a href="{e(safe_url(r.get("url")))}" rel="sponsored nofollow noopener" target="_blank">Open</a></td></tr>'
        for r in rows)
    return ('<div class="tbl"><table><thead><tr><th>Source</th><th>Listed price</th><th>HKD</th><th>Status</th><th>Page</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')

def summary_sentence(c, ri, rr):
    parts = [f'Mini GT {c["code"]} ({c["name"]}).']
    if ri:
        s = f'Average new retail price: {fmt(ri["avg"])}'
        s += f' across {ri["n"]} listing{"s" if ri["n"]>1 else ""}'
        if ri["close"]: s += ' (close match: same car under another catalogue code)'
        if ri["all_sold"]: s += ', all sold out'
        elif ri["sold"]: s += f', {ri["sold"]} sold out'
        parts.append(s + '.')
    else:
        parts.append('No verified retail price found.')
    if rr:
        a, b = rr["low"], rr["high"]
        parts.append(f'Resale (secondary market): {fmt(a) if a==b else fmt(a)+" to "+fmt(b)}' + (f' ({rr.get("label")})' if rr.get("label") else '') + '.')
    else:
        parts.append('No verified resale price yet.')
    parts.append(f'Prices checked {c.get("checkedAt","")}, converted to Hong Kong dollars at mid-market rates.')
    return " ".join(parts)

CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "site.css")).read()
import hashlib
CSS_V = hashlib.sha1(CSS.encode()).hexdigest()[:8]

def page(title, desc, path, body, jsonld, extra_head=""):
    url = BASE + path
    og_img = BASE + "/og.jpg"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="google-site-verification" content="fgTgTtd_iNLTWhihRsDFBA1sd7TtOeHNQjv8iqqsw5c">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
{extra_head}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/site.css?v={CSS_V}">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<div class="wrap">
{body}
<footer>
<p>Prices are collected from public shop and marketplace pages and converted to HKD at the mid-market rate on the check date; the original price is shown beside each conversion. Listings are matched on the exact Mini GT catalogue number. Other versions of the same car (box or blister, left- or right-hand drive, chase or regular) are not counted, except where a car is marked "Close match". Product photos belong to the shops credited under each photo. This site is independent and not affiliated with Mini GT or TSM-Model.</p>
<p><strong>Affiliate disclosure:</strong> some links to shops and marketplaces are affiliate links. If you buy after clicking one, this site may earn a small commission at no extra cost to you. Commissions never affect which listings are counted or how prices are shown.</p>
<p>Last updated {e(last_checked)}. <a href="/">All models</a> · <a href="/#method">How prices are collected</a></p>
</footer>
</div>
<script>
document.addEventListener('click',function(ev){{var b=ev.target.closest&&ev.target.closest('button.contact');if(!b)return;ev.preventDefault();ev.stopPropagation();
var m=b.getAttribute('data-u')+'@'+b.getAttribute('data-d');var w=document.createElement('span');w.className='contact-shown';
var a=document.createElement('a');a.href='mailto:'+m;a.textContent=m;w.appendChild(a);b.replaceWith(w);}});
</script>
<script type="text/javascript" src="https://s.skimresources.com/js/310746X1799231.skimlinks.js"></script>
</body>
</html>
'''

def product_ld(c, ri, rr, url):
    d = {"@type": "Product", "name": f'Mini GT {c["code"]} {c["name"]} 1:64 diecast model',
         "sku": c["code"], "mpn": c["code"], "brand": {"@type": "Brand", "name": "Mini GT"},
         "category": "Diecast model cars > 1:64 scale", "url": url,
         "description": summary_sentence(c, ri, rr)}
    if c.get("photo"): d["image"] = BASE + f'/photos/{slug(c["code"])}.jpg'
    if ri and not ri["close"]:
        d["offers"] = {"@type": "AggregateOffer", "priceCurrency": "HKD",
                       "lowPrice": round(ri["low"], 2), "highPrice": round(ri["high"], 2),
                       "offerCount": ri["n"], "availability":
                       "https://schema.org/OutOfStock" if ri["all_sold"] else "https://schema.org/InStock"}
    return d

os.makedirs(OUT, exist_ok=True)
for sub in ("cars", "photos"):
    shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)
os.makedirs(os.path.join(OUT, "photos"))
open(os.path.join(OUT, "site.css"), "w").write(CSS)

# photos
for c in cars:
    src = os.path.join(PHOTOS, c["code"] + ".jpg")
    if os.path.exists(src): shutil.copy(src, os.path.join(OUT, "photos", slug(c["code"]) + ".jpg"))
    else: c.pop("photo", None)

def photo_tag(c, cls, w, h, lazy=True):
    if not c.get("photo"): return f'<span class="{cls} ph" aria-hidden="true"></span>'
    alt = f'Mini GT {c["code"]} {c["name"]}' + (" box and model" if c["photo"].get("isBox") else " model car")
    return (f'<img class="{cls}" src="/photos/{slug(c["code"])}.jpg" alt="{e(alt)}" width="{w}" height="{h}"'
            f'{" loading=\"lazy\"" if lazy else ""} decoding="async">')

# ---------- car pages ----------
for c in cars:
    ri, rr = retail_info(c), resale_info(c)
    path = f'/cars/{slug(c["code"])}'
    url = BASE + path
    title = f'Mini GT {c["code"]} price: {c["name"]} | {SITE}'
    if len(title) > 110: title = f'Mini GT {c["code"]} price | {SITE}'
    full = summary_sentence(c, ri, rr)
    desc = full if len(full) <= 300 else full[:297].rsplit(" ",1)[0] + "…"
    retail_block = ""
    if c.get("retail"):
        retail_block = src_table(c["retail"])
    elif c.get("retailClose"):
        retail_block = ('<p class="note"><span class="tag close">Close match</span>No shop lists this exact code. '
                        'The average uses the same car under other catalogue codes:</p>' + src_table(c["retailClose"]))
    else:
        retail_block = '<p class="note">No verified retail listing found.</p>'
    resale_block = src_table(c.get("resale")) if c.get("resale") else '<p class="note">No verified resale price yet. Have one, or want to buy or sell this model?</p><p><button type="button" class="contact" data-u="minigt.prices" data-d="gmail.com" aria-label="Contact us about this model">Contact us</button></p>'
    if c.get("resaleNote"): resale_block += f'<p class="note">{e(c["resaleNote"])}</p>'
    excl = ""
    if c.get("excluded"):
        excl = '<section><h2 class="h3">Listings not counted</h2><ul class="ex">' + "".join(
            f'<li>{"<a href=%s rel=%s target=_blank>%s</a>" % (chr(34)+e(safe_url(x.get("url")))+chr(34), chr(34)+"sponsored nofollow noopener"+chr(34), e(x.get("label"))) if x.get("url") else e(x.get("label"))}: {e(x.get("reason"))}</li>'
            for x in c["excluded"]) + "</ul></section>"
    fig = ""
    if c.get("photo"):
        p = c["photo"]
        credit = f' · Photo: <a href="{e(safe_url(p.get("sourceUrl")))}" rel="nofollow noopener" target="_blank">{e(p.get("source","source"))}</a>' if p.get("sourceUrl") else ""
        fig = f'<figure class="hero">{photo_tag(c,"big",800,600,lazy=False)}<figcaption>{e(p.get("caption",""))}{credit}</figcaption></figure>'
    body = f'''<nav class="crumbs" aria-label="Breadcrumb"><a href="/">All models</a> › <span>{e(c["code"])}</span></nav>
<header class="carhead">
  <div class="eyebrow">Mini GT · 1:64 · {e(c["code"])}</div>
  <h1>{e(c["name"])}</h1>
  <p class="lede">{e(full)}</p>
</header>
<div class="facts">
  <div><span class="k">Retail (new, HKD)</span><span class="v">{retail_html(ri)}</span></div>
  <div><span class="k">Resale (HKD)</span><span class="v">{resale_html(rr)}</span></div>
  <div><span class="k">Catalogue number</span><span class="v mono">{e(c["code"])}</span></div>
  <div><span class="k">Checked</span><span class="v mono">{e(c.get("checkedAt",""))}</span></div>
</div>
<div class="cargrid">
  {fig}
  <section class="minw"><h2 class="h3">Retail price · new</h2>{retail_block}</section>
</div>
<section><h2 class="h3">Resale price · secondary market</h2>{resale_block}</section>
{excl}
{f'<p class="note">{e(c["notes"])}</p>' if c.get("notes") else ""}
<p class="note">Exchange rates: {e(c.get("fx","not needed (prices already in HKD)"))}</p>'''
    ld = {"@context": "https://schema.org", "@graph": [
        product_ld(c, ri, rr, url),
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "All models", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": c["code"], "item": url}]}]}
    og = f'<meta property="og:image" content="{BASE}/photos/{slug(c["code"])}.jpg">' if c.get("photo") else ""
    d = os.path.join(OUT, "cars", slug(c["code"]))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(page(title, desc, path, body, ld, og))

# ---------- index ----------
rows = []
for c in cars:
    ri, rr = retail_info(c), resale_info(c)
    search = " ".join([c["code"], c["code"].replace("MGT0", "").lstrip("0"), c["name"]]).lower()
    rows.append(f'''<div class="row" data-s="{e(search)}">
  {photo_tag(c,"thumb",96,72)}
  <span class="car"><a class="rowlink" href="/cars/{slug(c["code"])}"><span class="code">{e(c["code"])}</span><span class="name">{e(c["name"])}</span></a></span>
  <span class="price rp"><span class="plabel">Retail</span>{retail_html(ri)}</span>
  <span class="price sp"><span class="plabel">Resale</span>{resale_html(rr)}</span>
  <span class="chev" aria-hidden="true">›</span>
</div>''')

faq = [
 ("How are Mini GT prices collected?", "Each model is searched by its exact Mini GT catalogue number (for example MGT00499-L) across shop and marketplace pages. Only pages that were opened and checked are counted, and every source is linked on the model's page."),
 ("What does \"Close match\" mean?", "When no shop lists the exact catalogue number, the retail figure uses the same car sold under another code, such as the boxed, blister or other-hand-drive version. It is labelled \"Close match\" so it isn't mistaken for an exact price."),
 ("Why is a retail price shown for a sold-out model?", "The retail figure is the average listed price for a new car, even when every shop is sold out, so you can see what it originally cost. Sold-out listings are tagged \"Sold out\"."),
 ("What do the suffixes -L, -R, -BL, -MJ and -CH mean?", "They distinguish versions of the same Mini GT model: -L is left-hand drive and -R right-hand drive, -BL is a blister pack, and -MJ is a MiJo Exclusives (USA) release. -CH appears as a regular retail code at some shops; it does not mean chase. Chase cars are only marked as such when confirmed."),
 ("Which currency are prices in?", "All prices are shown in Hong Kong dollars (HKD), converted at the mid-market rate on the day they were checked. The original price and currency are shown next to each conversion."),
]
faq_html = "".join(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)

n_exact = sum(1 for c in cars if retail_info(c) and not retail_info(c)["close"])
intro = (f"Current retail and resale prices for {len(cars)} rare Mini GT 1:64 diecast models, matched on the exact "
         f"catalogue number and shown in Hong Kong dollars. Last updated {last_checked}.")
body = f'''<header>
  <div class="eyebrow">Mini GT · 1:64 · price watch</div>
  <h1>{e(SITE)}</h1>
  <p class="lede">{e(intro)} Retail shows the average listed price for a new car, even when sold out; "Close match" means the figure comes from the same car under another code.</p>
</header>
<div class="searchbar">
  <label for="q">Search models</label>
  <input id="q" type="search" placeholder="Code, make or race (e.g. 1052, Porsche)" autocomplete="off">
  <span id="hits" class="hits" aria-live="polite"></span>
  <span class="submit-model">Model not listed? Submit your model number <button type="button" class="contact" data-u="minigt.prices" data-d="gmail.com" aria-label="Submit a model number by email">Submit</button></span>
</div>
<section class="ledger" aria-label="Mini GT models and prices">
  <div class="row head" aria-hidden="true"><span></span><span>Model</span><span>Retail (HKD)</span><span>Resale (HKD)</span><span></span></div>
  {"".join(rows)}
  <p id="nomatch" class="empty" hidden>No model matches that search.</p>
</section>
<section id="method" class="prose">
  <h2>How prices are collected</h2>
  <p>Every model is tracked by its full Mini GT catalogue number, including the suffix that identifies the version (left- or right-hand drive, box or blister, regional exclusive). A price is counted only when the shop or marketplace page shows that exact code, and every source is linked on the model's page with its status (in stock, sold out or discontinued).</p>
  <p><strong>Retail</strong> is the average price listed by shops for a new car. <strong>Resale</strong> is the range of secondary-market listings, usually eBay; these are asking prices unless stated otherwise. Where no verified price exists, the site says so instead of estimating.</p>
  <h2>Frequently asked questions</h2>
  {faq_html}
</section>
<script>
(function(){{var q=document.getElementById('q'),rows=[].slice.call(document.querySelectorAll('.ledger .row[data-s]')),h=document.getElementById('hits'),nm=document.getElementById('nomatch');
function n(s){{return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}}
q.addEventListener('input',function(){{var t=n(q.value).split(/\\s+/).filter(Boolean),k=0;rows.forEach(function(r){{var s=n(r.getAttribute('data-s')),ok=t.every(function(x){{return s.indexOf(x)>-1}});r.hidden=!ok;if(ok)k++}});h.textContent=t.length?k+' of '+rows.length+' shown':'';nm.hidden=k>0}});}})();
</script>'''

ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "WebSite", "name": SITE, "url": BASE + "/", "inLanguage": "en"},
    {"@type": "ItemList", "name": "Mini GT rare models and prices (HKD)", "numberOfItems": len(cars),
     "itemListElement": [{"@type": "ListItem", "position": i+1, "url": BASE + f'/cars/{slug(c["code"])}',
                          "name": f'Mini GT {c["code"]} {c["name"]}'} for i, c in enumerate(cars)]},
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q,
       "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
desc = f"Retail and resale prices in HKD for {len(cars)} rare Mini GT 1:64 models, matched on exact catalogue numbers, with sources, photos and sold-out status. Updated {last_checked}."
first_photo = next((c for c in cars if c.get("photo")), None)
og = f'<meta property="og:image" content="{BASE}/og.jpg">'
open(os.path.join(OUT, "index.html"), "w").write(page(f"{SITE}: Mini GT 1:64 retail and resale prices (HKD)", desc, "/", body, ld, og))

# ---------- crawl files ----------
open(os.path.join(OUT, "robots.txt"), "w").write(
    "User-agent: *\nAllow: /\n\n"
    "# AI search and assistant crawlers are welcome\n"
    + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in ["GPTBot","OAI-SearchBot","ChatGPT-User","ClaudeBot","Claude-SearchBot","Claude-User","PerplexityBot","Google-Extended","Applebot-Extended","Bingbot"])
    + f"Sitemap: {BASE}/sitemap.xml\n")
urls = [("/", last_checked)] + [(f'/cars/{slug(c["code"])}', c.get("checkedAt") or last_checked) for c in cars]
open(os.path.join(OUT, "sitemap.xml"), "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "".join(f"  <url><loc>{BASE}{p}</loc><lastmod>{d}</lastmod></url>\n" for p, d in urls) + "</urlset>\n")
llms = [f"# {SITE}", "", f"> Retail and resale prices in Hong Kong dollars (HKD) for {len(cars)} rare Mini GT 1:64 diecast models, matched on exact catalogue numbers. Last updated {last_checked}.", "",
        "Retail = average listed price for a new car (sold-out listings included and flagged). \"Close match\" = same car under another catalogue code because no shop lists the exact code. Resale = secondary-market range, usually eBay asking prices. Sources are linked on each model page.", "", "## Models", ""]
for c in cars:
    ri, rr = retail_info(c), resale_info(c)
    r1 = (f'retail avg {fmt(ri["avg"])}' + (" (close match)" if ri["close"] else "") + (" (sold out)" if ri["all_sold"] else "")) if ri else "retail: no verified price"
    r2 = (f'resale {fmt(rr["low"])}' + (f'–{fmt(rr["high"])}' if rr["high"] != rr["low"] else "")) if rr else "resale: not yet known"
    llms.append(f'- [{c["code"]} {c["name"]}]({BASE}/cars/{slug(c["code"])}): {r1}; {r2}; checked {c.get("checkedAt","")}')
llms += ["", "## About", "", f"- [How prices are collected]({BASE}/#method)"]
open(os.path.join(OUT, "llms.txt"), "w").write("\n".join(llms) + "\n")
open(os.path.join(OUT, "favicon.svg"), "w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#1b4f8a"/><text x="32" y="42" font-family="Arial,sans-serif" font-size="26" font-weight="700" fill="#fff" text-anchor="middle">GT</text></svg>')
open(os.path.join(OUT, "vercel.json"), "w").write(json.dumps({
    "cleanUrls": True, "trailingSlash": False,
    "headers": [{"source": "/photos/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=604800"}]},
                {"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"}]}]}, indent=2))
print("built", len(cars), "cars ->", OUT)
