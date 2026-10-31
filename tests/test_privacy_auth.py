import unittest

import pandas as pd

from abassurance import auth, privacy


class TestPrivacy(unittest.TestCase):
    def test_mask_email(self):
        self.assertEqual(privacy.mask_email("jean.dupont@mail.fr"), "j***@mail.fr")
        self.assertEqual(privacy.mask_email("invalide"), "invalide")
        self.assertTrue(pd.isna(privacy.mask_email(None)))

    def test_mask_name(self):
        self.assertEqual(privacy.mask_name("Jean DUPONT"), "J*** D***")
        self.assertTrue(pd.isna(privacy.mask_name(None)))

    def test_pseudonymise_is_stable_and_not_reversible(self):
        first = privacy.pseudonymise("AB-1")
        self.assertEqual(first, privacy.pseudonymise("AB-1"))
        self.assertNotEqual(first, privacy.pseudonymise("AB-2"))
        self.assertNotIn("AB-1", first)
        self.assertNotEqual(first, privacy.pseudonymise("AB-1", salt="autre"))

    def test_anonymise_pairs_hides_identities(self):
        pairs = pd.DataFrame(
            {
                "customer_a": ["AB-1"],
                "customer_b": ["AP-1"],
                "name_a": ["Jean DUPONT"],
                "name_b": ["Jean DUPONT"],
                "email_a": ["j@mail.fr"],
                "email_b": ["j@mail.fr"],
            }
        )
        result = privacy.anonymise_pairs(pairs).iloc[0]
        self.assertEqual(result["name_a"], "J*** D***")
        self.assertEqual(result["email_a"], "j***@mail.fr")
        self.assertNotIn("AB-1", result["customer_a"])
        self.assertEqual(pairs.iloc[0]["name_a"], "Jean DUPONT")  # l'original n'est pas modifié


class TestAuth(unittest.TestCase):
    def test_valid_logins(self):
        self.assertEqual(auth.authenticate("admin", "AbAssurance-Admin26"), "admin")
        self.assertEqual(auth.authenticate("user", "AbAssurance-User26"), "user")

    def test_wrong_password_unknown_user_and_swapped_passwords(self):
        self.assertIsNone(auth.authenticate("admin", "mauvais"))
        self.assertIsNone(auth.authenticate("inconnu", "AbAssurance-Admin26"))
        self.assertIsNone(auth.authenticate("user", "AbAssurance-Admin26"))

    def test_password_is_not_stored_in_clear(self):
        for account in auth.USERS.values():
            self.assertNotIn("AbAssurance", account["password_hash"])

    def test_custom_users_table(self):
        users = {"x": {"role": "viewer", "password_hash": auth.hash_password("pw")}}
        self.assertEqual(auth.authenticate("x", "pw", users), "viewer")


if __name__ == "__main__":
    unittest.main()
