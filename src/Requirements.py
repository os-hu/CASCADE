from typing import Dict

class RequirementsMismatchExcption(Exception):
    pass

class Requirements():
    i = 0
    """
    A utility class which enables adding and checking requirements for Pipelines.

    The class contains two subclasses for enum values which are used in the functions.
    """


    class Level(enum):
        MANDATORY = 1
        OPTIONAL = 2


    class Kind(enum):
        PROVIDED = 1
        EXPECTED = 2


    def __init__(self, kind: Requirements.Kind, name: str="ANONYMOUS-"):
        """
        The constructor for a requirements object.
        
        :param
            kind: The ~Requirements.Kind of the requirements
            name: A name which can be set to make warning diagnostics simpler to understand
        """
        self.kind = kind
        self.reqs: Dict[str, Requirements.Level] = dict()
        if name == "ANONYMOUS-":
            name = name + str(i)
        self.name = name


    def addRequirement(self, name: str, level: Requirements.Level=Requirements.Level.MANDATORY):
        """
        A function to add requiremnts to this requirement object.

        To specify an optional requirement for:
        [
            {
                "signature": {
                    "name" : --The entry which is required--
                }
            }
        ]
        One has to use addRequirement("signature.name", Requiremnts.Level.OPTIONAL)

        :param
            name: The name of the requirement, if necessary hierarchically separated by dots
            level: The level the requirement has, is it mandatory or optional (defaults to mandatory)

        :return
            This object, so requirements can be daisy chained
        """
        self.reqs[name] = level
        return self


    def fulfills(self, other: Requirements):
        """
        Checks if the provided requirements fulfill the expected requirements.

        Prints a list of warnings for requirement level mismatches    

        :param
            other: The requirements to compare against

        :raise 
            RequirementsMismatchException: If both requirements are of the same ~Requirements.Kind
            RequirementsMismatchException: If any ~Requirements.Level.MANDATORY requirements were not fulfilled

        :return
            True if all requirements expected are fulfilled
        """
        if other.kind == self.kind:
            raise RequirementsMismatchException("Both Requirements were of kind " + ("provided" if self.kind == Requirements.Kind.PROVIDED else "expected") + ", you probably wanted to use self.merge() instead!")
        if self.kind == Requirements.Kind.EXPECTED:
            return other.fulfills(self)
        
        if "all" in self.reqs:
            return True

        warnings = []
        errors = []
        for key in other.reqs:
            if other.reqs[key] == Requirements.Level.MANDATORY:
                if key in self.reqs:
                    if other.reqs[key] != self.reqs[key]:
                        warnings.append(key)
                else:
                        errors.append(key)
        print(self.name + ": " +str(warnings))
        if errors:
            raise RequirementsMismatchException(str(errors))
        return not errors
    

    def verify(self, data: dict):
        """
        Checks if the data seems to fulfill the requirements.

        If the requirements contain 'all', they will NOT be verified

        :param
            data: The dictionary on which the requiremnts are supposed to hold
        
        :raise
            RequirementsMismatchException: If any ~Requirements.Level.MANDATORY requirements were not fulfilled

        :return
            True if all mandatory requirements are fulfilled (e.g., the key exists)
        """
        errors = []
        if "all" in self.reqs:
            print(self.name + ": Explicitly cannot verify if 'all' requirements are fulfilled.")
            return True
        for key in self.reqs:
            components = key.split(".")
            value = data
            for component in components:
                if component in value:
                    value = value[component]
                elif self.reqs[key] == Requirements.Level.MANDATORY:
                    errors.append(key)
        if errors:
            raise RequirementsMismatchException("Keys " + str(errors) + " were mandatory, but are missing.")
        return True


    def merge(self, other: Requirements):
        """
        Merges two requiremnts.

        For ~Requirements.Kind.PROVIDED:
            Takes all the requirements of both objects returns the less strict one if both share it (~Requirements.Kind.OPTIONAL)
        

        For ~Requirements.Kind.EXPECTED
            Takes all the requirements of both objects, returns the more strict one if both share it (~Requirements.Kind.MANDATORY)

        :param
            other: The requirements to merge with

        :raise 
            RequirementsMismatchException: If both requirements are of a different ~Requirements.Kind

        :return
            Returns a NEW Requirements object containing the merge result
        """
        if other.kind != self.kind:
            raise RequirementsMismatchException("Both Requirements were of different kinds, you probably wanted to use self.fulfills() instead!")

        r = Requirements(self.kind, "merged-" + self.name + "-" + other.name)
        # Iterate over symmetric difference and add all keys
        for key in self.reqs.keys ^ other.reqs.keys:
            if key in self.reqs:
                r.addRequirement(key, self.reqs[key])
            else:
                r.addRequirement(key, other.reqs[key])
        
        # Iterate over intersection and add key according to kind
        for key in self.reqs.keys & other.reqs.keys:
            if self.reqs[key] != other.reqs[key]:
                if self.kind == Requirements.Kind.PROVIDED 
                    level = Requirements.Level.OPTIONAL 
                else:
                    level = Requirements.Level.MANDATORY
            else
                level = self.reqs[key]
            r.addRequirement(key, level)

        return r
