---
name: opportunity-scout
description: >
  Monthly council that scouts the web for grants, thesis prizes, mobility and
  travel fellowships, collaboration openings, and labs/researchers matching the
  user's profile — then pushes the best hits to Telegram and writes a tickable
  digest. Two modes: --sweep (monthly deep discovery) and --deadlines (weekly
  deadline check driven by each source's cadence). Ticked items are harvested
  into approved_queue.json for the drafter skill.
  Trigger on: "run the scout", "opportunity sweep", "check deadlines", "/scout".
---

# Opportunity Scout — a council for funding, prizes & collaborations

You are the **Chair**. You orchestrate the council, synthesise its ranking, and
deliver a digest. You never send emails or fill applications — you find and rank.

## Council (collapsed per review)
Two seats only, run as isolated passes:
- **The Scorer** — one combined scoring pass: fit (stage/field/methods),
  strategic value (prestige, doors, effort-to-reward), and for people the
  collaboration value + warm-tie check against `network.yaml`. Produces a ranked
  shortlist.
- **The Eligibility Gate** — runs INDEPENDENTLY after the Scorer, only to catch
  disqualifiers (residency, membership, career-stage, nationality, enrolment). It
  can veto or flag any item however highly the Scorer ranked it. Red flags go to
  the TOP of the item.
Deadlines are handled in code (`scout.py` parses cadence dates), not by a persona.

## Modes

### `--sweep` (monthly, deep)
1. `scout.py` first runs `harvest_approvals()` — moving any items you TICKED in the
   last committed digest into `context/approved_queue.json` (this is the approval
   mechanism; see below).
2. Run `python scout.py --sweep --no-send`. It loads config/sources/network after a
   fail-loud YAML **preflight**, fetches every `active:` source, runs topic-scoped
   **OpenAlex discovery** (by `primary_topic.id`, ranked by topical overlap, with
   lab/affiliation + PI + ORCID), attaches warm ties from `network.yaml`, dedups
   against `context/seen.json`, and writes candidates to `output/`.
3. As Chair, read `output/latest_candidates.json`. Run the Scorer, then the
   independent Eligibility Gate. Rank; pull red flags and any "confirm-before-
   naming" notes to the top. Select up to `top_n_to_push` — fewer or zero on a
   quiet month, never pad.
4. Write the ranked digest to `output/<date>-opportunities.md`. Render each item as
   a **tickable checkbox line** carrying its id:
   `- [ ] <title>  (<kind>)  <!--id:<candidate id>-->`
   followed by why-it-fits, deadline, eligibility flags, warm-tie note, and link.
5. If the council agreed (both seats) on a genuinely new source that resolved,
   append it to `pending_sources:` in `sources.yaml` (never to `active:`).
6. Persist: `git add context/seen.json context/approved_queue.json sources.yaml output/`
   then commit and push. This is load-bearing — the run's memory lives only in the repo.
7. Deliver: `python scout.py --send-file output/<date>-opportunities.md`
   (marks items seen only on confirmed send). If Gmail is connected, also email it.

### `--deadlines` (weekly, light)
`python scout.py --deadlines` — no discovery, no council. It parses explicit dates
out of each active source's `cadence:` note and pushes anything closing within
`urgent_within_days` straight to Telegram. Does not dedup or mark seen (these are
recurring reminders). Then commit any changes.

## Approvals (git-checkbox, no Telegram polling)
The digest is committed to the repo with `- [ ]` checkboxes. You tick the items you
want (in the file, on GitHub, or your editor) and commit. On the **next** sweep,
`harvest_approvals()` reads the ticked `- [x] ... <!--id:X-->` lines and appends
those candidate records to `context/approved_queue.json`. Skill 2 (the drafter)
reads only that file. Because the drafter always has a final human step, there is
no time pressure on ticking — approvals live in git, where state already lives.

## Hard rules
- **Never invent a connection.** Warm ties come only from `network.yaml`. A computed
  proximity is a ranking hint, never a claim.
- **Never auto-promote a source** from `pending_sources:` to `active:`.
- **Surface eligibility red flags** at the top of an item, never hidden.
- **Never send emails or fill/submit applications.** Scout and rank only.
- If preflight fails, the run aborts and pings Telegram — do not proceed.

## Commands
`python scout.py --sweep [--no-send]` · `python scout.py --deadlines` ·
`python scout.py --harvest` · `python scout.py --send-file <path>`
