

class ExecutionResults():
    def __init__(self):
        self.results = ([],[],[])
        self.results_numbers = (0,0,0)
        self.comp_errors = None
        self.parsed_file = ""

        self.comp_error_matches = []
        self.test_overview_matches = []
        self.xml_blocks = []

    def __str__(self):
        string = (f"EXECUTIONResults---------------------------\nResults: {self.results}\n Numbers: {self.results_numbers}\n Comp Errors: {self.comp_errors}\n"
                  f"Parsed File: {self.parsed_file}\n Comp Error Matches: {self.comp_error_matches}\n"
                  f"Test Overview Matches: {self.test_overview_matches}\n XML Blocks: {self.xml_blocks}\nEXECUTIONResults---------------------\n"
                  )

        return string