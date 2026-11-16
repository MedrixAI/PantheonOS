"""Bounded real-source target pilot using PantheonOS Agents."""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pantheon.agent import Agent
from pantheon.factory.template_manager import TemplateManager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "medrix-scientist/reports/target-prioritization-pilot-2026-11-11"
SOURCES = {
    "EGFR": "https://www.fda.gov/drugs/cancer-approvals/fda-approves-osimertinib-chemotherapy-egfr-mutated-non-small-cell-lung-cancer",
    "MET": "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-tepotinib-metastatic-non-small-cell-lung-cancer",
    "ALK": "https://www.fda.gov/drugs/cancer-approvals/fda-approves-ensartinib-alk-positive-locally-advanced-or-metastatic-non-small-cell-lung-cancer",
}


async def ask(name, instructions, prompt):
    agent = Agent(name=name, instructions=instructions + "\nReturn valid JSON only.", model="openai/gpt-5-mini")
    response = await agent.run(prompt)
    value = (response.content or "").strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(value)


async def main():
    load_dotenv(ROOT / ".env")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "targets").mkdir(exist_ok=True)
    (OUT / "sources").mkdir(exist_ok=True)
    source_texts = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for target, url in SOURCES.items():
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()
            text = (soup.find("main") or soup).get_text("\n", strip=True)[:12000]
            source = f"Source: {url}\nRetrieved: {datetime.now(timezone.utc).isoformat()}\n{text}"
            (OUT / "sources" / f"{target}.txt").write_text(source)
            source_texts.append(source)

    manager = TemplateManager(work_dir=OUT)
    template = manager.get_template("target_prioritization_team")
    configs, _, _ = manager.prepare_team(template)
    skill = (ROOT / "pantheon/factory/templates/skills/target_prioritization/SKILL.md").read_text()
    context = "Metastatic NSCLC with confirmed EGFR exon 19 deletion; MET and ALK status unknown. Research priority only, not treatment advice."
    project = {"disease": context, "criteria": ["biomarker relevance", "direct evidence", "tractability", "uncertainty", "next experiment"], "branches": [{"target_id": t, "status": "planned"} for t in SOURCES], "sources": SOURCES}
    (OUT / "project.json").write_text(json.dumps(project, indent=2))

    async def research(target):
        prompt = f"Investigate {target} only. Context: {context}\nUse only these exact primary-source texts. Distinguish other biomarker populations from the EGFR-mutated case. Return a branch JSON matching the skill schema.\n" + "\n\n".join(source_texts)
        data = await ask(f"researcher_{target}", configs["researcher"]["instructions"] + skill, prompt)
        data["target_id"] = target
        (OUT / "targets" / f"{target}.json").write_text(json.dumps(data, indent=2))
        return data

    branches = await asyncio.gather(*(research(target) for target in SOURCES))
    for branch in project["branches"]:
        branch["status"] = next(b.get("status", "incomplete") for b in branches if b["target_id"] == branch["target_id"])
    (OUT / "project.json").write_text(json.dumps(project, indent=2))
    ranking = await ask("leader", configs["leader"]["instructions"][-3500:] + skill,
        f"Compare these branches for the exact EGFR exon 19 deletion context: {json.dumps(branches)}. Return JSON with ordered_targets, rankings (target_id, rationale, criterion_reasons), unresolved_tradeoffs, excluded_or_incomplete. Do not transfer evidence from ALK-positive or MET exon 14 populations.")
    (OUT / "ranking.json").write_text(json.dumps(ranking, indent=2))
    audit = await ask("auditor", configs["auditor"]["instructions"],
        f"Independently audit this research ranking. Context: {context}\nBranches: {json.dumps(branches)}\nRanking: {json.dumps(ranking)}\nCheck source links, biomarker subgroup mismatch, missing evidence, and overclaiming. Return JSON with verdict, findings array, required_corrections array.")
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2))
    report = ["# Target prioritization pilot", "", context, "", "## Ranking", ""]
    report += [f"- **{item.get('target_id', '?')}**: {item.get('rationale', '')}" for item in ranking.get("rankings", [])]
    report += ["", "## Audit", "", f"Verdict: {audit.get('verdict', 'unknown')}"]
    report += [f"- {item}" for item in audit.get("findings", [])]
    report += ["", "## Primary sources", ""] + [f"- {url}" for url in SOURCES.values()]
    (OUT / "report.md").write_text("\n".join(report) + "\n")
    print("output_dir:", OUT)
    print("branches:", [b.get("status") for b in branches])
    print("ranking:", ranking.get("ordered_targets"))
    print("audit:", audit.get("verdict"))


if __name__ == "__main__":
    asyncio.run(main())
