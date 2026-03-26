import unittest

import pandas as pd

from dashboard_filters import (
    apply_output_filters,
    detect_output_filter_config,
    sync_output_filter_state,
)


class DashboardFiltersTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "order_date": pd.to_datetime(
                    ["2024-01-01", "2024-01-10", "2024-02-05", "2024-03-01"]
                ),
                "region": ["North", "South", "North", "East"],
                "product_category": ["A", "B", "A", "C"],
                "sales": [100, 120, 150, 180],
            }
        )

    def test_detect_output_filter_config_finds_expected_columns(self):
        config = detect_output_filter_config(self.df)

        self.assertEqual(config["date_column"], "order_date")
        self.assertEqual(config["region_column"], "region")
        self.assertEqual(config["product_column"], "product_category")
        self.assertIn("Last 5 Weeks", config["date_options"])

    def test_apply_output_filters_uses_selected_state(self):
        config = detect_output_filter_config(self.df)
        state = {}
        sync_output_filter_state(state, "query-1", config)
        state["output_filter_region"] = "North"
        state["output_filter_product"] = "A"
        state["output_filter_date_range"] = "Last 2 Months"

        filtered = apply_output_filters(self.df, config, state)

        self.assertEqual(len(filtered), 2)
        self.assertTrue((filtered["region"] == "North").all())
        self.assertTrue((filtered["product_category"] == "A").all())


if __name__ == "__main__":
    unittest.main()
