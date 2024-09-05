import os
import unittest
import sys


import test


path = os.path.join("", "out")

# execute via testrunner
try:
    suite = unittest.TestLoader().loadTestsFromModule(test)

    all_tests = []
    for s in suite:
        for test in s:
            all_tests.append(test.id().split(".")[-1])

    test_result = unittest.TextTestRunner().run(suite)


except Exception as e:
    #  print an error in to the read out file
    with open(path, "w") as file:
        file.write(f"[];[];[]")
    sys.exit(-1)


failed = [failure[0].id().split('.')[-1] for failure in test_result.failures]
errored = [error[0].id().split('.')[-1] for error in test_result.errors]

passed = [id for id in all_tests if (id not in failed + errored)]

with open (path, "w") as file:
    file.write( f"{passed};{failed};{errored}" )