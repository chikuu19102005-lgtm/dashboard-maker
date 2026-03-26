import unittest

import pandas as pd

from dataset_engine import analyze_dataset


class DatasetEngineTests(unittest.TestCase):
    def test_analyze_dataset_includes_profile_metrics(self):
        df = pd.DataFrame(
            {
                "region": ["East", "West", None],
                "revenue": [100.0, None, 300.0],
                "orders": [5, 6, 7],
            }
        )

        info = analyze_dataset(df)

        self.assertEqual(info["rows"], 3)
        self.assertEqual(info["column_count"], 3)
        self.assertEqual(info["missing_values"], 2)
        self.assertEqual(len(info["top_columns"]), 3)
        self.assertEqual(info["top_columns"][0]["name"], "orders")


if __name__ == "__main__":
    unittest.main()
