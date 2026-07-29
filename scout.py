#!/usr/bin/env python3
"""
Opportunity Scout engine.

Does the mechanical work so the Claude Code Chair can focus on ranking judgement:
  - loads sources.yaml / network.yaml / config.yaml
  - fetches web sources and runs OpenAlex lab/researcher discovery
  - normalises to candidate records, dedups against context/seen.json
  - pushes a digest to Telegram (or writes to output/ if unconfigured)
  - reads Telegram replies to move greenlit items into approved_queue.json

This is a scaffold: the per-source parsers are deliberately generic. Tighten a
parser when you see a source you care about returning junk. No API keys needed.
"""
from __future__ import annotations
import argparse, json, os, sys, time, datetime as dt, urllib.parse, urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

ROOT = Path(__file__).parent
CTX = ROOT / "context"
OUT = ROOT / "output"
CTX.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)

def load_yaml(name):
    with open(ROOT / name) as f:
        return yaml.safe_load(f)

def http_get(url, accept="application/json", timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": "opportunity-scout/1.0 (mailto:you@example.com)",
        "Accept": accept,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

# ---------------------------------------------------------------------------
# Dedup store
# ---------------------------------------------------------------------------
def load_seen(cfg):
    p = ROOT / cfg["dedup"]["store"]
    if p.exists():
        return json.loads(p.read_text())
    return {}

def save_seen(cfg, seen):
    (ROOT / cfg["dedup"]["store"]).write_text(json.dumps(seen, indent=2))

def is_fresh(seen, key, suppress_days):
    if key not in seen:
        return True
    last = dt.date.fromisoformat(seen[key])
    return (dt.date.today() - last).days >= suppress_days

# ---------------------------------------------------------------------------
# OpenAlex lab / researcher discovery  (no key required)
# ---------------------------------------------------------------------------
def discover_labs(profile, per_keyword=8):
    """Find recent authors publishing on the profile's keywords."""
    out = []
    since = (dt.date.today() - dt.timedelta(days=365 * 2)).isoformat()
    for kw in profile.get("keywords_openalex", []):
        q = urllib.parse.quote(kw)
        url = (f"https://api.openalex.org/works?search={q}"
               f"&filter=from_publication_date:{since}"
               f"&sort=cited_by_count:desc&per-page={per_keyword}")
        try:
            data = json.loads(http_get(url))
        except Exception as e:
            print(f"  [openalex] {kw}: {e}", file=sys.stderr)
            continue
        for w in data.get("results", []):
            for a in w.get("authorships", [])[:2]:  # lead / senior
                author = a.get("author", {})
                inst = (a.get("institutions") or [{}])[0]
                out.append({
                    "id": f"person::{author.get('id','')}",
                    "kind": "person",
                    "title": author.get("display_name", "Unknown"),
                    "source": "OpenAlex",
                    "url": author.get("id", ""),
                    "deadline": None,
                    "eligibility_notes": "",
                    "why_it_fits": f"Recent work on '{kw}': {w.get('title','')[:120]}",
                    "tags": [kw],
                    "institution": inst.get("display_name", ""),
                })
    return out

def attach_warm_ties(people, network):
    """Match discovered people to warm connections in network.yaml (name substring)."""
    conns = {c["target"].lower(): c for c in network.get("connections", [])}
    for p in people:
        p["warm_tie"] = None
        name = p["title"].lower()
        for target, c in conns.items():
            if target in name or name in target:
                p["warm_tie"] = {
                    "connection": c.get("connection", ""),
                    "usable_as": c.get("usable_as", "none"),
                    "confirm_with": c.get("confirm_with", ""),
                    "status": c.get("status", "cold"),
                }
    return people

# ---------------------------------------------------------------------------
# Generic source fetch  (portals/aggregators return HTML the Chair reads;
# here we just confirm reachability + capture the page for the Chair to parse)
# ---------------------------------------------------------------------------
def fetch_source(src):
    """Return a lightweight candidate stub per source. The Chair (Claude) does
    the real content extraction from the fetched page; this proves reachability
    and hands back the URL + any obvious deadline text it can cheaply spot."""
    stub = {
        "id": f"source::{src['name']}",
        "kind": "grant",
        "title": src["name"],
        "source": src["name"],
        "url": src["url"],
        "deadline": None,
        "eligibility_notes": src.get("notes", ""),
        "why_it_fits": "",
        "tags": src.get("tags", []),
        "warm_tie": None,
        "reachable": False,
    }
    try:
        body = http_get(src["url"], accept="text/html")
        stub["reachable"] = True
        stub["_page_excerpt"] = body[:4000]  # Chair parses this for calls/deadlines
    except Exception as e:
        stub["eligibility_notes"] += f"  [UNREACHABLE: {e}]"
    return stub

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def tg_send(cfg, text):
    token = os.environ.get(cfg["telegram"]["bot_token_env"])
    chat = os.environ.get(cfg["telegram"]["chat_id_env"])
    if not (token and chat):
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "parse_mode": "Markdown",
        "disable_web_page_preview": "false",
    }).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=20)
        return True
    except Exception as e:
        print(f"  [telegram] {e}", file=sys.stderr)
        return False

def render_digest(items, mode):
    today = dt.date.today().isoformat()
    lines = [f"# Opportunity Scout — {mode} — {today}", ""]
    for i, it in enumerate(items, 1):
        flag = "⏰ " if it.get("deadline") else ""
        lines.append(f"**{i}. {flag}{it['title']}**  _({it['kind']})_")
        if it.get("why_it_fits"): lines.append(f"   ↳ {it['why_it_fits']}")
        if it.get("deadline"):    lines.append(f"   ⏳ deadline: {it['deadline']}")
        if it.get("eligibility_notes"): lines.append(f"   ⚠️ {it['eligibility_notes']}")
        if it.get("warm_tie"):
            wt = it["warm_tie"]
            lines.append(f"   🤝 warm tie ({wt['usable_as']}, {wt['status']}): {wt['connection']}")
        lines.append(f"   🔗 {it['url']}")
        lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(mode):
    cfg = load_yaml("config.yaml")
    sources = load_yaml("sources.yaml")
    network = load_yaml("network.yaml")
    seen = load_seen(cfg)
    m = cfg["modes"][mode]

    candidates = []

    # sources
    for src in sources.get("active", []):
        stub = fetch_source(src)
        candidates.append(stub)

    # lab discovery (sweep only)
    if m.get("do_lab_discovery"):
        people = discover_labs(sources["profile"])
        people = attach_warm_ties(people, network)
        candidates += people

    # dedup
    suppress = cfg["dedup"]["suppress_days"]
    fresh = [c for c in candidates if is_fresh(seen, c["id"], suppress)]

    # NOTE: ranking/scoring is done by the Claude Code Chair, not here.
    # The Chair reads output/latest_candidates.json, convenes the council,
    # ranks, and curates the final push. We cap to the config ceiling.
    ceil = m.get("max_candidates", len(fresh))
    fresh = fresh[:ceil]

    (OUT / "latest_candidates.json").write_text(json.dumps(fresh, indent=2))

    digest = render_digest(fresh, mode)
    (OUT / f"digest_{dt.date.today().isoformat()}_{mode}.md").write_text(digest)

    pushed = tg_send(cfg, digest[:3800])  # Telegram msg limit safety
    if not pushed:
        print("Telegram not configured — digest written to output/ only.")

    # record surfaced
    for c in fresh:
        seen[c["id"]] = dt.date.today().isoformat()
    save_seen(cfg, seen)

    print(f"{mode}: {len(fresh)} candidates surfaced. "
          f"Chair should now convene the council over output/latest_candidates.json.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--sweep", action="store_const", const="sweep", dest="mode")
    g.add_argument("--deadlines", action="store_const", const="deadlines", dest="mode")
    args = ap.parse_args()
    run(args.mode or "sweep")
