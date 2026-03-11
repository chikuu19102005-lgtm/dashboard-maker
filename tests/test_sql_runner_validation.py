import unittest

import pandas as pd

from sql_runner import SQLValidationError, run_sql, validate_sql


class SQLValidationTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "monthly_income": [100, 200],
                "daily_internet_hours": [3.5, 4.1],
            }
        )

    def test_rejects_unknown_column(self):
        with self.assertRaises(SQLValidationError):
            validate_sql('SELECT "missing_col" FROM dataframe', self.df.columns)

    def test_rejects_forbidden_keyword(self):
        with self.assertRaises(SQLValidationError):
            validate_sql("DROP TABLE dataframe", self.df.columns)

    def test_rejects_unknown_function(self):
        with self.assertRaises(SQLValidationError):
            validate_sql('SELECT mystery_fn("monthly_income") FROM dataframe', self.df.columns)

    def test_valid_query_runs(self):
        result = run_sql(self.df, 'SELECT AVG("monthly_income") AS avg_income FROM dataframe')
        self.assertEqual(list(result.columns), ["avg_income"])
        self.assertEqual(float(result.iloc[0]["avg_income"]), 150.0)


if __name__ == "__main__":
    unittest.main()
