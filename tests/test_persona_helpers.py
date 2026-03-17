# tests/test_persona_helpers.py
# Unit tests for Persona helper methods extracted during refactoring.
# These verify that _build_summary_messages, _apply_summary_updates,
# _build_belief_state_messages, and _apply_belief_state_updates produce
# the same output as the original inlined code.

import json
import pytest
from unittest.mock import MagicMock, patch
from framework.persona import Persona


MINIMAL_DEFINITION = {
    "Name": "TestPersona",
    "Archetype": "Test Archetype",
    "Purpose": "Testing",
    "Deliverables": "",
    "Strengths": "",
    "Watch-out": "",
    "Conversation_Style": "",
}


@pytest.fixture
def persona():
    with patch("framework.persona.OpenAI"), patch("framework.persona.AsyncOpenAI"):
        p = Persona(MINIMAL_DEFINITION, model_name="gpt-4o-mini")
    return p


@pytest.fixture
def exchange():
    return {"speaker": "Alice", "content": "The market is large.", "phase": "ideation"}


class TestBuildSummaryMessages:
    def test_returns_two_messages(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert len(msgs) == 2

    def test_system_message_role(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert msgs[0]["role"] == "system"

    def test_user_message_role(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert msgs[1]["role"] == "user"

    def test_system_contains_persona_name(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert "TestPersona" in msgs[0]["content"]

    def test_system_contains_archetype(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert "Test Archetype" in msgs[0]["content"]

    def test_prompt_contains_speaker(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert "Alice" in msgs[1]["content"]

    def test_prompt_contains_content(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert "The market is large." in msgs[1]["content"]

    def test_prompt_contains_phase(self, persona, exchange):
        msgs = persona._build_summary_messages(exchange)
        assert "ideation" in msgs[1]["content"]

    def test_prompt_contains_json_schema_fields(self, persona, exchange):
        prompt = persona._build_summary_messages(exchange)[1]["content"]
        assert "new_objective_facts" in prompt
        assert "new_subjective_notes" in prompt
        assert "key_concerns" in prompt

    def test_prompt_contains_persona_identity(self, persona, exchange):
        prompt = persona._build_summary_messages(exchange)[1]["content"]
        assert "TestPersona" in prompt
        assert "Test Archetype" in prompt


class TestApplySummaryUpdates:
    def test_adds_new_objective_facts(self, persona):
        updates = {"new_objective_facts": ["Fact A", "Fact B"], "new_subjective_notes": {}}
        persona._apply_summary_updates(updates)
        assert "Fact A" in persona.summary["objective_facts"]
        assert "Fact B" in persona.summary["objective_facts"]

    def test_does_not_duplicate_existing_facts(self, persona):
        persona.summary["objective_facts"].append("Existing fact")
        updates = {"new_objective_facts": ["Existing fact", "New fact"], "new_subjective_notes": {}}
        persona._apply_summary_updates(updates)
        assert persona.summary["objective_facts"].count("Existing fact") == 1

    def test_adds_subjective_notes(self, persona):
        updates = {
            "new_objective_facts": [],
            "new_subjective_notes": {"key_concerns": ["Risk of competition"]},
        }
        persona._apply_summary_updates(updates)
        assert "Risk of competition" in persona.summary["subjective_notes"]["key_concerns"]

    def test_does_not_duplicate_subjective_notes(self, persona):
        persona.summary["subjective_notes"]["key_concerns"].append("Existing concern")
        updates = {
            "new_objective_facts": [],
            "new_subjective_notes": {"key_concerns": ["Existing concern"]},
        }
        persona._apply_summary_updates(updates)
        assert persona.summary["subjective_notes"]["key_concerns"].count("Existing concern") == 1

    def test_adds_new_subjective_key(self, persona):
        updates = {
            "new_objective_facts": [],
            "new_subjective_notes": {"new_key": "some value"},
        }
        persona._apply_summary_updates(updates)
        assert persona.summary["subjective_notes"]["new_key"] == "some value"

    def test_empty_updates_are_safe(self, persona):
        original = json.dumps(persona.summary)
        persona._apply_summary_updates({"new_objective_facts": [], "new_subjective_notes": {}})
        assert json.dumps(persona.summary) == original


class TestBuildBeliefStateMessages:
    @pytest.fixture(autouse=True)
    def init_belief_state(self, persona):
        persona.belief_state = {
            "position": "Initial position",
            "confidence": 0.7,
            "uncertainties": [],
            "concessions": [],
            "deltas": [],
        }

    def test_returns_two_messages(self, persona, exchange):
        msgs = persona._build_belief_state_messages(exchange, turn_count=3)
        assert len(msgs) == 2

    def test_prompt_contains_turn_count(self, persona, exchange):
        prompt = persona._build_belief_state_messages(exchange, turn_count=5)[1]["content"]
        assert "5" in prompt

    def test_prompt_contains_current_belief_state(self, persona, exchange):
        prompt = persona._build_belief_state_messages(exchange, turn_count=0)[1]["content"]
        assert "Initial position" in prompt

    def test_prompt_contains_speaker_and_content(self, persona, exchange):
        prompt = persona._build_belief_state_messages(exchange, turn_count=0)[1]["content"]
        assert "Alice" in prompt
        assert "The market is large." in prompt

    def test_prompt_contains_required_json_fields(self, persona, exchange):
        prompt = persona._build_belief_state_messages(exchange, turn_count=0)[1]["content"]
        for field in ["position", "confidence", "new_uncertainties", "resolved_uncertainties",
                      "new_concessions", "new_deltas", "domain_specific"]:
            assert field in prompt

    def test_prompt_mentions_null_confidence(self, persona, exchange):
        prompt = persona._build_belief_state_messages(exchange, turn_count=0)[1]["content"]
        assert "or null" in prompt

    def test_system_contains_belief_state_updater(self, persona, exchange):
        msgs = persona._build_belief_state_messages(exchange, turn_count=0)
        assert "belief state updater" in msgs[0]["content"]


class TestApplyBeliefStateUpdates:
    @pytest.fixture(autouse=True)
    def init_belief_state(self, persona):
        persona.belief_state = {
            "position": "Original position",
            "confidence": 0.5,
            "uncertainties": ["First uncertainty"],
            "concessions": [],
            "deltas": [],
        }

    def test_updates_position(self, persona):
        persona._apply_belief_state_updates({"position": "New position"}, turn_count=1)
        assert persona.belief_state["position"] == "New position"

    def test_updates_confidence(self, persona):
        persona._apply_belief_state_updates({"confidence": 0.9}, turn_count=1)
        assert persona.belief_state["confidence"] == 0.9

    def test_adds_new_uncertainty(self, persona):
        persona._apply_belief_state_updates({"new_uncertainties": ["New uncertainty"]}, turn_count=1)
        assert "New uncertainty" in persona.belief_state["uncertainties"]

    def test_does_not_duplicate_uncertainty(self, persona):
        persona._apply_belief_state_updates({"new_uncertainties": ["First uncertainty"]}, turn_count=1)
        assert persona.belief_state["uncertainties"].count("First uncertainty") == 1

    def test_resolves_uncertainty_by_index(self, persona):
        persona._apply_belief_state_updates({"resolved_uncertainties": [0]}, turn_count=1)
        assert "First uncertainty" not in persona.belief_state["uncertainties"]

    def test_adds_concession(self, persona):
        conc = {"from_speaker": "Bob", "point": "Good point about market size"}
        persona._apply_belief_state_updates({"new_concessions": [conc]}, turn_count=2)
        assert len(persona.belief_state["concessions"]) == 1
        assert persona.belief_state["concessions"][0]["turn"] == 2

    def test_adds_delta(self, persona):
        delta = {"change": "Reconsidered scope", "reason": "Competitor data"}
        persona._apply_belief_state_updates({"new_deltas": [delta]}, turn_count=3)
        assert len(persona.belief_state["deltas"]) == 1

    def test_empty_updates_are_safe(self, persona):
        original_position = persona.belief_state["position"]
        persona._apply_belief_state_updates({}, turn_count=0)
        assert persona.belief_state["position"] == original_position

    def test_null_position_does_not_overwrite(self, persona):
        persona._apply_belief_state_updates({"position": None}, turn_count=0)
        assert persona.belief_state["position"] == "Original position"
