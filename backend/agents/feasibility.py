"""Feasibility Agent – assesses buildability, cost estimates, and risks.

Evaluates whether a student could realistically build the described product,
identifies potential failure points, and estimates costs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from backend.schemas import (
    BillOfMaterials,
    ConceptModel,
    FeasibilityLevel,
    FeasibilityReport,
    FeasibilityRisk,
)

logger = logging.getLogger("reality_compiler.feasibility_agent")

FEASIBILITY_SYSTEM_PROMPT = """You are a hardware feasibility assessment agent. Given a product description and bill of materials, assess the buildability and provide cost estimates.

Return ONLY valid JSON matching this schema:
{
  "score": "green" | "yellow" | "red",
  "summary": "Brief overall assessment",
  "risks": [
    {
      "area": "Risk category (e.g. Mechanical, Electrical, Assembly)",
      "description": "What might fail and why",
      "severity": "green" | "yellow" | "red"
    }
  ],
  "prototype_cost_gbp": 0.0,
  "manufacturing_unit_cost_gbp": 0.0
}

Assessment criteria:
- green: A motivated student could build this in a weekend with common tools
- yellow: Buildable but requires some specialized tools/skills or has moderate risks
- red: Significant challenges, requires professional equipment or expert knowledge

Be realistic about risks. Common issues include:
- Tolerance/fit issues with 3D printed parts
- Power/heat management in electronics
- Waterproofing challenges
- Structural strength under load
- Cost of specialized components"""


async def generate_feasibility(
    prompt: str,
    bom: BillOfMaterials,
    model: ConceptModel,
    previous_report: Optional[FeasibilityReport] = None,
    iteration_command: Optional[str] = None,
) -> FeasibilityReport:
    logger.info("Feasibility agent: assessing '%s'", prompt[:80])

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return await _generate_with_openai(prompt, bom, api_key)
        except Exception:
            logger.warning("OpenAI feasibility call failed, using heuristic", exc_info=True)

    return _generate_heuristic(prompt, bom)


async def _generate_with_openai(prompt: str, bom: BillOfMaterials, api_key: str) -> FeasibilityReport:
    import httpx

    bom_text = "\n".join(
        f"- {item.name} (x{item.quantity}): £{item.unit_cost_gbp:.2f} each – {item.specification}"
        for item in bom.items
    )
    user_content = f"Product: {prompt}\n\nBill of Materials:\n{bom_text}\nTotal BOM cost: £{bom.total_cost_gbp:.2f}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": FEASIBILITY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.5,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        logger.info("Feasibility agent: OpenAI score = %s", parsed.get("score"))
        return FeasibilityReport(**parsed)


def _generate_heuristic(prompt: str, bom: BillOfMaterials) -> FeasibilityReport:
    lp = prompt.lower()
    total_cost = bom.total_cost_gbp
    risks: list[FeasibilityRisk] = []
    prototype_multiplier = 1.3
    manufacturing_multiplier = 0.6

    if any(w in lp for w in ["motor", "servo", "actuator", "robot"]):
        risks.append(FeasibilityRisk(
            area="Electrical",
            description="Motor control requires proper H-bridge driver and adequate power supply. Stall current may exceed rated values.",
            severity=FeasibilityLevel.YELLOW,
        ))

    if any(w in lp for w in ["water", "liquid", "fluid"]):
        risks.append(FeasibilityRisk(
            area="Waterproofing",
            description="Any water-contact components need IP-rated enclosures. Silicone gaskets recommended at joints.",
            severity=FeasibilityLevel.YELLOW,
        ))

    if any(w in lp for w in ["precision", "cnc", "machined", "tolerance"]):
        risks.append(FeasibilityRisk(
            area="Manufacturing",
            description="Tight tolerances require CNC machining or precision 3D printing. FDM may not achieve required accuracy.",
            severity=FeasibilityLevel.RED,
        ))

    if any(w in lp for w in ["sensor", "detect", "measure"]):
        risks.append(FeasibilityRisk(
            area="Calibration",
            description="Sensor accuracy depends on proper calibration. Environmental factors (temperature, humidity) may affect readings.",
            severity=FeasibilityLevel.YELLOW,
        ))

    if total_cost > 100:
        risks.append(FeasibilityRisk(
            area="Cost",
            description=f"Total BOM cost of £{total_cost:.2f} is significant for a prototype. Consider value engineering to reduce costs.",
            severity=FeasibilityLevel.YELLOW,
        ))

    risks.append(FeasibilityRisk(
        area="Assembly",
        description="3D-printed enclosure parts may require post-processing (sanding, heat inserts) for reliable assembly.",
        severity=FeasibilityLevel.GREEN,
    ))

    risks.append(FeasibilityRisk(
        area="Structural",
        description="PLA/PETG prints are adequate for prototyping but may not withstand sustained mechanical loads. Consider reinforcement at stress points.",
        severity=FeasibilityLevel.YELLOW,
    ))

    red_count = sum(1 for r in risks if r.severity == FeasibilityLevel.RED)
    yellow_count = sum(1 for r in risks if r.severity == FeasibilityLevel.YELLOW)

    if red_count >= 2:
        score = FeasibilityLevel.RED
        summary = "Significant challenges identified. Professional tools or expertise likely required for successful build."
    elif red_count >= 1 or yellow_count >= 3:
        score = FeasibilityLevel.YELLOW
        summary = "Buildable with care. Some areas need attention — review risks before starting."
    else:
        score = FeasibilityLevel.GREEN
        summary = "Highly feasible for a student build. Standard tools and commonly available components."

    prototype_cost = total_cost * prototype_multiplier
    manufacturing_cost = total_cost * manufacturing_multiplier

    logger.info("Feasibility agent: score=%s, %d risks", score, len(risks))
    return FeasibilityReport(
        score=score,
        summary=summary,
        risks=risks,
        prototype_cost_gbp=round(prototype_cost, 2),
        manufacturing_unit_cost_gbp=round(manufacturing_cost, 2),
    )
