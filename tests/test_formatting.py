import unittest

from abassurance.formatting import format_euro, format_number, format_percent


class TestFormatting(unittest.TestCase):
    def test_thousands_separated_by_space(self):
        self.assertEqual(format_number(1234567), "1 234 567")
        self.assertEqual(format_number(1000), "1 000")

    def test_decimals_use_a_comma(self):
        self.assertEqual(format_number(1234.5, 1), "1 234,5")

    def test_euro_and_percent(self):
        self.assertEqual(format_euro(12345.6), "12 346 €")
        self.assertEqual(format_percent(1.8), "1,8 %")


if __name__ == "__main__":
    unittest.main()
