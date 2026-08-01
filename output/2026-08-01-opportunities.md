# Opportunity Scout — sweep — 2026-08-01

**Chair's note:** A mid-sweep bug fix changed this run's numbers, so flagging it up
front. `resolve_topic_id()`/`discover_labs()` had a live bug: `sort=relevance_score:desc`
is only a valid OpenAlex sort when a `search` term is present, so every topic-scoped
query for `animal cognition`, `decision making`, `collective behaviour`, and
`social learning` was returning `HTTP 400` and silently dropping to nothing. Fixed by
pairing the sort with `search=<keyword>` alongside the topic filter (see
`scout.py` `discover_labs()`), then re-ran the sweep. First pass (broken):
20 candidates, all via keyword-fallback. Second pass (fixed): 78 fresh candidates,
58 of them properly topic-scoped. The 78 are what's ranked below.

**Data-quality flag (not a candidate, a process note):** two of the eight profile
keywords are resolving to the *wrong* OpenAlex topic and produced zero usable
candidates this run — `decision making` → Multi-Criteria Decision Making /
fuzzy-set operations research (14 people, none behavioural), and
`collective behaviour` → complex-systems/emergence physics, including a couple of
non-mainstream "consciousness"/AGI titles (8 people, none behavioural). Both sets
were discarded outright, not ranked. Recommend swapping these two
`keywords_openalex` entries in `sources.yaml` for more specific phrasing (e.g.
"collective animal behaviour", "behavioural decision-making") next cycle — flagging
for your review rather than changing the profile file myself.

Of the remaining ~56 candidates (animal cognition, behavioural ecology-fallback,
social learning), most are genuine labs but many are companion-animal
welfare/therapy, plant/microbiome ecology, or otherwise off-profile. **Zero warm
ties** matched against `network.yaml` this run — everything below is cold
outreach, and none of it is a funding call or has a deadline (`OpenAlex` discovery
surfaces labs/researchers, not open positions — a "position" here means "worth
a cold email," not a confirmed vacancy). None of the 29 recurring grant/fellowship
sources produced a new dated call this cycle — they're all within the 120-day
dedup suppression window from the last confirmed send, so a quiet cycle for
calls specifically. Selecting 7 of 8 possible slots rather than padding.

---

- [ ] Lucy M. Aplin — social learning & culture in birds  (person)  <!--id:person::https://openalex.org/A5088537383-->
   - why it fits: Australian National University. Senior author on "Social learning
     and culture in birds: emerging patterns and relevance to conservation" — one
     of the field's leading voices on animal culture and behavioural flexibility
     via social learning, directly on-profile for collective animal cognition.
     High strategic value: ANU is a major node, a strong door-opener even cold.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none — informal contact, no eligibility gate applies
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5088537383

- [ ] Judith M. Burkart — cooperative cognition & social learning in marmosets  (person)  <!--id:person::https://openalex.org/A5125138636-->
   - why it fits: University of Zurich. Senior author on "Opportunities and
     mechanisms for learning through social interactions: lessons from marmosets" —
     strong cross-species comparative-cognition fit (marmoset social
     learning/cooperation vs. your bird/comparative work), well-established lab.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold (note: Zurich also hosts
     other comparative-cognition groups; nothing here is a confirmed tie, don't
     imply one)
   - link: https://openalex.org/A5125138636

- [ ] Enikő Kubinyi — canine cognition & the Family Dog Project  (person)  <!--id:person::https://openalex.org/A5086539835-->
   - why it fits: Eötvös Loránd University. Senior author on "Age-related effects
     on a hierarchical structure of canine cognition" (with Zsófia Bognár) —
     established comparative-cognition group, relevant methods overlap on
     cognitive structure/ageing models.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5086539835

- [ ] Per Jensen — domestication effects on animal cognition  (person)  <!--id:person::https://openalex.org/A5071463695-->
   - why it fits: Linköping University. Senior author (with Vitor Hugo Bessa
     Ferreira) on "Are domesticated animals dumber than their wild relatives?" — a
     comprehensive review directly on behavioural-flexibility/domestication
     comparative cognition, good entry point for a methods-exchange conversation.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5071463695

- [ ] Esther Bouma (with Jennifer Vonk) — cognition/emotion attribution in companion animals  (person)  <!--id:person::https://openalex.org/A5039706983-->
   - why it fits: University of Groningen (Bouma) and Oakland University (Vonk,
     a well-known comparative psychologist) co-authored "Attachment as the
     Catalyst for the Attribution of Complex Cognition and Emotion to Companion
     Cats." Moderate fit — companion-animal leaning rather than core comparative
     cognition, included for Vonk's standing in the field rather than topical
     precision.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5039706983

- [ ] Pengfei Wei (with Yaning Han) — 3D multi-animal pose estimation & behaviour embedding  (person)  <!--id:person::https://openalex.org/A5101506671-->
   - why it fits: Chinese Academy of Sciences. "Multi-animal 3D social pose
     estimation, identification and behaviour embedding with a few-shot learning
     framework" — a methods/tools fit rather than a topical-cognition fit:
     computational behaviour-quantification pipeline that complements your
     GLM-HMM/behavioural-modelling toolkit. Surfaced via the `behavioural ecology`
     fallback search (topic resolution failed for this keyword), so treat the
     match as looser than the topic-scoped picks above.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5101506671

- [ ] Justin Kitzes (with Sam Lapp) — OpenSoundscape bioacoustics analysis toolkit  (person)  <!--id:person::https://openalex.org/A5073601081-->
   - why it fits: University of Pittsburgh. Maintainer of OpenSoundscape, an
     open-source Python bioacoustics package. Tools/methods fit for behavioural
     ecology data pipelines rather than a cognition-topic match; lower strategic
     priority than the picks above but a plausible low-effort methods contact.
     Also surfaced via the `behavioural ecology` fallback search, same caveat as
     above.
   - deadline: none — cold-outreach lead, not a call
   - eligibility flags: none identified
   - warm-tie note: none found in network.yaml — cold
   - link: https://openalex.org/A5073601081
