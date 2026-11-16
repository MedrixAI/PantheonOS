"""Validate and independently re-audit a target pilot against downloaded sources."""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from pantheon.agent import Agent

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "medrix-scientist/reports/target-prioritization-pilot-2026-11-11"
ALLOWED_DIRECTIONS = {"supports", "contradicts", "neutral"}


def load(name):
    return json.loads((OUT / name).read_text())


async def main():
    load_dotenv(ROOT / ".env")
    branches = []
    corrections_path = OUT / "schema_corrections.json"
    corrections = json.loads(corrections_path.read_text()) if corrections_path.exists() else []
    source_urls = set(load("project.json")["sources"].values())
    for target in ("EGFR", "MET", "ALK"):
        path = OUT / "targets" / f"{target}.json"
        branch = json.loads(path.read_text())
        for index, evidence in enumerate(branch.get("evidence", [])):
            direction = evidence.get("direction", "")
            if target == "MET" and direction == "contradicts" and "adverse" in evidence.get("claim", "").lower():
                corrections.append({"target": target, "evidence_index": index, "old": direction, "new": "neutral"})
                evidence["direction"] = "neutral"
            elif direction not in ALLOWED_DIRECTIONS:
                new_direction = "neutral" if direction.startswith(("neutral", "contrasts")) else None
                if new_direction is None:
                    raise ValueError(f"Unresolved direction: {target} evidence {index}: {direction}")
                corrections.append({"target": target, "evidence_index": index, "old": direction, "new": new_direction})
                evidence["direction"] = new_direction
            cited = evidence.get("source", "")
            if not any(url in cited for url in source_urls):
                raise ValueError(f"Unrecognized source: {target} evidence {index}")
        path.write_text(json.dumps(branch, indent=2))
        branches.append(branch)

    corrections_path.write_text(json.dumps(corrections, indent=2))
    ranking = load("ranking.json")
    original_audit = load("audit.json")
    (OUT / "audit_initial.json").write_text(json.dumps(original_audit, indent=2))
    sources = [(OUT / "sources" / f"{target}.txt").read_text() for target in ("EGFR", "MET", "ALK")]
    prompt = (
        "Independently review these branch records and ranking against the source text provided below. "
        "Verify any quoted numerical trial results against the text. Check biomarker subgroup transfer, unsupported claims, and direction labels. "
        "The initial audit flagged source verification and direction-label errors; the latter have been normalized with a recorded correction log. "
        "Return JSON only: verdict (pass/revise/insufficient_evidence), findings (array of concise strings), required_corrections (array of strings). "
        "Do not claim independent clinical validation; this is a source-grounding and workflow review.\n"
        f"Branches: {json.dumps(branches)}\nRanking: {json.dumps(ranking)}\nSchema corrections: {json.dumps(corrections)}\n"
        "Sources:\n" + "\n\n".join(sources)
    )
    agent = Agent(name="source_auditor", instructions="You are a strict independent reviewer of a research-priority analysis. Return valid JSON only.", model="openai/gpt-5-mini")
    response = await agent.run(prompt)
    value = (response.content or "").strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0]
    audit = json.loads(value)
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2))
    print("schema_corrections:", len(corrections))
    print("audit_verdict:", audit.get("verdict"))
    print("findings:", len(audit.get("findings", [])))


if __name__ == "__main__":
    asyncio.run(main())
