import os

from cascade.extraction.Extraction import Extraction
from cascade.filters.Filter import Filter
from cascade.analysis.Analysis import Analysis
from cascade.utils.Utils import load_json_from_path


class Pipeline():
    def __init__(self, extraction: Extraction, _filter: Filter, analysis: Analysis, setup_config: dict):
        """
        The main pipeline object. Calls "extract" and "analyse" in an appropriate manner.
        is usually build through Pipeline_Factory
        :param extraction: the specific instantiated Extraction object that is used for extraction
        :param analysis: the specific instantiated analysis object
         :param setup: a dictionary that contains the names of the specific instances used
         for extraction, analysis and the objects inside of them,
        """
        self.extraction = extraction
        self._filter = _filter
        self.analysis = analysis
        self.setup_config = setup_config

    def execute(self, input_path, output_path) -> None:
        """
        This executes the entire pipline. First extract() from the extraction object is called.
        he output of that is passed to the analysis object. and analyze is executed.

        These specific objects handle what the specific operations do and any things like temporary or
        intermediate saving, which type of analyses should be done and the generator that the analysis uses.
        """
        preanalyzed_path = os.path.join(output_path, "analyzed.json")
        use_preanalyzed = os.environ.get("CASCADE_USE_PREANALYZED", "0") == "1"

        if not use_preanalyzed or not os.path.exists(preanalyzed_path):
            print("Extraction started")
            data = self.extraction.extract(input_path, output_path)
            print("Extraction finished. Extracted: ", len(data))

            print("Filtering started")
            filtered_data = self._filter.filter_all(data)
            print("Filtering finished. Remaining: ", len(filtered_data))

        else:
            print("Using benchmark target from analyzed.json")
            temp_data = load_json_from_path(preanalyzed_path)
            filtered_data = []
            if temp_data:
                filtered_data = temp_data

        if not filtered_data:
            print("No data to analyze")
            return

        print("Analysis started")
        self.analysis.analyze(filtered_data, input_path, output_path)
        print("Analysis finished")

