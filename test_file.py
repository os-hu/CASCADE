import unittest
import src.Basic_Calc

class test_Basic_Calc(unittest.TestCase):

    def test_sumgood(self):
        self.assertEqual((3+3), src.Basic_Calc.sum(3, 3))
    def test_sumbad(self):
        self.assertNotEquals(55, src.Basic_Calc.sum(50, 5))

