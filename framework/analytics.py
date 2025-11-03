"""
ConversationAnalytics - Post-conversation analysis and reporting

Analyzes completed conversations to provide insights on:
- Persona participation and contribution
- Idea diversity and uniqueness
- Phase efficiency (time, cost, turns)
- Facilitator decision patterns
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from collections import Counter


class ConversationAnalytics:
    """
    Analyze completed conversations for quality, participation, and efficiency metrics.

    Example:
        >>> analytics = ConversationAnalytics.from_session("conversation_logs/session_xyz")
        >>> analytics.persona_contributions()
        >>> analytics.generate_html_report("report.html")
    """

    def __init__(self, session_path: str):
        """
        Initialize analytics from a session log directory.

        Args:
            session_path: Path to session folder (e.g., "conversation_logs/session_20251028")
        """
        self.session_path = Path(session_path)
        if not self.session_path.exists():
            raise FileNotFoundError(f"Session path not found: {session_path}")

        # Load all log files
        self.metadata = self._load_json("session_metadata.json")
        self.exchanges = self._load_json("full_conversation.json")
        self.facilitator_decisions = self._load_json("facilitator_decisions.json")
        self.persona_summaries = self._load_json("persona_summaries.json")

        # Extract key info
        self.session_id = self.session_path.name
        self.mode = self.metadata.get("mode", "unknown")
        self.model = self.metadata.get("model", "unknown")

    @classmethod
    def from_session(cls, session_path: str) -> 'ConversationAnalytics':
        """
        Create analytics instance from session path.

        Args:
            session_path: Path to session folder

        Returns:
            ConversationAnalytics instance
        """
        return cls(session_path)

    def _load_json(self, filename: str) -> Any:
        """Load JSON file from session directory."""
        file_path = self.session_path / filename
        if not file_path.exists():
            return {}  # Return empty dict if file doesn't exist

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def persona_contributions(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze how much each persona contributed.

        Returns:
            Dict mapping persona names to contribution metrics:
            {
                "persona_name": {
                    "turns": int,
                    "tokens_estimated": int,
                    "participation_pct": float,
                    "phases": ["phase1", "phase2"]
                }
            }
        """
        contributions = {}
        total_turns = len(self.exchanges)

        for exchange in self.exchanges:
            speaker = exchange.get("speaker", "Unknown")
            phase = exchange.get("phase", "unknown")
            content = exchange.get("content", "")

            # Estimate tokens (rough: ~4 chars per token)
            tokens_estimated = len(content) // 4

            if speaker not in contributions:
                contributions[speaker] = {
                    "turns": 0,
                    "tokens_estimated": 0,
                    "participation_pct": 0.0,
                    "phases": set(),
                    "archetype": exchange.get("archetype", "")
                }

            contributions[speaker]["turns"] += 1
            contributions[speaker]["tokens_estimated"] += tokens_estimated
            contributions[speaker]["phases"].add(phase)

        # Calculate participation percentages and convert sets to lists
        for speaker in contributions:
            contributions[speaker]["participation_pct"] = (
                contributions[speaker]["turns"] / total_turns * 100
                if total_turns > 0 else 0
            )
            contributions[speaker]["phases"] = sorted(list(contributions[speaker]["phases"]))

        return contributions

    def idea_diversity(self) -> Dict[str, Any]:
        """
        Analyze diversity and uniqueness of ideas discussed.

        Returns:
            Dict with:
            {
                "unique_ideas": int,
                "ideas_per_phase": Dict[str, int],
                "idea_titles": List[str]
            }
        """
        # Extract ideas from metadata (final ideas)
        final_ideas = self.metadata.get("ideas", [])
        final_idea_titles = [idea.get("title", "Untitled") for idea in final_ideas]

        # Count idea mentions by phase (from exchanges)
        ideas_by_phase = {}
        all_mentioned_ideas = set()

        for exchange in self.exchanges:
            phase = exchange.get("phase", "unknown")
            content = exchange.get("content", "")

            if phase not in ideas_by_phase:
                ideas_by_phase[phase] = set()

            # Simple heuristic: look for capitalized words that might be idea names
            # Better: use the ideas_discussed from shared_context if available
            for title in final_idea_titles:
                if title.lower() in content.lower():
                    ideas_by_phase[phase].add(title)
                    all_mentioned_ideas.add(title)

        # Convert sets to counts
        ideas_per_phase = {
            phase: len(ideas)
            for phase, ideas in ideas_by_phase.items()
        }

        return {
            "unique_ideas": len(final_ideas),
            "ideas_mentioned": len(all_mentioned_ideas),
            "ideas_per_phase": ideas_per_phase,
            "idea_titles": final_idea_titles
        }

    def phase_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze efficiency and metrics for each phase.

        Returns:
            Dict mapping phase IDs to metrics:
            {
                "phase_id": {
                    "turns": int,
                    "tokens_estimated": int,
                    "duration_seconds": float,
                    "personas_active": List[str]
                }
            }
        """
        phases = {}

        # Group exchanges by phase
        for exchange in self.exchanges:
            phase_id = exchange.get("phase", "unknown")

            if phase_id not in phases:
                phases[phase_id] = {
                    "turns": 0,
                    "tokens_estimated": 0,
                    "personas_active": set(),
                    "start_time": exchange.get("timestamp"),
                    "end_time": exchange.get("timestamp")
                }

            phases[phase_id]["turns"] += 1
            phases[phase_id]["tokens_estimated"] += len(exchange.get("content", "")) // 4
            phases[phase_id]["personas_active"].add(exchange.get("speaker", "Unknown"))
            phases[phase_id]["end_time"] = exchange.get("timestamp")

        # Calculate durations and convert sets to lists
        for phase_id in phases:
            start = phases[phase_id]["start_time"]
            end = phases[phase_id]["end_time"]

            if start and end:
                try:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                    duration = (end_dt - start_dt).total_seconds()
                    phases[phase_id]["duration_seconds"] = duration
                except:
                    phases[phase_id]["duration_seconds"] = 0
            else:
                phases[phase_id]["duration_seconds"] = 0

            phases[phase_id]["personas_active"] = sorted(list(phases[phase_id]["personas_active"]))

        return phases

    def cost_analysis(self, cost_per_1k_tokens: float = 0.002) -> Dict[str, Any]:
        """
        Analyze total cost and cost breakdown.

        Args:
            cost_per_1k_tokens: Cost per 1000 tokens (default: $0.002 for gpt-4o-mini)

        Returns:
            Dict with cost metrics
        """
        # Calculate total tokens (rough estimate)
        total_tokens = sum(
            len(ex.get("content", "")) // 4
            for ex in self.exchanges
        )

        # Tokens by phase
        phase_costs = {}
        for phase_id, metrics in self.phase_metrics().items():
            tokens = metrics["tokens_estimated"]
            cost = (tokens / 1000.0) * cost_per_1k_tokens
            phase_costs[phase_id] = {
                "tokens": tokens,
                "cost": cost
            }

        total_cost = sum(p["cost"] for p in phase_costs.values())

        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "cost_per_1k_tokens": cost_per_1k_tokens,
            "by_phase": phase_costs
        }

    def facilitator_analysis(self) -> Dict[str, Any]:
        """
        Analyze facilitator decision patterns.

        Returns:
            Dict with facilitator metrics
        """
        persona_selections = []
        speaker_choices = []

        for decision in self.facilitator_decisions:
            decision_type = decision.get("type", "unknown")

            if decision_type == "persona_selection":
                personas = decision.get("decision", [])
                persona_selections.append({
                    "phase": decision.get("phase"),
                    "personas": personas,
                    "count": len(personas)
                })

            elif decision_type == "speaker_choice":
                speaker = decision.get("decision")
                speaker_choices.append({
                    "phase": decision.get("phase"),
                    "speaker": speaker
                })

        # Count speaker frequency
        speaker_frequency = Counter(
            choice["speaker"]
            for choice in speaker_choices
            if choice["speaker"]
        )

        return {
            "persona_selections": persona_selections,
            "speaker_frequency": dict(speaker_frequency),
            "total_decisions": len(self.facilitator_decisions)
        }

    def summary_stats(self) -> Dict[str, Any]:
        """
        Get high-level summary statistics.

        Returns:
            Dict with overall metrics
        """
        contributions = self.persona_contributions()
        phase_data = self.phase_metrics()
        cost_data = self.cost_analysis()
        idea_data = self.idea_diversity()

        # Calculate session duration
        if self.exchanges:
            start = self.exchanges[0].get("timestamp")
            end = self.exchanges[-1].get("timestamp")

            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                duration_seconds = (end_dt - start_dt).total_seconds()
            except:
                duration_seconds = 0
        else:
            duration_seconds = 0

        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "model": self.model,
            "total_phases": len(phase_data),
            "total_turns": len(self.exchanges),
            "total_personas": len(contributions),
            "unique_ideas": idea_data["unique_ideas"],
            "total_tokens": cost_data["total_tokens"],
            "total_cost": cost_data["total_cost"],
            "duration_seconds": duration_seconds,
            "duration_formatted": self._format_duration(duration_seconds)
        }

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def generate_html_report(self, output_path: str) -> None:
        """
        Generate comprehensive HTML report.

        Args:
            output_path: Path to save HTML report
        """
        summary = self.summary_stats()
        contributions = self.persona_contributions()
        phases = self.phase_metrics()
        costs = self.cost_analysis()
        ideas = self.idea_diversity()
        facilitator = self.facilitator_analysis()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Conversation Analytics - {self.session_id}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2 {{
            color: #333;
        }}
        .summary-box {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .bar {{
            background-color: #4CAF50;
            height: 30px;
            margin: 5px 0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding-left: 10px;
            color: white;
        }}
    </style>
</head>
<body>
    <h1>Conversation Analytics Report</h1>
    <p><strong>Session:</strong> {self.session_id}</p>
    <p><strong>Mode:</strong> {summary['mode']} | <strong>Model:</strong> {summary['model']}</p>

    <div class="summary-box">
        <h2>Summary Statistics</h2>
        <div class="metric">
            <div class="metric-value">{summary['total_phases']}</div>
            <div class="metric-label">Phases</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['total_turns']}</div>
            <div class="metric-label">Turns</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['total_personas']}</div>
            <div class="metric-label">Personas</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['unique_ideas']}</div>
            <div class="metric-label">Ideas</div>
        </div>
        <div class="metric">
            <div class="metric-value">${summary['total_cost']:.4f}</div>
            <div class="metric-label">Cost</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['duration_formatted']}</div>
            <div class="metric-label">Duration</div>
        </div>
    </div>

    <div class="summary-box">
        <h2>Persona Contributions</h2>
        <table>
            <tr>
                <th>Persona</th>
                <th>Turns</th>
                <th>Tokens</th>
                <th>Participation</th>
                <th>Phases</th>
            </tr>
            {''.join(f'''
            <tr>
                <td>{name}</td>
                <td>{data['turns']}</td>
                <td>{data['tokens_estimated']:,}</td>
                <td>{data['participation_pct']:.1f}%</td>
                <td>{', '.join(data['phases'])}</td>
            </tr>
            ''' for name, data in sorted(contributions.items(), key=lambda x: x[1]['turns'], reverse=True))}
        </table>
    </div>

    <div class="summary-box">
        <h2>Phase Metrics</h2>
        <table>
            <tr>
                <th>Phase</th>
                <th>Turns</th>
                <th>Duration</th>
                <th>Tokens</th>
                <th>Cost</th>
                <th>Active Personas</th>
            </tr>
            {''.join(f'''
            <tr>
                <td>{phase_id}</td>
                <td>{data['turns']}</td>
                <td>{self._format_duration(data['duration_seconds'])}</td>
                <td>{data['tokens_estimated']:,}</td>
                <td>${costs['by_phase'].get(phase_id, {}).get('cost', 0):.4f}</td>
                <td>{len(data['personas_active'])}</td>
            </tr>
            ''' for phase_id, data in phases.items())}
        </table>
    </div>

    <div class="summary-box">
        <h2>Ideas Generated</h2>
        <p><strong>Unique Ideas:</strong> {ideas['unique_ideas']}</p>
        <ul>
            {''.join(f'<li>{title}</li>' for title in ideas['idea_titles'])}
        </ul>
    </div>

    <div class="summary-box">
        <h2>Facilitator Analysis</h2>
        <p><strong>Total Decisions:</strong> {facilitator['total_decisions']}</p>
        <h3>Speaker Frequency</h3>
        {''.join(f'''
        <div class="bar" style="width: {count / max(facilitator['speaker_frequency'].values()) * 100}%;">
            {speaker}: {count} turns
        </div>
        ''' for speaker, count in sorted(facilitator['speaker_frequency'].items(), key=lambda x: x[1], reverse=True))}
    </div>

    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated by Assembly Framework ConversationAnalytics</p>
        <p>Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
</body>
</html>"""

        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"[OK] HTML report saved to: {output_path}")
