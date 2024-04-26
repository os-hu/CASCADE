from src.Pipeline import Pipeline
from src.Generation import Generation

from src import utils

import sys


import os
import importlib


class Pipeline_Factory:
    """
    TODO
    """

    def __init__ (self, folder_path):
        """
        TODO Write Doc
        """
        self.all_setups = {}

        # read in all setup files in the specified folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            if os.path.isfile(file_path):
                data = utils.load_json_from_path(file_path)

                # remove the ending of the filename  if there is one
                name = filename.rsplit('.', 1)[0]

                # TODO check for format and errors etc.
                # there are two types of entries   with and without parameters.
                setup = {}
                for key, value in data.items():
                    if isinstance(value, str):
                        setup[key] = {"name": value, "kwargs": {}}
                    else:
                        setup[key] = value
                #print(setup)
                self.all_setups[name] = setup

        #print(self.all_setups)
        if self.all_setups == {}:
            print(f"no setup files could be extracted for path: {folder_path}")
            sys.exit(-1)

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


    def build(self, pipelineName):
        """
        TODO
        :return: a build pipeline object
        """
        if pipelineName not in self.all_setups:
            print(f"'{pipelineName}' is not in the setup files\n content: {list(self.all_setups.keys())}")
            sys.exit(-2)

        else:
            setup = self.all_setups[pipelineName]

        name = setup["Extraction"]["name"]
        path = "src.implementations.extraction." + name
        kwargs_ = setup["Extraction"]["kwargs"]
        extraction = self.load_class(name, path, [], kwargs_)

        name = setup["Code_Generator"]["name"]
        path = "src.implementations.generation.code_generator." + name
        kwargs_ = setup["Code_Generator"]["kwargs"]
        code_generator = self.load_class(name, path, [], kwargs_)

        name = setup["Test_Generator"]["name"]
        path = "src.implementations.generation.test_generator." + name
        kwargs_ = setup["Test_Generator"]["kwargs"]
        test_generator = self.load_class(name, path, [], kwargs_)

        generation = Generation(code_generator, test_generator)

        name = setup["Executor"]["name"]
        path = "src.implementations.analysis.analysis_executor." + name
        kwargs_ = setup["Executor"]["kwargs"]
        analysis_executor = self.load_class(name, path, [], kwargs_)

        name = setup["Visualizer"]["name"]
        path = "src.implementations.analysis.analysis_visualizer." + name
        kwargs_ = setup["Visualizer"]["kwargs"]
        analysis_visualizer = self.load_class(name, path, [], kwargs_)

        name = setup["Analysis"]["name"]
        path = "src.implementations.analysis." + name
        kwargs_ = setup["Analysis"]["kwargs"]
        analysis = self.load_class(name, path, [generation, analysis_visualizer, analysis_executor], kwargs_)

        pipeline = Pipeline(extraction, analysis, setup)

        return pipeline


