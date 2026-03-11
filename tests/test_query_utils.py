import unittest

import pandas as pd

from query_utils import build_fallback_sql, detect_query_type, extract_sql


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

    def test_build_fallback_sql_compare(self):
        sql = build_fallback_sql("internet hours vs social media hours", self.df)
        self.assertIn('"daily_internet_hours"', sql)
        self.assertIn('"social_media_hours"', sql)

    def test_build_fallback_sql_top(self):
        sql = build_fallback_sql("top 5 by monthly income", self.df)
        self.assertIn('ORDER BY "monthly_income" DESC', sql)
        self.assertIn("LIMIT 5", sql)


if __name__ == "__main__":
    unittest.main()
