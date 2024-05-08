from src.extraction.Extraction import Extraction
from src.filters.Filter import Filter
from src.analysis.Analysis import Analysis


class Pipeline():
    def __init__(self, extraction: Extraction, filter: Filter, analysis: Analysis, setup: dict):
        """
         The main pipeline object. Calls "extract" and "analyse" in an appropriate manner.
         is usually build through Pipeline_Factory
         :param extraction: the specific instantiated Extraction object that is used for extraction
         :param analysis: the specific instantiated analysis object
         :param setup: a dictionary that contains the names of the specific instances used
         for extraction, analysis and the objects inside of them,
        """
        self.extraction = extraction
        self.filter = filter
        self.analysis = analysis
        self.setup = setup

    def execute(self, input_path, output_path):
        """
       This executes the entire pipline. First extract() from the extraction object is called.
       The output of that is passed to the analysis object. and analyse is executed.

       These specific objects handle what the specific operations do and any things like temporary or
       intermediate saving, which type of analyses should be done and the generator that the analysis uses.
        The visualizer of the analysis object handles whether any output/results are printed
        or just saved to the output_path.
        """

        data = self.extraction.extract(input_path, output_path)

        filtered_data = self.filter.filter_all(data, output_path)

        can_work = True
        can_work &= self.analysis.extraction_requirements.verify(filtered_data)
        can_work &= self.analysis.generator.test_generator.extraction_requirements.verify(filtered_data)
        can_work &= self.analysis.generator.code_generator.extraction_requirements.verify(filtered_data)
        can_work &= self.analysis.generator.doc_generator.extraction_requirements.verify(filtered_data)
        can_work &= self.analysis.executor.extraction_requirements.verify(filtered_data)
        can_work &= self.analysis.visualizer.extraction_requirements.verify(filtered_data)

        results = self.analysis.analyse(filtered_data, output_path)

        # TODO save results to output path   or handle that in the analysis?    doc cutrently states that the visualizer handles that.
        #  Should the output path be given to the analysis as well?
        #print(results)
