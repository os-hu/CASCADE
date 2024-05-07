from src.generation.NoGenerator import NoGenerator
from src.Pipeline import Pipeline
from src.generation.Generation import Generation
from src.filters.Filter import Filter
from src.utils import Utils

import sys
import json


import os
import importlib


class PipelineFactory:
    """
    TODO
    """

    def __init__ (self):
        """
        TODO Write Doc
        """

        # TODO replace this with CLI input later
        self.api_key_path = ""
        if "API_KEY_PATH" in os.environ:
            self.api_key_path = os.environ["API_KEY_PATH"]



    @staticmethod
    def load_class(class_name, module_path, args, kwargs):
        """
        Dynamically loads a class and instantiates it with given arguments.

        :param
            class_name: The name of the class to be instantiated.
            module_path: The dot-separated path to the module containing the class.
                               For example, 'package.subpackage.module'.
            **kwargs: Arbitrary keyword arguments passed to the class constructor.
        :return
            An instance of the specified class, instantiated with the given arguments.
        """
        try:
            # Dynamically import the module where the class is defined
            module = importlib.import_module(module_path)

            # Get the class by its name
            cls = getattr(module, class_name)

            # Instantiate the class with the provided arguments
            instance = cls(*args, **kwargs)

            return instance
        except ModuleNotFoundError as e:
            print(f"Module '{module_path}' not found: {e}")
        except AttributeError as e:
            print(f"Class '{class_name}' not found in '{module_path}': {e}")
        except Exception as e:
            print(f"Error instantiating class '{class_name}': {e}")


    def build(self, pipeline_path):
        """
        TODO
        :return: a build pipeline object
        """

        setup = Utils.load_json_from_path(pipeline_path)


        # TODO    change the path to be more individual    provided by the CLI
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
        print(sys.path)

        name = setup["Extraction"]["name"]
        path = "src.extraction." + name
        kwargs_ = setup["Extraction"]["kwargs"]
        extraction = self.load_class(name, path, [], kwargs_)

        filter_functions = []
        if "FilterFunctions" in setup:
            for f in setup["FilterFunctions"]:
                name = f["name"]
                path = "src.filters." + name
                kwargs_ = f["kwargs"]
                filter_functions.append(self.load_class(name, path, [], kwargs_))

        filter_ = Filter(filter_functions)

        generator_strings = [("CodeGenerator", "code"),
                             ("TestGenerator", "test"),
                             ("DocGenerator", "doc")]

        generators = {gen[1]: NoGenerator() for gen in generator_strings}
        for gen in generator_strings:
            if gen[0] in setup and "name" in setup[gen[0]]:
                current = setup[gen[0]]
                name = current["name"]
                path = f"src.generation.{gen[1]}." + name
                kwargs_ = current["kwargs"]
                generators[gen[1]] = self.load_class(name, path, [self.api_key_path], kwargs_)

        generation = Generation(generators["code"], generators["test"], generators["doc"])

        # TODO handle that these might be optional???
        name = setup["Executor"]["name"]
        path = "src.analysis.executor." + name
        kwargs_ = setup["Executor"]["kwargs"]
        analysis_executor = self.load_class(name, path, [], kwargs_)

        name = setup["Visualizer"]["name"]
        path = "src.analysis.visualizer." + name
        kwargs_ = setup["Visualizer"]["kwargs"]
        analysis_visualizer = self.load_class(name, path, [], kwargs_)

        name = setup["Analysis"]["name"]
        path = "src.analysis." + name
        kwargs_ = setup["Analysis"]["kwargs"]
        analysis = self.load_class(name, path, [generation, analysis_visualizer, analysis_executor], kwargs_)

        pipeline = Pipeline(extraction, filter_, analysis, setup)

        return pipeline


