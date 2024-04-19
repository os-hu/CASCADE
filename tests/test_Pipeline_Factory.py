import unittest
from src.Pipeline_Factory import Pipeline_Factory


class test_Pipeline_Factory(unittest.TestCase):

    def test_build(self):
        pipelineName = "GPT35_HumanEval"  # "test_pipeline"
        filePath = "./test_resources/setup/"

        pipeline = Pipeline_Factory(filePath).build(pipelineName)

        self.assertEqual(str(type(pipeline.extraction)), "<class 'src.implementations.extraction.Human_Eval_Basic_Extraction.Human_Eval_Basic_Extraction'>")

    def test_build_with_arguments(self):
        pipelineName = "setup_with_arg"  # "test_pipeline"
        filePath = "./test_resources/setup/"

        pipeline = Pipeline_Factory(filePath).build(pipelineName)

        self.assertEqual(str(type(pipeline.extraction)),
                             "<class 'src.implementations.extraction.Human_Eval_Basic_Extraction.Human_Eval_Basic_Extraction'>")
        self.assertEqual(pipeline.analysis.generator.code_generator.max_attempts , 3)

        # TODO finish this test

if __name__ == '__main__':
    unittest.main()