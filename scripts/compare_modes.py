"""
Compare fast and medium mode sessions with HTML reports
"""

from framework import ConversationAnalytics
import webbrowser
import os

# Session paths
FAST_SESSION = "conversation_logs/session_20251028_200835"
MEDIUM_SESSION = "conversation_logs/session_20251028_201033"

print("="*70)
print("GENERATING COMPARISON REPORTS")
print("="*70)

# Generate Fast Mode Report
print("\n1. Analyzing FAST mode session...")
fast_analytics = ConversationAnalytics.from_session(FAST_SESSION)
fast_summary = fast_analytics.summary_stats()

print(f"   Mode: {fast_summary['mode']}")
print(f"   Phases: {fast_summary['total_phases']}")
print(f"   Turns: {fast_summary['total_turns']}")
print(f"   Duration: {fast_summary['duration_formatted']}")
print(f"   Cost: ${fast_summary['total_cost']:.4f}")

fast_analytics.generate_html_report("report_fast_mode.html")

# Generate Medium Mode Report
print("\n2. Analyzing MEDIUM mode session...")
medium_analytics = ConversationAnalytics.from_session(MEDIUM_SESSION)
medium_summary = medium_analytics.summary_stats()

print(f"   Mode: {medium_summary['mode']}")
print(f"   Phases: {medium_summary['total_phases']}")
print(f"   Turns: {medium_summary['total_turns']}")
print(f"   Duration: {medium_summary['duration_formatted']}")
print(f"   Cost: ${medium_summary['total_cost']:.4f}")

medium_analytics.generate_html_report("report_medium_mode.html")

# Print comparison
print("\n" + "="*70)
print("COMPARISON SUMMARY")
print("="*70)

print(f"\nPhases:")
print(f"  Fast:   {fast_summary['total_phases']} phases")
print(f"  Medium: {medium_summary['total_phases']} phases")
print(f"  Difference: +{medium_summary['total_phases'] - fast_summary['total_phases']} phases")

print(f"\nTurns:")
print(f"  Fast:   {fast_summary['total_turns']} turns")
print(f"  Medium: {medium_summary['total_turns']} turns")
print(f"  Difference: +{medium_summary['total_turns'] - fast_summary['total_turns']} turns")

print(f"\nDuration:")
print(f"  Fast:   {fast_summary['duration_formatted']}")
print(f"  Medium: {medium_summary['duration_formatted']}")

print(f"\nCost:")
print(f"  Fast:   ${fast_summary['total_cost']:.4f}")
print(f"  Medium: ${medium_summary['total_cost']:.4f}")
print(f"  Difference: ${medium_summary['total_cost'] - fast_summary['total_cost']:.4f}")

cost_ratio = medium_summary['total_cost'] / fast_summary['total_cost'] if fast_summary['total_cost'] > 0 else 0
print(f"  Medium is {cost_ratio:.1f}x more expensive")

print(f"\nPersonas:")
print(f"  Fast:   {fast_summary['total_personas']} personas active")
print(f"  Medium: {medium_summary['total_personas']} personas active")

print("\n" + "="*70)
print("OPENING REPORTS IN BROWSER...")
print("="*70)

# Open both reports in browser
fast_path = os.path.abspath("report_fast_mode.html")
medium_path = os.path.abspath("report_medium_mode.html")

print(f"\nFast Mode Report:   {fast_path}")
print(f"Medium Mode Report: {medium_path}")

webbrowser.open('file://' + fast_path)
webbrowser.open('file://' + medium_path)

print("\n[OK] Reports opened in browser!")
print("     You can now compare them side-by-side.")
