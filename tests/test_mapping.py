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
