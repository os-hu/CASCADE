import os

from cascade.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer
from cascade.utils.Utils import log


class BaselineVisualizer(AnalysisVisualizer):
    def __init__(self, vis_key="name", logger="print"):
        super().__init__()
        self.logger = logger
        self.vis_key = vis_key


    def visualize(self, data, output_path, full=False):

        positives = []
        negatives = []

        for d in data:
            if "results" in d:
                r = d["results"]
                if r[0] == "Positive" and r[1] == "Positive" and r[2] == "Positive" and r[3] == "Positive":
                    # all positive
                    positives.append(d["id"])
                else:
                    negatives.append(d["id"])

        print("Positive: ", len(positives))
        print("Negative: ", len(negatives))
        print("--------------------")
        if full:
            print("Positive: ", positives)
            print("Negative: ", negatives)
