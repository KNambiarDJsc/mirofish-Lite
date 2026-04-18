"""
Report Agent — AXonic (Indian Market Campaign Decision Engine)

ReAct-based report generator:
  1. Plans a 2-section outline (Decision + Personas/Private-Network)
  2. Generates each section via tool-driven ReAct loop
  3. Produces per-section files + assembled full_report.md
  4. Logs every step to agent_log.jsonl + console_log.txt
"""

import os
import json
import re
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.gemini_service import GeminiService
from .supabase_memory import get_memory, get_client


# ═══════════════════════════════════════════════════════════════════════════════
# Search service
# ═══════════════════════════════════════════════════════════════════════════════

class SearchResult:
    def __init__(self, facts=None, nodes=None):
        self.facts = facts or []
        self.nodes = nodes or []

    def to_text(self):
        return "\n".join(f"- {f}" for f in self.facts[:20]) or "No results found."


InsightForgeResult = SearchResult
PanoramaResult = SearchResult
InterviewResult = SearchResult


class SupabaseSearchService:
    """Supabase-backed search service."""

    def __init__(self):
        self.memory = get_memory()
        self.gemini = GeminiService.get_instance()

    def quick_search(self, graph_id: str, query: str, limit: int = 10) -> SearchResult:
        edges = self.memory.search_edges(graph_id, query, top_k=limit)
        facts = [e.get("fact", "") for e in edges if e.get("fact")]
        return SearchResult(facts=facts)

    def insight_forge(
        self, graph_id: str, query: str,
        simulation_requirement: str = "", report_context: str = "",
    ) -> SearchResult:
        edges = self.memory.search_edges(graph_id, query, top_k=15)
        nodes = self.memory.search_nodes(graph_id, query, top_k=5)
        facts = [e.get("fact", "") for e in edges if e.get("fact")]
        node_summaries = [
            f"{n.get('name', '')}: {n.get('summary', '')}"
            for n in nodes if n.get("summary")
        ]
        return SearchResult(facts=facts + node_summaries)

    def panorama_search(
        self, graph_id: str, query: str, include_expired: bool = True,
    ) -> SearchResult:
        all_edges = self.memory.get_all_edges(graph_id)
        facts = [e.get("fact", "") for e in all_edges if e.get("fact")]
        q = query.lower()
        relevant = [f for f in facts if q in f.lower()] if q else facts
        return SearchResult(facts=relevant[:30])

    def get_graph_statistics(self, graph_id: str) -> dict:
        return self.memory.get_graph_stats(graph_id)

    def get_entity_summary(self, graph_id: str, entity_name: str) -> dict:
        nodes = self.memory.search_nodes(graph_id, entity_name, top_k=1)
        return nodes[0] if nodes else {"name": entity_name, "summary": "Not found"}

    def get_entities_by_type(self, graph_id: str, entity_type: str):
        from .supabase_entity_reader import SupabaseEntityReader
        reader = SupabaseEntityReader()
        return reader.get_entities_by_type(graph_id, entity_type)

    def interview_agents(self, simulation_id: str, query: str, limit: int = 5) -> SearchResult:
        """Find and 'interview' specific agents based on a query."""
        try:
            client = get_client()
            # Perform a keyword search on persona/bio/archetype
            res = (
                client.table("personas")
                .select("name, tier, archetype, persona, bio")
                .eq("simulation_id", simulation_id)
                .or_(f"persona.ilike.%{query}%,bio.ilike.%{query}%,archetype.ilike.%{query}%")
                .limit(limit)
                .execute()
            )
            rows = res.data or []
            facts = [
                f"Agent {r['name']} ({r['tier']}, {r['archetype']}): {r['persona']}"
                for r in rows
            ]
            return SearchResult(facts=facts)
        except Exception as e:
            logger.error(f"Interview agents failed: {e}")
            return SearchResult(facts=[f"Error interviewing agents: {str(e)}"])

    def get_persona_analytics(self, simulation_id: str) -> Dict[str, Any]:
        """Call RPC to get math-heavy tier/trait distributions."""
        try:
            client = get_client()
            res = client.rpc("get_persona_tier_distribution", {"p_simulation_id": simulation_id}).execute()
            return {"tier_distribution": res.data or []}
        except Exception as e:
            logger.error(f"Persona analytics failed: {e}")
            return {"tier_distribution": [], "error": str(e)}

    def get_simulation_context(
        self, graph_id: str, simulation_id: str = "", simulation_requirement: str = "",
    ) -> dict:
        stats = self.get_graph_statistics(graph_id)
        related = self.insight_forge(graph_id, simulation_requirement or "all events")
        related_facts = related.facts[:15]
        
        persona_stats = {}
        if simulation_id:
            persona_stats = self.get_persona_analytics(simulation_id)

        return {
            "graph_statistics": {
                "total_nodes": stats.get("node_count", 0),
                "total_edges": stats.get("edge_count", 0),
            },
            "entity_types": stats.get("entity_types", {}),
            "total_entities": stats.get("node_count", 0),
            "persona_analytics": persona_stats,
            "related_facts": related_facts,
            "related_facts_json": json.dumps(related_facts, ensure_ascii=False, indent=2),
        }


ZepToolsService = SupabaseSearchService
logger = get_logger('axonic.report_agent')


# ═══════════════════════════════════════════════════════════════════════════════
# Loggers
# ═══════════════════════════════════════════════════════════════════════════════

class ReportLogger:
    """Structured JSONL logger written to report folder."""

    def __init__(self, report_id: str):
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

    def _elapsed(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def log(self, action, stage, details, section_title=None, section_index=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._elapsed(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details,
        }
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_start(self, simulation_id, graph_id, simulation_requirement):
        self.log("report_start", "pending", {
            "simulation_id": simulation_id,
            "graph_id": graph_id,
            "simulation_requirement": simulation_requirement,
            "message": "Report generation started",
        })

    def log_planning_start(self):
        self.log("planning_start", "planning", {"message": "Planning outline"})

    def log_planning_context(self, context):
        self.log("planning_context", "planning", {
            "message": "Fetched simulation context", "context": context,
        })

    def log_planning_complete(self, outline_dict):
        self.log("planning_complete", "planning", {
            "message": "Outline planned", "outline": outline_dict,
        })

    def log_section_start(self, section_title, section_index):
        self.log("section_start", "generating",
                 {"message": f"Section started: {section_title}"},
                 section_title=section_title, section_index=section_index)

    def log_react_thought(self, section_title, section_index, iteration, thought):
        self.log("react_thought", "generating", {
            "iteration": iteration, "thought": thought,
            "message": f"ReAct iter {iteration}",
        }, section_title=section_title, section_index=section_index)

    def log_tool_call(self, section_title, section_index, tool_name, parameters, iteration):
        self.log("tool_call", "generating", {
            "iteration": iteration, "tool_name": tool_name,
            "parameters": parameters,
            "message": f"Tool call: {tool_name}",
        }, section_title=section_title, section_index=section_index)

    def log_tool_result(self, section_title, section_index, tool_name, result, iteration):
        self.log("tool_result", "generating", {
            "iteration": iteration, "tool_name": tool_name,
            "result": result, "result_length": len(result),
            "message": f"Tool {tool_name} returned",
        }, section_title=section_title, section_index=section_index)

    def log_llm_response(self, section_title, section_index, response, iteration,
                         has_tool_calls, has_final_answer):
        self.log("llm_response", "generating", {
            "iteration": iteration, "response": response,
            "response_length": len(response),
            "has_tool_calls": has_tool_calls,
            "has_final_answer": has_final_answer,
            "message": f"LLM response (tools={has_tool_calls}, final={has_final_answer})",
        }, section_title=section_title, section_index=section_index)

    def log_section_content(self, section_title, section_index, content, tool_calls_count):
        self.log("section_content", "generating", {
            "content": content, "content_length": len(content),
            "tool_calls_count": tool_calls_count,
            "message": f"Section content: {section_title}",
        }, section_title=section_title, section_index=section_index)

    def log_section_full_complete(self, section_title, section_index, full_content):
        self.log("section_complete", "generating", {
            "content": full_content, "content_length": len(full_content),
            "message": f"Section complete: {section_title}",
        }, section_title=section_title, section_index=section_index)

    def log_report_complete(self, total_sections, total_time_seconds):
        self.log("report_complete", "completed", {
            "total_sections": total_sections,
            "total_time_seconds": round(total_time_seconds, 2),
            "message": "Report complete",
        })

    def log_error(self, error_message, stage, section_title=None):
        self.log("error", stage,
                 {"error": error_message, "message": f"Error: {error_message}"},
                 section_title=section_title)


class ReportConsoleLogger:
    """Mirrors Python logger output to console_log.txt."""

    def __init__(self, report_id: str):
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        self._file_handler = None
        self._setup()

    def _setup(self):
        import logging
        self._file_handler = logging.FileHandler(
            self.log_file_path, mode='a', encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        for name in ('axonic.report_agent', 'axonic.zep_tools',
                     'mirofish.report_agent', 'mirofish.zep_tools'):
            target = logging.getLogger(name)
            if self._file_handler not in target.handlers:
                target.addHandler(self._file_handler)

    def close(self):
        import logging
        if self._file_handler:
            for name in ('axonic.report_agent', 'axonic.zep_tools',
                         'mirofish.report_agent', 'mirofish.zep_tools'):
                target = logging.getLogger(name)
                if self._file_handler in target.handlers:
                    target.removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

    def __del__(self):
        self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

class ReportStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    title: str
    content: str = ""

    def to_dict(self):
        return {"title": self.title, "content": self.content}

    def to_markdown(self, level: int = 2):
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    title: str
    summary: str
    sections: List[ReportSection]

    def to_dict(self):
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections],
        }

    def to_markdown(self):
        md = f"# {self.title}\n\n> {self.summary}\n\n"
        for s in self.sections:
            md += s.to_markdown()
        return md


@dataclass
class Report:
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def to_dict(self):
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt constants — AXonic (Indian Market)
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_DESC_INSIGHT_FORGE = """\
[Deep Insight Retrieval — primary research tool]
Strongest retrieval for decision-grade analysis:
1. Breaks the question into sub-questions automatically
2. Retrieves from multiple angles in the simulation graph
3. Combines semantic search, entity analysis, relationship-chain lookups
4. Returns comprehensive supporting evidence

[Use when]
- Understanding how Indian audiences reacted to a campaign element
- Unpacking a Tier1/Tier2/Tier3 reaction pattern
- Gathering rich evidence for a report section

[Returns]
- Source-quoted facts (quotable as persona reactions)
- Core entity insights (which consumer segments drove what)
- Relationship chains (amplification paths — public to private)"""

TOOL_DESC_PANORAMA_SEARCH = """\
[Broad Search — full-picture view]
Complete arc of simulated audience reaction over time.
1. Retrieves all related nodes and relationships
2. Distinguishes live (current) facts from expired (historical) facts
3. Shows how reaction evolved across rounds

[Use when]
- You need the full timeline of reaction
- You want to compare launch stage vs amplification vs private-network stage
- You need comprehensive entity + relationship coverage"""

TOOL_DESC_QUICK_SEARCH = """\
[Simple Search — fast lookup]
Lightweight retrieval for specific queries.

[Use when]
- Verifying a specific fact
- Looking up a single consumer reaction
- Quick confirmation of a data point"""

TOOL_DESC_INTERVIEW_AGENTS = """\
[Deep Interview — live agent interviews on Twitter + Reddit]
Calls OASIS interview API against live running agents. NOT LLM roleplay.

Workflow:
1. Reads persona files to understand every agent
2. Picks agents most relevant by tier, archetype, role
3. Auto-generates interview questions
4. Calls /api/simulation/interview/batch across both platforms
5. Consolidates multi-perspective results

[Use when]
- Need first-person reactions from a specific consumer segment
- Want direct quotes from Tier1/Tier2/Tier3 personas
- Need media/influencer/regulator voices

[Returns]
- Identity of each interviewed agent (tier / SEC / archetype / city / traits)
- Twitter + Reddit responses
- Pull-quote candidates (ready for direct citation)
- Cross-perspective summary

[Requires] OASIS simulation alive (waiting-for-commands mode)."""


PLAN_SYSTEM_PROMPT = """\
You are a senior Indian marketing strategist writing a "Campaign Decision Report".
You have god-view access to a simulation of Indian audience reaction — every Tier1/Tier2/Tier3 persona, every influencer, every media outlet, every amplification path, every private-network forward.

[Core philosophy]
A marketing campaign is a hypothesis about how Indian consumers will react. The simulation tests this hypothesis across tiers, SEC segments, languages, platforms, and crucially — private networks (WhatsApp / peer groups). Your report must answer:

1. What happens if we run this campaign in the Indian market?
2. Which personas react how — and why (Tier1/2/3 + behavioral drivers)?
3. What is the decision: LAUNCH / HOLD / KILL — with what confidence and business impact?

[Decision rigor — MANDATORY]

The report MUST output a clear business decision:

- Decision: LAUNCH | HOLD | KILL
- Confidence Score: single integer 0–100 (NO ranges, NO "around 70")
- Expected Outcome: 1–2 lines describing realistic market behaviour
- Business Impact:
  - Conversion impact: High | Medium | Low
  - Brand risk: High | Medium | Low
- If HOLD: specify exactly what must change to move to LAUNCH
- If KILL: state the dominant failure mode

[Failure mode detection — MANDATORY when HOLD or KILL]
Identify whether failure is due to:
- Pricing mismatch
- Cultural mismatch (language, region, festival timing)
- Trust deficit (skepticism, brand perception)
- Weak differentiation (campaign reads like noise)
Label the dominant failure mode explicitly.

[Report positioning]
- YES — decision-grade for Indian marketing teams
- YES — sharp, specific, numeric, actionable
- YES — persona-wise + private-network breakdown
- NO — generic marketing essay / academic tone
- NO — opinion without simulation evidence

[Structural rules]
- EXACTLY 2 top-level sections
- No sub-sections — each section is one cohesive block
- Dense, decision-relevant content
- Structure is yours — design based on what the simulation revealed

Return the outline as JSON:
{
    "title": "Report title",
    "summary": "One-sentence core decision finding",
    "sections": [
        {"title": "Section title", "description": "What this covers"}
    ]
}

`sections` array MUST have EXACTLY 2 entries."""

PLAN_USER_PROMPT_TEMPLATE = """\
[Campaign context]
Campaign / strategy being tested: {simulation_requirement}

[Simulation scale]
- Simulated agents (Indian personas): {total_nodes}
- Agent interactions produced: {total_edges}
- Entity type distribution: {entity_types}
- Active agents: {total_entities}

[Sample of simulated reactions]
{related_facts_json}

Review the simulation as a senior Indian marketing strategist:
1. Does this campaign land with Indian audiences — across tiers AND in private networks?
2. Which persona clusters reacted positively / negatively / indifferently — and WHY (price / trust / influence / brand)?
3. Decision (LAUNCH/HOLD/KILL), confidence, business impact, failure mode if applicable

Design a 2-section outline that delivers the decision + persona + private-network dynamics clearly.

[Reminder] Exactly 2 sections. Dense. Decision-focused. Indian market framing throughout."""


SECTION_SYSTEM_PROMPT_TEMPLATE = """\
You are a senior Indian marketing strategist writing one section of a Campaign Decision Report.

Report title        : {report_title}
Report summary      : {report_summary}
Campaign / strategy : {simulation_requirement}

Current section: {section_title}

═══════════════════════════════════════════════════════════════════════════════
CORE PHILOSOPHY
═══════════════════════════════════════════════════════════════════════════════

The simulation is a dress rehearsal for the Indian market. Every simulated agent represents a real persona (Tier1/2/3, SEC, language, archetype, behavioral traits). Your job: translate simulated behaviour into sharp, decision-grade insight.

- DO surface what happens when this campaign meets Indian consumers
- DO predict how Tier1 / Tier2 / Tier3 reactions diverge
- DO explain private-network dynamics (WhatsApp / peer / family forwards)
- DO flag concrete risks (ASCI, cultural misfit, price perception, festive timing)
- DO flag concrete opportunities (WhatsApp virality, IPL timing, UPI hooks)
- DO NOT produce generic marketing prose
- DO NOT hedge — strategists need a call, not a both-sides essay

═══════════════════════════════════════════════════════════════════════════════
MANDATORY CONTENT RULES
═══════════════════════════════════════════════════════════════════════════════

1. [TOOLS ARE REQUIRED]
   - MUST call a tool at least once before writing Final Answer
   - Capped at {max_tool_calls} total tool calls
   - Every claim based on retrieved simulation data, not prior knowledge

2. [QUOTE REAL PERSONA VOICES]
   - Agent reactions are the core evidence
   - Use blockquote format: > "<persona voice>"
   - Quotes ARE the persona reactions — show, don't paraphrase

3. [LANGUAGE]
   - Report body in English
   - Quote Hindi / Hinglish / regional voices in original form
     (transliterate to Roman if not already); add 4–6 word English gloss in parentheses if needed
   - Keep quotes authentic — "paisa vasool" beats "good value for money"

4. [FIDELITY]
   - Report only what the simulation showed
   - If a tier has no coverage, say so explicitly
   - Never invent reactions — call another tool if evidence is thin

═══════════════════════════════════════════════════════════════════════════════
PERSONA QUANTIFICATION (required when describing persona reactions)
═══════════════════════════════════════════════════════════════════════════════

For each persona cluster described, quantify:
- % positive vs negative sentiment (approximation acceptable, "about 65% skeptical")
- Dominant driver: price | trust | influencer | brand | peer-validation
- Conversion likelihood: High | Medium | Low

Example format:
> Tier2 (Pune / Jaipur / Kochi):
> ~65% skeptical due to pricing
> driven by value perception + peer validation
> conversion likelihood: Medium (needs discount trigger)

═══════════════════════════════════════════════════════════════════════════════
ROOT CAUSE ANALYSIS (required for each major reaction cluster)
═══════════════════════════════════════════════════════════════════════════════

For each major reaction cluster, explain:
- What triggered the reaction (specific campaign element or message)
- Why this matters in Indian context (cultural, linguistic, economic lens)
- Whether the reaction SCALES or COLLAPSES at larger audience sizes

═══════════════════════════════════════════════════════════════════════════════
PRIVATE NETWORK DYNAMICS (required — do not skip)
═══════════════════════════════════════════════════════════════════════════════

Explicitly analyse:
- WhatsApp / peer / family-group sharing impact
- Trust amplification OR decay when campaign moves from public to private network
- Whether campaign survives beyond public platforms (Instagram/Twitter) into private chats

If absent from simulation, state explicitly:
"This campaign does not translate into private-network trust — [reason]."

═══════════════════════════════════════════════════════════════════════════════
ACTIONABILITY (required for every recommendation)
═══════════════════════════════════════════════════════════════════════════════

Every recommendation MUST include:
- Specific change (creative / pricing / messaging / channel / timing)
- Expected impact on Tier1 / Tier2 / Tier3 (differentiated, not generic)
- Why this will improve conversion (mechanism, not hope)

Vague advice like "improve messaging" is forbidden. Replace with:
"Swap English voice-over for Hinglish + add UPI cashback CTA for Tier2 → expected +12–18% save-rate."

═══════════════════════════════════════════════════════════════════════════════
SIMULATION LIMITATIONS (honesty layer — builds trust)
═══════════════════════════════════════════════════════════════════════════════

If certain segments are underrepresented, data is thin, or a reaction pattern is uncertain:
- State it explicitly ("Tier3 coverage is thin — only 8 agents")
- Do NOT overgeneralize
- Do NOT fill gaps with plausible-sounding narrative

═══════════════════════════════════════════════════════════════════════════════
FORMATTING RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════

[Section = smallest content unit]
- NO Markdown headings (#, ##, ###, ####) — none
- Section heading is added by the system — write body only
- Use **bold** for sub-section emphasis, not headings
- Blockquotes (>) for persona voices — own paragraph with blank lines before/after
- Lists fine (- or 1. 2. 3.) when they help scanability

[CORRECT]
```
Tier1 metro audience responded strongly to the premium positioning; save-rate outpaced share-rate 3:1.

**Tier1 reaction (conversion likelihood: Medium-High)**

Mumbai and Bengaluru personas treated the campaign as aspirational shorthand:

> "Finally a brand that gets what we actually care about — quality over discount."

Driver: brand + influence. Scales well because Tier1 saves first, buys after 2–3 touchpoints.

**Tier2 reaction (conversion likelihood: Low)**

Pune/Jaipur audiences flagged pricing as a blocker — ~70% skeptical...
```

[WRONG]
```
## Tier1 reaction        ← never write ## inside a section
### Detailed analysis    ← never use ### at all
```

═══════════════════════════════════════════════════════════════════════════════
AVAILABLE TOOLS (call at least once)
═══════════════════════════════════════════════════════════════════════════════

{tools_description}

[Tool selection]
- insight_forge     : deep multi-angle analysis of theme or cluster
- panorama_search   : full arc of reaction across rounds
- quick_search      : one specific fact-check
- interview_agents  : live first-person quotes (use for persona-wise reactions)

═══════════════════════════════════════════════════════════════════════════════
WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

Each message does ONE of two things:

Option A — Call a tool:
Write reasoning, then one tool call:
<tool_call>
{{"name": "<tool_name>", "parameters": {{"<param>": "<value>"}}}}
</tool_call>
System runs tool and returns Observation. You MUST NOT invent tool output.

Option B — Write the section:
When evidence is sufficient, start your reply with "Final Answer:" followed by the section body.

[Strictly forbidden]
- Mixing a tool call and Final Answer in the same reply
- Fabricating tool output
- Multiple tool calls in one reply
- Skipping Persona Quantification / Root Cause / Private-Network / Actionability rules"""


SECTION_USER_PROMPT_TEMPLATE = """\
Earlier sections (read carefully — avoid repeating these):
{previous_content}

═══════════════════════════════════════════════════════════════════════════════
Current task: write the section titled "{section_title}"
═══════════════════════════════════════════════════════════════════════════════

[Important]
1. Read earlier sections to avoid repetition
2. Call a tool before writing the final answer
3. Mix tool types — don't rely on one
4. All content must be grounded in retrieved simulation data
5. Apply mandatory rules: Persona Quantification, Root Cause, Private-Network, Actionability, Simulation Limitations

[Formatting warning]
- NO headings (no #, ##, ###, ####)
- Do NOT start with "{section_title}" as a title — system adds it
- Use **bold** instead of sub-headings
- Blockquotes stand alone as paragraphs

Proceed:
1. Think about what this section needs
2. Call a tool to retrieve simulation evidence
3. After enough evidence, respond with "Final Answer:" followed by the body (no headings)"""


REACT_OBSERVATION_TEMPLATE = """\
Observation (tool result):

═══ Tool {tool_name} returned ═══
{result}

═══════════════════════════════════════════════════════════════════════════════
Tool calls used: {tool_calls_count}/{max_tool_calls}  (used: {used_tools_str}){unused_hint}
- If evidence is sufficient: respond with "Final Answer:" and the section body
  (MUST cite retrieved voices + apply Persona Quantification / Root Cause /
   Private-Network / Actionability rules)
- If more evidence is needed: call another tool
═══════════════════════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "[Note] Only called tools {tool_calls_count} time(s); minimum {min_tool_calls}. "
    "Call another tool for more simulation evidence before Final Answer.{unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Only {tool_calls_count} tool call(s); minimum {min_tool_calls} required. "
    "Call a tool for more simulation data.{unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Tool-call limit reached ({tool_calls_count}/{max_tool_calls}). No more tool calls. "
    'Produce the section now — start with "Final Answer:".'
)

REACT_UNUSED_TOOLS_HINT = "\n[Tip] You haven't used: {unused_list}. Mixing tools improves angle coverage."

REACT_FORCE_FINAL_MSG = 'Tool-call limit reached. Respond with "Final Answer:" and the section body now.'


CHAT_SYSTEM_PROMPT_TEMPLATE = """\
You are a concise, pragmatic Indian market campaign assistant.

[Context]
Campaign being analysed: {simulation_requirement}

[Generated decision report]
{report_content}

[Rules]
1. Answer from the report first; retrieve only if the report lacks the answer
2. Direct answer — no preamble, no thinking-out-loud
3. Call a tool only when necessary (max 1–2 calls per user turn)
4. Use Indian market framing (tier, SEC, festive timing, ASCI, private-network) when relevant
5. Keep persona quotes in original voice (> blockquote)
6. For decisions: include confidence (single integer) and business impact
7. For recommendations: follow the Actionability rule

[Available tools — use only when needed]
{tools_description}

[Tool call format]
<tool_call>
{{"name": "<tool_name>", "parameters": {{"<param>": "<value>"}}}}
</tool_call>

[Answer style]
- Lead with the conclusion
- Support with the smallest evidence set that proves the point
- Use > format for persona quotes
- No headings"""

CHAT_OBSERVATION_SUFFIX = "\n\nAnswer concisely."


# ═══════════════════════════════════════════════════════════════════════════════
# ReportAgent
# ═══════════════════════════════════════════════════════════════════════════════

class ReportAgent:
    """ReAct-driven Indian marketing decision report generator."""

    MAX_TOOL_CALLS_PER_SECTION = 2
    MAX_REFLECTION_ROUNDS = 3
    MAX_TOOL_CALLS_PER_CHAT = 2
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents", "get_persona_analytics"}

    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        zep_tools: Optional[ZepToolsService] = None,
    ):
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement
        self.llm = llm_client or LLMClient(provider="gemini")
        self.zep_tools = zep_tools or SupabaseSearchService()
        self.tools = self._define_tools()
        self.report_logger: Optional[ReportLogger] = None
        self.console_logger: Optional[ReportConsoleLogger] = None
        logger.info(f"ReportAgent init: graph_id={graph_id}, simulation_id={simulation_id}")

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "Theme or question to analyse in depth",
                    "report_context": "Section context (optional, helps sub-question generation)",
                },
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "Search query for relevance ranking",
                    "include_expired": "Include historical/expired facts (default True)",
                },
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "Search query string",
                    "limit": "Result count (optional, default 10)",
                },
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "query": "Topic or trait to find agents for (e.g. 'Tier 2 students')",
                    "limit": "Max agents to interview (default 5)",
                },
            },
            "get_persona_analytics": {
                "name": "get_persona_analytics",
                "description": "Returns math-heavy distribution of persona tiers, SECs, and behavioral traits from Supabase.",
                "parameters": {},
            },
        }

    def _execute_tool(
        self, tool_name: str, parameters: Dict[str, Any], report_context: str = "",
    ) -> str:
        logger.info(f"Tool: {tool_name}, params: {parameters}")
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.zep_tools.insight_forge(
                    graph_id=self.graph_id, query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx,
                )
                return result.to_text()

            if tool_name == "panorama_search":
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.zep_tools.panorama_search(
                    graph_id=self.graph_id, query=query, include_expired=include_expired,
                )
                return result.to_text()

            if tool_name == "quick_search":
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.quick_search(
                    graph_id=self.graph_id, query=query, limit=limit,
                )
                return result.to_text()

            if tool_name == "interview_agents":
                query = parameters.get("query", parameters.get("interview_topic", ""))
                limit = parameters.get("limit", parameters.get("max_agents", 5))
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.zep_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    query=query,
                    limit=limit,
                )
                return result.to_text()

            if tool_name == "get_persona_analytics":
                stats = self.zep_tools.get_persona_analytics(self.simulation_id)
                return json.dumps(stats, ensure_ascii=False, indent=2)

            # Legacy tool redirects
            if tool_name == "search_graph":
                return self._execute_tool("quick_search", parameters, report_context)
            if tool_name == "get_graph_statistics":
                return json.dumps(
                    self.zep_tools.get_graph_statistics(self.graph_id),
                    ensure_ascii=False, indent=2,
                )
            if tool_name == "get_entity_summary":
                return json.dumps(
                    self.zep_tools.get_entity_summary(
                        graph_id=self.graph_id,
                        entity_name=parameters.get("entity_name", ""),
                    ),
                    ensure_ascii=False, indent=2,
                )
            if tool_name == "get_simulation_context":
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            if tool_name == "get_entities_by_type":
                nodes = self.zep_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=parameters.get("entity_type", ""),
                )
                return json.dumps([n.to_dict() for n in nodes], ensure_ascii=False, indent=2)

            return f"Unknown tool: {tool_name}. Available: insight_forge, panorama_search, quick_search, interview_agents."

        except Exception as e:
            logger.error(f"Tool failed: {tool_name}, error: {str(e)}")
            return f"Tool execution failed: {str(e)}"

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Parse tool calls from LLM response. Supports <tool_call> XML or bare JSON."""
        tool_calls = []

        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                tool_calls.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                pass
        if tool_calls:
            return tool_calls

        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                data = json.loads(stripped)
                if self._is_valid_tool_call(data):
                    return [data]
            except json.JSONDecodeError:
                pass

        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if self._is_valid_tool_call(data):
                    tool_calls.append(data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False

    def _get_tools_description(self) -> str:
        desc_parts = ["Available tools:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  params: {params_desc}")
        return "\n".join(desc_parts)

    def plan_outline(self, progress_callback: Optional[Callable] = None) -> ReportOutline:
        logger.info("Planning report outline...")

        if progress_callback:
            progress_callback("planning", 0, "Analyzing campaign...")

        context = self.zep_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
        )

        if progress_callback:
            progress_callback("planning", 30, "Generating outline...")

        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(
                context.get('related_facts', [])[:10], ensure_ascii=False, indent=2,
            ),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            if progress_callback:
                progress_callback("planning", 80, "Parsing outline...")

            sections = [
                ReportSection(title=s.get("title", ""), content="")
                for s in response.get("sections", [])
            ]

            outline = ReportOutline(
                title=response.get("title", "Campaign Decision Report"),
                summary=response.get("summary", ""),
                sections=sections,
            )

            if progress_callback:
                progress_callback("planning", 100, "Outline planned")

            logger.info(f"Outline planned: {len(sections)} sections")
            return outline

        except Exception as e:
            logger.error(f"Outline planning failed: {str(e)}")
            return ReportOutline(
                title="Campaign Decision Report",
                summary="Decision, business impact, and persona-wise reactions for the Indian market.",
                sections=[
                    ReportSection(title="Decision, Confidence & Business Impact"),
                    ReportSection(title="Persona Reactions & Private-Network Dynamics"),
                ],
            )

    def _generate_section_react(
        self,
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0,
    ) -> str:
        logger.info(f"ReAct generating section: {section.title}")

        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)

        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
        )

        if previous_sections:
            previous_parts = [
                (s[:4000] + "...") if len(s) > 4000 else s
                for s in previous_sections
            ]
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(This is the first section)"

        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        tool_calls_count = 0
        max_iterations = 5
        min_tool_calls = 1
        conflict_retries = 0
        used_tools: set = set()
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}
        report_context = f"Section: {section.title}\nCampaign: {self.simulation_requirement}"

        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating",
                    int((iteration / max_iterations) * 100),
                    f"Retrieving + writing ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})",
                )

            response = self.llm.chat(messages=messages, temperature=0.5, max_tokens=4096)

            if response is None:
                logger.warning(f"Section {section.title} iter {iteration + 1}: LLM returned None")
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(empty response)"})
                    messages.append({"role": "user", "content": "Please continue."})
                    continue
                break

            logger.debug(f"LLM response: {response[:200]}...")

            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # Conflict: both tool call + Final Answer
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"Section {section.title} iter {iteration + 1}: "
                    f"LLM emitted both tool call and Final Answer (conflict #{conflict_retries})"
                )

                if conflict_retries <= 2:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[Format error] Your reply contained BOTH a tool call AND Final Answer. "
                            "Each reply must do ONLY ONE of:\n"
                            "- Call a single tool (one <tool_call> block, no Final Answer)\n"
                            "- Output Final Answer (start with 'Final Answer:', no <tool_call>)\n"
                            "Please retry doing only one."
                        ),
                    })
                    continue
                else:
                    logger.warning(
                        f"Section {section.title}: {conflict_retries} conflicts — "
                        "truncating to first tool call"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title, section_index=section_index,
                    response=response, iteration=iteration + 1,
                    has_tool_calls=has_tool_calls, has_final_answer=has_final_answer,
                )

            # Final Answer branch
            if has_final_answer:
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused = all_tools - used_tools
                    hint = f" (Try: {', '.join(unused)})" if unused else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=hint,
                        ),
                    })
                    continue

                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"Section {section.title} complete (tools: {tool_calls_count})")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title, section_index=section_index,
                        content=final_answer, tool_calls_count=tool_calls_count,
                    )
                return final_answer

            # Tool call branch
            if has_tool_calls:
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM emitted {len(tool_calls)} tool calls, only first: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title, section_index=section_index,
                        tool_name=call["name"], parameters=call.get("parameters", {}),
                        iteration=iteration + 1,
                    )

                result = self._execute_tool(
                    call["name"], call.get("parameters", {}), report_context=report_context,
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title, section_index=section_index,
                        tool_name=call["name"], result=result, iteration=iteration + 1,
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                unused = all_tools - used_tools
                hint = ""
                if unused and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    hint = REACT_UNUSED_TOOLS_HINT.format(unused_list=", ".join(unused))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"], result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=hint,
                    ),
                })
                continue

            # No tool call, no Final Answer
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                unused = all_tools - used_tools
                hint = f" (Try: {', '.join(unused)})" if unused else ""
                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=hint,
                    ),
                })
                continue

            # Tools satisfied, content without prefix — accept as final
            logger.info(
                f"Section {section.title} no 'Final Answer:' prefix, accepting as final "
                f"(tools: {tool_calls_count})"
            )
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title, section_index=section_index,
                    content=final_answer, tool_calls_count=tool_calls_count,
                )
            return final_answer

        # Forced finalization
        logger.warning(f"Section {section.title} max iterations, forcing final")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})

        response = self.llm.chat(messages=messages, temperature=0.5, max_tokens=4096)

        if response is None:
            logger.error(f"Section {section.title} forced-final LLM returned None")
            final_answer = "(Section failed: LLM returned empty response. Retry.)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response

        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title, section_index=section_index,
                content=final_answer, tool_calls_count=tool_calls_count,
            )

        return final_answer

    def generate_report(
        self,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None,
    ) -> Report:
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()

        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )

        completed_section_titles: List[str] = []

        try:
            ReportManager._ensure_report_folder(report_id)

            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement,
            )

            self.console_logger = ReportConsoleLogger(report_id)

            ReportManager.update_progress(
                report_id, "pending", 0, "Initializing report...",
                completed_sections=[],
            )
            ReportManager.save_report(report)

            # Stage 1: outline
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "Planning outline...",
                completed_sections=[],
            )

            self.report_logger.log_planning_start()

            if progress_callback:
                progress_callback("planning", 0, "Planning outline...")

            outline = self.plan_outline(
                progress_callback=lambda stage, prog, msg:
                    progress_callback(stage, prog // 5, msg) if progress_callback else None,
            )
            report.outline = outline

            self.report_logger.log_planning_complete(outline.to_dict())

            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15,
                f"Outline planned: {len(outline.sections)} sections",
                completed_sections=[],
            )
            ReportManager.save_report(report)

            logger.info(f"Outline saved: {report_id}/outline.json")

            # Stage 2: sections
            report.status = ReportStatus.GENERATING
            total_sections = len(outline.sections)
            generated_sections: List[str] = []

            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)

                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"Generating: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles,
                )

                if progress_callback:
                    progress_callback(
                        "generating", base_progress,
                        f"Generating: {section.title} ({section_num}/{total_sections})",
                    )

                section_content = self._generate_section_react(
                    section=section, outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage,
                            base_progress + int(prog * 0.7 / total_sections),
                            msg,
                        ) if progress_callback else None,
                    section_index=section_num,
                )

                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                full_section_content = f"## {section.title}\n\n{section_content}"
                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip(),
                    )

                logger.info(f"Section saved: {report_id}/section_{section_num:02d}.md")

                ReportManager.update_progress(
                    report_id, "generating",
                    base_progress + int(70 / total_sections),
                    f"Section complete: {section.title}",
                    current_section=None,
                    completed_sections=completed_section_titles,
                )

            # Stage 3: assemble
            if progress_callback:
                progress_callback("generating", 95, "Assembling full report...")

            ReportManager.update_progress(
                report_id, "generating", 95, "Assembling full report...",
                completed_sections=completed_section_titles,
            )

            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()

            total_time = (datetime.now() - start_time).total_seconds()

            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time,
                )

            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "Report complete",
                completed_sections=completed_section_titles,
            )

            if progress_callback:
                progress_callback("completed", 100, "Report complete")

            logger.info(f"Report complete: {report_id}")

            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None

            return report

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)

            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")

            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"Report failed: {str(e)}",
                    completed_sections=completed_section_titles,
                )
            except Exception:
                pass

            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None

            return report

    def chat(
        self, message: str, chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Chat: {message[:50]}...")
        chat_history = chat_history or []

        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [report truncated] ..."
        except Exception as e:
            logger.warning(f"Failed to fetch report: {e}")

        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "(no report yet)",
            tools_description=self._get_tools_description(),
        )

        messages = [{"role": "system", "content": system_prompt}]
        for h in chat_history[-10:]:
            messages.append(h)
        messages.append({"role": "user", "content": message})

        tool_calls_made: List[Dict[str, Any]] = []
        max_iterations = 2

        for iteration in range(max_iterations):
            response = self.llm.chat(messages=messages, temperature=0.5)
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                clean = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean = re.sub(r'\[TOOL_CALL\].*?\)', '', clean)
                return {
                    "response": clean.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made],
                }

            tool_results = []
            for call in tool_calls[:1]:
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500],
                })
                tool_calls_made.append(call)

            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']} result]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX,
            })

        final_response = self.llm.chat(messages=messages, temperature=0.5)
        clean = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean = re.sub(r'\[TOOL_CALL\].*?\)', '', clean)

        return {
            "response": clean.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made],
        }

    def generate_lite_report(
        self,
        simulation_id: str,
        graph_id: str,
        simulation_requirement: str,
        report_id: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Report:
        """Single-pass Micro-Lite report (1 LLM call, no ReAct loop)."""
        logger.info(f"Generating Micro-Lite report for {simulation_id}")
        if progress_callback:
            progress_callback(10, "Fetching simulation data...")

        tools = ZepToolsService()
        context = tools.get_simulation_context(graph_id, simulation_requirement)
        facts = context.get("related_facts", [])

        if progress_callback:
            progress_callback(40, "Synthesizing lite report...")

        prompt = f"""\
Draft a concise Campaign Decision Summary for the Indian market based on this simulation.

Campaign: {simulation_requirement}
Simulation findings: {json.dumps(facts, ensure_ascii=False)}

Structure (use **bold** instead of headings — no Markdown headings):
1. **Decision** — LAUNCH | HOLD | KILL, with a single-integer confidence (0–100)
2. **Business Impact** — conversion impact (High/Medium/Low), brand risk (High/Medium/Low)
3. **Persona Reactions** — 2–3 bullets across Tier1/Tier2/Tier3 with % sentiment + conversion likelihood
4. **Private-Network Dynamics** — one sentence on whether campaign survives WhatsApp/peer trust layer
5. **Top 3 Recommendations** — specific change + expected tier-wise impact + mechanism
6. If HOLD/KILL: name the dominant failure mode (pricing / cultural / trust / differentiation)

Rules:
- English body; Hinglish pull-quotes in original form (> blockquote format)
- No Markdown headings (#, ##, ###)
- Keep it tight — a single strategist-grade page
"""

        try:
            llm = LLMClient(report=True)
            response = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            report = Report(
                report_id=report_id,
                simulation_id=simulation_id,
                graph_id=graph_id,
                simulation_requirement=simulation_requirement,
                status=ReportStatus.COMPLETED,
                markdown_content=response,
                created_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat(),
            )

            report_dir = os.path.join(Config.UPLOAD_FOLDER, 'reports', report_id)
            os.makedirs(report_dir, exist_ok=True)
            with open(os.path.join(report_dir, 'report.json'), 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
            with open(os.path.join(report_dir, 'report.md'), 'w', encoding='utf-8') as f:
                f.write(response)

            if progress_callback:
                progress_callback(100, "Lite report generated.")
            return report

        except Exception as e:
            logger.error(f"Lite report failed: {e}")
            return Report(
                report_id=report_id, simulation_id=simulation_id, graph_id=graph_id,
                simulation_requirement=simulation_requirement,
                status=ReportStatus.FAILED, error=str(e),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ReportManager
# ═══════════════════════════════════════════════════════════════════════════════

class ReportManager:
    """Persistent storage + retrieval for reports. Folder-per-report layout."""

    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')

    @classmethod
    def _ensure_reports_dir(cls):
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)

    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        return os.path.join(cls.REPORTS_DIR, report_id)

    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder

    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "meta.json")

    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")

    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "outline.json")

    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "progress.json")

    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        return os.path.join(
            cls._get_report_folder(report_id), f"section_{section_index:02d}.md"
        )

    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")

    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")

    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        log_path = cls._get_console_log_path(report_id)
        if not os.path.exists(log_path):
            return {"logs": [], "total_lines": 0, "from_line": 0, "has_more": False}

        logs = []
        total_lines = 0
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    logs.append(line.rstrip('\n\r'))

        return {"logs": logs, "total_lines": total_lines,
                "from_line": from_line, "has_more": False}

    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        return cls.get_console_log(report_id, from_line=0)["logs"]

    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        log_path = cls._get_agent_log_path(report_id)
        if not os.path.exists(log_path):
            return {"logs": [], "total_lines": 0, "from_line": 0, "has_more": False}

        logs = []
        total_lines = 0
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue

        return {"logs": logs, "total_lines": total_lines,
                "from_line": from_line, "has_more": False}

    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        return cls.get_agent_log(report_id, from_line=0)["logs"]

    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        cls._ensure_report_folder(report_id)
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Outline saved: {report_id}")

    @classmethod
    def save_section(
        cls, report_id: str, section_index: int, section: ReportSection,
    ) -> str:
        cls._ensure_report_folder(report_id)
        cleaned = cls._clean_section_content(section.content, section.title)
        md = f"## {section.title}\n\n"
        if cleaned:
            md += f"{cleaned}\n\n"

        suffix = f"section_{section_index:02d}.md"
        path = os.path.join(cls._get_report_folder(report_id), suffix)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md)

        logger.info(f"Section saved: {report_id}/{suffix}")
        return path

    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """Strip duplicate section titles; convert all headings to bold."""
        if not content:
            return content

        content = content.strip()
        lines = content.split('\n')
        cleaned: List[str] = []
        skip_next_empty = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)

            if heading_match:
                title_text = heading_match.group(2).strip()

                if i < 5:
                    if (title_text == section_title
                            or title_text.replace(' ', '') == section_title.replace(' ', '')):
                        skip_next_empty = True
                        continue

                cleaned.append(f"**{title_text}**")
                cleaned.append("")
                continue

            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue

            skip_next_empty = False
            cleaned.append(line)

        while cleaned and cleaned[0].strip() == '':
            cleaned.pop(0)

        while cleaned and cleaned[0].strip() in ['---', '***', '___']:
            cleaned.pop(0)
            while cleaned and cleaned[0].strip() == '':
                cleaned.pop(0)

        return '\n'.join(cleaned)

    @classmethod
    def update_progress(
        cls, report_id: str, status: str, progress: int, message: str,
        current_section: str = None, completed_sections: List[str] = None,
    ) -> None:
        cls._ensure_report_folder(report_id)
        data = {
            "status": status, "progress": progress, "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat(),
        }
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        path = cls._get_progress_path(report_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        folder = cls._get_report_folder(report_id)
        if not os.path.exists(folder):
            return []

        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                path = os.path.join(folder, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])
                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content,
                })

        return sections

    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        md = f"# {outline.title}\n\n> {outline.summary}\n\n---\n\n"

        for section_info in cls.get_generated_sections(report_id):
            md += section_info["content"]

        md = cls._post_process_report(md, outline)

        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md)

        logger.info(f"Full report assembled: {report_id}")
        return md

    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """Dedupe titles, keep only # and ## for report title / section titles."""
        lines = content.split('\n')
        processed: List[str] = []
        prev_was_heading = False
        section_titles = {s.title for s in outline.sections}

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)

            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                is_duplicate = False
                for j in range(max(0, len(processed) - 5), len(processed)):
                    prev = processed[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev)
                    if prev_match and prev_match.group(2).strip() == title:
                        is_duplicate = True
                        break

                if is_duplicate:
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue

                if level == 1:
                    if title == outline.title:
                        processed.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        processed.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        processed.append(f"**{title}**")
                        processed.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        processed.append(line)
                        prev_was_heading = True
                    else:
                        processed.append(f"**{title}**")
                        processed.append("")
                        prev_was_heading = False
                else:
                    processed.append(f"**{title}**")
                    processed.append("")
                    prev_was_heading = False

                i += 1
                continue

            if stripped == '---' and prev_was_heading:
                i += 1
                continue

            if stripped == '' and prev_was_heading:
                if processed and processed[-1].strip() != '':
                    processed.append(line)
                prev_was_heading = False
            else:
                processed.append(line)
                prev_was_heading = False

            i += 1

        # Collapse 3+ blank lines to 2
        result: List[str] = []
        empty_count = 0
        for line in processed:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result.append(line)
            else:
                empty_count = 0
                result.append(line)

        return '\n'.join(result)

    @classmethod
    def save_report(cls, report: Report) -> None:
        cls._ensure_report_folder(report.report_id)

        # 1. Local Persistence
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        if report.outline:
            cls.save_outline(report.report_id, report.outline)

        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id),
                      'w', encoding='utf-8') as f:
                f.write(report.markdown_content)

        # 2. Supabase Persistence (Decision-Grade)
        if report.status == ReportStatus.COMPLETED or report.markdown_content:
            try:
                client = get_client()
                
                # Extract Decision Data from Markdown
                decision = "HOLD"
                confidence = 50
                impact = "Medium"
                
                if report.markdown_content:
                    content = report.markdown_content.upper()
                    if "DECISION: LAUNCH" in content: decision = "LAUNCH"
                    elif "DECISION: KILL" in content: decision = "KILL"
                    elif "DECISION: HOLD" in content: decision = "HOLD"
                    
                    # Try to find confidence integer
                    conf_match = re.search(r'CONFIDENCE.*?(\d+)', content)
                    if conf_match:
                        confidence = int(conf_match.group(1))

                report_data = {
                    "id": report.report_id,
                    "simulation_id": report.simulation_id,
                    "title": report.outline.title if report.outline else "Campaign Decision Report",
                    "summary": report.outline.summary if report.outline else "",
                    "content": report.markdown_content,
                    "decision": decision,
                    "confidence_score": confidence,
                    "business_impact": impact # DEFAULT
                }
                
                # Upsert into Supabase
                client.table("reports").upsert(report_data).execute()
                logger.info(f"Report persisted to Supabase: {report.report_id}")
            except Exception as e:
                logger.error(f"Failed to persist report to Supabase: {e}")

        logger.info(f"Report saved: {report.report_id}")

    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        path = cls._get_report_path(report_id)

        if not os.path.exists(path):
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        outline = None
        if data.get('outline'):
            od = data['outline']
            sections = [
                ReportSection(title=s['title'], content=s.get('content', ''))
                for s in od.get('sections', [])
            ]
            outline = ReportOutline(
                title=od['title'], summary=od['summary'], sections=sections,
            )

        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()

        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error'),
        )

    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        cls._ensure_reports_dir()
        for item in os.listdir(cls.REPORTS_DIR):
            path = os.path.join(cls.REPORTS_DIR, item)
            if os.path.isdir(path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            elif item.endswith('.json'):
                report = cls.get_report(item[:-5])
                if report and report.simulation_id == simulation_id:
                    return report
        return None

    @classmethod
    def list_reports(
        cls, simulation_id: Optional[str] = None, limit: int = 50,
    ) -> List[Report]:
        cls._ensure_reports_dir()
        reports: List[Report] = []
        for item in os.listdir(cls.REPORTS_DIR):
            path = os.path.join(cls.REPORTS_DIR, item)
            if os.path.isdir(path):
                r = cls.get_report(item)
                if r and (simulation_id is None or r.simulation_id == simulation_id):
                    reports.append(r)
            elif item.endswith('.json'):
                r = cls.get_report(item[:-5])
                if r and (simulation_id is None or r.simulation_id == simulation_id):
                    reports.append(r)

        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports[:limit]

    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        import shutil

        folder = cls._get_report_folder(report_id)
        if os.path.exists(folder) and os.path.isdir(folder):
            shutil.rmtree(folder)
            logger.info(f"Report folder deleted: {report_id}")
            return True

        deleted = False
        old_json = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        if os.path.exists(old_json):
            os.remove(old_json); deleted = True
        if os.path.exists(old_md):
            os.remove(old_md); deleted = True

        return deleted