import unittest

import pandas as pd

from explanation_engine import (
    answer_analysis_question,
    generate_strategic_insights,
    summarize_all_charts,
)


class ExplanationEngineTests(unittest.TestCase):
    def test_generate_strategic_insights_returns_forward_looking_points(self):
        df = pd.DataFrame(
            {
                "revenue": [100, 120, 150, 180],
                "cost": [60, 65, 70, 80],
                "segment": ["A", "A", "B", "B"],
            }
        )

        insights = generate_strategic_insights(df)

        self.assertTrue(any("Overall conclusion:" in item for item in insights))
        self.assertTrue(any("Future trend:" in item for item in insights))
        self.assertTrue(any("Profit" in item for item in insights))

    def test_summarize_all_charts_labels_each_chart(self):
        summaries = summarize_all_charts(
            {
                "bar": "Top region leads.",
                "line": "Revenue is rising.",
                "pie": "Segment A dominates.",
                "scatter": "Income and spend are correlated.",
            }
        )

        self.assertEqual(len(summaries), 4)
        self.assertTrue(summaries[0].startswith("Bar chart:"))

    def test_answer_analysis_question_returns_profit_insight(self):
        df = pd.DataFrame(
            {
                "revenue": [100, 120, 150, 180],
                "cost": [60, 65, 70, 80],
                "segment": ["A", "A", "B", "B"],
            }
        )
        strategic_insights = generate_strategic_insights(df)

        answer = answer_analysis_question(
            "what is the profit outlook",
            df,
            chart_explanations={"scatter": "Revenue and cost are correlated."},
            strategic_insights=strategic_insights,
            chart_summaries=["Trend chart: Revenue is rising."],
        )

        self.assertTrue("profit" in answer.lower() or "loss" in answer.lower())

    def test_answer_analysis_question_says_profit_cannot_be_determined_without_fields(self):
        df = pd.DataFrame(
            {
                "avg_online_spend": [100, 120, 140],
                "segment": ["A", "B", "A"],
            }
        )

        answer = answer_analysis_question(
            "what is the profit outlook",
            df,
            chart_explanations={},
            strategic_insights=generate_strategic_insights(df),
            chart_summaries=[],
        )

        self.assertIn("profit cannot be calculated", answer.lower())

    def test_answer_analysis_question_returns_correlation_explanation(self):
        df = pd.DataFrame(
            {
                "income": [10, 20, 30, 40],
                "spend": [8, 18, 29, 41],
            }
        )

        answer = answer_analysis_question(
            "show correlation",
            df,
            chart_explanations={"scatter": "Income and spend have a positive relationship."},
            strategic_insights=[],
            chart_summaries=[],
        )

        self.assertIn("positive relationship", answer.lower())


if __name__ == "__main__":
    unittest.main()
