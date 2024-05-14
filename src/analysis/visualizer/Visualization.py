import copy

from src.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer


class Visualization:
    def __init__(self, visualizer: AnalysisVisualizer):
        self.visualizer = visualizer

    def visualize(self, data, **kwargs):
        self.visualizer.visualize(copy.deepcopy(data), **kwargs)
