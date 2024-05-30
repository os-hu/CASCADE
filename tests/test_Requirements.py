import unittest
from cascade.Requirements import Requirements, RequirementsMismatchException

Kind = Requirements.Kind
Level = Requirements.Level


class test_Requirements(unittest.TestCase):
    """
    Tests the Requirements class, requires nothing
    """

    def test_add_requirement(self):
        test_requirements = Requirements(Kind.PROVIDED, "Add")
        test_requirements.add_requirement("signature.name") 
        test_requirements.add_requirement("signature.type", Level.OPTIONAL) 
        
        self.assertEqual(test_requirements.reqs.items(),
                          {("signature.name", Level.MANDATORY), ("signature.type", Level.OPTIONAL)})

    def test_fulfills(self):
        test_requirements_p1 = Requirements(Kind.PROVIDED, "Fulfills Provider 1")
        test_requirements_p2 = Requirements(Kind.PROVIDED, "Fulfills Provider 2")
        test_requirements_e1 = Requirements(Kind.EXPECTED, "Fulfills Expected 1")
        test_requirements_e2 = Requirements(Kind.EXPECTED, "Fulfills Expected 2")

        test_requirements_p1.add_requirement("signature.name")
        test_requirements_p1.add_requirement("signature.type", Level.OPTIONAL)
        
        test_requirements_e1.add_requirement("signature.name")
        test_requirements_e1.add_requirement("signature.type")
        
        test_requirements_e2.add_requirement("signature.generics") 

        with self.assertRaises(RequirementsMismatchException):
            test_requirements_p1.fulfills(test_requirements_p2)
        
        with self.assertRaises(RequirementsMismatchException):
            test_requirements_e2.fulfills(test_requirements_p1)

        self.assertTrue(test_requirements_e1.fulfills(test_requirements_p1))

    def test_verify(self):
        data = [{
                "signature": {
                    "name": "TEST",
                    "type": "int",
                    "modifiers": []
                },
                "doc": "THIS IS A TEST DOC"
                }, {
                "signature": {
                    "name": "TEST",
                    "type": "int"
                },
                "doc": "THIS IS A TEST DOC"
                }, {
                "signature": {
                    "name": "TEST",
                    "type": "int",
                    "generics": []
                },
                "doc": "THIS IS A TEST DOC"
                }]
        test_requirements_passing = Requirements(Kind.PROVIDED, "Verify Provider 1")
        test_requirements_failing = Requirements(Kind.PROVIDED, "Verify Provider 2")
        
        test_requirements_passing.add_requirement("signature.name")
        test_requirements_passing.add_requirement("signature.modifiers", Level.OPTIONAL)
        
        test_requirements_failing.add_requirement("signature.name")
        test_requirements_failing.add_requirement("signature.modifiers")

        with self.assertRaises(RequirementsMismatchException):
            test_requirements_failing.verify(data)

        self.assertTrue(test_requirements_passing.verify(data))

    def test_merge(self):
        test_requirements_p1 = Requirements(Kind.PROVIDED, "Merge Provider 1")
        test_requirements_p2 = Requirements(Kind.PROVIDED, "Merge Provider 2")
        test_requirements_e1 = Requirements(Kind.EXPECTED, "Merge Expected 1")
        test_requirements_e2 = Requirements(Kind.EXPECTED, "Merge Expected 2")

        test_requirements_p1.add_requirement("signature.name") 
        test_requirements_p1.add_requirement("signature.type", Level.OPTIONAL) 

        test_requirements_p2.add_requirement("signature.name") 
        test_requirements_p2.add_requirement("signature.type") 
        
        test_requirements_e1.add_requirement("signature.name") 
        test_requirements_e1.add_requirement("signature.type") 
        
        test_requirements_e2.add_requirement("signature.name", Level.OPTIONAL) 
        test_requirements_e2.add_requirement("signature.generics") 

        with self.assertRaises(RequirementsMismatchException):
            test_requirements_p1.fulfills(test_requirements_e2)

        provided_merged = test_requirements_p1.merge(test_requirements_p2)
        self.assertTrue(provided_merged is not test_requirements_p1 and provided_merged is not test_requirements_p2)
        self.assertEqual(provided_merged.reqs.items(), {("signature.name", Level.MANDATORY), ("signature.type", Level.MANDATORY)})

        expected_merged = test_requirements_e1.merge(test_requirements_e2)
        self.assertTrue(expected_merged is not test_requirements_e1 and expected_merged is not test_requirements_e2)
        self.assertEqual(expected_merged.reqs.items(), {("signature.name", Level.MANDATORY), ("signature.type", Level.MANDATORY),
                                            ("signature.generics", Level.MANDATORY)})

