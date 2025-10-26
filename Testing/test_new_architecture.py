"""
Quick test to validate the new architecture without running the full pipeline.
This test checks:
1. Dynamic persona loading
2. Persona summary initialization
3. FacilitatorAgent creation
4. Basic integration

Run this before running the full pipeline to catch any integration issues.
"""

from dotenv import load_dotenv
load_dotenv()

from utils import load_all_personas
from facilitator import FacilitatorAgent
from persona import Persona

def test_persona_loading():
    """Test dynamic persona loading from personas/ directory."""
    print("\n" + "="*60)
    print("TEST 1: Dynamic Persona Loading")
    print("="*60)

    try:
        personas = load_all_personas(directory="personas", model_name="gpt-4o-mini")
        print(f"\n[OK] Successfully loaded {len(personas)} personas")

        # Verify each persona has a summary
        for name, persona in personas.items():
            assert hasattr(persona, 'summary'), f"{name} missing summary attribute"
            assert 'objective_facts' in persona.summary, f"{name} summary missing objective_facts"
            assert 'subjective_notes' in persona.summary, f"{name} summary missing subjective_notes"

        print("[OK] All personas have proper summary structure")
        return True

    except Exception as e:
        print(f"[FAIL] Persona loading failed: {e}")
        return False


def test_facilitator():
    """Test FacilitatorAgent initialization."""
    print("\n" + "="*60)
    print("TEST 2: FacilitatorAgent Creation")
    print("="*60)

    try:
        facilitator = FacilitatorAgent(model_name="gpt-4o-mini")
        print("[OK] FacilitatorAgent created successfully")

        # Verify it has the required methods
        assert hasattr(facilitator, 'select_personas_for_phase'), "Missing select_personas_for_phase"
        assert hasattr(facilitator, 'decide_next_speaker'), "Missing decide_next_speaker"
        assert hasattr(facilitator, 'summarize_phase'), "Missing summarize_phase"

        print("[OK] FacilitatorAgent has all required methods")
        return True

    except Exception as e:
        print(f"[FAIL] FacilitatorAgent creation failed: {e}")
        return False


def test_persona_summary_format():
    """Test persona summary formatting."""
    print("\n" + "="*60)
    print("TEST 3: Persona Summary Formatting")
    print("="*60)

    try:
        # Load a single persona
        persona = Persona.from_file("personas/founder.json", model_name="gpt-4o-mini")

        # Test empty summary formatting
        empty_summary = persona._format_summary()
        print(f"[i] Empty summary: {empty_summary}")
        assert "No summary yet" in empty_summary, "Empty summary format incorrect"

        # Add some test data
        persona.summary["objective_facts"].append("Test fact 1")
        persona.summary["subjective_notes"]["opinions"].append("Test opinion 1")

        # Test populated summary formatting
        populated_summary = persona._format_summary()
        print(f"\n[i] Populated summary:\n{populated_summary}")
        assert "Test fact 1" in populated_summary, "Objective facts not in summary"
        assert "Test opinion 1" in populated_summary, "Subjective notes not in summary"

        print("\n[OK] Persona summary formatting works correctly")
        return True

    except Exception as e:
        print(f"[FAIL] Summary formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test basic integration without making API calls."""
    print("\n" + "="*60)
    print("TEST 4: Integration Test")
    print("="*60)

    try:
        # Load personas
        personas = load_all_personas(directory="personas", model_name="gpt-4o-mini")

        # Create facilitator
        facilitator = FacilitatorAgent(model_name="gpt-4o-mini")

        # Create a test phase
        test_phase = {
            "phase_id": "test_phase",
            "goal": "Test the integration",
            "desired_outcome": "Verify all components work together",
            "max_turns": 5
        }

        # Create shared context
        shared_context = {
            "user_prompt": "Test prompt",
            "test_mode": True
        }

        print(f"[OK] Created test phase and shared context")
        print(f"[OK] Available personas: {list(personas.keys())}")
        print(f"[OK] Facilitator ready")
        print("\n[OK] Integration test passed - all components initialized correctly")

        return True

    except Exception as e:
        print(f"[FAIL] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING NEW ARCHITECTURE")
    print("="*60)

    results = {
        "Persona Loading": test_persona_loading(),
        "FacilitatorAgent": test_facilitator(),
        "Summary Formatting": test_persona_summary_format(),
        "Integration": test_integration()
    }

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED")
        print("Ready to run the full pipeline with: python main.py")
    else:
        print("SOME TESTS FAILED")
        print("Fix issues before running the full pipeline")
    print("="*60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
