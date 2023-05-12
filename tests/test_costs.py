"""
Test the fetching and calculating of cost data.
"""
import unittest
import sqlite3
from programme_costing_utilities.calculations import serve_population, calculate_personnel_annual_salary, fit_FTE

class TestDemographics(unittest.TestCase):
    """Test getting demography."""

    def setUp(self):
        self.country = "VNM"
        self.conn = sqlite3.connect('./data/undp_wpp.db')

    def test_population_before_1950(self):
        """Test getting the population before 1950."""
        self.assertEqual(serve_population(self.country, 1949, self.conn), serve_population(self.country, 1950, self.conn))
        self.assertNotEqual(serve_population(self.country, 1949, self.conn), 0)

    def test_population_after_2100(self):
        """Test getting the population before 2100."""
        self.assertEqual(serve_population(self.country, 2101, self.conn), serve_population(self.country, 2100, self.conn))
        self.assertNotEqual(serve_population(self.country, 2100, self.conn), 0)

class TestPersonnel(unittest.TestCase):
    """Test calculating cadres."""

    def setUp(self):
        # create a list of example ISO3 codes
        self.country = "DZA"
        self.cadre_1 = 6742
        self.cadre_2 = 8791
        self.cadre_3 = 11606
        self.cadre_4 = 18791
        self.price_db = sqlite3.connect('./data/who_choice_price_database.db')
        self.demog_db = sqlite3.connect('./data/undp_wpp.db')
        self.normalized_FTE = 1

    def test_cadre_1(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculate_personnel_annual_salary(self.country, 1, self.price_db)[0], 6741.5
        )

    def test_cadre_2(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculate_personnel_annual_salary(self.country, 2, self.price_db)[0], 8790.6
        )

    def test_cadre_3(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculate_personnel_annual_salary(self.country, 3, self.price_db)[0], 11605.54
        )

    def test_cadre_4(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculate_personnel_annual_salary(self.country, 4, self.price_db)[0], 18791.08
        )

    def test_normalized_fte_national(self):
        """Test calculating the normalized FTE for national personnel."""
        self.assertEqual(
            fit_FTE(self.country, 1, self.price_db), self.normalized_FTE
        )

    def test_normalized_fte_provincial(self):
        """Test calculating the normalized FTE for provincial personnel."""
        self.assertEqual(
            fit_FTE(self.country, 1, self.price_db), self.normalized_FTE
        )

    def test_normalized_fte_district(self):
        """Test calculating the normalized FTE for district personnel."""
        self.assertEqual(
            fit_FTE(self.country, 1, self.price_db), self.normalized_FTE
        )
