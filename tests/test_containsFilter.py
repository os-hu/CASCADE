import unittest
from cascade.filters.ContainsFilterFunction import ContainsFilterFunction

testDict = {
    "1": ["A", "B"],
    "2": ["A"],
    "3": ["B"],
    "4": [],
    "5": "A",
    "6": "B"
}

class test_containsfilter(unittest.TestCase):

    def test_1(self):
        f = ContainsFilterFunction("1", "B", invert=False)
        self.assertEqual(f(testDict), True)  # add assertion here

    def test_1_not(self):
        f = ContainsFilterFunction("1", "B", invert=True)
        self.assertEqual(f(testDict), False)  # add assertion here

    def test_2(self):
        f = ContainsFilterFunction("2", "B", invert=False)
        self.assertEqual(f(testDict), False)  # add assertion here

    def test_2_not(self):
        f = ContainsFilterFunction("2", "B", invert=True)
        self.assertEqual(f(testDict), True)  # add assertion here

    def test_3(self):
        f = ContainsFilterFunction("3", "B", invert=False)
        self.assertEqual(f(testDict), True)  # add assertion here

    def test_3_not(self):
        f = ContainsFilterFunction("3", "B", invert=True)
        self.assertEqual(f(testDict), False)  # add assertion here


    def test_4(self):
        f = ContainsFilterFunction("4", "B", invert=False)
        self.assertEqual(f(testDict), False)  # add assertion here

    def test_4_not(self):
        f = ContainsFilterFunction("4", "B", invert=True)
        self.assertEqual(f(testDict), True)  # add assertion here

    def test_5(self):
        f = ContainsFilterFunction("5", "B", invert=False)
        self.assertEqual(f(testDict), False)  # add assertion here

    def test_5_not(self):
        f = ContainsFilterFunction("5", "B", invert=True)
        self.assertEqual(f(testDict), True)  # add assertion here


    def test_6(self):
        f = ContainsFilterFunction("6", "B", invert=False)
        self.assertEqual(f(testDict), True)  # add assertion here

    def test_6_not(self):
        f = ContainsFilterFunction("6", "B", invert=True)
        self.assertEqual(f(testDict), False)  # add assertion here


    def test_7(self):
        f = ContainsFilterFunction("7", "B", invert=False)
        self.assertEqual(f(testDict), False)  # add assertion here

    def test_7_not(self):
        f = ContainsFilterFunction("7", "B", invert=True)
        self.assertEqual(f(testDict), False)  # add assertion here



if __name__ == '__main__':
    unittest.main()
