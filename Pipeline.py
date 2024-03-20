from Extraction import Extraction
from Analysis import Analysis

class Pipeline():
    def __init__(self, extraction: Extraction, analysis: Analysis):
        """
         the main pipeline object. calls extract analyse and generator in an appropriate manor.
         is usually build through Pipeline_Factory

        """
        self.extraction = extraction
        self.analysis = analysis

    def run(self, input_path, output_path=None):
        """
        TODO
        :return:
        """
        data = self.extraction.extract(input_path)
        results = self.analysis.analyse(data)

        # TODO save results to output path   if it is not None
        print(results, output_path)
