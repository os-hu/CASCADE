import os

from cascade.analysis.Analysis import Analysis

from cascade.Requirements import Requirements
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.visualizer.Visualization import Visualization
from cascade.generation.Generation import Generation

from cascade.utils.Utils import save_dicts_list_to_json

class emptyAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, visualizer: Visualization):
        super().__init__(generator, executor, visualizer)
        self.provided = Requirements(Requirements.Kind.PROVIDED, name="Analysis-Provided")
        self.provided.add_requirement("all", Requirements.Level.MANDATORY)
        self.extraction_requirements = Requirements(Requirements.Kind.EXPECTED, name="Analysis-Extraction-Expected")


    def analyse(self, data, input_path, output_path):
        """
        This is the main analysis method.
        :param **kwargs:
        :return:
        """
        
        save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
