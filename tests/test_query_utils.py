import unittest

import pandas as pd

from query_utils import (
    build_fallback_sql,
    detect_query_type,
    extract_sql,
    validate_question_columns,
)


class QueryUtilsTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "monthly_income": [100, 200, 300],
                "daily_internet_hours": [2.5, 3.0, 4.0],
                "social_media_hours": [1.0, 1.5, 2.0],
                "city_tier": ["Tier 1", "Tier 2", "Tier 1"],
            }
        )

    def test_extract_sql_from_fenced_block(self):
        raw = "```sql\nSELECT * FROM dataframe;\n```"
        self.assertEqual(extract_sql(raw), "SELECT * FROM dataframe")

    def test_detect_query_type(self):
        self.assertEqual(detect_query_type("internet hours vs social media hours"), "compare")
        self.assertEqual(detect_query_type("top 5 people by monthly income"), "top")
        self.assertEqual(detect_query_type("average daily internet hours"), "average")
        self.assertEqual(detect_query_type("total sales in the month"), "total")

    def test_build_fallback_sql_compare(self):
        sql = build_fallback_sql("internet hours vs social media hours", self.df)
        self.assertIn('"daily_internet_hours"', sql)
        self.assertIn('"social_media_hours"', sql)

    def test_build_fallback_sql_top(self):
        sql = build_fallback_sql("top 5 by monthly income", self.df)
        self.assertIn('ORDER BY "monthly_income" DESC', sql)
        self.assertIn("LIMIT 5", sql)

    def test_build_fallback_sql_total_semantic(self):
        sql = build_fallback_sql("total sales in the month", self.df)
        self.assertIn('SUM("monthly_income")', sql)

    def test_validate_question_columns_rejects_missing_field(self):
        is_valid, reason = validate_question_columns("average age", self.df)
        self.assertFalse(is_valid)
        self.assertIn("Invalid query", reason)

    def test_validate_question_columns_accepts_existing_field(self):
        is_valid, reason = validate_question_columns("average daily internet hours", self.df)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_validate_question_columns_accepts_semantic_match(self):
        is_valid, reason = validate_question_columns("total sales in the month", self.df)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_validate_question_columns_allows_trend_query_with_fallback_numeric(self):
        is_valid, reason = validate_question_columns("monthly sales trend show", self.df)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_validate_question_columns_allows_table_query_with_existing_columns(self):
        is_valid, reason = validate_question_columns("show the data", self.df)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")

    def test_validate_question_columns_allows_non_english_query(self):
        is_valid, reason = validate_question_columns(
            "कुल बिक्री",
            self.df,
            query_language="hi",
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
