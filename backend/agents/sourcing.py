"""Sourcing Agent – finds real-world components and purchase links.

Generates search queries for Amazon UK, RS Components, and Alibaba
based on the bill of materials.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Optional

from backend.schemas import BillOfMaterials, BomItem, SourcingLink, SourcingResult, SourcePlatform

logger = logging.getLogger("reality_compiler.sourcing_agent")

SOURCING_SYSTEM_PROMPT = """You are a hardware sourcing agent. Given a product description and bill of materials, generate sourcing links for each component.

Return ONLY valid JSON matching this schema:
{
  "links": [
    {
      "component": "Component Name",
      "platform": "Amazon UK" | "RS Components" | "Alibaba",
      "search_query": "search terms for the platform",
      "url": "full search URL"
    }
  ]
}

For each BOM item, provide at least one link per platform (Amazon UK, RS Components, Alibaba).
Use realistic search terms that would find the actual component.
Generate proper search URLs for each platform."""

_PLATFORM_SEARCH_URLS = {
    SourcePlatform.AMAZON_UK: "https://www.amazon.co.uk/s?k={}",
    SourcePlatform.RS_COMPONENTS: "https://uk.rs-online.com/web/c/?searchTerm={}",
    SourcePlatform.ALIBABA: "https://www.alibaba.com/trade/search?SearchText={}",
}


async def generate_sourcing(
    prompt: str,
    bom: BillOfMaterials,
    previous_sourcing: Optional[SourcingResult] = None,
    iteration_command: Optional[str] = None,
) -> SourcingResult:
    logger.info("Sourcing agent: generating links for %d BOM items", len(bom.items))

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return await _generate_with_openai(prompt, bom, api_key)
        except Exception:
            logger.warning("OpenAI sourcing call failed, using heuristic", exc_info=True)

    return _generate_heuristic(bom)


async def _generate_with_openai(prompt: str, bom: BillOfMaterials, api_key: str) -> SourcingResult:
    import httpx

    bom_text = "\n".join(f"- {item.name}: {item.specification}" for item in bom.items)
    user_content = f"Product: {prompt}\n\nBill of Materials:\n{bom_text}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SOURCING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.5,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        logger.info("Sourcing agent: OpenAI returned %d links", len(parsed.get("links", [])))
        return SourcingResult(**parsed)


def _generate_heuristic(bom: BillOfMaterials) -> SourcingResult:
    links: list[SourcingLink] = []

    for item in bom.items:
        search_term = f"{item.name} {item.specification}".strip()
        for platform in SourcePlatform:
            encoded = urllib.parse.quote_plus(search_term)
            url = _PLATFORM_SEARCH_URLS[platform].format(encoded)
            links.append(SourcingLink(
                component=item.name,
                platform=platform,
                search_query=search_term,
                url=url,
            ))

    logger.info("Sourcing agent: generated %d heuristic links", len(links))
    return SourcingResult(links=links)
