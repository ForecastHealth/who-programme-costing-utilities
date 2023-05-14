"""
Test the main module and runtime.
"""
import unittest
import sqlite3
import main
from programme_costing_utilities import runtime

class TestRuntime(unittest.TestCase):
    """Set-up main and run"""
    def setUp(self):
        self.data = main.DEFAULTS
        self.conn = sqlite3.connect('./data/who_choice_price_database.db')

    def test_runtime(self):
        records = runtime.run(self.data, self.conn)
        ...