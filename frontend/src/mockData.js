// Mock data used when the backend isn't reachable.
// Shape of one announcement (what the backend should return):
// {
//   id: string,
//   company: string,
//   title: string,            // "Annual tech summit"
//   date: string | null,      // "Dec 5"
//   location: string | null,
//   people: number | null,
//   verdict: 'high' | 'standard' | 'light' | 'skip',
//   why: string,              // one-line reason shown in the table
//   duplicateOf: string|null, // id of the original if this is a duplicate
//   source: string | null,    // URL of the announcement
//   reasoning: string[],      // bullet points shown in the detail drawer
//   dossier: { industry, size, contact, notes },
//   proposal: string          // draft email / proposal text
// }

const base = (o) => ({
  location: 'Kochi', source: null, duplicateOf: null, reasoning: [], dossier: null, proposal: '', ...o,
})

export const MOCK_ANNOUNCEMENTS = [
  base({
    id: 'a1', company: 'Keralytics', title: 'Annual tech summit', date: 'Dec 5', people: 500,
    verdict: 'high', why: '2-day summit, ~₹9L deal, we’re free both days',
    reasoning: ['500 attendees × 2 days × ~₹900/head ≈ ₹9L', 'Calendar is clear on Dec 5–6', 'Repeat annual event → long-term account'],
    dossier: { industry: 'Data analytics', size: '800 employees', contact: 'events@keralytics.in', notes: 'Used a Bangalore caterer last year; reviews mention late delivery.' },
    proposal: 'Hi Keralytics team,\n\nCongrats on the upcoming Annual Tech Summit! We’d love to handle catering for both days — breakfast, lunch, and evening snacks for 500 guests, with a live counter on day 2.\n\nCan we set up a 15-min call this week?\n\n— Team Catering',
  }),
  base({ id: 'a8', company: 'InfoPark Phase 3', title: 'Tenant welcome week', date: 'Jan 10', people: 1200, verdict: 'high', why: 'Huge footfall, multi-day, park-wide contract possible' }),
  base({ id: 'a9', company: 'UST Global', title: 'Hackathon finale', date: 'Nov 28', people: 400, verdict: 'high', why: '24-hr event, 4 meals, ~₹6L' }),

  base({
    id: 'a2', company: 'Nexora Tech', title: 'Office launch', date: 'Nov 3', people: 250,
    verdict: 'standard', why: 'Mid-size launch, could become daily office catering',
    reasoning: ['250 people, single evening', 'New office → no existing caterer', 'Upsell to daily lunch plan'],
    dossier: { industry: 'SaaS', size: '250 employees', contact: 'hr@nexora.tech', notes: 'Moving from Trivandrum to Kakkanad.' },
    proposal: 'Hi Nexora,\n\nWelcome to Kochi! We’d love to cater your office launch on Nov 3 and talk about daily lunch for the new office.\n\n— Team Catering',
  }),
  base({ id: 'a10', company: 'Experion', title: 'Quarterly town hall', date: 'Nov 14', people: 180, verdict: 'standard', why: 'Recurring every quarter' }),
  base({ id: 'a11', company: 'Fingent', title: 'Client meetup', date: 'Dec 2', people: 120, verdict: 'standard', why: 'Premium crowd, good margin' }),

  base({ id: 'a3', company: 'BlueOrbit Labs', title: 'Team offsite', date: 'Dec 12', people: 60, verdict: 'light', why: 'Small one-day event, ~₹40K' }),
  base({ id: 'a4', company: 'TCS Kochi', title: 'Board meeting', date: 'Nov 20', people: 12, verdict: 'light', why: 'Big brand, but a tiny meeting' }),
  base({ id: 'a12', company: 'Qburst', title: 'Farewell lunch', date: 'Nov 8', people: 40, verdict: 'light', why: 'Small, but warm lead' }),

  base({ id: 'a5', company: 'Finverse', title: 'Funding announcement', date: null, people: null, verdict: 'skip', why: 'News, not an event' }),
  base({ id: 'a6', company: 'Nexora Tech', title: 'Office launch (news site)', date: 'Nov 3', people: 250, verdict: 'skip', why: 'Duplicate of the row above', duplicateOf: 'a2' }),
  base({ id: 'a7', company: 'Zentrix', title: 'Hackathon', date: null, location: 'Bangalore', people: 150, verdict: 'skip', why: 'Outside our service area' }),
]
