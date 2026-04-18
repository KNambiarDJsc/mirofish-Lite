"""
Ontology Generator — AXonic
Indian marketing campaign ontology with consumer-segment, influencer-hierarchy,
peer/family-group, and private-network (FORWARDS_TO / VALIDATES / DOUBTS /
RECOMMENDS) edge types.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


ONTOLOGY_SYSTEM_PROMPT = """You are an expert ontology designer for Indian marketing campaign simulation.

Output ONLY valid JSON — no markdown, no commentary.

## Purpose
Design entities + edges that simulate how Indian audiences (Tier1/2/3, varied SEC, varied language) react to a marketing campaign — including private WhatsApp/peer-network amplification, not just public social media.

## Valid entity types (real actors — can post/react)

**Consumer segments (behavior-aware):**
- Tier1Consumer / Tier2Consumer / Tier3Consumer (geography)
- HNIConsumer / MassConsumer / AspirationalConsumer (income/intent)
- Student / Parent / HomemakerConsumer / UrbanProfessional (life stage)
- ConsumerSegment (abstract cluster with shared behaviour — use when simulating group-level reaction)

**Influencer hierarchy (India runs on this):**
- NanoInfluencer / MicroInfluencer / MegaCreator
- Reviewer / FinfluencerCreator / FoodCreator / AutoInfluencer / EducationInfluencer
- RegionalInfluencer

**Networks (private amplification — critical for India):**
- PeerGroup    (friend circles — validate or doubt)
- FamilyGroup  (WhatsApp family groups — where final decisions happen)
- MediaAmplifier (any entity whose role is to amplify, regardless of domain)

**Brands / retail / media / regulators:**
- Brand / CompetitorBrand
- MediaOutlet / RegionalMediaOutlet / FinMediaOutlet / EducationMediaOutlet
- Regulator / ASCIRegulator / SEBIRegulator / FSSAIRegulator
- Retailer / QuickCommercePlatform / ModernTradeRetailer / KiranaRetailer
- Platform / Bank / University / Agency

## Invalid (abstract — do NOT use)
"Sentiment", "Trend", "Virality", "Engagement", "Youth opinion", "Market demand", "Backlash"

## Output

```json
{
    "entity_types": [
        {
            "name": "EntityType (PascalCase)",
            "description": "<100 char description",
            "attributes": [
                {"name": "attr (snake_case)", "type": "text", "description": "..."}
            ],
            "examples": ["ex1", "ex2"]
        }
    ],
    "edge_types": [
        {
            "name": "EDGE_NAME (UPPER_SNAKE_CASE)",
            "description": "<100 char",
            "source_targets": [{"source": "Type1", "target": "Type2"}],
            "attributes": []
        }
    ],
    "analysis_summary": "2–3 sentences"
}
```

## Rules

### Entity types — EXACTLY 10
1. First 8 = campaign-specific Indian marketing entities
2. Last 2 = fallbacks `Person`, `Organization`

### Edge types — 6 to 10, MUST include at least ONE private-network edge
Required Indian-market edges (use whichever fit the campaign):

- PROMOTES / ENDORSES                 — Brand/Creator → audience
- REVIEWS                             — Reviewer → Product/Brand
- RECOMMENDS_TO                       — Consumer/PeerGroup → Consumer (peer validation)
- VALIDATES                           — PeerGroup/FamilyGroup → Brand/Product (social proof)
- DOUBTS                              — Consumer/Peer → Brand (skepticism, trust gap)
- COMPETES_WITH / COMPARES_TO         — Brand ↔ CompetitorBrand
- AMPLIFIES                           — Media/Influencer/MediaAmplifier → Brand
- FORWARDS_TO                         — Consumer/FamilyGroup → Consumer (WhatsApp virality — HIGHEST impact edge in India)
- COMPLAINS_ABOUT                     — Consumer → Brand
- DISTRIBUTES                         — Retailer → Brand
- REGULATES                           — Regulator → Brand
- TARGETS                             — Brand → ConsumerSegment

At least ONE of FORWARDS_TO / VALIDATES / DOUBTS / RECOMMENDS_TO must be present — these model the private network that drives Indian purchase decisions.

### Attributes
1–3 per entity. Reserved (DO NOT USE): `name`, `uuid`, `group_id`, `created_at`, `summary`.
Use: `full_name`, `brand_name`, `tier`, `sec`, `primary_language`, `city`, `role`, `follower_count`, `specialization`, `org_type`, `group_size`, `relation_type`.
"""


class OntologyGenerator:
    MAX_TEXT_LENGTH_FOR_LLM = 2000

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_message = self._build_user_message(
            document_texts, simulation_requirement, additional_context
        )
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        result = self.llm_client.chat_json(
            messages=messages, temperature=0.3, max_tokens=4096,
        )
        return self._validate_and_process(result)

    def _build_user_message(
        self, document_texts, simulation_requirement, additional_context,
    ) -> str:
        combined = "\n\n---\n\n".join(document_texts)
        original_len = len(combined)
        if len(combined) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined = combined[: self.MAX_TEXT_LENGTH_FOR_LLM]
            combined += f"\n\n...(truncated — original {original_len} chars)..."

        msg = f"""## Campaign Requirement
{simulation_requirement}

## Strategy Document
{combined}
"""
        if additional_context:
            msg += f"\n## Additional Context\n{additional_context}\n"

        msg += """
Design entity + edge types for simulating Indian audience reaction.

MANDATORY:
1. EXACTLY 10 entity types — last 2 are `Person` and `Organization` (fallbacks)
2. First 8 are campaign-specific Indian marketing entities (consumer segments, influencer hierarchy, brand/media/retail)
3. 6–10 edge types, at least ONE of FORWARDS_TO / VALIDATES / DOUBTS / RECOMMENDS_TO
4. Reserved words — NEVER use `name`, `uuid`, `group_id` as attributes; use `full_name`, `brand_name`, `tier`, `relation_type`, etc.
5. All text in English.
"""
        return msg

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        result.setdefault("entity_types", [])
        result.setdefault("edge_types", [])
        result.setdefault("analysis_summary", "")

        for entity in result["entity_types"]:
            entity.setdefault("attributes", [])
            entity.setdefault("examples", [])
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."

        for edge in result["edge_types"]:
            edge.setdefault("source_targets", [])
            edge.setdefault("attributes", [])
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."

        MAX_ENTITIES, MAX_EDGES = 10, 10

        person_fallback = {
            "name": "Person",
            "description": "Any Indian individual not fitting a more specific consumer type.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name"},
                {"name": "tier", "type": "text", "description": "Tier1/Tier2/Tier3 by city"},
                {"name": "primary_language", "type": "text", "description": "Primary language"},
            ],
            "examples": ["anonymous urban consumer", "first-time online buyer"],
        }
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting a more specific organization type.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name"},
                {"name": "org_type", "type": "text", "description": "Brand/Agency/Platform/Retailer/Media/Regulator"},
            ],
            "examples": ["small D2C brand", "local distribution partner"],
        }

        names = {e["name"] for e in result["entity_types"]}
        to_add = []
        if "Person" not in names:
            to_add.append(person_fallback)
        if "Organization" not in names:
            to_add.append(organization_fallback)

        if to_add:
            current = len(result["entity_types"])
            if current + len(to_add) > MAX_ENTITIES:
                result["entity_types"] = result["entity_types"][: MAX_ENTITIES - len(to_add)]
            result["entity_types"].extend(to_add)

        result["entity_types"] = result["entity_types"][:MAX_ENTITIES]
        result["edge_types"] = result["edge_types"][:MAX_EDGES]

        # Guarantee at least one private-network edge
        edge_names = {e["name"] for e in result["edge_types"]}
        private_net_edges = {"FORWARDS_TO", "VALIDATES", "DOUBTS", "RECOMMENDS_TO"}
        if not (edge_names & private_net_edges) and len(result["edge_types"]) < MAX_EDGES:
            result["edge_types"].append({
                "name": "FORWARDS_TO",
                "description": "Private-network forward (WhatsApp/peer) — virality backbone in India.",
                "source_targets": [
                    {"source": "Person", "target": "Person"},
                    {"source": "FamilyGroup", "target": "Person"},
                ],
                "attributes": [
                    {"name": "trust_boost", "type": "text", "description": "Trust added via private forward"}
                ],
            })

        return result

    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """Generate Zep-compatible Python module from ontology dict."""
        lines = [
            '"""',
            'Custom entity type definitions',
            'Auto-generated by AXonic for Indian marketing campaign simulation',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Entity type definitions ==============',
            '',
        ]

        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            lines.append(f'class {name}(EntityModel):')
            lines.append(f'    """{desc}"""')
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    lines.append(f'    {attr["name"]}: EntityText = Field(')
                    lines.append(f'        description="{attr.get("description", attr["name"])}",')
                    lines.append(f'        default=None')
                    lines.append(f'    )')
            else:
                lines.append('    pass')
            lines.append('')
            lines.append('')

        lines.append('# ============== Relationship type definitions ==============')
        lines.append('')

        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(w.capitalize() for w in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            lines.append(f'class {class_name}(EdgeModel):')
            lines.append(f'    """{desc}"""')
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    lines.append(f'    {attr["name"]}: EntityText = Field(')
                    lines.append(f'        description="{attr.get("description", attr["name"])}",')
                    lines.append(f'        default=None')
                    lines.append(f'    )')
            else:
                lines.append('    pass')
            lines.append('')
            lines.append('')

        lines.append('# ============== Type configuration ==============')
        lines.append('')
        lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            lines.append(f'    "{entity["name"]}": {entity["name"]},')
        lines.append('}')
        lines.append('')
        lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            class_name = ''.join(w.capitalize() for w in edge["name"].split('_'))
            lines.append(f'    "{edge["name"]}": {class_name},')
        lines.append('}')
        lines.append('')
        lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            sts = edge.get("source_targets", [])
            if sts:
                st_str = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in sts
                ])
                lines.append(f'    "{edge["name"]}": [{st_str}],')
        lines.append('}')

        return '\n'.join(lines)