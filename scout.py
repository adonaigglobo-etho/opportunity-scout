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
PROFILE_REGION = {}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def load_yaml(name):
    with io.open(ROOT / name, encoding="utf-8", errors="replace") as f:
        return yaml.safe_load(f)

def http_get(url, accept="application/json", timeout=25, insecure_fallback=False):
    mail = os.environ.get("OPENALEX_MAILTO", "").strip() or "opportunity-scout@example.com"
    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
        "Accept": accept,
        "Accept-Language": "en,es;q=0.8,ca;q=0.6",
        "X-Contact": f"mailto:{mail}"})
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
    global PROFILE_REGION
    PROFILE_REGION = profile.get('region', {})
    since = (dt.date.today() - dt.timedelta(days=365 * 3)).isoformat()
    people = {}
    methods = {}  # keyword -> "topic:<name>" or "fallback"
    for kw in profile.get("keywords_openalex", []):
        tid, tname = resolve_topic_id(kw)
        time.sleep(1.1)  # stay under the ~1/sec OpenAlex topics limit
        search = ""
        if tid:
            filt = f"primary_topic.id:{tid},from_publication_date:{since}"
            # relevance_score sort is ONLY valid when a search term is present, so
            # pair the topic filter with search=<keyword>. Without this, OpenAlex
            # returns HTTP 400 and the query silently yields nothing.
            search = f"&search={urllib.parse.quote(kw)}"
            sort = "relevance_score:desc"
            methods[kw] = f"topic:{tname}"
        else:
            filt = f"title_and_abstract.search:{urllib.parse.quote(kw)},from_publication_date:{since}"
            sort = "cited_by_count:desc"
            methods[kw] = "fallback"
        url = (f"https://api.openalex.org/works?filter={filt}{search}"
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
        r["tier"] = _classify_tier(r, PROFILE_REGION)
        r["why_it_fits"] = (f"[{r['discovery']}] overlaps {r['overlap']} of your topics "
                            f"({', '.join(r['matched_topics'])}); e.g. \"{r['example_work']}\"")
    out.sort(key=lambda r: r["overlap"], reverse=True)
    return out

# ------------------------------------------------------------------ Warm ties
def _norm_tokens(name):
    return set(t for t in "".join(
        c.lower() if (c.isalnum() or c.isspace()) else " " for c in name).split() if len(t) > 1)

def discover_regional(profile, per_keyword=6):
    """Second discovery pass filtered to Spanish institutions, so regional/national
    researchers surface instead of being buried under high-citation international labs.
    Uses OpenAlex institutions.country_code:ES. Ranked by relevance within Spain."""
    global PROFILE_REGION
    PROFILE_REGION = profile.get("region", {})
    since = (dt.date.today() - dt.timedelta(days=365 * 4)).isoformat()
    people = {}
    for kw in profile.get("keywords_openalex", []):
        tid, tname = resolve_topic_id(kw)
        time.sleep(1.1)
        if tid:
            filt = (f"primary_topic.id:{tid},institutions.country_code:es,"
                    f"from_publication_date:{since}")
            search = f"&search={urllib.parse.quote(kw)}"
            sort = "relevance_score:desc"
            method = f"topic-ES:{tname}"
        else:
            filt = (f"title_and_abstract.search:{urllib.parse.quote(kw)},"
                    f"institutions.country_code:es,from_publication_date:{since}")
            search = ""
            sort = "cited_by_count:desc"
            method = "fallback-ES"
        url = (f"https://api.openalex.org/works?filter={filt}{search}"
               f"&sort={sort}&per-page={per_keyword}{_oa_suffix()}")
        try:
            data = json.loads(http_get(url)); time.sleep(1.1)
        except Exception as e:
            print(f"  [openalex ES] {kw}: {e}", file=sys.stderr); continue
        for w in data.get("results", []):
            auths = w.get("authorships", [])
            pi = next((a.get("author", {}).get("display_name", "")
                       for a in auths if a.get("author_position") == "last"), "")
            for a in auths:
                if a.get("author_position") == "middle":
                    continue
                author = a.get("author", {}); aid = author.get("id", "")
                if not aid:
                    continue
                inst = (a.get("institutions") or [{}])
                # only keep authors with a Spanish affiliation on this work
                if not any((i.get("country_code") or "").lower() == "es" for i in inst):
                    continue
                rec = people.get(aid)
                if not rec:
                    rec = {"id": f"person::{aid}", "kind": "person",
                           "title": author.get("display_name", "Unknown"),
                           "source": "OpenAlex-ES", "url": aid,
                           "orcid": author.get("orcid", "") or "", "deadline": None,
                           "eligibility_notes": "",
                           "institution": inst[0].get("display_name", "") if inst else "",
                           "raw_affiliation": "; ".join(a.get("raw_affiliation_strings", []) or []),
                           "pi_last_author": pi, "matched_topics": [], "match_methods": [],
                           "example_work": w.get("title", "")[:140], "tags": []}
                    people[aid] = rec
                if kw not in rec["matched_topics"]:
                    rec["matched_topics"].append(kw)
                    rec["match_methods"].append(method)
    out = list(people.values())
    for r in out:
        r["overlap"] = len(r["matched_topics"]); r["tags"] = list(r["matched_topics"])
        r["discovery"] = "topic-ES" if any(m.startswith("topic-ES") for m in r["match_methods"]) else "fallback-ES"
        r["tier"] = _classify_tier(r, PROFILE_REGION)
        r["why_it_fits"] = (f"[{r['discovery']}] Spain-based; overlaps {r['overlap']} of your "
                            f"topics ({', '.join(r['matched_topics'])}); e.g. \"{r['example_work']}\"")
    out.sort(key=lambda r: r["overlap"], reverse=True)
    return out

def _score(c):
    """Relevance score for ordering within a tier. People rank by topic overlap;
    grants get a mid score so a strongly-matching researcher can outrank a generic
    portal, but grants still place."""
    if c.get("kind") == "person":
        return 10 + int(c.get("overlap", 1))   # people with more topic overlap rank higher
    # grants: reachable, on-profile-tagged ones rank a touch higher
    base = 5
    if c.get("reachable"): base += 1
    return base

def select_by_tier_quota(candidates, total, tiers=("regional","national","international"), quota=None):
    """Fill each tier up to its quota, BLENDING grants and people so neither type is
    shut out by file order. Within a tier we interleave the (score-sorted) grants and
    people, starting with a grant so funding always shows. Unfilled slots redistribute
    to tiers with surplus. `quota` e.g. {'regional':4,'national':6,'international':8}."""
    if quota:
        want = {t: int(quota.get(t, 0)) for t in tiers}
    else:
        base = total // len(tiers)
        want = {t: base for t in tiers}

    def blend_for(t):
        pool = [c for c in candidates if c.get("tier", "international") == t]
        grants = sorted([c for c in pool if c.get("kind") != "person"],
                        key=_score, reverse=True)
        people = sorted([c for c in pool if c.get("kind") == "person"],
                        key=_score, reverse=True)
        out, gi, pi, turn = [], 0, 0, "g"
        while gi < len(grants) or pi < len(people):
            if turn == "g" and gi < len(grants):
                out.append(grants[gi]); gi += 1; turn = "p"
            elif turn == "p" and pi < len(people):
                out.append(people[pi]); pi += 1; turn = "g"
            elif gi < len(grants):
                out.append(grants[gi]); gi += 1
            elif pi < len(people):
                out.append(people[pi]); pi += 1
        return out

    blended = {t: blend_for(t) for t in tiers}
    picked, used = [], {t: 0 for t in tiers}
    for t in tiers:
        take = blended[t][:want[t]]
        picked += take; used[t] = len(take)
    remaining = total - len(picked)
    while remaining > 0:
        progressed = False
        for t in tiers:
            if remaining <= 0: break
            if len(blended[t]) > used[t]:
                picked.append(blended[t][used[t]]); used[t] += 1
                remaining -= 1; progressed = True
        if not progressed:
            break
    picked_ids = {c["id"] for c in picked}
    return [c for c in picked]  # already in tier+blend order

def _classify_tier(rec, region):
    """Tag a person hit as regional / national / international from institution text."""
    inst = " ".join([rec.get("institution", ""), rec.get("raw_affiliation", "")]).lower()
    if not inst.strip():
        return "international"
    homes = [h.lower() for h in region.get("home_institutions", [])]
    provs = [p.lower() for p in region.get("regional_provinces", [])]
    if any(h in inst for h in homes) or any(p in inst for p in provs):
        return "regional"
    # crude national check: Spain/Portugal mentions
    if any(w in inst for w in ["spain", "españa", "espanya", "portugal", "madrid",
                                "sevilla", "granada", "bilbao", "santiago", "lisbon", "porto"]):
        return "national"
    return "international"

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
            "cadence": src.get("cadence", ""), "tier": src.get("tier", "international")}
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
    order = ["regional", "national", "international"]
    labels = {"regional": "REGIONAL (Catalonia + <2h of Barcelona)",
              "national": "NATIONAL (Spain + Portugal)",
              "international": "INTERNATIONAL (mostly Europe)"}
    buckets = {k: [] for k in order}
    for it in items:
        buckets.get(it.get("tier", "international"), buckets["international"]).append(it)
    n = 0
    for tier in order:
        group = buckets[tier]
        if not group:
            continue
        lines.append(f"== {labels[tier]} ==")
        lines.append("")
        for it in group:
            n += 1
            flag = "[!] " if it.get("deadline") else ""
            head = (f"- [ ] {flag}{it['title']}  ({it['kind']})  <!--id:{it['id']}-->"
                    if checkboxes else f"{n}. {flag}{it['title']}  ({it['kind']})")
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
def write_digest_map(items):
    """Record the digest numbering so Telegram replies can be mapped to ids.
    Numbering MUST match the order the Chair presents; the Chair should rewrite
    this file if it reorders or trims the list when it composes the final digest."""
    m = {"date": dt.date.today().isoformat(),
         "items": [{"n": i, "id": it.get("id"), "title": it.get("title", "")}
                   for i, it in enumerate(items, 1)]}
    (CTX / "last_digest_map.json").write_text(
        json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

def run_sweep(cfg, sources, network, no_send=False):
    seen = load_seen(cfg); m = cfg["modes"]["sweep"]
    candidates = [fetch_source(s) for s in sources.get("active", [])]
    if m.get("do_lab_discovery"):
        people = discover_labs(sources["profile"])
        people += discover_regional(sources["profile"])   # Spain-filtered pass
        # dedupe people by id (a Spanish author may appear in both passes)
        seen_ids, deduped = set(), []
        for pr in people:
            if pr["id"] not in seen_ids:
                seen_ids.add(pr["id"]); deduped.append(pr)
        candidates += attach_warm_ties(deduped, network)
    fresh = [c for c in candidates if is_fresh(seen, c["id"], cfg["dedup"]["suppress_days"])]
    # apply the per-tier quota so regional/national aren't crowded out by international
    quota_total = m.get("quota_total", m.get("max_candidates", 100))
    fresh = select_by_tier_quota(fresh, quota_total, quota=m.get("tier_quota"))

    stamp = dt.date.today().isoformat()
    (OUT / "latest_candidates.json").write_text(json.dumps(fresh, indent=2), encoding="utf-8")
    (OUT / f"{stamp}_sweep_candidates.json").write_text(json.dumps(fresh, indent=2), encoding="utf-8")
    digest = render_digest(fresh, "sweep", checkboxes=True)
    digest += "\n\nReply to greenlight: e.g. 'yes Chittka' or the item number (name is safest)."
    (OUT / f"digest_{stamp}_sweep.md").write_text(digest, encoding="utf-8")

    # Numbered index so you can greenlight by replying "yes Chittka" in Telegram.
    # IMPORTANT: only (re)write the index when this run actually produced candidates.
    # An empty run must NOT clobber the last real digest's index (that caused a 404
    # when the harvester fetched it). Quiet runs preserve the previous index.
    if fresh:
        order = ["regional", "national", "international"]
        ordered = [it for t in order for it in fresh if it.get("tier", "international") == t]
        index = {str(i): it for i, it in enumerate(ordered, 1)}
        (CTX / "last_digest_index.json").write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        write_digest_map(fresh)
    else:
        print("empty run: preserving previous last_digest_index.json (not overwriting).")

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
