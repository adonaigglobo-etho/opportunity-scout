#!/usr/bin/env python3
"""
Opportunity Scout engine  (Windows-safe; post-review build).

P0: fail-loud preflight; topic-scoped OpenAlex discovery ranked by overlap (not
raw citations), capturing lab/affiliation, PI and ORCID; seen.json written only
after confirmed delivery; chunked auto-send; id/strict-name warm-tie matching.
P1: --deadlines parses dates from each source's cadence note (no longer a no-op);
git-checkbox approvals harvested from committed digests into approved_queue.json.
"""
from __future__ import annotations
import io, re, time, ssl, argparse, json, os, sys, datetime as dt, urllib.parse, urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

ROOT = Path(__file__).parent
CTX = ROOT / "context"; OUT = ROOT / "output"
CTX.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
CONFIG_FILES = ["config.yaml", "sources.yaml", "network.yaml"]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def load_yaml(name):
    with io.open(ROOT / name, encoding="utf-8", errors="replace") as f:
        return yaml.safe_load(f)

def http_get(url, accept="application/json", timeout=25, insecure_fallback=False):
    mail = os.environ.get("OPENALEX_MAILTO", "").strip() or "opportunity-scout@example.com"
    req = urllib.request.Request(url, headers={
        "User-Agent": f"Mozilla/5.0 (opportunity-scout; mailto:{mail})", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except (ssl.SSLError, urllib.error.URLError) as e:
        # Some government/portal sites have incomplete cert chains. For reading
        # PUBLIC pages only, retry once without verification. Never used for
        # anything that sends credentials (Telegram uses its own path).
        reason = getattr(e, "reason", e)
        if insecure_fallback and ("SSL" in str(reason) or "CERTIFICATE" in str(reason).upper()):
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read().decode("utf-8", "replace")
        raise

# ------------------------------------------------------------------ Telegram
def _tg_creds(cfg=None):
    def pick(cfgkey, *envs):
        if cfg:
            v = os.environ.get(cfg["telegram"][cfgkey])
            if v: return v
        for e in envs:
            v = os.environ.get(e)
            if v: return v
        return None
    return (pick("bot_token_env", "TELEGRAM_BOT_TOKEN", "SCOUT_BOT_TOKEN"),
            pick("chat_id_env", "TELEGRAM_CHAT_ID", "SCOUT_CHAT_ID"))

def tg_send(cfg, text):
    token, chat = _tg_creds(cfg)
    if not (token and chat): return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_web_page_preview": "false"}).encode("utf-8")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=20); return True
    except Exception as e:
        print(f"  [telegram] {e}", file=sys.stderr); return False

def tg_send_long(cfg, text, limit=3800):
    ok = True; buf = ""
    for para in text.split("\n\n"):
        if buf and len(buf) + len(para) + 2 > limit:
            ok = tg_send(cfg, buf) and ok; buf = para
        else:
            buf = (buf + "\n\n" + para) if buf else para
    if buf.strip(): ok = tg_send(cfg, buf) and ok
    return ok

def emergency_tg(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("SCOUT_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("SCOUT_CHAT_ID")
    if not (token and chat): return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode("utf-8")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=20); return True
    except Exception:
        return False

# ------------------------------------------------------------------ Preflight
def preflight():
    problems = []
    for f in CONFIG_FILES:
        try:
            if load_yaml(f) is None: problems.append(f"{f}: parsed empty")
        except Exception as e:
            problems.append(f"{f}: {type(e).__name__}: {e}")
    if problems:
        msg = "Opportunity Scout PREFLIGHT FAILED - run aborted:\n" + "\n".join(problems)
        emergency_tg(msg); print(msg, file=sys.stderr); sys.exit(1)

# ------------------------------------------------------------------ Dedup
def load_seen(cfg):
    p = ROOT / cfg["dedup"]["store"]
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def save_seen(cfg, seen):
    (ROOT / cfg["dedup"]["store"]).write_text(json.dumps(seen, indent=2), encoding="utf-8")

def is_fresh(seen, key, suppress_days):
    if key not in seen: return True
    return (dt.date.today() - dt.date.fromisoformat(seen[key])).days >= suppress_days

def mark_seen_and_save(cfg, ids):
    seen = load_seen(cfg); today = dt.date.today().isoformat()
    for k in ids:
        if k: seen[k] = today
    save_seen(cfg, seen)

# ------------------------------------------------------------------ OpenAlex
def _oa_suffix():
    parts = []
    mail = os.environ.get("OPENALEX_MAILTO", "").strip()
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if mail: parts.append("mailto=" + urllib.parse.quote(mail))
    if key: parts.append("api_key=" + key)
    return ("&" + "&".join(parts)) if parts else ""

def resolve_topic_id(keyword):
    """Return (topic_id, topic_name) or (None, None). Retries once on failure,
    since the topics endpoint is rate-limited (~1/sec) and a throttled call is
    the most common reason resolution silently falls back to text search."""
    q = urllib.parse.quote(keyword)
    url = f"https://api.openalex.org/topics?search={q}&per-page=1{_oa_suffix()}"
    for attempt in range(2):
        try:
            data = json.loads(http_get(url))
            r = data.get("results", [])
            if r:
                tid = r[0].get("id", "")
                name = r[0].get("display_name", "")
                return (tid.rsplit("/", 1)[-1] if tid else None), name
            return None, None
        except Exception as e:
            print(f"  [openalex topic] {keyword} (try {attempt+1}): {e}", file=sys.stderr)
            time.sleep(1.2)  # respect ~1/sec limit before retry
    return None, None

def discover_labs(profile, per_keyword=10):
    since = (dt.date.today() - dt.timedelta(days=365 * 3)).isoformat()
    people = {}
    methods = {}  # keyword -> "topic:<name>" or "fallback"
    for kw in profile.get("keywords_openalex", []):
        tid, tname = resolve_topic_id(kw)
        time.sleep(1.1)  # stay under the ~1/sec OpenAlex topics limit
        if tid:
            filt = f"primary_topic.id:{tid},from_publication_date:{since}"
            # within a correct topic, relevance beats raw citations for on-profile hits
            sort = "relevance_score:desc"
            methods[kw] = f"topic:{tname}"
        else:
            filt = f"title_and_abstract.search:{urllib.parse.quote(kw)},from_publication_date:{since}"
            sort = "cited_by_count:desc"
            methods[kw] = "fallback"
        url = (f"https://api.openalex.org/works?filter={filt}"
               f"&sort={sort}&per-page={per_keyword}{_oa_suffix()}")
        try:
            data = json.loads(http_get(url)); time.sleep(1.1)
        except Exception as e:
            print(f"  [openalex works] {kw}: {e}", file=sys.stderr); continue
        for w in data.get("results", []):
            auths = w.get("authorships", [])
            pi = next((a.get("author", {}).get("display_name", "")
                       for a in auths if a.get("author_position") == "last"), "")
            for a in auths:
                if a.get("author_position") == "middle": continue
                author = a.get("author", {}); aid = author.get("id", "")
                if not aid: continue
                inst = (a.get("institutions") or [{}])
                rec = people.get(aid)
                if not rec:
                    rec = {"id": f"person::{aid}", "kind": "person",
                           "title": author.get("display_name", "Unknown"),
                           "source": "OpenAlex", "url": aid,
                           "orcid": author.get("orcid", "") or "", "deadline": None,
                           "eligibility_notes": "",
                           "institution": inst[0].get("display_name", "") if inst else "",
                           "raw_affiliation": "; ".join(a.get("raw_affiliation_strings", []) or []),
                           "pi_last_author": pi, "matched_topics": [],
                           "match_methods": [],
                           "example_work": w.get("title", "")[:140], "tags": []}
                    people[aid] = rec
                if kw not in rec["matched_topics"]:
                    rec["matched_topics"].append(kw)
                    rec["match_methods"].append(methods.get(kw, "?"))
    out = list(people.values())
    for r in out:
        r["overlap"] = len(r["matched_topics"]); r["tags"] = list(r["matched_topics"])
        r["discovery"] = "topic" if any(m.startswith("topic:") for m in r["match_methods"]) else "fallback"
        r["why_it_fits"] = (f"[{r['discovery']}] overlaps {r['overlap']} of your topics "
                            f"({', '.join(r['matched_topics'])}); e.g. \"{r['example_work']}\"")
    out.sort(key=lambda r: r["overlap"], reverse=True)
    return out

# ------------------------------------------------------------------ Warm ties
def _norm_tokens(name):
    return set(t for t in "".join(
        c.lower() if (c.isalnum() or c.isspace()) else " " for c in name).split() if len(t) > 1)

def attach_warm_ties(people, network):
    conns = network.get("connections", [])
    for p in people:
        p["warm_tie"] = None
        p_oa = (p.get("url") or "").rsplit("/", 1)[-1].lower()
        p_orcid = (p.get("orcid") or "").rsplit("/", 1)[-1].lower()
        p_tokens = _norm_tokens(p.get("title", ""))
        for c in conns:
            c_oa = (c.get("openalex_id") or "").rsplit("/", 1)[-1].lower()
            c_orcid = (c.get("orcid") or "").rsplit("/", 1)[-1].lower()
            matched = False
            if c_oa and c_oa == p_oa: matched = True
            elif c_orcid and c_orcid == p_orcid: matched = True
            else:
                ct = _norm_tokens(c.get("target", ""))
                if len(ct) >= 2 and len(p_tokens) >= 2 and (ct <= p_tokens or p_tokens <= ct):
                    matched = True
            if matched:
                p["warm_tie"] = {"connection": c.get("connection", ""),
                                 "usable_as": c.get("usable_as", "none"),
                                 "confirm_with": c.get("confirm_with", ""),
                                 "status": c.get("status", "cold")}
                break
    return people

# ------------------------------------------------------------------ Sources
def fetch_source(src):
    stub = {"id": f"source::{src['name']}", "kind": "grant", "title": src["name"],
            "source": src["name"], "url": src["url"], "deadline": None,
            "eligibility_notes": src.get("notes", ""), "why_it_fits": "",
            "tags": src.get("tags", []), "warm_tie": None, "reachable": False,
            "cadence": src.get("cadence", "")}
    try:
        body = http_get(src["url"], accept="text/html", insecure_fallback=True)
        stub["reachable"] = True; stub["_page_excerpt"] = body[:4000]
    except Exception as e:
        stub["eligibility_notes"] += f"  [UNREACHABLE: {e}]"
    return stub

# ------------------------------------------------------------------ Cadence deadlines
def parse_cadence_deadlines(text, within_days, today=None):
    today = today or dt.date.today(); found = []
    for m in re.finditer(r"~?(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
                         (text or "").lower()):
        day = int(m.group(1)); mon = MONTHS[m.group(2)]
        for yr in (today.year, today.year + 1):
            try:
                d = dt.date(yr, mon, day)
            except ValueError:
                break
            if d >= today:
                if (d - today).days <= within_days: found.append(d)
                break
    return sorted(set(found))

# ------------------------------------------------------------------ Digest
def render_digest(items, mode, checkboxes=False):
    today = dt.date.today().isoformat()
    lines = [f"Opportunity Scout - {mode} - {today}", ""]
    for i, it in enumerate(items, 1):
        flag = "[!] " if it.get("deadline") else ""
        head = (f"- [ ] {flag}{it['title']}  ({it['kind']})  <!--id:{it['id']}-->"
                if checkboxes else f"{i}. {flag}{it['title']}  ({it['kind']})")
        lines.append(head)
        if it.get("why_it_fits"): lines.append(f"   - {it['why_it_fits']}")
        if it.get("institution"): lines.append(f"   - {it['institution']}")
        if it.get("deadline"): lines.append(f"   - deadline: {it['deadline']}")
        if it.get("eligibility_notes"): lines.append(f"   - note: {it['eligibility_notes']}")
        if it.get("warm_tie"):
            wt = it["warm_tie"]
            cw = f" (confirm with {wt['confirm_with']})" if wt.get("confirm_with") else ""
            lines.append(f"   - WARM TIE ({wt['usable_as']}, {wt['status']}){cw}: {wt['connection']}")
        lines.append(f"   - {it['url']}")
        lines.append("")
    return "\n".join(lines)

# ------------------------------------------------------------------ Approval harvest
def harvest_approvals():
    qp = CTX / "approved_queue.json"
    queue = json.loads(qp.read_text(encoding="utf-8")) if qp.exists() else []
    have = {c.get("id") for c in queue}
    records = {}
    for f in list(OUT.glob("*_candidates.json")) + [OUT / "latest_candidates.json"]:
        if f.exists():
            try:
                for c in json.loads(f.read_text(encoding="utf-8")):
                    records.setdefault(c.get("id"), c)
            except Exception:
                pass
    ticked = set()
    for md in OUT.glob("*.md"):
        for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*-\s*\[[xX]\].*?<!--id:(.*?)-->", line)
            if m: ticked.add(m.group(1))
    added = 0
    for tid in ticked:
        if tid in have: continue
        rec = records.get(tid)
        if rec:
            queue.append(rec); have.add(tid); added += 1
    qp.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    return added

# ------------------------------------------------------------------ Runs
def run_sweep(cfg, sources, network, no_send=False):
    seen = load_seen(cfg); m = cfg["modes"]["sweep"]
    candidates = [fetch_source(s) for s in sources.get("active", [])]
    if m.get("do_lab_discovery"):
        candidates += attach_warm_ties(discover_labs(sources["profile"]), network)
    fresh = [c for c in candidates if is_fresh(seen, c["id"], cfg["dedup"]["suppress_days"])]
    fresh = fresh[:m.get("max_candidates", len(fresh))]

    stamp = dt.date.today().isoformat()
    (OUT / "latest_candidates.json").write_text(json.dumps(fresh, indent=2), encoding="utf-8")
    (OUT / f"{stamp}_sweep_candidates.json").write_text(json.dumps(fresh, indent=2), encoding="utf-8")
    digest = render_digest(fresh, "sweep", checkboxes=True)
    (OUT / f"digest_{stamp}_sweep.md").write_text(digest, encoding="utf-8")

    if no_send:
        print(f"--no-send: {len(fresh)} candidates written; Chair ranks & sends. "
              "seen.json untouched until delivery."); return
    if tg_send_long(cfg, digest):
        mark_seen_and_save(cfg, [c["id"] for c in fresh])
        print(f"sweep: {len(fresh)} candidates surfaced and delivered.")
    else:
        print("sweep: send failed/unconfigured - digest in output/ only; seen.json untouched.")

def run_deadlines(cfg, sources):
    within = cfg["modes"]["deadlines"]["urgent_within_days"]; items = []
    for s in sources.get("active", []):
        for d in parse_cadence_deadlines(s.get("cadence", ""), within):
            items.append({"id": f"deadline::{s['name']}::{d.isoformat()}", "kind": "deadline",
                          "title": s["name"], "url": s["url"], "deadline": d.isoformat(),
                          "why_it_fits": f"cadence: {s.get('cadence','')}",
                          "eligibility_notes": "", "institution": "", "warm_tie": None})
    items.sort(key=lambda x: x["deadline"])
    if not items:
        tg_send(cfg, f"Opportunity Scout - deadlines - nothing closing within {within} days.")
        print("deadlines: none within window."); return
    tg_send_long(cfg, render_digest(items, "deadlines"))
    print(f"deadlines: {len(items)} urgent item(s) pushed.")

# ------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--sweep", action="store_const", const="sweep", dest="mode")
    g.add_argument("--deadlines", action="store_const", const="deadlines", dest="mode")
    ap.add_argument("--no-send", action="store_true", dest="no_send")
    ap.add_argument("--harvest", action="store_true",
                    help="move ticked digest items into approved_queue.json")
    ap.add_argument("--send-file", dest="send_file", default=None)
    args = ap.parse_args()

    preflight()

    if args.harvest:
        print(f"harvest: {harvest_approvals()} newly approved item(s) queued."); sys.exit(0)
    if args.send_file:
        cfg = load_yaml("config.yaml")
        if tg_send_long(cfg, io.open(args.send_file, encoding="utf-8").read()):
            lc = OUT / "latest_candidates.json"
            if lc.exists():
                mark_seen_and_save(cfg, [c.get("id") for c in json.loads(lc.read_text(encoding="utf-8"))])
            print("sent; seen.json updated on confirmed delivery.")
        else:
            print("send failed / not configured; seen.json untouched.")
        sys.exit(0)

    cfg = load_yaml("config.yaml"); sources = load_yaml("sources.yaml"); network = load_yaml("network.yaml")
    if (args.mode or "sweep") == "sweep":
        harvest_approvals()               # capture last cycle's ticked approvals first
        run_sweep(cfg, sources, network, no_send=args.no_send)
    else:
        run_deadlines(cfg, sources)
