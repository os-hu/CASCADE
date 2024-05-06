from src.analysis.visualizer.AnalysisVisualizer import AnalysisVisualizer


class TreeVisualizer(AnalysisVisualizer):
    def __init__(self, vis_key="name"):
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

        self.draw_tree(data)


    def draw_tree(self, data):
        k = self.vis_key
        total = len(data)
        executed = list(filter(lambda x: "results" in x ,data))
        print(len(executed))

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
                print(l)
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
            print(f"{l['level']}:\t p:{len(l['p'])}, f:{len(l['f'])}, e:{len(l['e'])}")


        pass

    def remove_tree(self, data):
        pass