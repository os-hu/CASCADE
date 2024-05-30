import unittest
from cascade.PipelineFactory import PipelineFactory


class test_PipelineFactory(unittest.TestCase):

    def test_build_with_arguments(self):
        pipeline_path = "resources/setup/setup_with_arg.json"  # "test_pipeline"

        pipeline_fact = (PipelineFactory())

        pipeline_fact.api_key_path = "./resources/apikeys/openai_key"


        pipeline = pipeline_fact.build(pipeline_path)

        self.assertEqual(str(type(pipeline.extraction)),
                             "<class 'cascade.extraction.HumanEvalExtraction.HumanEvalExtraction'>")
        self.assertEqual(pipeline.analysis.generator.code_generator.prompt_executor.max_attempts , 3)

        print(pipeline.filter.filter_functions)

        # TODO finish this test



if __name__ == '__main__':
    unittest.main()