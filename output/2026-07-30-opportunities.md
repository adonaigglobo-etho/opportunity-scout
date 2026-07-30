# Opportunity Scout — sweep — 2026-07-30

## Council verdict: 0 items selected — run failed at the network layer, not a quiet month

This was the first `--sweep` run (empty `seen.json`, empty `approved_queue.json`, no prior
checkbox digest to harvest from). Before the council could score anything, discovery itself
failed completely:

- **All 29 `active:` sources in `sources.yaml`** came back `UNREACHABLE` (403 from the
  session's egress proxy) when `fetch_source()` tried to load each portal page. Zero page
  content was retrieved for any of them.
- **OpenAlex lab/PI discovery** (`discover_labs()`) failed on every one of the 8
  `keywords_openalex` topic + works lookups, same 403.
- **Telegram delivery** (`tg_send_long`) is also blocked by the same egress policy — confirmed
  via a direct connectivity check to `api.telegram.org`, independent of the scout script.

Root cause (checked via the proxy status endpoint): this session's outbound network policy is
denying CONNECT to every external host the scout needs — `api.openalex.org`, `orcid.org`,
`jobrxiv.org`, `bsky.app`, `api.telegram.org`, and (by inference, same policy) the grant-portal
domains in `sources.yaml` (la Caixa, AEI, MEFP, etc.). This is an infrastructure/environment
restriction, not a finding about your field.

**No items are being ranked or pushed.** The 29 records in `output/latest_candidates.json` are
empty stubs (source name + URL only, no fetched content) — running the Scorer/Eligibility Gate
over them would mean inventing "why it fits" text with zero actual information, which the
council's hard rules forbid. Better to report zero than to pad with unverifiable placeholders.

### What to do
- This is worth checking with whoever manages this environment's network egress policy: the
  scout needs outbound HTTPS to research portals, OpenAlex, ORCID, and Telegram to function at
  all.
- No action needed on `network.yaml` or `sources.yaml` — nothing was resolved to review, and
  nothing is being proposed as a new source this cycle.
- Next run: once network access is restored, a normal `--sweep` should work — `seen.json` is
  untouched by this run, so no sources were incorrectly suppressed.

*(`python scout.py --send-file` and the Telegram send were both attempted per the standing
workflow; both failed closed, as expected — `seen.json` was not modified.)*
