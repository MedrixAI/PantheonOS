---
id: target-prioritization
name: Target Prioritization Decision Guide
description: |
  Compare candidate drug targets for a defined disease using source-linked
  evidence, explicit decision criteria, independent branches, and audit.
tags: [drug_discovery, target_prioritization, evidence, research]
---

# Target prioritization decision guide

Use this skill for research prioritization of named biological targets. It does
not supply target facts by itself; all facts must come from identified sources.

## Decision rules

1. Normalize target identifier, alias, organism, and disease context. Keep
   ambiguous identities separate until resolved.
2. Prefer direct human disease genetics and causal perturbation evidence to
   expression correlation alone. State study population, model, endpoint, and
   direction of effect. A review is a discovery route, not primary evidence.
3. Treat association, mechanism, tractability, and safety as separate axes.
   A strong association cannot substitute for a viable intervention modality.
4. Record contradictory and null findings, model limitations, tissue context,
   and potential on-target liabilities. Missing data means unknown, not safe.
5. Compare candidates against the user's criteria before producing an overall
   order. Use ordinal judgments with rationale unless calibrated numeric data
   and a justified weighting scheme exist.
6. Recommend the smallest informative next experiment for each leading target,
   including a measurable readout and a result that would weaken the hypothesis.

## Branch record (`targets/<target-id>.json`)

```json
{
  "target_id": "stable identifier or explicitly unresolved",
  "symbol": "gene/protein symbol",
  "organism": "species",
  "disease": "specified disease",
  "status": "complete | incomplete | identity_unresolved",
  "evidence": [
    {
      "claim": "specific finding",
      "direction": "supports | contradicts | neutral",
      "kind": "human_genetics | perturbation | clinical | preclinical | computational | review | other",
      "source": "URL, DOI, PMID, or database record ID",
      "measured_endpoint": "what was actually observed",
      "limitations": "study and inference limits"
    }
  ],
  "tractability": "modality and supporting evidence, or unknown",
  "safety_selectivity": "evidence and uncertainty, or unknown",
  "open_questions": [],
  "next_experiment": "test, readout, and disconfirming outcome"
}
```

`project.json` records the input and criteria, with a `branches` array of
objects containing `target_id` and `status`. `ranking.json` contains
`ordered_targets` (target ID array) and `rankings` (objects with `target_id`,
`rationale`, and criterion-level reasons), plus unresolved tradeoffs and
excluded or incomplete branches. `audit.json` contains `verdict` (`pass`,
`revise`, or `insufficient_evidence`), `findings` (string array), and
`required_corrections` (string array).
The final report links these files and distinguishes findings from hypotheses.

This skill is a human-authored initial decision guide. Do not describe it as
Paper2Skill-extracted or experimentally validated.
