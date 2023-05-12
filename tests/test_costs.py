"""
Test the fetching and calculating of cost data.
"""
import unittest
import sqlite3
from programme_costing_utilities import calculations


class TestDemographics(unittest.TestCase):
    """Test getting demography."""

    def setUp(self):
        self.country = "VNM"
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_population_before_1950(self):
        """Test getting the population before 1950."""
        self.assertEqual(
            calculations.serve_population(self.country, 1949, self.conn), 
            calculations.serve_population(self.country, 1950, self.conn))
        self.assertNotEqual(calculations.serve_population(self.country, 1949, self.conn), 0)

    def test_population_after_2100(self):
        """Test getting the population before 2100."""
        self.assertEqual(
            calculations.serve_population(self.country, 2101, self.conn), 
            calculations.serve_population(self.country, 2100, self.conn))
        self.assertNotEqual(calculations.serve_population(self.country, 2100, self.conn), 0)

    def test_arbitrary_population_between_1950_and_2100(self):
        """Test getting the population between 1950 and 2100."""
        self.assertEqual(calculations.serve_population(self.country, 2020, self.conn), 96_648_685)


class TestStatisticalDivisions(unittest.TestCase):
    """Test getting statistical/administrative divisions."""
    def setUp(self):
        self.country = "CHN"
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_national_division(self):
        """Test getting the national division."""
        self.assertEqual(calculations.serve_number_of_divisions(self.country, "National", self.conn), 1)

    def test_provincial_division(self):
        """Test getting the provincial division."""
        self.assertEqual(calculations.serve_number_of_divisions(self.country, "PROVINCIAL", self.conn), 31)

    def test_district_division(self):
        """Test getting the district division."""
        self.assertEqual(calculations.serve_number_of_divisions(self.country, "district", self.conn), 350)


class TestPersonnel(unittest.TestCase):
    """Test calculating cadres."""

    def setUp(self):
        # create a list of example ISO3 codes
        self.country = "DZA"
        self.cadre_1 = 6742
        self.cadre_2 = 8791
        self.cadre_3 = 11606
        self.cadre_4 = 18791
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')
        self.standard_FTE = 1

    def test_cadre_1(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculations.calculate_personnel_annual_salary(self.country, 1, self.conn)[0], 6741.5
        )

    def test_cadre_2(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculations.calculate_personnel_annual_salary(self.country, 2, self.conn)[0], 8790.6
        )

    def test_cadre_3(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculations.calculate_personnel_annual_salary(self.country, 3, self.conn)[0], 11605.54
        )

    def test_cadre_4(self):
        """Test calculating the annual salary of a cadre."""
        self.assertEqual(
            calculations.calculate_personnel_annual_salary(self.country, 4, self.conn)[0], 18791.08
        )

    def test_normalized_fte_national(self):
        """Test calculating the normalized FTE for national personnel."""
        self.assertEqual(
            calculations.fit_FTE(
                self.standard_FTE,
                self.country,
                2020,
                "National",
                self.conn
            ), 
            0.86903332
        )

    def test_normalized_fte_provincial(self):
        """Test calculating the normalized FTE for provincial personnel."""
        self.assertEqual(
            calculations.fit_FTE(
                self.standard_FTE,
                self.country,
                2020,
                "provincial",
                self.conn
            ),
            0.18104860833333333
        )

    def test_normalized_fte_district(self):
        """Test calculating the normalized FTE for district personnel."""
        self.assertEqual(
            calculations.fit_FTE(
                self.standard_FTE,
                self.country,
                2020,
                "DISTRICT",
                self.conn
            ), 
            0.056394115509409475
        )


class TestConsumable(unittest.TestCase):
    """
    Testing the ability to get accurate prices.
    """
    def setUp(self):
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_paper(self):
        """Test getting the price of paper."""
        self.assertEqual(calculations.serve_consumable_cost("Paper plain", self.conn)[0], 0.02171)

    def test_photocopier(self):
        """Test getting the price of paper."""
        item = "Multifunciton Photocopier, Fax, Printer and Scanner "
        self.assertEqual(calculations.serve_consumable_cost(item, self.conn)[0], 2199)


class TestPerDiem(unittest.TestCase):
    """
    Test per diem calculations.
    """
    def setUp(self):
        self.country = "ARG"
        self.year = 2019
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_per_diem_int_national(self):
        """Test getting the per diem for an international."""
        actual_per_diem = calculations.serve_per_diem(
            self.country,
            "NATIONAL",
            self.conn,
            local=False
        )[0]

        expected = 265.416155869506
        self.assertEqual(actual_per_diem, expected)

    def test_per_diem_local_provincial(self):
        """Test getting the per diem for a local provincial."""
        actual_per_diem = calculations.serve_per_diem(
            self.country,
            "provincial",
            self.conn,
            local=True
        )[0]

        expected_international = 149.84705803456
        local_proportion = 0.2
        self.assertAlmostEqual(
            actual_per_diem, 
            expected_international * local_proportion,
            6
        )

    def test_per_diem_international_district(self):
        """Test getting the per diem for an international district."""
        actual_per_diem = calculations.serve_per_diem(
            self.country,
            "district",
            self.conn,
            local=False
        )[0]

        expected = 97.9540342065485
        self.assertEqual(actual_per_diem, expected)


class TestDDist(unittest.TestCase):
    """Test the retrieval of DDIst information"""

    def setUp(self):
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_ddist95(self):
        """Test getting the DDist95 value"""
        country = "AUS"
        approx_value = int(calculations.serve_distance_between_regions(country, "DDist95", self.conn))
        expected_value = 1148
        self.assertEqual(approx_value, expected_value)

    def test_ddist10(self):
        """Test getting the DDist10 value"""
        country = "NAM"
        approx_value = int(calculations.serve_distance_between_regions(country, "DDist10", self.conn))
        expected_value = 574
        self.assertEqual(approx_value, expected_value)

    def test_landmass(self):
        """Test getting the landmass value"""
        country = "RUS"
        approx_value = int(calculations.serve_distance_between_regions(country, "size_km_sq", self.conn))
        expected_value = 16_889_000
        self.assertEqual(approx_value, expected_value)


class TestMeetings(unittest.TestCase):
    """
    Test meetings and workshops.
    """
    def setUp(self):
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')
        self.country = "ARG"
        self.year = 2019

    def test_national_workshop(self):
        attendees = [
            ("National Experts", "visiting", 4, True),
            ("Local Professional Staff", "visiting", 20, True),
            ("Support Staff", "local", 2, False)
        ]
        national_workshop_records = calculations.serve_meeting_costs(
            country=self.country,
            year=self.year,
            division="national",
            days=5,
            attendees=attendees,
            room_size=200,
            conn=self.conn)
        ...
        

    def test_provincial_meeting(self):
        ...

    def test_district_workshop(self):
        attendees = [
            ("National Experts", "visiting", 4, True),
            ("Local Professional Staff", "visiting", 20, True),
            ("Support Staff", "local", 2, False)
        ]
        provincial_workshop_records = calculations.serve_meeting_costs(
            country=self.country,
            year=self.year,
            division="national",
            days=5,
            attendees=attendees,
            room_size=200,
            conn=self.conn,
            frequency=2,
            annual_meetings=3)
        ...

class CalculateVehicles(unittest.TestCase):
    """
    Calculate operating costs for vehicles.
    """
    def setUp(self):
        self.car = "Corolla sedan 2014 model"
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_operating_cost_per_km(self):
        """Test getting the operating cost per km."""
        cost = calculations.serve_vehicle_operating_cost(self.car, self.conn)[0]
        self.assertEqual(
            cost, 0.13837172222222222
        )

    def test_fuel_consumption_per_km(self):
        """Test getting the fuel consumption per km."""
        consumption = calculations.serve_vehicle_fuel_consumption(self.car, self.conn)[0]
        self.assertEqual(
            consumption, 0.0668
        )

class TestCostRebasing(unittest.TestCase):
    ...

class TestAnnualCosts(unittest.TestCase):
    ...