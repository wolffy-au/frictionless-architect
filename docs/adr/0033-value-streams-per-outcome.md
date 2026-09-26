# ADR-0033: One value stream per outcome, organised by value recipient

- **Status:** Accepted
- **Date:** 2026-09-26
- **Sources:** this session; `architecture/model/elements.yaml` §A (Goal & Outcomes, Value streams), `architecture/model/relationships.yaml` §A; amends [ADR-0027](0027-capability-value-stream-and-motivation-spine.md) decisions 3–5

## Context

ADR-0027 gave the capability layer a single value stream, *Governed
Architecture Delivery*, realizing the single outcome *Architecture as
Executable Intelligence*. The goal has since been split into four outcomes,
each answering one assessment:

| Assessment | Outcome |
|---|---|
| Time-to-market falling behind AI-native competitors | Approved Change Reaches Production at AI Speed |
| Manual compliance evidence too slow and error-prone | Compliance Proven Before Release |
| Human review cannot keep pace with AI-speed delivery | Accountable, Auditable Automation |
| Architectural drift accumulating as unmanaged risk | Drift Detected and Reconciled Continuously |

One stream could no longer honestly realize all four: it realized only the
(renamed) drift outcome, reading as though the whole delivery stream existed
to control drift. Per-role value streams (one per section-B `BusinessRole`)
were considered and rejected — see Alternatives.

## Decision

1. **One value stream per outcome.** Each stream `Realization`-links to
   exactly one outcome and `Association`-links to the stakeholders who receive
   that value:

   | Value stream | Realizes | Value recipients | Stages |
   |---|---|---|---|
   | Governed Architecture Delivery | Change at AI Speed | Delivery Organisation, Executive Leadership & Board | Establish Reuse Baseline → Specify → Build Under Supervision → Release to Production |
   | Obligation to Evidence | Compliance Proven Before Release | Risk & Compliance, APRA | Establish Control Baseline → Prove Compliance |
   | Exception to Decision | Accountable, Auditable Automation | Executive Leadership & Board, Risk & Compliance | Escalate Non-Standard Change → Decide & Sign Off → Record as Evidence |
   | Drift to Remediation | Drift Detected and Reconciled | Enterprise Architecture Function | Observe As-Built State → Reconcile & Remediate |

2. **The new streams take stages over from the delivery stream** rather than
   duplicating them: *Prove Compliance* moves to Obligation to Evidence,
   *Reconcile & Remediate* to Drift to Remediation; *Establish Control & Reuse
   Baseline* splits into a reuse baseline (delivery) and a control baseline
   (compliance); *Release & Attest* becomes *Release to Production*, its
   sign-off and ledger-recording halves becoming Exception to Decision's
   stages. Stage ids are kept where a stage survives.

3. **Streams hand off across stage boundaries.** Build → Prove → Release
   (`Triggering`); Prove → Escalate for changes that cannot be validated
   deterministically; Sign Off → Release as a `Flow` ("approval") — a
   `Triggering` there would make Prove → Release derived via the escalation
   path; Release → Observe; Reconcile → Specify (`Flow`, drift remediation
   re-enters delivery).

4. **The phrase "architecture as executable intelligence"** lives in the
   delivery stream's description, not in an outcome name — it describes a
   means, not a measurable end result.

5. **No derived relationships in the motivation or stream chains.**
   Assessment → Outcome → Goal (not Assessment → Goal); Requirement → Outcome
   (not Requirement → Goal); no Assessment → Requirement; each stage belongs
   to one stream.

## Consequences

- The skeleton grows from 1 stream + 6 stages to 4 streams + 11 stages, and
  from 1 outcome to 4. The Strategy and Outcome Realization views show all four.
- Every outcome now has a traceable why (its assessment), how (its
  requirements) and delivery (its stream).
- The Value Stream view is split so each diagram stays readable: one
  view per stream (its stages, the capabilities serving them, recipients
  and outcome) and a *Value Stream Hand-offs* view showing only the 11
  stages and the Triggering / Flow edges within and across streams.
- Who *does* the work — the roles' journeys — belongs in the business layer:
  the `bfn-*` business functions could be re-cut to align with role journeys
  (noted in `elements.yaml`, not yet done).

## Alternatives considered

- **One value stream per role (customer journeys).** Rejected: ArchiMate 3.2
  defines a value stream as "a sequence of activities that create an overall
  result for a customer, stakeholder, or end user" — it is organised around
  who receives the value, not who performs it. Role journeys are business
  processes/functions.
- **Keep one stream realizing all four outcomes.** Rejected: a single stream
  cannot show which stages produce which outcome, and its stakeholder
  associations blur together.
- **New streams duplicating the delivery stream's stages.** Rejected: the
  same stage in two streams is two elements for one activity.
