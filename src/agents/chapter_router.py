"""
LLM-based Chapter Router using SPOAR loop pattern.

Routes student queries to relevant chapters using:
1. LLM analysis of query intent and topics
2. Chapter metadata matching
"""
from typing import Dict, Any, List
from dataclasses import dataclass
import json
import re


@dataclass
class RoutingResult:
    """Result of chapter routing."""

    primary_chapter: int
    secondary_chapters: List[int]
    confidence: float
    reasoning: str
    topics_identified: List[str]


class ChapterRouterAgent:
    """
    Routes queries to relevant chapters using SPOAR loop.

    Uses LLM to analyze query and match against chapter metadata.
    """

    # Chapter metadata for routing decisions
    CHAPTER_INDEX = {
        1: {
            "title": "Physical Quantities and Measurement",
            "topics": [
                "physical quantities",
                "SI units",
                "measurement",
                "vernier caliper",
                "screw gauge",
                "significant figures",
                "scientific notation",
                "prefixes",
            ],
            "keywords": [
                "measure",
                "unit",
                "quantity",
                "instrument",
                "precision",
                "accuracy",
            ],
        },
        2: {
            "title": "Kinematics",
            "topics": [
                "motion",
                "displacement",
                "velocity",
                "acceleration",
                "equations of motion",
                "distance-time graph",
                "velocity-time graph",
                "free fall",
                "projectile",
            ],
            "keywords": [
                "speed",
                "move",
                "travel",
                "graph",
                "fall",
                "s=ut+1/2at^2",
                "v=u+at",
            ],
        },
        3: {
            "title": "Dynamics",
            "topics": [
                "force",
                "Newton laws",
                "momentum",
                "friction",
                "inertia",
                "action reaction",
                "circular motion",
                "centripetal force",
            ],
            "keywords": [
                "push",
                "pull",
                "F=ma",
                "Newton",
                "momentum",
                "friction",
                "circular",
            ],
        },
        4: {
            "title": "Turning Effect of Forces",
            "topics": [
                "torque",
                "moment of force",
                "equilibrium",
                "center of gravity",
                "couple",
                "stability",
                "lever",
                "principle of moments",
            ],
            "keywords": [
                "rotate",
                "turn",
                "balance",
                "lever",
                "torque",
                "moment",
                "pivot",
            ],
        },
        5: {
            "title": "Gravitation",
            "topics": [
                "gravitation",
                "gravity",
                "mass",
                "weight",
                "gravitational field",
                "Newton law of gravitation",
                "g value",
                "satellites",
                "orbit",
            ],
            "keywords": [
                "gravity",
                "weight",
                "mass",
                "fall",
                "planet",
                "satellite",
                "orbit",
                "G",
            ],
        },
        6: {
            "title": "Work and Energy",
            "topics": [
                "work",
                "energy",
                "power",
                "kinetic energy",
                "potential energy",
                "conservation of energy",
                "efficiency",
                "joule",
                "watt",
            ],
            "keywords": [
                "work",
                "energy",
                "power",
                "joule",
                "kinetic",
                "potential",
                "conserve",
            ],
        },
        7: {
            "title": "Properties of Matter",
            "topics": [
                "density",
                "pressure",
                "atmospheric pressure",
                "Archimedes principle",
                "buoyancy",
                "Pascal law",
                "states of matter",
                "fluid",
            ],
            "keywords": [
                "density",
                "pressure",
                "float",
                "sink",
                "liquid",
                "gas",
                "solid",
                "buoyancy",
            ],
        },
        8: {
            "title": "Thermal Properties of Matter",
            "topics": [
                "temperature",
                "heat",
                "thermal expansion",
                "specific heat",
                "latent heat",
                "thermometer",
                "Celsius",
                "Kelvin",
            ],
            "keywords": [
                "heat",
                "temperature",
                "expand",
                "specific heat",
                "latent",
                "thermal",
            ],
        },
        9: {
            "title": "Transfer of Heat",
            "topics": [
                "conduction",
                "convection",
                "radiation",
                "thermal conductivity",
                "insulation",
                "greenhouse effect",
                "thermos flask",
            ],
            "keywords": [
                "conduct",
                "convect",
                "radiate",
                "transfer",
                "insulate",
                "thermos",
            ],
        },
    }

    def __init__(self, llm_client, model: str = "llama-3.3-70b-versatile", debug: bool = False):
        """
        Initialize router.

        Args:
            llm_client: Groq client instance
            model: Model to use for routing
            debug: Enable debug output
        """
        self.llm = llm_client
        self.model = model
        self.memory = []
        self.debug = debug

    def route(
        self,
        query: str,
        class_level: int = 9,
        subject: str = "Physics",
        max_iterations: int = 2,
    ) -> RoutingResult:
        """
        Route query to relevant chapters using SPOAR loop.

        Args:
            query: Student's question
            class_level: Class level (default 9)
            subject: Subject name (default Physics)
            max_iterations: Max SPOAR iterations for refinement

        Returns:
            RoutingResult with chapter recommendations
        """
        if self.debug:
            print(f"\n{'='*60}")
            print(f"[ROUTER] Starting SPOAR loop for query: {query}")
            print(f"{'='*60}")

        context = {
            "query": query,
            "class_level": class_level,
            "subject": subject,
            "iteration": 0,
            "candidates": [],
            "routing_history": [],
        }

        for iteration in range(1, max_iterations + 1):
            context["iteration"] = iteration

            if self.debug:
                print(f"\n[ROUTER] --- Iteration {iteration} ---")

            # SENSE: Analyze query
            sensed = self._sense(context)

            if self.debug:
                print(f"[ROUTER] SENSE: keywords={sensed.get('detected_keywords', [])}")

            # PLAN: Decide routing strategy
            plan = self._plan(sensed)

            if self.debug:
                print(f"[ROUTER] PLAN: {plan}")

            # Check if confident enough to complete
            if plan.get("action") == "COMPLETE":
                if self.debug:
                    print(f"[ROUTER] COMPLETE: chapter={plan.get('primary_chapter')}, "
                          f"confidence={plan.get('confidence')}")
                return self._create_result(plan)

            # ACT: Verify routing decision
            result = self._act(plan, context)

            # OBSERVE: Record what happened
            observation = self._observe(plan, result)

            # REFLECT: Evaluate routing decision
            reflection = self._reflect(context, observation)

            # Update context
            context["last_plan"] = plan
            context["last_result"] = result
            context["last_reflection"] = reflection
            context["routing_history"].append(
                {
                    "iteration": iteration,
                    "plan": plan,
                    "result": result,
                }
            )

        # Return best result from iterations
        return self._create_result(
            context.get(
                "last_plan", {"primary_chapter": 1, "confidence": 0.5}
            )
        )

    def _sense(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """SENSE: Extract query features for routing."""
        query = context["query"]

        sensed = {
            **context,
            "query_length": len(query.split()),
            "has_formula": bool(self._detect_formula(query)),
            "detected_keywords": self._extract_keywords(query),
            "chapter_index": self.CHAPTER_INDEX,
        }

        return sensed

    def _plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """PLAN: Use LLM to decide which chapters are relevant."""
        chapter_desc = self._format_chapter_index()

        prompt = f"""You are routing a student's Physics question to relevant chapters.

STUDENT QUERY: {context['query']}

AVAILABLE CHAPTERS:
{chapter_desc}

DETECTED KEYWORDS: {', '.join(context.get('detected_keywords', []))}

Analyze the query and determine which chapter(s) are most relevant.

Respond with ONLY valid JSON:
{{
    "action": "COMPLETE",
    "primary_chapter": <chapter number 1-9>,
    "secondary_chapters": [<additional relevant chapters>],
    "confidence": <0.0 to 1.0>,
    "reasoning": "<why you chose these chapters>",
    "topics_identified": ["<topic1>", "<topic2>"]
}}

Rules:
- Primary chapter should be most relevant
- Secondary chapters for related concepts (max 2)
- Confidence 0.8+ means very confident
- If query spans multiple topics, include secondary chapters"""

        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a chapter routing assistant. Respond only with JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        plan = self._parse_json(response.choices[0].message.content)
        return plan

    def _act(
        self, plan: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ACT: Verify routing decision against chapter data."""
        primary = plan.get("primary_chapter", 1)
        secondary = plan.get("secondary_chapters", [])

        # Validate chapter numbers
        valid_primary = primary if primary in self.CHAPTER_INDEX else 1
        valid_secondary = [
            c
            for c in secondary
            if c in self.CHAPTER_INDEX and c != valid_primary
        ]

        # Get chapter details
        primary_info = self.CHAPTER_INDEX.get(valid_primary, {})

        return {
            "primary_chapter": valid_primary,
            "primary_title": primary_info.get("title", "Unknown"),
            "secondary_chapters": valid_secondary[:2],
            "validated": True,
        }

    def _observe(
        self, plan: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OBSERVE: Record routing outcome."""
        return {
            "action": plan.get("action"),
            "chapters_selected": [result["primary_chapter"]]
            + result["secondary_chapters"],
            "success": result.get("validated", False),
        }

    def _reflect(
        self, context: Dict[str, Any], observation: Dict[str, Any]
    ) -> str:
        """REFLECT: Evaluate routing quality."""
        if observation["success"]:
            return f"Successfully routed to chapter(s): {observation['chapters_selected']}"
        else:
            return "Routing validation failed, may need refinement"

    def _create_result(self, plan: Dict[str, Any]) -> RoutingResult:
        """Create final RoutingResult from plan."""
        return RoutingResult(
            primary_chapter=plan.get("primary_chapter", 1),
            secondary_chapters=plan.get("secondary_chapters", []),
            confidence=plan.get("confidence", 0.5),
            reasoning=plan.get("reasoning", ""),
            topics_identified=plan.get("topics_identified", []),
        )

    def _format_chapter_index(self) -> str:
        """Format chapter index for LLM prompt."""
        lines = []
        for num, info in self.CHAPTER_INDEX.items():
            topics = ", ".join(info["topics"][:5])
            lines.append(f"Chapter {num}: {info['title']} - Topics: {topics}")
        return "\n".join(lines)

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query for matching."""
        query_lower = query.lower()
        keywords = []

        for chapter_info in self.CHAPTER_INDEX.values():
            for keyword in chapter_info.get("keywords", []):
                if keyword.lower() in query_lower:
                    keywords.append(keyword)

        return list(set(keywords))

    def _detect_formula(self, text: str) -> bool:
        """Detect if text contains a formula."""
        patterns = [
            r"[A-Za-z]\s*=\s*[A-Za-z0-9]",
            r"F\s*=\s*ma",
            r"v\s*=\s*u",
        ]
        return any(re.search(p, text) for p in patterns)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text.strip())
