Opportunity Scout — sweep — 2026-09-01

Chair's note: 18 raw candidates came out of the sweep quota (4 regional / 6
national / 8 international), but three were cut before ranking rather than
padded in:
  - Two "regional" OpenAlex hits (Edoardo Fazzari, Cesare Stefanini — both
    Sant'Anna/Pisa, Italy) were mistagged by a substring bug in
    `_classify_tier` (Piazza Martiri della "Libertà" contains "ibe", which
    matched your home-institution keyword "IBE"). They're not regional, and
    their match quality was the weakest tier ("fallback", robotics-oriented,
    not cognition), so they're dropped rather than reclassified into
    international.
  - One "international" OpenAlex hit (Elodie P. Remoissenet, "Barnsley
    College" / "Barkley AI") reads as a low-quality/AI-generated-looking hit
    — not a real academic affiliation for this field. Dropped.
That leaves 15 items below: 2 regional / 6 national / 7 international.
Worth a one-line fix in scout.py's `_classify_tier` to require word-boundary
matching, not urgent.

== REGIONAL (Catalonia + <2h of Barcelona) ==

1. Govern Illes Balears — ajuts predoctorals (GOIB/DGPRI)  (grant)  <!--id:source::Govern Illes Balears — ajuts predoctorals (GOIB/DGPRI)-->
   - ELIGIBILITY FLAG: this is a predoctoral contract — it typically requires
     current or simultaneous enrolment in a doctoral programme. You're a
     Research Assistant who just finished the TFM and haven't started a PhD
     yet — confirm you can apply pre-enrolment (some predoc calls let you
     apply with an admission letter) before counting on this one.
   - RELIABILITY FLAG: the source page was unreachable this run (HTTP 400) —
     confirm the current call is actually open before acting.
   - why it fits: Balearic Islands regional predoc/research aid; within your
     <2h/ferry regional reach per profile.
   - deadline: not confirmed (annual; check CAIB seu electrònica)
   - link: https://www.caib.es/seucaib/es/tramites/

2. Generalitat Valenciana — ajudes predoctorals (GVA/Conselleria)  (grant)  <!--id:source::Generalitat Valenciana — ajudes predoctorals (GVA/Conselleria)-->
   - ELIGIBILITY FLAG: same as above — Valencian predoc grants (ACIF/Santiago
     Grisolía-style) generally require doctoral-programme enrolment; confirm
     against your actual admission timeline.
   - RELIABILITY FLAG: source page was unreachable this run (502 Bad Gateway)
     — confirm the current-year call is open before acting.
   - why it fits: Valencian regional predoctoral grants; within your <2h
     regional reach.
   - deadline: not confirmed (GVA predoc calls typically open in autumn)
   - link: https://innova.gva.es/es/ayudas

== NATIONAL (Spain + Portugal) ==

3. UAB — Premi Extraordinari de Màster  (thesis-prize)  <!--id:source::UAB — Premis / Premi Extraordinari de Màster-->
   - CONFIRM-BEFORE-COUNTING-ON-IT: this prize is awarded automatically by
     faculty tribunal, not applied for — but the INc programme site
     currently only lists doctorate-level prizes. Confirm with your
     programme's academic-affairs office that a master's-level extraordinary
     prize track exists for your INc master, and that your GPA clears the
     ≥8.0 threshold, before assuming this applies to you.
   - why it fits: you just completed the TFM at Institut de Neurociències —
     this is the closest thing to a sure win on the list if the criteria
     hold, since there's nothing to submit.
   - deadline: none — awarded once per academic year for the prior year's
     graduates
   - link: https://www.uab.cat/web/estudis/grau/informacio-academica/premis-extraordinaris-de-titulacio-1345662186782.html

4. AEI — Agencia Estatal de Investigación (all calls)  (grant)  <!--id:source::AEI — Agencia Estatal de Investigación (all calls)-->
   - why it fits: master index of all Spanish state R&D calls (predoc,
     postdoc, project funding). Broad, not a specific call — worth a
     periodic skim rather than a single action.
   - deadline: rolling / varies by call
   - link: https://www.aei.gob.es/convocatorias/buscador-convocatorias

5. Bernardo Hernández  (person)  <!--id:person::https://openalex.org/A5001223146-->
   - why it fits: PI, Universidad de La Laguna, human-animal interaction
     research (e.g. "Pets, protected animals and farm animals: three
     perceptual spaces of animal abuse"). Topic overlap is moderate —
     adjacent to your cognition focus via the human-animal interaction angle
     — real academic group, worth a look rather than a priority contact.
   - link: https://openalex.org/A5001223146

6. Andrea Vera  (person)  <!--id:person::https://openalex.org/A5101772132-->
   - why it fits: same group as Hernández above (Universidad de La Laguna),
     same human-animal interaction angle. Moderate, tangential fit to your
     core cognition/behavioural-flexibility work.
   - link: https://openalex.org/A5101772132

7. David J. Menor-Campos  (person)  <!--id:person::https://openalex.org/A5062885870-->
   - why it fits: University of Córdoba, animal-welfare/human-animal
     attitudes research. Tangential to your cognition focus but Spain-based
     and topically adjacent.
   - link: https://openalex.org/A5062885870

8. Fondation Fyssen — postdoctoral study grants  (grant)  <!--id:source::Fondation Fyssen — postdoctoral study grants-->
   - ELIGIBILITY FLAG — NOT YET ELIGIBLE: postdoc-stage only (~€45k mobility
     grant). You're pre-PhD. Listed here purely as a seed for after your
     PhD, not something to act on now.
   - why it fits: animal-cognition-focused foundation, exactly your field —
     just the wrong career stage today.
   - deadline: annual, application window roughly Feb–Mar (confirm on site)
   - link: https://www.fondationfyssen.fr/en/

== INTERNATIONAL (mostly Europe) ==

9. ASAB Research Grants  (grant)  <!--id:source::ASAB Research Grants-->
   - DEADLINE FLAG: next round closes 1 Oct 2026 — about 4 weeks out from
     today. Decide quickly if you want to pursue this cycle.
   - why it fits: up to £10k (£15k with justification) explicitly for travel
     to conduct collaborative research or bring a collaborator to you — no
     nationality restriction affecting Spain-based applicants, no overheads.
     Strong match for cross-lab collaboration funding.
   - deadline: three rounds/year — 1 Feb, 1 Jun, 1 Oct (verified)
   - link: https://www.asab.org/research-grants

10. Per Jensen  (person)  <!--id:person::https://openalex.org/A5071463695-->
   - why it fits: PI, Linköping University, AVIAN Behavioural Genomics and
     Physiology group — established name in domestication effects on animal
     cognition, directly overlapping your comparative-cognition/behavioural-
     flexibility interests. Best-fit person on this list.
   - link: https://openalex.org/A5071463695

11. Vitor Hugo Bessa Ferreira  (person)  <!--id:person::https://openalex.org/A5088217940-->
   - why it fits: same group as Per Jensen (Linköping/INRAE), first-author on
     "Are domesticated animals dumber than their wild relatives?" — direct
     topical overlap with your cognition work.
   - link: https://openalex.org/A5088217940

12. Company of Biologists — Travelling Fellowships  (grant)  <!--id:source::Company of Biologists — Travelling Fellowships-->
   - ELIGIBILITY FLAG: eligibility is stated as "grad students & postdocs."
     Confirm whether a pre-enrolment Research Assistant qualifies, or
     whether you need to wait until you're formally enrolled in a PhD.
   - why it fits: up to £3k for ECRs to undertake collaborative lab visits,
     no nationality restriction, rolling basis. Good low-friction fit for a
     first collaboration visit.
   - deadline: rolling / journal-specific
   - link: https://www.biologists.com/grants/travelling-fellowships/

13. Animal Behavior Society — Grants & Awards  (grant)  <!--id:source::Animal Behavior Society — Grants & Awards-->
   - ELIGIBILITY FLAG: many of these awards require current ABS (or ASAB)
     membership in good standing — factor in membership cost/timing before
     picking a specific award to target.
   - why it fits: Early Career Research Grants, Student Research Grants, and
     Travel Awards on-profile for animal behaviour/cognition.
   - deadline: annual cycles, varies per award — check current-cycle dates
   - link: https://www.animalbehaviorsociety.org/web/awards.php

14. ASAB Scholarships & smaller grants  (grant)  <!--id:source::ASAB Scholarships & smaller grants-->
   - why it fits: overview of smaller ASAB awards (conference support,
     education grants, caregiver grants) — worth a skim for anything
     ECR-eligible, no single standout call identified this run.
   - deadline: various
   - link: https://www.asab.org/grant-overview

15. Sam Sonnega  (person)  <!--id:person::https://openalex.org/A5036381816-->
   - why it fits: UMass Dartmouth, PI Michael J. Sheriff — wild-animal
     welfare/physiology angle (gut microbiome as welfare biomarker). Weakest
     fit on this list — tangential to cognition, included for topic overlap
     only.
   - link: https://openalex.org/A5036381816

---

No warm ties this run — nothing in network.yaml matched any candidate above,
so none is claimed.

To greenlight items: reply in Telegram with the researcher's or grant's NAME
(e.g. "yes Jensen, Company of Biologists"), name being safest. Ticked items
get harvested into the approval queue on the next sweep.
