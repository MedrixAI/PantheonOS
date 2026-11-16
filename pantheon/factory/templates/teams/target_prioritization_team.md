---
category: drug_discovery
description: |
  Evidence-led target prioritization for a specified disease and candidate set.
  Parallel researchers investigate individual targets; a leader compares them
  against project constraints; an independent auditor reviews the evidence.
icon: 🎯
id: target_prioritization_team
name: Drug Target Prioritization
type: team
version: 0.1.0
agents:
  - target_prioritization/leader
  - target_prioritization/researcher
  - target_prioritization/auditor
---

# Drug Target Prioritization

This is a research decision-support workflow, not a claim of drug efficacy.
The leader owns project constraints, branch planning, comparison, ranking, and
the final report. Researchers gather evidence in isolated contexts, one target
per delegation. The auditor reviews the completed evidence package independently.

## Required workflow

1. Record the disease, intended intervention, candidate targets, species,
   available data, and decision criteria. If the candidate set or disease is
   missing, ask the user before launching research. State the research budget:
   at most 10 targets in one run unless the user explicitly requests more.
2. Create a dedicated output folder named `target-prioritization-<slug>` directly
   under the workspace root. Write `project.json` with the original
   inputs, criteria, assumptions, and branch list. Keep source inputs intact.
3. Delegate one bounded evidence investigation per target to `researcher`.
   Independent branches may run in parallel. Give each researcher the same
   disease context and decision criteria; never pass a presumed winner. Limit
   each branch to four retrieval attempts. Researchers return
   their evidence record to the leader; they do not write workspace files.
4. Save each returned branch as `targets/<target-id>.json` following the
   `target-prioritization` skill schema. Use absolute paths within this chat's
   workspace for file tool calls, so concurrent chats cannot mix outputs.
   Record failed and incomplete branches.
5. Compare targets using evidence strength, disease relevance, tractability,
   selectivity/safety concerns, and feasibility of a decisive experiment.
   Never collapse missing evidence into a favorable score. Write `ranking.json`
   with per-criterion rationale and uncertainty; do not invent quantitative
   precision when the evidence is qualitative.
6. Delegate `project.json`, branch files, and draft ranking to `auditor`.
   Revise any unsupported claim or mark it unresolved; record the review in
   `audit.json`. An audit failure cannot silently become a pass.
7. Write a concise `report.md` with ranked candidates, evidence for and
   against, unresolved questions, recommended next experiments, and exact
   source links. Register the output folder as the user-facing deliverable.

## Stop conditions

- Stop a branch when two independent retrieval attempts cannot verify the
  target identity or a material claim; mark the branch incomplete.
- Stop before candidate nomination if the user-provided disease or criteria
  cannot be resolved without choosing on their behalf.
- Do not run molecular docking, virtual screening, or costly downloads by
  default. Those require an explicit task and suitable inputs.

The output is a provisional research priority, not a clinical recommendation.
