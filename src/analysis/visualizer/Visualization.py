import copy

from AnalysisVisualizer import AnalysisVisualizer


class Visualization:
    def __init__(self, visualizer: AnalysisVisualizer):
        self.visualizer = visualizer

    def visualize(self, data, **kwargs):
        imm = tuple(copy.deepcopy(data))
        self.visualizer.visualize(imm, **kwargs)
