import unittest
import src.Basic_Calc


class test_Basic_Calc(unittest.TestCase):

    def test_sumgood(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((3 + 3), c.sum(3, 3))

    def test_sumgood2(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertEqual((4 + 3), c.sum(3, 4))

    def test_sumbad(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, c.sum(50, 5))

    def test_sumerror(self):
        c = src.Basic_Calc.Basic_Calc()
        self.assertNotEqual(55, src.Basic_Calc.sum(50, 5))

