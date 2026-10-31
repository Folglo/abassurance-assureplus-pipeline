import unittest

import pandas as pd

from abassurance import config, mapping
from abassurance.quality import QualityLog

TODAY = pd.Timestamp("2026-10-30")


def oracle_clients():
    return pd.DataFrame(
        {
            "AB_CLIENT_ID": ["1"],
            "AB_NOM": ["dupont "],
            "AB_PRENOM": ["jean"],
            "AB_DATE_NAISSANCE": ["1980-05-17"],
            "AB_EMAIL": ["Jean@Mail.fr"],
            "AB_TELEPHONE": ["06 12 34 56 78"],
            "AB_ADRESSE": ["1 rue A"],
            "AB_CODE_POSTAL": ["6000"],
            "AB_NUM_FISCAL": ["123"],
            "AB_DATE_CREATION": ["2020-01-02 10:00:00"],
            "AB_STATUT_CLIENT": ["ACTIF"],
        }
    )


def sqlserver_users():
    return pd.DataFrame(
        {
            "AP_USER_ID": ["7"],
            "AP_FULL_NAME": ["Jean DUPONT"],
            "AP_BIRTH_DATE": ["17/05/1980"],
            "AP_MAIL_ADDRESS": ["JEAN@MAIL.FR"],
            "AP_PHONE_NUMBER": ["+33 6 12 34 56 78"],
            "AP_STREET_ADDRESS": ["1 rue A"],
            "AP_ZIP_CODE": ["06000"],
            "AP_CREATED_AT": ["2021-03-04 09:00:00"],
            "AP_CUSTOMER_STATUS": ["SUSPENDED"],
            "AP_LOYALTY_SCORE": ["42"],
        }
    )


class TestSplitFullName(unittest.TestCase):
    def test_first_name_then_upper_last_name(self):
        self.assertEqual(mapping.split_full_name("Jean-Pierre DUPONT"), ("DUPONT", "Jean-Pierre"))

    def test_upper_last_name_first(self):
        self.assertEqual(mapping.split_full_name("DUPONT Jean"), ("DUPONT", "Jean"))

    def test_comma_format(self):
        self.assertEqual(mapping.split_full_name("DUPONT, jean"), ("DUPONT", "Jean"))

    def test_no_upper_case_uses_last_word(self):
        self.assertEqual(mapping.split_full_name("jean dupont"), ("DUPONT", "Jean"))

    def test_single_word_and_missing(self):
        self.assertEqual(mapping.split_full_name("Madonna"), ("MADONNA", None))
        self.assertEqual(mapping.split_full_name(None), (None, None))


class TestCustomerMapping(unittest.TestCase):
    def test_oracle_customer(self):
        row = mapping.map_customers_oracle(oracle_clients(), QualityLog(), TODAY).iloc[0]
        self.assertEqual(row["customer_key"], "AB-1")
        self.assertEqual((row["last_name"], row["first_name"]), ("DUPONT", "Jean"))
        self.assertEqual(row["email"], "jean@mail.fr")
        self.assertEqual(row["zip_code"], "06000")
        self.assertEqual(row["status"], "active")
        self.assertTrue(pd.isna(row["loyalty_score"]))

    def test_sqlserver_customer(self):
        log = QualityLog()
        row = mapping.map_customers_sqlserver(sqlserver_users(), log, TODAY).iloc[0]
        self.assertEqual(row["customer_key"], "AP-7")
        self.assertEqual((row["last_name"], row["first_name"]), ("DUPONT", "Jean"))
        self.assertEqual(row["birth_date"], pd.Timestamp("1980-05-17"))
        self.assertEqual(row["phone"], "0612345678")
        self.assertEqual(row["status"], "suspended")
        self.assertEqual(row["loyalty_score"], 42)
        self.assertTrue(pd.isna(row["tax_number"]))
        self.assertTrue(log.to_frame().empty)

    def test_invalid_birth_date_is_logged(self):
        raw = sqlserver_users()
        raw["AP_BIRTH_DATE"] = ["1980-99-99"]
        log = QualityLog()
        row = mapping.map_customers_sqlserver(raw, log, TODAY).iloc[0]
        self.assertTrue(pd.isna(row["birth_date"]))
        self.assertEqual(log.to_frame().iloc[0]["reason"], "unparseable")

    def test_unsplittable_name_is_logged(self):
        raw = sqlserver_users()
        raw["AP_FULL_NAME"] = [""]
        log = QualityLog()
        mapping.map_customers_sqlserver(raw, log, TODAY)
        self.assertIn("unsplittable", set(log.to_frame()["reason"]))


class TestContractClaimPaymentMapping(unittest.TestCase):
    def test_sqlserver_monthly_premium_becomes_annual(self):
        raw = pd.DataFrame(
            {
                "AP_CONTRACT_REF": ["C1"],
                "AP_USER_ID": ["7"],
                "AP_PRODUCT_CODE": ["AUTO_PREMIUM"],
                "AP_START_DATE": ["2024-01-01 00:00:00"],
                "AP_END_DATE": ["2027-01-01 00:00:00"],
                "AP_MONTHLY_PREMIUM": ["50.25"],
                "AP_CONTRACT_STATE": ["ACTIVE"],
                "AP_BROKER_CODE": ["BRK001"],
            }
        )
        row = mapping.map_contracts_sqlserver(raw, QualityLog(), TODAY).iloc[0]
        self.assertEqual(row["annual_premium"], 603.0)
        self.assertEqual((row["insurance_type"], row["status"]), ("auto", "active"))
        self.assertEqual((row["customer_key"], row["contract_key"]), ("AP-7", "AP-C1"))
        self.assertEqual(row["end_date"], pd.Timestamp("2027-01-01"))

    def test_oracle_contract(self):
        raw = pd.DataFrame(
            {
                "AB_POLICY_NUMBER": ["P1"],
                "AB_CLIENT_ID": ["1"],
                "AB_TYPE_ASSURANCE": ["SANTE"],
                "AB_DATE_DEBUT": ["2024-01-01"],
                "AB_DATE_FIN": ["2027-01-01"],
                "AB_PRIME_ANNUELLE": ["900"],
                "AB_STATUT_CONTRAT": ["ACTIF"],
                "AB_AGENCE_ID": ["12"],
            }
        )
        row = mapping.map_contracts_oracle(raw, QualityLog(), TODAY).iloc[0]
        self.assertEqual((row["insurance_type"], row["annual_premium"]), ("health", 900.0))
        self.assertEqual(row["intermediary_code"], "12")

    def test_claims(self):
        ab = pd.DataFrame(
            {
                "AB_CLAIM_ID": ["1"],
                "AB_POLICY_NUMBER": ["P1"],
                "AB_DATE_SINISTRE": ["2025-02-03 10:00:00"],
                "AB_MONTANT_ESTIME": ["1500"],
                "AB_STATUT_SINISTRE": ["EN_COURS"],
                "AB_DESCRIPTION": ["Bris de glace"],
            }
        )
        ap = pd.DataFrame(
            {
                "AP_SINISTRE_NUM": ["9"],
                "AP_CONTRACT_REF": ["C1"],
                "AP_INCIDENT_DATE": ["2025-02-03 10:00:00"],
                "AP_ESTIMATED_AMOUNT": ["800.5"],
                "AP_CLAIM_STATUS": ["REJECTED"],
                "AP_CLAIM_COMMENT": ["Vol"],
                "AP_FRAUD_SCORE": ["85"],
            }
        )
        ab_row = mapping.map_claims_oracle(ab, QualityLog(), TODAY).iloc[0]
        ap_row = mapping.map_claims_sqlserver(ap, QualityLog(), TODAY).iloc[0]
        self.assertEqual((ab_row["status"], ab_row["contract_key"]), ("in_progress", "AB-P1"))
        self.assertTrue(pd.isna(ab_row["fraud_score"]))
        self.assertEqual((ap_row["status"], ap_row["fraud_score"]), ("rejected", 85.0))

    def test_payments(self):
        ab = pd.DataFrame(
            {
                "AB_PAYMENT_ID": ["1"],
                "AB_POLICY_NUMBER": ["P1"],
                "AB_DATE_PAIEMENT": ["2026-01-05"],
                "AB_MONTANT": ["75"],
                "AB_MODE_PAIEMENT": ["CB"],
            }
        )
        ap = pd.DataFrame(
            {
                "AP_PAYMENT_REF": ["AAA"],
                "AP_CONTRACT_REF": ["C1"],
                "AP_PAYMENT_DATETIME": ["2026-01-05 10:00:00"],
                "AP_AMOUNT_PAID": ["40"],
                "AP_PAYMENT_CHANNEL": ["WIRE"],
                "AP_TRANSACTION_STATUS": ["FAILED"],
            }
        )
        ab_row = mapping.map_payments_oracle(ab, QualityLog(), TODAY).iloc[0]
        ap_row = mapping.map_payments_sqlserver(ap, QualityLog(), TODAY).iloc[0]
        self.assertEqual((ab_row["method"], ab_row["status"]), ("card", "paid"))
        self.assertEqual((ap_row["method"], ap_row["status"]), ("transfer", "failed"))


class TestIntegrityRules(unittest.TestCase):
    def test_duplicate_keys_keep_first_and_are_logged(self):
        frame = pd.DataFrame({"customer_key": ["AB-1", "AB-1", "AB-2"], "v": [1, 2, 3]})
        log = QualityLog()
        result = mapping.drop_duplicate_keys(frame, "customer_key", "customers", log)
        self.assertEqual(list(result["v"]), [1, 3])
        self.assertEqual(len(log.to_frame()), 1)

    def test_orphans_are_removed_and_logged(self):
        frame = pd.DataFrame({"customer_key": ["AB-1", "AB-404"]})
        log = QualityLog()
        result = mapping.drop_orphans(frame, {"AB-1"}, "customer_key", "contracts", log)
        self.assertEqual(list(result["customer_key"]), ["AB-1"])
        self.assertEqual(log.to_frame().iloc[0]["row_id"], "AB-404")

    def test_all_common_vocabularies_use_known_sources(self):
        self.assertEqual(set(config.SOURCE_CODES), {config.SOURCE_AB, config.SOURCE_AP})


if __name__ == "__main__":
    unittest.main()
