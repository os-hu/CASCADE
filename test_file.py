











import unittest

class test_func(unittest.TestCase):
    METADATA = {}

    def test_find_zero(self):
        import math
        import random
        rng = random.Random(42)
        import copy
        for _ in range(100):
            ncoeff = 2 * rng.randint(1, 4)
            coeffs = []
            for _ in range(ncoeff):
                coeff = rng.randint(-10, 10)
                if coeff == 0:
                    coeff = 1
                coeffs.append(coeff)
            solution = find_zero(copy.deepcopy(coeffs))
            self.assertTrue(math.fabs(poly(coeffs, solution)) < 0.0001)

