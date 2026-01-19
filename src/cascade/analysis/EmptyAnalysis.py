import os

from cascade.analysis.Analysis import Analysis

from cascade.Requirements import Requirements
from cascade.analysis.executor.Execution import Execution
from cascade.generation.Generation import Generation

from cascade.utils.Utils import save_dicts_list_to_json

class EmptyAnalysis(Analysis):
    """
    This is a placeholder Analysis class that does nothing.
    """
    def __init__(self, generator: Generation, executor: Execution):
        super().__init__(generator, executor)
        self.provided = Requirements(Requirements.Kind.PROVIDED, name="Analysis-Provided")
        self.provided.add_requirement("all", Requirements.Level.MANDATORY)
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Analysis-Extraction-Expected")


    def analyze(self, data, input_path, output_path):
        """
        This analysis should do nothing.
        """
        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
