from Pipeline import Pipeline

from Extraction import Extraction

from Generation import Generation
from Code_Generator import Code_Generator
from Test_Generator import Test_Generator
from Prompt_Executor import Prompt_Executor

from Analysis import Analysis
from Analysis_Executor import Analysis_Executor
from Analysis_Visualizer import Analysis_Visualizer


import sys, json, os, importlib

class Pipeline_Factory():
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
                with open(file_path, 'r') as file:
                    data = json.load(file)

                # remove the ending of the filename  if there is any
                name = filename.rsplit('.', 1)[0]

                self.all_setups[name] = data

        print(self.all_setups)
        if self.all_setups == {}:
            print(f"no setup files could be extracted for path: {folder_path}")
            sys.exit(-1)

    def load(self, class_name, module_path, **kwargs):
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
        if True: #try:
            # Dynamically import the module where the class is defined
            module = importlib.import_module(module_path)

            # Get the class by its name
            cls = getattr(module, class_name)

            # Instantiate the class with the provided arguments
            instance = cls(**kwargs)

            return instance
        #except ModuleNotFoundError as e:
            print(f"Module '{module_path}' not found: {e}")
        #except AttributeError as e:
            print(f"Class '{class_name}' not found in '{module_path}': {e}")
        #except Exception as e:
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


        # TODO most of these are missing there positinal arguments

        name = setup["Extraction"]
        path = "implementations.extraction." + name
        extraction = self.load(name, path)

        name = setup["Code_Generator"]
        path = "implementations.generation.code_generator." + name
        code_generator = self.load(name, path)

        name = setup["Test_Generator"]
        path = "implementations.generation.test_generator." + name
        test_generator = self.load(name, path)

        name = setup["Analysis"]
        path = "implementations.analysis." + name
        analysis = self.load(name, path)

        name = setup["Executor"]
        path = "implementations.analysis.analysis_executor." + name
        analysis_executor = self.load(name, path)

        name = setup["Visualizer"]
        path = "implementations.analysis.analysis_visualizer." + name
        analysis_visualizer = self.load(name, path)

        generation = Generation()

        pipeline = Pipeline()


        return pipeline


