"""
Test script for ConversationAnalytics and ConversationReplayer

Tests both features with existing session logs from medium mode run.
"""

from framework import ConversationAnalytics, ConversationReplayer

# Use the medium mode session for testing
SESSION_PATH = "conversation_logs/session_20251028_201033"

print("="*70)
print("TESTING CONVERSATION ANALYTICS")
print("="*70)

# Test Analytics
analytics = ConversationAnalytics.from_session(SESSION_PATH)

print("\n1. Summary Statistics:")
summary = analytics.summary_stats()
for key, value in summary.items():
    print(f"   {key}: {value}")

print("\n2. Persona Contributions:")
contributions = analytics.persona_contributions()
for persona, data in sorted(contributions.items(), key=lambda x: x[1]['turns'], reverse=True):
    print(f"   {persona}: {data['turns']} turns, {data['participation_pct']:.1f}%")

print("\n3. Idea Diversity:")
ideas = analytics.idea_diversity()
print(f"   Unique ideas: {ideas['unique_ideas']}")
print(f"   Ideas mentioned: {ideas['ideas_mentioned']}")
print(f"   Idea titles: {', '.join(ideas['idea_titles'])}")

print("\n4. Phase Metrics:")
phases = analytics.phase_metrics()
for phase_id, data in phases.items():
    print(f"   {phase_id}: {data['turns']} turns, {data['duration_seconds']:.1f}s")

print("\n5. Cost Analysis:")
costs = analytics.cost_analysis()
print(f"   Total tokens: {costs['total_tokens']:,}")
print(f"   Total cost: ${costs['total_cost']:.4f}")

print("\n6. Generating HTML Report...")
analytics.generate_html_report("conversation_report.html")

print("\n" + "="*70)
print("TESTING CONVERSATION REPLAYER")
print("="*70)

# Test Replayer
replayer = ConversationReplayer.from_session(SESSION_PATH)

print("\n1. Display Summary:")
replayer.display_summary()

print("\n2. List Phases:")
replayer.list_phases()

print("\n3. List Personas:")
replayer.list_personas()

print("\n4. Navigate to phase 'ideation':")
replayer.goto_phase("ideation")

print("\n5. View current exchange:")
replayer.view_exchange()

print("\n6. View facilitator decision:")
replayer.view_facilitator_decision()

print("\n7. Navigate to turn 10:")
replayer.goto_turn(10)
replayer.view_exchange()

print("\n8. Search for 'SympleSync':")
results = replayer.search_content("SympleSync")

print("\n9. Export snapshot:")
replayer.export_snapshot("replay_snapshot.json")

print("\n" + "="*70)
print("ALL TESTS COMPLETE!")
print("="*70)
print("\nGenerated files:")
print("  - conversation_report.html (analytics report)")
print("  - replay_snapshot.json (replayer snapshot)")
