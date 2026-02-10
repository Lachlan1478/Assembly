# Phase 1: Standard test prompts for system validity testing

# Standard inspiration for reliability testing
# Clear goal with explicit request to propose a startup
STANDARD_INSPIRATION = """
Goal: Create a startup that helps young professionals learn to invest.

Domain: Personal finance
Target users: Young professionals (25-35) new to investing
Primary outcome: Build confidence in making investment decisions

Problem: Most investment apps are overwhelming for beginners.
They present too much information without guidance, leading to
analysis paralysis and poor decisions.

Task: Propose a specific startup idea (with a name) that solves this
problem. The solution should provide a simpler, more guided experience
that builds investment knowledge gradually.
"""

# Alternative test prompts for variation testing
ALTERNATIVE_INSPIRATIONS = [
    """
    Goal: Create a startup that improves remote team communication.

    Domain: Remote work productivity
    Target users: Distributed teams (10-50 people) struggling with async communication
    Primary outcome: Reduce meeting fatigue while improving team alignment

    Problem: Remote teams spend too much time in synchronous meetings.
    Async tools create information silos and people feel disconnected.

    Task: Propose a specific startup idea (with a name) that solves this problem.
    """,
    """
    Goal: Create a startup that helps busy parents stay healthy.

    Domain: Health and wellness
    Target users: Busy parents (30-45) trying to maintain healthy habits
    Primary outcome: Sustainable health improvements without major lifestyle changes

    Problem: Parents know what healthy habits look like but struggle to
    maintain them with limited time and competing priorities.

    Task: Propose a specific startup idea (with a name) that solves this problem.
    """,
    """
    Goal: Create a startup that helps working professionals learn new skills.

    Domain: Education technology
    Target users: Working professionals looking to upskill or change careers
    Primary outcome: Learn new skills effectively around a full-time job

    Problem: Online courses have high dropout rates. People start motivated
    but lose momentum. Traditional education doesn't fit working schedules.

    Task: Propose a specific startup idea (with a name) that solves this problem.
    """,
]
