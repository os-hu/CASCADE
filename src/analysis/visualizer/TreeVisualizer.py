from tqdm import tqdm

from src.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer
from src.utils.Utils import log


class TreeVisualizer(AnalysisVisualizer):
    def __init__(self, vis_key="name", logger="print"):
        super().__init__()
        self.logger = logger
        self.vis_key = vis_key


    def visualize(self, data, full=False):
        """
        :param full:
        :param data: the data to be visualized
        TODO write this


        data in here is a list of dicts.
        { id
        type:   failed, succeeded, errored

        }
        """
        self.vis_key = "id"
        self.draw_tree(data, full=full)


    def draw_tree(self, data, full=False):

        k = self.vis_key
        total = len(data)
        executed = list(filter(lambda x: "results" in x ,data))
        log(f"generated: {len(executed)}/{total}", logger=self.logger)

        levels = {
            "1" : {"level": "(code, tests)", "p": [], "f": [], "e": []},
            "2" : {"level": "(code, new_tests)", "p": [], "f": [], "e": []},
            "3" : {"level": "(new_code, new_tests)", "p": [], "f": [], "e": []},
            "4" : {"level": "(new_code, tests)", "p": [], "f": [], "e": []}
        }
        # TODO all in a dict

        for d in executed:
            res = d["results"]
            for l in levels.values():
                if l["level"] in res:
                    if res[l["level"]][0] == [] and res[l["level"]][1] == []:
                        # if there was an internal error append the key to the array
                        l["e"].append(d[k])
                    elif res[l["level"]][1] == [] and res[l["level"]][2] == []:
                        # if no errors or failures  then passed
                        l["p"].append(d[k])
                    else:
                        l["f"].append(d[k])


        for l in levels.values():
            log(f"{l['level']}:\t p:{len(l['p'])}, f:{len(l['f'])}, e:{len(l['e'])}" , logger=self.logger)

        if full:
            log("------------final---------------", logger=self.logger)
            for l in levels.values():
                log(f"{l['level']}:\t p:{l['p']}, f:{l['f']}, e:{l['e']}", logger=self.logger)


    def remove_tree(self, data):
        pass