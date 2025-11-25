# persona.py
import json
import asyncio
from typing import Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI


def extract_last_claim(last_turn: Dict) -> str:
    """
    Extract a specific claim (5-12 words) from the last speaker's turn.

    Args:
        last_turn: Dict with 'speaker' and 'content' keys

    Returns:
        Truncated claim quote (max 12 words)
    """
    content = last_turn.get("content", "")
    if not content:
        return "the previous point"

    # Split into sentences and take the first substantial one
    sentences = content.replace("!", ".").replace("?", ".").split(".")
    for sentence in sentences:
        words = sentence.strip().split()
        if len(words) >= 5:
            # Return 5-12 words from this sentence
            claim_words = words[:12]
            return " ".join(claim_words)

    # Fallback: take first 12 words of entire content
    words = content.split()[:12]
    return " ".join(words) if words else "the previous point"


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())

class Persona:
    def __init__(self, definition: Dict[str, Any], model_name: str = "gpt-3.5-turbo"):
        """
        definition: dict loaded from JSON defining this persona
        model_name: default model used for responses
        """
        self.name = definition.get("Name", "Unknown Persona")
        self.archetype = definition.get("Archetype", "")
        self.purpose = definition.get("Purpose", "")
        self.deliverables = definition.get("Deliverables", "")
        self.strengths = definition.get("Strengths", "")
        self.watchouts = definition.get("Watch-out", "")
        self.conversation_style = definition.get("Conversation_Style", "")
        self.model_name = model_name
        self.client = OpenAI()  # your LLM client
        self.async_client = AsyncOpenAI()  # async LLM client for parallel operations

        # Initialize hybrid summary (objective facts + subjective notes)
        self.summary = {
            "objective_facts": [],
            "subjective_notes": {
                "key_concerns": [],
                "priorities": [],
                "opinions": []
            }
        }

        # Enhanced persona memory with belief state delta tracking
        self.memory = {
            "belief_state": None,  # Initialized on first turn
            "last_relevant_point": None,  # Single extracted quote from last speaker
            "history_delta": []  # List of deltas for debugging
        }

        # Domain-adapted belief state (separate from summary)
        # Summary = what happened (memory)
        # Belief state = current position/uncertainties/concessions (epistemic state)
        self.belief_state = None  # Initialized on first turn
        self._domain = None       # Detected from phase config

        # Native conversation threading - maintains OpenAI message format
        # Each persona has their own conversation thread
        self.conversation_history = []  # List of {"role": "user"/"assistant", "content": "..."}

    @classmethod
    def from_file(cls, path: str, model_name: str = "gpt-3.5-turbo"):
        """Initialize persona directly from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            definition = json.load(f)
        return cls(definition, model_name=model_name)

    def _initialize_belief_state(self, domain: str, phase_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize domain-adapted belief state on first turn with delta-based tracking.

        Args:
            domain: Domain type ("philosophical_debate", "startup_ideas", etc.)
            phase_info: Current phase information

        Returns:
            Initialized belief state dict with certainty, conditional_rules, exceptions, accepted_critiques
        """
        # Base schema with new delta-based fields
        base_schema = {
            "position": None,  # Will be set on first response
            "certainty": "medium",  # "low" | "medium" | "high"
            "conditional_rules": [],  # "If X then Y" type rules
            "exceptions": [],  # Known exceptions to position
            "accepted_critiques": [],  # Critiques accepted from others
            "confidence": 0.5,  # 0.0-1.0 numeric scale (backward compatible)
        }

        # Domain-specific schemas
        if domain == "philosophical_debate":
            return {
                **base_schema,
                "uncertainties": [],  # What I'm unsure about
                "concessions": [],  # Points acknowledged from others: {from_speaker, point, turn}
                "deltas": [],  # Position shifts: {turn, change, reason}
                "cruxes": []  # Key questions that would change my mind
            }
        elif domain == "startup_ideas":
            return {
                **base_schema,
                "uncertainties": [],  # Market/tech/competitive risks
                "concessions": [],  # Acknowledged concerns/benefits from others
                "deltas": [],  # Preference shifts
                "key_tradeoffs": []  # Recognized tradeoffs between options
            }
        else:
            # Generic fallback for unknown domains
            return {
                **base_schema,
                "uncertainties": [],
                "concessions": [],
                "deltas": []
            }

    def response(self, ctx: Dict[str, Any], prompt_key: Optional[str] = None, prompt_logger: Optional[callable] = None) -> Dict[str, Any]:
        """
        Generate a persona response using native OpenAI conversation threading.
        Each persona maintains their own conversation history with proper message roles.

        Args:
            ctx: Context dictionary containing:
                - initial_prompt: Facilitator's starter prompt for this phase
                - other_speaker: Optional dict with {name, message} from the last speaker
                - turn_count: Current turn number in phase
                - phase: Phase information (for belief state)
            prompt_logger: Optional callback to log the full prompt input before LLM call

        Returns:
            Dict with persona, archetype, and response
        """
        # Extract context
        initial_prompt = ctx.get("initial_prompt", "")
        other_speaker = ctx.get("other_speaker")  # {name, message} or None
        turn_count = ctx.get("turn_count", 0)
        phase = ctx.get("phase", {})

        # Initialize belief state on first turn if not already set
        domain = phase.get("domain") or ctx.get("domain")
        if self.belief_state is None and turn_count == 0:
            if not domain:
                phase_id = phase.get("phase_id", "")
                if "ethical" in phase_id or "philosophical" in phase_id or "moral" in phase_id:
                    domain = "philosophical_debate"
                elif "idea" in phase_id or "startup" in phase_id or "product" in phase_id:
                    domain = "startup_ideas"
                else:
                    domain = "general"
            self._domain = domain
            self.belief_state = self._initialize_belief_state(domain, phase)
            print(f"[i] Initialized {domain} belief state for {self.name}")

        # Build system message as bare logic-role (no personality)
        response_rules = """

RESPONSE RULES:
- Max 4 sentences
- Quote exact prior text
- State agreement/disagreement explicitly
- Update belief state or state no-update
- No gratitude, no social language, no metaphors"""

        system_message = (
            f"Role: {self.name}\n"
            f"Reasoning type: {self.archetype}\n"
            f"Objective: {self.purpose}\n"
            f"Belief structure: {self.deliverables}\n"
            f"Strengths: {self.strengths}\n"
            f"Failure mode: {self.watchouts}"
            f"{response_rules}"
        )

        # Build new user message
        # First turn: just initial_prompt
        # Subsequent turns for first speaker: initial_prompt (already in history) + other speaker's message
        # Subsequent turns for others: other speaker's message
        if not self.conversation_history:
            # First time this persona speaks
            if other_speaker:
                # Not the first speaker in the conversation
                new_user_message = f"{initial_prompt}\n\n{other_speaker['name']} says: {other_speaker['message']}"
            else:
                # First speaker in the conversation
                new_user_message = initial_prompt
        else:
            # Persona has spoken before - just add other speaker's message
            new_user_message = f"{other_speaker['name']} says: {other_speaker['message']}"

        # Build messages array: system + conversation_history + new user message
        messages = [{"role": "system", "content": system_message}] + self.conversation_history + [{"role": "user", "content": new_user_message}]

        # Log prompt input if callback provided
        if prompt_logger:
            try:
                # For logging, reconstruct the full prompt view
                full_prompt = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
                prompt_logger({
                    "system_message": system_message,
                    "enhanced_prompt": full_prompt,
                    "token_count": 0  # Token counting can be added later if needed
                })
            except Exception as e:
                print(f"[!] Warning: Failed to log prompt input: {e}")

        # Call LLM
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )

        content = completion.choices[0].message.content.strip()

        # Append to conversation history
        self.conversation_history.append({"role": "user", "content": new_user_message})
        self.conversation_history.append({"role": "assistant", "content": content})

        return {
            "persona": self.name,
            "archetype": self.archetype,
            "response": content
        }

    def _format_summary(self) -> str:
        """
        Format persona's memory as 1-2 bullet points ONLY.

        Max output: ~150 tokens (vs previous 1K-5K tokens unbounded growth)
        """
        if not self.summary.get("objective_facts") and not any(self.summary.get("subjective_notes", {}).values()):
            return "No memory yet (first turn)"

        lines = []

        # Take ONLY last 1-2 objective facts (most recent observations)
        obj_facts = self.summary.get("objective_facts", [])
        if obj_facts:
            recent_facts = obj_facts[-2:]  # Last 2 only
            lines.append("Your recent observations:")
            for fact in recent_facts:
                # Truncate each fact to 50 chars max
                truncated = fact[:50] + "..." if len(fact) > 50 else fact
                lines.append(f"  - {truncated}")

        # Take ONLY last 1 subjective note from MOST IMPORTANT category
        # Priority order: key_concerns > priorities > opinions
        subj_notes = self.summary.get("subjective_notes", {})
        if subj_notes.get("key_concerns"):
            concern = subj_notes["key_concerns"][-1]  # Last 1 only
            concern_truncated = concern[:50] + "..." if len(concern) > 50 else concern
            lines.append(f"Your main concern: {concern_truncated}")
        elif subj_notes.get("priorities"):
            priority = subj_notes["priorities"][-1]  # Last 1 only
            priority_truncated = priority[:50] + "..." if len(priority) > 50 else priority
            lines.append(f"Your priority: {priority_truncated}")

        return "\n".join(lines) if lines else "No memory yet"

    def _format_shared_context_compressed(self, shared_context: Dict[str, Any]) -> str:
        """
        Format shared context with RICH idea memory cards (2-3 full summaries).

        Max output: ~400-500 tokens (keeping 2-3 idea summaries with full context)

        Shows actual solutions with pros/cons/examples instead of just titles.

        Args:
            shared_context: Full shared context dict

        Returns:
            Compressed snapshot with 2-3 idea memory cards with full details
        """
        lines = []

        # Current focus (1 line)
        if shared_context.get("current_focus"):
            lines.append(f"Current focus: {shared_context['current_focus']}")
            lines.append("")  # Blank line

        # In-play ideas as RICH MEMORY CARDS (150 tokens each × 3 = 450 tokens)
        try:
            from src.idea_generation.idea_tracker import (
                get_ideas_in_play,
                format_ideas_as_memory_cards
            )

            in_play = get_ideas_in_play(shared_context.get("ideas_discussed", []))
            if in_play:
                # Show current focus + 2 alternatives (max 3 ideas with full context)
                if shared_context.get("current_focus"):
                    # Find current focus idea + two others
                    focus_idea = next((i for i in in_play if i["title"] == shared_context["current_focus"]), None)
                    other_ideas = [i for i in in_play if i["title"] != shared_context["current_focus"]][-2:]
                    ideas_to_show = ([focus_idea] if focus_idea else []) + other_ideas
                else:
                    # No focus set, show last 3
                    ideas_to_show = in_play[-3:]

                # Format as memory cards with FULL details (2-sentence solution + reasons + counterpoint)
                cards = format_ideas_as_memory_cards(ideas_to_show, max_count=3)
                lines.append(cards)
                lines.append("")  # Blank line
        except ImportError:
            # idea_tracker not available in basic setup - fall back to basic format
            ideas_discussed = shared_context.get("ideas_discussed", [])
            if ideas_discussed:
                in_play = [idea for idea in ideas_discussed if idea.get("status") != "rejected"]
                if in_play:
                    lines.append("Ideas being discussed:")
                    for idea in in_play[-3:]:  # Last 3 ideas
                        title = idea.get("title", "Untitled")
                        overview = idea.get("overview", "")[:100]  # Keep some context
                        lines.append(f"  - {title}: {overview}")

        # Rejected ideas (titles only, 1 line)
        try:
            from src.idea_generation.idea_tracker import get_rejected_ideas
            rejected = get_rejected_ideas(shared_context.get("ideas_discussed", []))
            if rejected:
                rejected_titles = [idea["title"] for idea in rejected[-2:]]
                lines.append(f"Rejected: {', '.join(rejected_titles)}")
        except ImportError:
            pass

        return "\n".join(lines) if lines else "No shared context yet"

    def _format_recent_exchanges(self, exchanges: List[Dict[str, Any]]) -> str:
        """
        Format ONLY the last 1-2 exchanges for tight, focused context.

        Max output: ~200 tokens (vs previous 625 tokens from 5 exchanges)

        Args:
            exchanges: List of exchange dicts with speaker, content, etc.

        Returns:
            Formatted string showing last 1-2 turns only
        """
        if not exchanges:
            return "No discussion yet (you're first)"

        # Take ONLY last 2 exchanges (user requirement: 1-2 turns)
        recent = exchanges[-2:]

        formatted = []
        for ex in recent:
            speaker = ex.get("speaker", "Unknown")
            content = ex.get("content", "")

            # Truncate to 200 chars (was 500)
            truncated = content[:200] + "..." if len(content) > 200 else content
            formatted.append(f"{speaker}: {truncated}")

        return "\n\n".join(formatted)

    def _format_full_history(self, exchanges: List[Dict[str, Any]], max_turns: int = 15) -> str:
        """
        Format the full conversation history (last N turns) with complete content.

        Args:
            exchanges: List of exchange dicts with speaker, content, turn, etc.
            max_turns: Maximum number of turns to include (default: 15)

        Returns:
            Formatted string showing full conversation history with no truncation
        """
        if not exchanges:
            return "No discussion yet (you're first)"

        # Take last N exchanges (default 15 for balance between context and tokens)
        recent = exchanges[-max_turns:]

        formatted = []
        for ex in recent:
            turn = ex.get("turn", "?")
            speaker = ex.get("speaker", "Unknown")
            content = ex.get("content", "")

            # Include full content with no truncation
            formatted.append(f"Turn {turn} - {speaker}:\n{content}")

        return "\n\n".join(formatted)

    def _format_belief_state(self) -> str:
        """
        Format belief state for inclusion in prompts with delta-based fields.

        Returns:
            Formatted string showing position, certainty, conditional_rules, exceptions, accepted_critiques, etc.
        """
        if not self.belief_state:
            return "No belief state yet (first turn)"

        lines = []

        # Current position
        position = self.belief_state.get("position")
        if position:
            lines.append(f"Current position: {position}")

        # Certainty level (new delta-based field)
        certainty = self.belief_state.get("certainty", "medium")
        lines.append(f"Certainty: {certainty}")

        # Confidence level (backward compatible)
        confidence = self.belief_state.get("confidence", 0.5)
        conf_label = "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
        lines.append(f"Confidence (numeric): {conf_label} ({confidence:.1f})")

        # Conditional rules (new delta-based field)
        conditional_rules = self.belief_state.get("conditional_rules", [])
        if conditional_rules:
            lines.append("Conditional rules:")
            for rule in conditional_rules[-3:]:  # Show last 3
                rule_truncated = rule[:60] + "..." if len(rule) > 60 else rule
                lines.append(f"  - {rule_truncated}")

        # Exceptions (new delta-based field)
        exceptions = self.belief_state.get("exceptions", [])
        if exceptions:
            lines.append("Exceptions to position:")
            for exc in exceptions[-3:]:  # Show last 3
                exc_truncated = exc[:60] + "..." if len(exc) > 60 else exc
                lines.append(f"  - {exc_truncated}")

        # Accepted critiques (new delta-based field)
        accepted_critiques = self.belief_state.get("accepted_critiques", [])
        if accepted_critiques:
            lines.append("Accepted critiques:")
            for critique in accepted_critiques[-3:]:  # Show last 3
                critique_truncated = critique[:60] + "..." if len(critique) > 60 else critique
                lines.append(f"  - {critique_truncated}")

        # Uncertainties (show last 2-3)
        uncertainties = self.belief_state.get("uncertainties", [])
        if uncertainties:
            recent_uncertainties = uncertainties[-3:]
            lines.append("Uncertainties:")
            for unc in recent_uncertainties:
                unc_truncated = unc[:60] + "..." if len(unc) > 60 else unc
                lines.append(f"  - {unc_truncated}")

        # Concessions (show last 2)
        concessions = self.belief_state.get("concessions", [])
        if concessions:
            recent_concessions = concessions[-2:]
            lines.append("Concessions:")
            for conc in recent_concessions:
                from_speaker = conc.get("from_speaker", "Unknown")
                point = conc.get("point", "")[:50] + "..." if len(conc.get("point", "")) > 50 else conc.get("point", "")
                lines.append(f"  - Acknowledged from {from_speaker}: {point}")

        # Deltas (show last 2 position shifts)
        deltas = self.belief_state.get("deltas", [])
        if deltas:
            recent_deltas = deltas[-2:]
            lines.append("Position changes:")
            for delta in recent_deltas:
                turn = delta.get("turn", "?")
                change = delta.get("change", "")[:50] + "..." if len(delta.get("change", "")) > 50 else delta.get("change", "")
                lines.append(f"  - Turn {turn}: {change}")

        # Domain-specific fields
        # For philosophical debates: cruxes
        if "cruxes" in self.belief_state and self.belief_state["cruxes"]:
            cruxes = self.belief_state["cruxes"][-2:]
            lines.append("Key cruxes (what would change my mind):")
            for crux in cruxes:
                crux_truncated = crux[:60] + "..." if len(crux) > 60 else crux
                lines.append(f"  - {crux_truncated}")

        # For startup ideas: key_tradeoffs
        if "key_tradeoffs" in self.belief_state and self.belief_state["key_tradeoffs"]:
            tradeoffs = self.belief_state["key_tradeoffs"][-2:]
            lines.append("Recognized tradeoffs:")
            for tradeoff in tradeoffs:
                tradeoff_truncated = tradeoff[:60] + "..." if len(tradeoff) > 60 else tradeoff
                lines.append(f"  - {tradeoff_truncated}")

        return "\n".join(lines) if lines else "No belief state yet"

    def update_summary(self, new_exchange: Dict[str, Any]) -> None:
        """
        Update the persona's summary based on a new conversation exchange.

        Uses LLM to extract:
        1. Objective facts that should be added to shared understanding
        2. Subjective observations relevant to this persona's role

        Args:
            new_exchange: Dict containing:
                - speaker: Who spoke
                - content: What was said
                - phase: Current phase info (optional)
        """
        speaker = new_exchange.get("speaker", "Unknown")
        content = new_exchange.get("content", "")
        phase = new_exchange.get("phase", "")

        # Build prompt for summary update
        update_prompt = f"""You are {self.name}, the {self.archetype}.

CURRENT SUMMARY:
{self._format_summary()}

NEW EXCHANGE:
{speaker}: {content}

CURRENT PHASE: {phase}

Update your summary by:
1. Extracting any new OBJECTIVE FACTS (concrete information that everyone should know)
2. Adding your SUBJECTIVE NOTES as {self.archetype} (concerns, priorities, opinions)

Respond ONLY with a JSON object in this format:
{{
  "new_objective_facts": ["fact1", "fact2"],
  "new_subjective_notes": {{
    "key_concerns": ["concern1"],
    "priorities": ["priority1"],
    "opinions": ["opinion1"]
  }}
}}

Only include fields that have new information. Empty lists/objects are fine if nothing new."""

        messages = [
            {
                "role": "system",
                "content": f"You are a summary updater for {self.name}, the {self.archetype}. "
                           f"Extract objective facts and subjective notes from conversations."
            },
            {
                "role": "user",
                "content": update_prompt
            }
        ]

        # Call LLM to update summary
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            updates = json.loads(response_content)

            # Merge new facts (avoid duplicates)
            new_facts = updates.get("new_objective_facts", [])
            for fact in new_facts:
                if fact and fact not in self.summary["objective_facts"]:
                    self.summary["objective_facts"].append(fact)

            # Merge subjective notes
            new_subj = updates.get("new_subjective_notes", {})
            for key, values in new_subj.items():
                if key in self.summary["subjective_notes"]:
                    if isinstance(values, list):
                        for val in values:
                            if val and val not in self.summary["subjective_notes"][key]:
                                self.summary["subjective_notes"][key].append(val)
                    else:
                        self.summary["subjective_notes"][key] = values
                else:
                    self.summary["subjective_notes"][key] = values

        except Exception as e:
            print(f"[!] Failed to update summary for {self.name}: {e}")
            # Continue without updating - non-critical failure

    async def update_summary_async(self, new_exchange: Dict[str, Any]) -> None:
        """
        Async version of update_summary for parallel execution.

        Update the persona's summary based on a new conversation exchange.
        This method can be called concurrently with other personas for speedup.

        Uses LLM to extract:
        1. Objective facts that should be added to shared understanding
        2. Subjective observations relevant to this persona's role

        Args:
            new_exchange: Dict containing:
                - speaker: Who spoke
                - content: What was said
                - phase: Current phase info (optional)
        """
        speaker = new_exchange.get("speaker", "Unknown")
        content = new_exchange.get("content", "")
        phase = new_exchange.get("phase", "")

        # Build prompt for summary update
        update_prompt = f"""You are {self.name}, the {self.archetype}.

CURRENT SUMMARY:
{self._format_summary()}

NEW EXCHANGE:
{speaker}: {content}

CURRENT PHASE: {phase}

Update your summary by:
1. Extracting any new OBJECTIVE FACTS (concrete information that everyone should know)
2. Adding your SUBJECTIVE NOTES as {self.archetype} (concerns, priorities, opinions)

Respond ONLY with a JSON object in this format:
{{
  "new_objective_facts": ["fact1", "fact2"],
  "new_subjective_notes": {{
    "key_concerns": ["concern1"],
    "priorities": ["priority1"],
    "opinions": ["opinion1"]
  }}
}}

Only include fields that have new information. Empty lists/objects are fine if nothing new."""

        messages = [
            {
                "role": "system",
                "content": f"You are a summary updater for {self.name}, the {self.archetype}. "
                           f"Extract objective facts and subjective notes from conversations."
            },
            {
                "role": "user",
                "content": update_prompt
            }
        ]

        # Call LLM asynchronously to update summary
        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            updates = json.loads(response_content)

            # Merge new facts (avoid duplicates)
            new_facts = updates.get("new_objective_facts", [])
            for fact in new_facts:
                if fact and fact not in self.summary["objective_facts"]:
                    self.summary["objective_facts"].append(fact)

            # Merge subjective notes
            new_subj = updates.get("new_subjective_notes", {})
            for key, values in new_subj.items():
                if key in self.summary["subjective_notes"]:
                    if isinstance(values, list):
                        for val in values:
                            if val and val not in self.summary["subjective_notes"][key]:
                                self.summary["subjective_notes"][key].append(val)
                    else:
                        self.summary["subjective_notes"][key] = values
                else:
                    self.summary["subjective_notes"][key] = values

        except Exception as e:
            print(f"[!] Failed to async update summary for {self.name}: {e}")
            # Continue without updating - non-critical failure

    def update_belief_state(self, new_exchange: Dict[str, Any], turn_count: int) -> None:
        """
        Update the persona's belief state based on a new conversation exchange.

        Uses LLM to extract:
        1. Updated position (if changed)
        2. New uncertainties or resolved ones
        3. Concessions made to other speakers
        4. Position deltas (what changed and why)
        5. Domain-specific fields (cruxes, key_tradeoffs, etc.)

        Args:
            new_exchange: Dict containing:
                - speaker: Who spoke
                - content: What was said
                - phase: Current phase info (optional)
            turn_count: Current turn number
        """
        if not self.belief_state:
            return  # Belief state not initialized yet

        speaker = new_exchange.get("speaker", "Unknown")
        content = new_exchange.get("content", "")
        phase = new_exchange.get("phase", "")

        # Build prompt for belief state update
        current_belief_state = json.dumps(self.belief_state, indent=2)

        update_prompt = f"""You are {self.name}, the {self.archetype}.

CURRENT BELIEF STATE:
{current_belief_state}

NEW EXCHANGE:
{speaker}: {content}

CURRENT PHASE: {phase}
TURN: {turn_count}

Update your belief state by extracting:
1. **position**: Has your position changed? (if yes, provide new position statement, else leave null)
2. **confidence**: Updated confidence level 0.0-1.0 (or null if no change)
3. **new_uncertainties**: Any new things you're uncertain about
4. **resolved_uncertainties**: Any uncertainties that were resolved (provide index from current list)
5. **new_concessions**: Points you acknowledged from the last speaker (if any)
6. **new_deltas**: Position shifts (if any) - what changed and why
7. **domain_specific**: Any domain-specific updates (cruxes for debates, key_tradeoffs for ideas)

Respond ONLY with a JSON object in this format:
{{
  "position": "updated position statement or null",
  "confidence": 0.7 or null,
  "new_uncertainties": ["uncertainty1"],
  "resolved_uncertainties": [0, 1],
  "new_concessions": [
    {{"from_speaker": "Name", "point": "what you acknowledged"}}
  ],
  "new_deltas": [
    {{"turn": {turn_count}, "change": "what shifted", "reason": "why"}}
  ],
  "domain_specific": {{
    "cruxes": ["new crux"] or "key_tradeoffs": ["new tradeoff"]
  }}
}}

Only include fields with new information. Empty lists/objects are fine if nothing new."""

        messages = [
            {
                "role": "system",
                "content": f"You are a belief state updater for {self.name}, the {self.archetype}. "
                           f"Extract position changes, uncertainties, concessions, and deltas."
            },
            {
                "role": "user",
                "content": update_prompt
            }
        ]

        # Call LLM to update belief state
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            updates = json.loads(response_content)

            # Update position if changed
            if updates.get("position"):
                old_position = self.belief_state.get("position")
                self.belief_state["position"] = updates["position"]
                if old_position and old_position != updates["position"]:
                    print(f"[i] {self.name} position changed: {old_position[:50]}... → {updates['position'][:50]}...")

            # Update confidence if changed
            if updates.get("confidence") is not None:
                self.belief_state["confidence"] = updates["confidence"]

            # Add new uncertainties
            for unc in updates.get("new_uncertainties", []):
                if unc and unc not in self.belief_state.get("uncertainties", []):
                    self.belief_state["uncertainties"].append(unc)

            # Remove resolved uncertainties
            for idx in sorted(updates.get("resolved_uncertainties", []), reverse=True):
                if 0 <= idx < len(self.belief_state.get("uncertainties", [])):
                    resolved = self.belief_state["uncertainties"].pop(idx)
                    print(f"[i] {self.name} resolved uncertainty: {resolved[:50]}...")

            # Add new concessions
            for conc in updates.get("new_concessions", []):
                if conc:
                    conc["turn"] = turn_count
                    self.belief_state["concessions"].append(conc)
                    print(f"[i] {self.name} conceded point from {conc.get('from_speaker')}: {conc.get('point', '')[:50]}...")

            # Add new deltas
            for delta in updates.get("new_deltas", []):
                if delta:
                    self.belief_state["deltas"].append(delta)
                    print(f"[i] {self.name} position delta (turn {turn_count}): {delta.get('change', '')[:50]}...")

            # Update domain-specific fields
            domain_spec = updates.get("domain_specific", {})
            for key, values in domain_spec.items():
                if key in self.belief_state and isinstance(values, list):
                    for val in values:
                        if val and val not in self.belief_state[key]:
                            self.belief_state[key].append(val)

        except Exception as e:
            print(f"[!] Failed to update belief state for {self.name}: {e}")
            # Continue without updating - non-critical failure

    async def update_belief_state_async(self, new_exchange: Dict[str, Any], turn_count: int) -> None:
        """
        Async version of update_belief_state for parallel execution.

        Update the persona's belief state based on a new conversation exchange.
        This method can be called concurrently with other personas for speedup.

        Args:
            new_exchange: Dict containing:
                - speaker: Who spoke
                - content: What was said
                - phase: Current phase info (optional)
            turn_count: Current turn number
        """
        if not self.belief_state:
            return  # Belief state not initialized yet

        speaker = new_exchange.get("speaker", "Unknown")
        content = new_exchange.get("content", "")
        phase = new_exchange.get("phase", "")

        # Build prompt for belief state update
        current_belief_state = json.dumps(self.belief_state, indent=2)

        update_prompt = f"""You are {self.name}, the {self.archetype}.

CURRENT BELIEF STATE:
{current_belief_state}

NEW EXCHANGE:
{speaker}: {content}

CURRENT PHASE: {phase}
TURN: {turn_count}

Update your belief state by extracting:
1. **position**: Has your position changed? (if yes, provide new position statement, else leave null)
2. **confidence**: Updated confidence level 0.0-1.0 (or null if no change)
3. **new_uncertainties**: Any new things you're uncertain about
4. **resolved_uncertainties**: Any uncertainties that were resolved (provide index from current list)
5. **new_concessions**: Points you acknowledged from the last speaker (if any)
6. **new_deltas**: Position shifts (if any) - what changed and why
7. **domain_specific**: Any domain-specific updates (cruxes for debates, key_tradeoffs for ideas)

Respond ONLY with a JSON object in this format:
{{
  "position": "updated position statement or null",
  "confidence": 0.7 or null,
  "new_uncertainties": ["uncertainty1"],
  "resolved_uncertainties": [0, 1],
  "new_concessions": [
    {{"from_speaker": "Name", "point": "what you acknowledged"}}
  ],
  "new_deltas": [
    {{"turn": {turn_count}, "change": "what shifted", "reason": "why"}}
  ],
  "domain_specific": {{
    "cruxes": ["new crux"] or "key_tradeoffs": ["new tradeoff"]
  }}
}}

Only include fields with new information. Empty lists/objects are fine if nothing new."""

        messages = [
            {
                "role": "system",
                "content": f"You are a belief state updater for {self.name}, the {self.archetype}. "
                           f"Extract position changes, uncertainties, concessions, and deltas."
            },
            {
                "role": "user",
                "content": update_prompt
            }
        ]

        # Call LLM asynchronously to update belief state
        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            updates = json.loads(response_content)

            # Update position if changed
            if updates.get("position"):
                old_position = self.belief_state.get("position")
                self.belief_state["position"] = updates["position"]
                if old_position and old_position != updates["position"]:
                    print(f"[i] {self.name} position changed: {old_position[:50]}... → {updates['position'][:50]}...")

            # Update confidence if changed
            if updates.get("confidence") is not None:
                self.belief_state["confidence"] = updates["confidence"]

            # Add new uncertainties
            for unc in updates.get("new_uncertainties", []):
                if unc and unc not in self.belief_state.get("uncertainties", []):
                    self.belief_state["uncertainties"].append(unc)

            # Remove resolved uncertainties
            for idx in sorted(updates.get("resolved_uncertainties", []), reverse=True):
                if 0 <= idx < len(self.belief_state.get("uncertainties", [])):
                    resolved = self.belief_state["uncertainties"].pop(idx)
                    print(f"[i] {self.name} resolved uncertainty: {resolved[:50]}...")

            # Add new concessions
            for conc in updates.get("new_concessions", []):
                if conc:
                    conc["turn"] = turn_count
                    self.belief_state["concessions"].append(conc)
                    print(f"[i] {self.name} conceded point from {conc.get('from_speaker')}: {conc.get('point', '')[:50]}...")

            # Add new deltas
            for delta in updates.get("new_deltas", []):
                if delta:
                    self.belief_state["deltas"].append(delta)
                    print(f"[i] {self.name} position delta (turn {turn_count}): {delta.get('change', '')[:50]}...")

            # Update domain-specific fields
            domain_spec = updates.get("domain_specific", {})
            for key, values in domain_spec.items():
                if key in self.belief_state and isinstance(values, list):
                    for val in values:
                        if val and val not in self.belief_state[key]:
                            self.belief_state[key].append(val)

        except Exception as e:
            print(f"[!] Failed to async update belief state for {self.name}: {e}")
            # Continue without updating - non-critical failure
