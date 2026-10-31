import unittest

import pandas as pd

from abassurance import stats

TODAY = "2026-10-30"


def customers():
    return pd.DataFrame(
        {
            "source": ["AbAssurance", "AbAssurance", "AssurePlus", "AssurePlus"],
            "status": ["active", "inactive", "active", "active"],
            "birth_date": pd.to_datetime(["2006-01-01", "1990-06-15", "1950-02-02", None]),
            "zip_code": ["75011", "75012", "69003", None],
        }
    )


def contracts():
    return pd.DataFrame(
        {
            "contract_key": ["AB-1", "AB-2", "AP-1"],
            "source": ["AbAssurance", "AbAssurance", "AssurePlus"],
            "insurance_type": ["health", "health", "auto"],
            "annual_premium": [1000.0, 500.0, 600.0],
            "status": ["active", "expired", "active"],
        }
    )


class TestCustomerStats(unittest.TestCase):
    def setUp(self):
        self.result = stats.customer_stats(customers(), TODAY)

    def test_total_and_source(self):
        self.assertEqual(self.result["total"], 4)
        by_source = self.result["by_source"].set_index("source")["customers"]
        self.assertEqual(by_source["AbAssurance"], 2)

    def test_age_groups_include_unknown(self):
        groups = self.result["by_age_group"].set_index(["source", "age_group"])["customers"]
        self.assertEqual(groups[("AbAssurance", "< 25")], 1)
        self.assertEqual(groups[("AbAssurance", "35-44")], 1)
        self.assertEqual(groups[("AssurePlus", "65+")], 1)
        self.assertEqual(groups[("AssurePlus", "unknown")], 1)

    def test_departments(self):
        departments = self.result["by_department"].set_index("department")["customers"]
        self.assertEqual(departments["75"], 2)
        self.assertEqual(departments["unknown"], 1)

    def test_default_reference_date(self):
        self.assertEqual(stats.customer_stats(customers())["total"], 4)

    def test_by_status(self):
        self.assertEqual(int(self.result["by_status"]["customers"].sum()), 4)


class TestContractStats(unittest.TestCase):
    def test_kpis_and_groups(self):
        result = stats.contract_stats(contracts())
        self.assertEqual((result["total"], result["active"]), (3, 2))
        self.assertEqual(result["total_premium"], 2100.0)
        health = result["by_type"].query("insurance_type == 'health'").iloc[0]
        self.assertEqual((health["contracts"], health["average_premium"]), (2, 750.0))
        self.assertEqual(int(result["by_status"]["contracts"].sum()), 3)


class TestClaimStats(unittest.TestCase):
    def test_kpis(self):
        claims = pd.DataFrame(
            {
                "claim_key": ["AB-1", "AP-1"],
                "source": ["AbAssurance", "AssurePlus"],
                "contract_key": ["AB-1", "AP-1"],
                "estimated_amount": [1000.0, 3000.0],
                "status": ["open", "closed"],
                "fraud_score": [float("nan"), 91.0],
            }
        )
        result = stats.claim_stats(claims, contracts())
        self.assertEqual(result["total"], 2)
        self.assertEqual((result["total_amount"], result["average_amount"]), (4000.0, 2000.0))
        self.assertEqual(result["claims_per_100_contracts"], 66.7)
        self.assertEqual(result["fraud_alerts"], 1)
        self.assertEqual(set(result["by_type"]["insurance_type"]), {"health", "auto"})
        self.assertEqual(int(result["by_status"]["claims"].sum()), 2)


class TestFinanceStats(unittest.TestCase):
    def test_kpis(self):
        payments = pd.DataFrame(
            {
                "source": ["AbAssurance", "AssurePlus", "AssurePlus", "AssurePlus"],
                "payment_date": pd.to_datetime(
                    ["2026-01-05", "2026-01-20", "2026-02-02", "2026-02-03"]
                ),
                "amount": [100.0, 50.0, 50.0, 50.0],
                "method": ["card", "transfer", "transfer", "card"],
                "status": ["paid", "paid", "paid", "failed"],
            }
        )
        result = stats.finance_stats(payments, contracts())
        self.assertEqual(result["total_paid"], 200.0)
        self.assertEqual(result["failed_payments"], 1)
        self.assertEqual(result["failure_rate"], 25.0)
        self.assertEqual(result["annual_premiums"], 2100.0)
        january = result["by_month"].query("month == '2026-01'")["amount"].sum()
        self.assertEqual(january, 150.0)
        self.assertEqual(result["by_method"]["amount"].sum(), 200.0)


if __name__ == "__main__":
    unittest.main()
