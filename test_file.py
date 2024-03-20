import importlib
def load_and_instantiate(self, class_name, module_path, **kwargs):
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
    if True:  # try:
        # Dynamically import the module where the class is defined
        print("meh")
        module = importlib.import_module(module_path)
        print("here0")
        # Get the class by its name
        cls = getattr(module, class_name)

        # Instantiate the class with the provided arguments
        print("here1")
        instance = cls  # cls(**kwargs)
        print("here 2")

        return instance
        # except ModuleNotFoundError as e:
        print(f"Module '{module_path}' not found: {e}")
        # except AttributeError as e:
        print(f"Class '{class_name}' not found in '{module_path}': {e}")
        # except Exception as e:
        print(f"Error instantiating class '{class_name}': {e}")


if __name__ == '__main__':
    module_path = 'implementations.extraction.Human_Eval_Basic_Extraction'  # Example module
    #class_name = "Human_Eval_Basic_Extraction"
    module = importlib.import_module(module_path)
    print(module)
    print(module.__name__)
    clas
    cls = getattr(module, class_name)

    print(module)