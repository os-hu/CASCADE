from src.abstract_classes.Extraction import Extraction
from src.abstract_classes.Analysis import Analysis

class Pipeline():
    def __init__(self, extraction: Extraction, analysis: Analysis, setup: dict):
        """
         the main pipeline object. calls extract analyse and generator in an appropriate manner.
         is usually build through Pipeline_Factory

        """
        self.extraction = extraction
        self.analysis = analysis
        self.setup = setup

    def execute(self, input_path, output_path):
        """
        TODO
        :return:
        """
        data = self.extraction.extract(input_path, output_path)
        results = self.analysis.analyse(data)


        # TODO save results to output path
        print(results, output_path)
