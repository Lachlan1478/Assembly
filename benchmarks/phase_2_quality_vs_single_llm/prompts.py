# Phase 2: Standard benchmark prompts for quality comparison
# 10 diverse startup domains for consistent testing

BENCHMARK_PROMPTS = [
    # 1. Personal Finance (baseline domain)
    {
        "id": "finance",
        "domain": "Personal finance",
        "inspiration": """
Domain: Personal finance
Target users: Young professionals (25-35) new to investing
Primary outcome: Build confidence in making investment decisions

Context: Most investment apps are overwhelming for beginners.
They present too much information without guidance, leading to
analysis paralysis and poor decisions.
        """.strip(),
    },

    # 2. Remote Work / Productivity
    {
        "id": "remote_work",
        "domain": "Remote work productivity",
        "inspiration": """
Domain: Remote work and team collaboration
Target users: Distributed teams (10-50 people) struggling with async communication
Primary outcome: Reduce meeting fatigue while maintaining team alignment

Context: Remote teams spend too much time in synchronous meetings that
could be async. But async tools create information silos and people
feel disconnected.
        """.strip(),
    },

    # 3. Health & Wellness
    {
        "id": "health",
        "domain": "Health and wellness",
        "inspiration": """
Domain: Health and wellness
Target users: Busy parents (30-45) trying to maintain healthy habits
Primary outcome: Sustainable health improvements without major lifestyle changes

Context: Parents know what healthy habits look like but struggle to
maintain them with limited time and competing priorities.
        """.strip(),
    },

    # 4. Education Technology
    {
        "id": "education",
        "domain": "Education technology",
        "inspiration": """
Domain: Adult education and skill development
Target users: Working professionals looking to upskill or change careers
Primary outcome: Learn new skills effectively around a full-time job

Context: Online courses have high dropout rates. People start motivated
but lose momentum. Traditional education doesn't fit working schedules.
        """.strip(),
    },

    # 5. Small Business Operations
    {
        "id": "small_business",
        "domain": "Small business operations",
        "inspiration": """
Domain: Small business operations
Target users: Solo entrepreneurs and small teams (1-5 people)
Primary outcome: Automate repetitive business tasks without technical expertise

Context: Small businesses spend too much time on admin tasks that
enterprise companies automate. Existing tools are too complex or expensive.
        """.strip(),
    },

    # 6. Sustainable Living
    {
        "id": "sustainability",
        "domain": "Sustainable living",
        "inspiration": """
Domain: Environmental sustainability
Target users: Environmentally conscious consumers who want to reduce their impact
Primary outcome: Make sustainable choices easy and trackable

Context: People want to live more sustainably but don't know where to start.
There's too much conflicting information about what actually makes a difference.
        """.strip(),
    },

    # 7. Creator Economy
    {
        "id": "creator_economy",
        "domain": "Creator economy",
        "inspiration": """
Domain: Content creation and monetization
Target users: Part-time creators trying to grow their audience
Primary outcome: Build sustainable income from creative work

Context: Most creators struggle to grow beyond hobby income. Platform algorithms
are unpredictable and monetization options are limited or exploitative.
        """.strip(),
    },

    # 8. Mental Health
    {
        "id": "mental_health",
        "domain": "Mental health",
        "inspiration": """
Domain: Mental health and emotional wellbeing
Target users: Young adults (18-30) experiencing anxiety or stress
Primary outcome: Accessible mental health support between therapy sessions

Context: Therapy is expensive and hard to access. Apps exist but feel generic.
People need support that's available when they need it, not on a schedule.
        """.strip(),
    },

    # 9. Local Services / Marketplace
    {
        "id": "local_services",
        "domain": "Local services",
        "inspiration": """
Domain: Local services and community
Target users: Homeowners needing reliable service providers
Primary outcome: Find trustworthy local professionals without the hassle

Context: Finding reliable contractors, cleaners, etc. is frustrating.
Reviews are often fake, prices vary wildly, and availability is unclear.
        """.strip(),
    },

    # 10. Professional Networking
    {
        "id": "networking",
        "domain": "Professional networking",
        "inspiration": """
Domain: Professional networking and career development
Target users: Mid-career professionals seeking new opportunities
Primary outcome: Build meaningful professional relationships that lead to opportunities

Context: LinkedIn feels transactional and spammy. Networking events are awkward.
People want genuine connections but don't know how to build them at scale.
        """.strip(),
    },
]


def get_prompt_by_id(prompt_id: str) -> dict:
    """Get a specific benchmark prompt by ID."""
    for prompt in BENCHMARK_PROMPTS:
        if prompt["id"] == prompt_id:
            return prompt
    raise ValueError(f"Unknown prompt ID: {prompt_id}")


def get_all_inspirations() -> list[str]:
    """Get list of all inspiration texts."""
    return [prompt["inspiration"] for prompt in BENCHMARK_PROMPTS]
