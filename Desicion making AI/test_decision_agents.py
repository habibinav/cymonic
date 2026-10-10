"""
test_decision_agents.py - Unit Test Suite for Member 1 Decision-Making AI

Tests qualification_agent.py, reasoning_agent.py, and strategy_agent.py.
Verifies business-rule compliance, hard constraint overrides, score calculations,
and correct pursuit tier selection.
"""

import unittest
from datetime import date, timedelta

from schemas import (
    BusinessProfile,
    LeadAnalysis,
    EvidenceFact,
    EvidenceClassification,
    QualificationStatus,
    PursuitTier,
)
from qualification_agent import qualify
from reasoning_agent import evaluate
from strategy_agent import choose_strategy


class TestDecisionAgents(unittest.TestCase):

    def setUp(self):
        """Default configurable business profile for testing."""
        self.profile = BusinessProfile(
            company_name="Apex Corporate Catering",
            service_areas=["Kochi", "Ernakulam", "Trivandrum", "Bangalore"],
            min_capacity=20,
            max_capacity=1000,
            min_order_value=5000.0,
            min_notice_days=3,
        )

    def test_strong_opportunity_high_effort_pitch(self):
        """
        Test Case 1: Strong, high-attendance opportunity within service area with catering demand.
        Expected: QUALIFIED -> High Commercial Score -> pursuit_tier = HIGH_EFFORT_PITCH
        """
        future_date = (date.today() + timedelta(days=14)).isoformat()
        analysis = LeadAnalysis(
            company_name="TechCorp India",
            event_name="Annual Tech Summit 2026",
            event_type="staff conference",
            event_date=future_date,
            location="Kochi",
            attendance_estimate=400,
            catering_evidence="Hot buffet lunch and evening reception provided for 400 attendees.",
            evidence_facts=[
                EvidenceFact(fact="Buffet lunch provided", classification=EvidenceClassification.EXPLICIT)
            ],
        )

        qual_res = qualify(analysis, self.profile)
        self.assertEqual(qual_res.status, QualificationStatus.QUALIFIED)
        self.assertTrue(qual_res.is_service_area_matched)
        self.assertTrue(qual_res.is_capacity_matched)
        self.assertTrue(qual_res.has_catering_demand_evidence)

        reasoning_res = evaluate(analysis, qual_res)
        self.assertGreaterEqual(reasoning_res.commercial_potential_score, 7.5)
        self.assertGreaterEqual(reasoning_res.operational_feasibility_score, 6.0)

        strat_res = choose_strategy(qual_res, reasoning_res)
        self.assertEqual(strat_res.pursuit_tier, PursuitTier.HIGH_EFFORT_PITCH)

    def test_standard_opportunity_standard_proposal(self):
        """
        Test Case 2: Moderate attendance (80 guests) qualified lead.
        Expected: QUALIFIED -> Moderate Commercial Score -> pursuit_tier = STANDARD_PROPOSAL
        """
        future_date = (date.today() + timedelta(days=10)).isoformat()
        analysis = LeadAnalysis(
            company_name="InnoSoft",
            event_name="Quarterly Leadership Workshop",
            event_type="workshop",
            event_date=future_date,
            location="Bangalore",
            attendance_estimate=80,
            catering_evidence="Coffee break snacks and boxed lunch needed.",
        )

        qual_res = qualify(analysis, self.profile)
        self.assertEqual(qual_res.status, QualificationStatus.QUALIFIED)

        reasoning_res = evaluate(analysis, qual_res)
        self.assertTrue(5.0 <= reasoning_res.commercial_potential_score < 7.5)

        strat_res = choose_strategy(qual_res, reasoning_res)
        self.assertEqual(strat_res.pursuit_tier, PursuitTier.STANDARD_PROPOSAL)

    def test_hard_constraint_override_capacity_exceeded(self):
        """
        Test Case 3: Hard Constraint Override test.
        An apparently attractive high-budget conference in Kochi for 2,500 people.
        Max capacity is 1,000.
        Expected: Hard DISQUALIFIED override -> pursuit_tier = NONE.
        """
        future_date = (date.today() + timedelta(days=20)).isoformat()
        analysis = LeadAnalysis(
            company_name="Global MegaCorp",
            event_name="Global Developer Conference",
            event_type="conference",
            event_date=future_date,
            location="Kochi",
            attendance_estimate=2500,  # Exceeds max capacity of 1000!
            catering_evidence="Full day 3-course catering for all participants.",
        )

        qual_res = qualify(analysis, self.profile)
        self.assertEqual(qual_res.status, QualificationStatus.DISQUALIFIED)
        self.assertIn("exceeds maximum confirmed catering capacity", qual_res.disqualification_reasons[0])

        reasoning_res = evaluate(analysis, qual_res)
        self.assertEqual(reasoning_res.commercial_potential_score, 0.0)
        self.assertEqual(reasoning_res.operational_feasibility_score, 0.0)

        strat_res = choose_strategy(qual_res, reasoning_res)
        self.assertEqual(strat_res.pursuit_tier, PursuitTier.NONE)

    def test_out_of_service_area_disqualification(self):
        """
        Test Case 4: Event location is Mumbai, which is outside service area.
        Expected: Hard DISQUALIFIED -> pursuit_tier = NONE.
        """
        analysis = LeadAnalysis(
            company_name="FinanceHub",
            event_name="Banking Summit",
            event_type="seminar",
            event_date=(date.today() + timedelta(days=15)).isoformat(),
            location="Mumbai",
            attendance_estimate=150,
            catering_evidence="Lunch provided for executive guests.",
        )

        qual_res = qualify(analysis, self.profile)
        self.assertEqual(qual_res.status, QualificationStatus.DISQUALIFIED)
        self.assertFalse(qual_res.is_service_area_matched)

        reasoning_res = evaluate(analysis, qual_res)
        strat_res = choose_strategy(qual_res, reasoning_res)
        self.assertEqual(strat_res.pursuit_tier, PursuitTier.NONE)

    def test_missing_critical_info_needs_research(self):
        """
        Test Case 5: Event missing location and exact attendance count.
        Expected: NEEDS_RESEARCH -> pursuit_tier = NEEDS_RESEARCH
        """
        analysis = LeadAnalysis(
            company_name="BioHealth Ltd",
            event_name="Product Launch",
            event_type="launch event",
            event_date="TBD",
            location="Unknown",
            attendance_estimate=None,
            catering_evidence="Catering will be arranged.",
        )

        qual_res = qualify(analysis, self.profile)
        self.assertEqual(qual_res.status, QualificationStatus.NEEDS_RESEARCH)
        self.assertIn("Event Location", qual_res.missing_critical_info)
        self.assertIn("Attendance Estimate", qual_res.missing_critical_info)

        reasoning_res = evaluate(analysis, qual_res)
        self.assertTrue(len(reasoning_res.uncertainties) >= 2)

        strat_res = choose_strategy(qual_res, reasoning_res)
        self.assertEqual(strat_res.pursuit_tier, PursuitTier.NEEDS_RESEARCH)


if __name__ == "__main__":
    unittest.main()