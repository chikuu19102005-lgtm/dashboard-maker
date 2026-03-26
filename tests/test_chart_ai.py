import unittest

import pandas as pd

from chart_ai import build_dashboard_charts


class ChartAITests(unittest.TestCase):
    def test_build_dashboard_charts_handles_single_metric_result(self):
        df = pd.DataFrame({"total_sales": [1250.0]})

        charts = build_dashboard_charts(df)

        self.assertIsNotNone(charts["bar"])
        self.assertIsNotNone(charts["line"])
        self.assertIsNotNone(charts["pie"])
        self.assertIsNotNone(charts["scatter"])

    def test_build_dashboard_charts_handles_category_only_result(self):
        df = pd.DataFrame({"segment": ["A", "B", "A", "C"]})

        charts = build_dashboard_charts(df)

        self.assertIsNotNone(charts["bar"])
        self.assertIsNotNone(charts["line"])
        self.assertIsNotNone(charts["pie"])
        self.assertIsNotNone(charts["scatter"])


if __name__ == "__main__":
    unittest.main()
