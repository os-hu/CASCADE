from abc import ABC, abstractmethod


class Extraction(ABC):
    @abstractmethod
    def extract(self, input_path, output_path) -> dict:
        """
        This is the main method of the Extraction module.
        It gets an input path which could be for a root directory of an entire project or a dataset file or a jar.
        It then should extract functions and other required data from there.

        These should then be returned as a list of dictionaries but also saved as a json file to the output path.
        Either with the generic name such as "extracted.json" or with the name provided in the path if it ends with ".json".
        This could also be used to append to an existing file.

        The expected output format for one function is
        {
            doc :
            id :
            signature : {
                name : the simple name of the function
                returns : return type of the function,
                params : parameters, including types -- if existent -- as one string ,
                modifier : ,
                annotations: ,
                generics :
                }
            language : e.g. python or java
            parent : {
                name : ,
                doc : ,
                imports : ,
                other_methods : ,
                variables : global variables of the class that could be used by the function under test,
                generics :
                }
            code : the body of the function
            code_file_path :
            called_functions :
            tests :  TODO ???
            test_imports :
            test_file_path :
            testrunner:  e.g. unnittest, junit,
        }



        Note that depending on the Analysis and generate implementations not all of these fields need to be filled.

        You can use the implementation 'json_Extraction' and its extract() method to check whether
        the file already exists in the output path and just load this one instead.

        The output

        """
        pass
