"""Sample announcements used when the backend isn't reachable.

Shape of one announcement (what the backend / agents should return):
{
    "id": str,
    "company": str,
    "title": str,              # "Annual tech summit"
    "date": str | None,        # "Dec 5"
    "location": str | None,
    "people": int | None,
    "verdict": "high" | "standard" | "light" | "skip",
    "why": str,                # one-line reason shown in the table
    "duplicate_of": str | None,# id of the original if this is a duplicate
    "source": str | None,      # URL of the announcement
    "reasoning": list[str],
    "dossier": dict | None,    # {"industry", "size", "contact", "notes"}
    "proposal": str,           # draft email / proposal
}
"""


def _a(**kw):
    base = dict(location="Kochi", source=None, duplicate_of=None, reasoning=[], dossier=None, proposal="")
    base.update(kw)
    return base


MOCK_ANNOUNCEMENTS = [
    _a(
        id="a1", company="Keralytics", title="Annual tech summit", date="Dec 5", people=500,
        verdict="high", why="2-day summit, ~₹9L deal, we're free both days",
        reasoning=[
            "500 attendees × 2 days × ~₹900/head ≈ ₹9L",
            "Calendar is clear on Dec 5–6",
            "Annual event → could become a long-term account",
        ],
        dossier={"industry": "Data analytics", "size": "800 employees", "contact": "events@keralytics.in",
                 "notes": "Used a Bangalore caterer last year; reviews mention late delivery."},
        proposal=("Hi Keralytics team,\n\nCongrats on the upcoming Annual Tech Summit! We'd love to handle "
                  "catering for both days — breakfast, lunch and evening snacks for 500 guests, with a live "
                  "counter on day 2.\n\nCould we set up a 15-minute call this week?\n\n— Team Catering"),
    ),
    _a(id="a8", company="InfoPark Phase 3", title="Tenant welcome week", date="Jan 10", people=1200,
       verdict="high", why="Huge footfall, multi-day, park-wide contract possible",
       reasoning=["1,200 people across a 5-day welcome week", "Park-wide event → access to 40+ tenant companies",
                  "Could turn into a recurring food-court contract"],
       dossier={"industry": "IT park / real estate", "size": "40+ tenant companies", "contact": "admin@infopark.in",
                "notes": "Phase 3 opening in January; no official caterer announced yet."},
       proposal=("Hi InfoPark team,\n\nCongratulations on opening Phase 3! We'd love to cater the Tenant Welcome "
                 "Week — daily lunch and evening snacks for up to 1,200 guests, with a rotating Kerala & "
                 "continental menu.\n\nHappy to share a tasting menu this week.\n\n— Team Catering")),
    _a(id="a9", company="UST Global", title="Hackathon finale", date="Nov 28", people=400,
       verdict="high", why="24-hr event, 4 meals, ~₹6L"),

    _a(
        id="a2", company="Nexora Tech", title="Office launch", date="Nov 3", people=250,
        verdict="standard", why="Mid-size launch, could become daily office catering",
        reasoning=["250 people, single evening", "New office → no existing caterer", "Upsell to a daily lunch plan"],
        dossier={"industry": "SaaS", "size": "250 employees", "contact": "hr@nexora.tech",
                 "notes": "Moving from Trivandrum to Kakkanad."},
        proposal=("Hi Nexora,\n\nWelcome to Kochi! We'd love to cater your office launch on Nov 3 and talk "
                  "about daily lunch for the new office.\n\n— Team Catering"),
    ),
    _a(id="a10", company="Experion", title="Quarterly town hall", date="Nov 14", people=180,
       verdict="standard", why="Recurring every quarter"),
    _a(id="a11", company="Fingent", title="Client meetup", date="Dec 2", people=120,
       verdict="standard", why="Premium crowd, good margin"),

    _a(id="a3", company="BlueOrbit Labs", title="Team offsite", date="Dec 12", people=60,
       verdict="light", why="Small one-day event, ~₹40K"),
    _a(id="a4", company="TCS Kochi", title="Board meeting", date="Nov 20", people=12,
       verdict="light", why="Big brand, but a tiny meeting"),
    _a(id="a12", company="Qburst", title="Farewell lunch", date="Nov 8", people=40,
       verdict="light", why="Small, but a warm lead"),

    _a(id="a5", company="Finverse", title="Funding announcement", date=None, people=None,
       verdict="skip", why="News, not an event"),
    _a(id="a6", company="Nexora Tech", title="Office launch (news site)", date="Nov 3", people=250,
       verdict="skip", why="Duplicate of the row above", duplicate_of="a2"),
    _a(id="a7", company="Zentrix", title="Hackathon", date=None, location="Bangalore", people=150,
       verdict="skip", why="Outside our service area"),
]
