import unittest

import pandas as pd

from abassurance import config
from abassurance.duplicates import count_unique_customers, duplicate_matrix, find_duplicates


def customer(key, source, first, last, birth, email, phone):
    return {
        "customer_key": key,
        "source": source,
        "first_name": first,
        "last_name": last,
        "birth_date": pd.Timestamp(birth) if birth else pd.NaT,
        "email": email,
        "phone": phone,
    }


AB, AP = config.SOURCE_AB, config.SOURCE_AP


class TestFindDuplicates(unittest.TestCase):
    def test_same_person_in_both_sources(self):
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Jean", "DUPONT", "1980-05-17", "j@mail.fr", "0612345678"),
                customer("AP-1", AP, "JEAN", "Dupont", "1980-05-17", "j@mail.fr", "0612345678"),
            ]
        )
        pairs = find_duplicates(customers)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs.iloc[0]["match_status"], "certain")
        self.assertEqual(pairs.iloc[0]["matched_on"], "birth_date, email, phone")

    def test_name_order_and_accents_do_not_matter(self):
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Hélène", "MORIN", "1990-01-01", "h@mail.fr", "0611111111"),
                customer("AP-1", AP, "Morin", "Helene", "1990-01-01", "x@mail.fr", "0622222222"),
            ]
        )
        pairs = find_duplicates(customers)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs.iloc[0]["match_status"], "to_review")

    def test_regression_missing_birth_date_does_not_hide_a_duplicate(self):
        """Bug corrigé : une date de naissance illisible (NaT) excluait le client du calcul."""
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Jean", "DUPONT", "1980-05-17", "j@mail.fr", "0612345678"),
                customer("AP-1", AP, "Jean", "DUPONT", None, "j@mail.fr", "0612345678"),
            ]
        )
        self.assertEqual(len(find_duplicates(customers)), 1)
        self.assertEqual(len(find_duplicates(customers, identifiers=("birth_date",))), 0)

    def test_family_sharing_contact_details_is_not_a_duplicate(self):
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Marie", "DUPONT", "1980-05-17", "f@mail.fr", "0612345678"),
                customer("AB-2", AB, "Paul", "DUPONT", "2005-02-01", "f@mail.fr", "0612345678"),
            ]
        )
        self.assertTrue(find_duplicates(customers).empty)

    def test_homonyms_with_nothing_in_common_are_not_duplicates(self):
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Jean", "MARTIN", "1980-05-17", "a@mail.fr", "0611111111"),
                customer("AP-1", AP, "Jean", "MARTIN", "1975-01-01", "b@mail.fr", "0622222222"),
            ]
        )
        self.assertTrue(find_duplicates(customers).empty)

    def test_missing_values_are_never_matched_together(self):
        customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Jean", "MARTIN", None, None, None),
                customer("AP-1", AP, "Jean", "MARTIN", None, None, None),
            ]
        )
        self.assertTrue(find_duplicates(customers).empty)


class TestMatrixAndUniqueCount(unittest.TestCase):
    def setUp(self):
        self.customers = pd.DataFrame(
            [
                customer("AB-1", AB, "Jean", "DUPONT", "1980-05-17", "j@mail.fr", "0612345678"),
                customer("AP-1", AP, "Jean", "DUPONT", "1980-05-17", "j@mail.fr", "0612345678"),
                customer("AB-2", AB, "Jean", "DUPONT", "1980-05-17", "j@mail.fr", "0612345678"),
                customer("AP-2", AP, "Anna", "LEROY", "1991-03-03", "a@mail.fr", "0699999999"),
                customer("AP-3", AP, "Anna", "LEROY", "1991-03-03", "a@mail.fr", "0699999999"),
            ]
        )
        self.pairs = find_duplicates(self.customers)

    def test_matrix_counts_cross_and_internal_pairs(self):
        matrix = duplicate_matrix(self.pairs)
        self.assertEqual(matrix.loc[AB, AB], 1)
        self.assertEqual(matrix.loc[AP, AP], 1)
        self.assertEqual(matrix.loc[AB, AP], 2)
        self.assertEqual(matrix.loc[AP, AB], 2)

    def test_matrix_without_pairs_is_all_zero(self):
        matrix = duplicate_matrix(self.pairs.iloc[0:0])
        self.assertEqual(int(matrix.to_numpy().sum()), 0)

    def test_unique_customers_merges_groups(self):
        self.assertEqual(count_unique_customers(self.customers, self.pairs), 2)

    def test_unique_customers_without_pairs(self):
        self.assertEqual(count_unique_customers(self.customers, self.pairs.iloc[0:0]), 5)


if __name__ == "__main__":
    unittest.main()
