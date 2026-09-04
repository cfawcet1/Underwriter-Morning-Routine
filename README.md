# Stand UW Agentic Assistant

## Design Principle

An experienced underwriter scanning a morning queue is unconsciously doing something that no deterministic system can replicate — running a probabilistic inference over the gestalt of a lead, looking for the combination of conditions that suggests an exposure no single field captures and no playbook anticipated. That signal is the most valuable thing in the underwriting process and the hardest to scale. This system is designed around it. Deterministic logic handles what is known — field validation, playbook traversal, hard stops. The LLM is pointed at precisely the layer where determinism fails: surfacing the unknown unknowns in the risk calculation. The probabilistic and generative nature of LLMs is typically framed as a liability to be managed. Here it is the mechanism. Not because the technology is interesting but because it is the right tool for the right problem — making underwriter judgment legible, scalable, and cumulative without replacing it. When the agent stops and hands off to a human, that handoff is precise enough to act on in ten seconds. That is the design principle everything else is accountable to. The eval loop is how the system learns which handoffs were right — turning every underwriter decision on every edge case into the signal that makes the next inference better.

---

## Assumptions

### What we encoded and why

We encoded three FigJam pages — Profile, Occupancy, and PC 9 & 10 — and made that choice on a principled basis. Profile is where the insured's knowledge enters the system through the application filter, and where reputational risk to Stand is most directly assessed. Occupancy is where the relationship between the insured and the property is established — a condition that changes the exposure profile fundamentally. PC 9 & 10 is the highest consequence decision path in the playbook, the one most likely to contain tacit underwriting knowledge the diagram doesn't fully surface, and the one where the Palisades fire demonstrated that historical proxy assumptions can fail catastrophically under novel conditions.

We encoded these three pages as versioned domain knowledge in `shared/playbook/` — not as agent logic, not as prompt content. The agent consumes the playbook. It does not own it. This separation means when Stand's underwriting guidelines change, the playbook files change. Nothing else does.

### Epistemic assumptions we made

The KYC score is treated as a proxy for relational risk, not a direct measure of it. The score tells us a number. The OSINT instruction in the Profile FigJam tells us the number is downstream of something a human would find by looking. When KYC is borderline, the agent surfaces the gap rather than resolving it.

Protection class defaults to 9 when missing, per the field registry `missingDefault`. This encodes the FigJam sticky note directly — assume worst case and run the full PC 9 & 10 diagram.

Water source availability is treated as more fundamental than fire department response time. This ordering reflects hard-won knowledge from the Palisades fire — infrastructure that checks out on paper can fail under simultaneous peak demand during a firestorm. Response capability without suppression capability is insufficient.

The field registry `editableByProducer: false` boundary is treated as a hard architectural constraint. Fields in that category are never requested from a human. The agent fetches or derives them. This is not a preference — it is a domain boundary the registry encodes explicitly.

The four decision states — ready to quote, decline, refer to underwriter, and conditionally bindable pending mitigation — are not equal. The cost of a wrong yes is categorically higher than the cost of a wrong no. The system is calibrated around that asymmetry.

### What we explicitly did not encode and why

The remaining ten FigJam pages — Fire Simulation, Roof Class, Siding, Post & Pier Foundations, Plumbing, Electrical Systems, Swimming Pools, Trusts & LLCs, Replacement Cost, and the Decision Points overview — were not encoded in this POC. This was a principled deferral, not an oversight.

Encoding domain knowledge we haven't epistemically interrogated produces an agent that is confidently wrong at the boundaries. We know the boundaries of what we encoded. We do not yet know the boundaries of what we didn't. The eval loop is the mechanism by which those boundaries get mapped — through actual underwriter decisions on actual edge cases, not through pre-hoc assumption.

When a lead triggers a decision path this system hasn't encoded, the agent classifies that condition explicitly and escalates with a precise description of what it encountered and why it stopped. The underwriter is never handed silence. They are handed a legible boundary.

Hard stops for electrical systems — Federal Pacific, Stab-Lok, Zinsco, and Challenger panels, and knob and tube wiring — are encoded in `shared/playbook/hard_stops.py` because they represent near-automatic declines that fire before any other reasoning runs. These are deterministic. They do not require LLM reasoning.

---

## Architecture Overview

Seven top-level directories. Each owns a single concern and nothing else. `shared/` is the domain model — the typed contracts and versioned playbook that every other layer reads from but never writes to. `agent/` is the reasoning pipeline — scanner, traverser, and LLM reasoning in sequence. `eval/` is the learning loop — deterministic and qualitative tracks running in parallel, feedback path returning underwriter decisions as signal. `api/` is the thin bridge between agent and frontend — routes own no logic, services own the translation. `frontend/` is the underwriter's surface — built for a morning queue workflow, not for a technical audience. `data/` holds the persistence layer and static fixtures. `docker-compose.yml` orchestrates the provided lead generator and mock mailbox services.

If you can't infer the architecture from the folder structure, the folder structure is wrong. The README explains the reasoning behind the design. The folders explain the design itself.

---

## The Ontology as Contract

`shared/` is the boundary between the deterministic and LLM layers. Nothing crosses that boundary as raw data.

`ontology.py` defines the typed objects the agent produces and the eval consumes — `LeadState`, `TriageResult`, `IncompletenessClassification`, `EscalationPackage`, `EvalResult`. These are the contracts. If a type changes, both layers know about it because both layers import from here.

`triage_rules.py` encodes the field registry logic programmatically — the four triage actions derived from the combination of presence, required level, and editableByProducer. The traverser calls this. Nothing else does.

`playbook/` contains the FigJam pages as versioned Python modules. Each file has a version string at the top. When guidelines change, the file changes, the version bumps, and the change is reviewable, diffable, and reversible. The agent reads from the playbook. It does not write to it.

The LLM never receives raw lead data. It receives a typed `LeadState` object constructed by the traverser from the ontology. Its reasoning space is bounded by what that object contains.

---

## Four Decision States

The standard three-exit model — decline, refer, bind — is insufficient for this domain. This system operates on four states.

**Ready to quote.** The scanner found no hard stops. The traverser resolved all blocking fields or applied authorized defaults. The lead is clean against the encoded playbook pages.

**Decline recommended.** A hard stop fired — ineligible electrical panel, knob and tube wiring, or a deterministic rule that produces a decline regardless of other conditions. No LLM reasoning required. The composer formats the finding precisely.

**Refer to underwriter.** The agent encountered a condition it cannot resolve — a structurally unknowable field, a genuine judgment call, a combination of conditions the playbook didn't anticipate. The escalation package names what is unknowable, what the agent determined from what was present, and what specific decision the underwriter is being asked to make.

**Conditionally bindable pending mitigation.** The lead is not a clean write and not a decline. It can be written if specific conditions are satisfied — a dry hydrant installed within the underwriting period, centrally monitored sprinklers, a Knox box, a central station fire alarm. The mitigation tracker holds these conditions and advances the lead as they are confirmed.

---

## Eval Loop

Two tracks running in parallel.

**Deterministic track.** Scores the 65% — the cases the playbook covers cleanly. Known correct outputs, rule-based checks, pass/fail per decision. Measures whether the agent traversed the playbook correctly and applied the right triage action for each field.

**Qualitative track.** Scores the 35% — the edge cases where the playbook has no clean answer. A second LLM evaluates the reasoning quality of the first against versioned criteria in `eval/qualitative/criteria.py`. It does not check the output against a reference answer. It evaluates whether the agent correctly classified the type of incompleteness, identified the minimum sufficient condition to advance the case, and produced an output appropriate to that classification.

Three independent scores per lead — classification accuracy, action appropriateness, output scope. Three different diagnostics. Three different targets for iteration.

**Feedback loop.** Every underwriter decision on an escalated lead is captured in `eval/feedback/`. `integrator.py` turns those decisions into eval signal — did the agent's classification match what the underwriter found? Did the escalation framing give the underwriter what they needed? This is the mechanism by which the system compounds. The agent gets better by watching which judgments underwriters confirmed and which they corrected.

---

## How to Run

### Requirements

```bash
pip install -r requirements.txt
```

### Start provided services

```bash
docker-compose up
```

### Run with mock LLM — no credentials required

```bash
python -m api.main --mock
```

### Run with Anthropic backend

```bash
ANTHROPIC_API_KEY=sk-... python -m api.main
```

### Frontend

Deployed on Vercel. Set `NEXT_PUBLIC_API_URL` in `.env.example` to your Railway backend URL or local tunnel address.

---

## Known Limitations

Only three FigJam pages are encoded. Leads triggering unencoded decision paths are escalated with an explicit boundary description rather than silently mishandled.

Hard stops are deterministic and do not account for Tier 1 broker exceptions that may exist in the electrical systems flow. That exception path is noted as a priority addition in the roadmap.

The qualitative eval criteria reflect our current epistemic framework for the domain. They will need refinement as underwriter feedback accumulates and the edge case population grows.

Fixtures are static for presentation stability. The provided lead generator is included in docker-compose for development and iteration use.

The feedback integrator captures underwriter decisions but does not yet automatically retrain or update the qualitative eval criteria. That integration is the next iteration after the POC.

Replacement cost derivation is stubbed. The field registry marks it as `editableByProducer: false` — in production this would be fetched from a third party valuation service. For the POC the agent flags it as a required derivation and notes it cannot be requested from the producer.

---

## Production Roadmap

### Remaining playbook pages

Fire Simulation, Roof Class, Siding, Post & Pier Foundations, Plumbing, Swimming Pools, Trusts & LLCs, Replacement Cost — prioritized in that order based on frequency of appearance in the lead payload and consequence of misclassification.

### Knowledge graph — ArangoDB

The relational risk model this system reasons about — the connections between insured identity, property conditions, geographic exposure, and institutional risk appetite — is a graph problem. ArangoDB's multi-model architecture supports document, graph, and key-value in a single store, which means the ontology can evolve toward a graph representation without a storage migration. Neo4j was evaluated and rejected — its failure modes in regulated verticals at scale and licensing constraints make it an inappropriate foundation for a system that will touch claims data.

### Third party integrations

GIS lookup for hydrant proximity and road access. ISO PPC lookup by address. Wildfire risk scoring for P(F) derivation. Replacement cost valuation service. Each replaces a current stub without touching the agent or eval layers — the service interface in `api/services/` abstracts the source.

### Proxy drift detection

The analyzer in `eval/results/` is the embryonic form of a portfolio-level pattern detector. In production it monitors whether rating factors are producing systematically different outcomes than historical loss data would predict — the early warning system for unknown unknowns in the process of becoming known ones.

### Feedback loop maturation

Underwriter decisions currently feed into eval signal manually. The next iteration closes the loop automatically — confirmed flags strengthen qualitative criteria, dismissed flags weaken them, and the criteria file is versioned so every change is reviewable.
