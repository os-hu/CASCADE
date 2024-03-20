from Pipeline_Factory import Pipeline_Factory

if __name__ == '__main__':

    pipelineName = "GPT35_HumanEval" #"test_pipeline"
    filePath = "./setup"

    pipeline = Pipeline_Factory(filePath).build(pipelineName)








