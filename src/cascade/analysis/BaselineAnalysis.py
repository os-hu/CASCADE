import os
from openai import OpenAI
from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, save_dicts_list_to_json
from cascade.utils.JavaUtils import build_context, build_signature

class BaselineAnalysis(Analysis):
    """
    TODO
    """
    def __init__(self, generator: Generation, executor: Execution, regenerate=False, reexecute=False, debug=0, step_size=1, die_if_setup_fails=False):
        super().__init__(generator, executor)
        self.die_if_setup_fails = die_if_setup_fails
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug


    def analyse(self, data: list, input_path, output_path):
        model = "gpt-4o-mini-2024-07-18"
        def makeModelRequest(promptList, max_tokens=1200, temperature=0, freq_penalty=0.0):
            if "OPENAI_API_KEY" in os.environ:
                api_key = os.environ["OPENAI_API_KEY"]
            else:
                # TODO
                raise Exception("No api key in environment")

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=promptList,
                max_tokens=max_tokens,
                temperature=temperature,
                frequency_penalty=freq_penalty
            )

            answer = str(response.choices[0].message.content)
            return answer

        #  loop through data
        for d in tqdm(data):
            code = d["code"]
            doc = d["doc"]

            results = [None, None, None, None]
            answers = {}

            full_code = build_signature(d, doc=True) + code + "\n"

            try:
                # Phase 1 -----------------------------------------------------------------------------------------------
                promptList = []
                promptList.append({"role": "system",
                                   "content": "Are the following docstring and code consistent. Answer first with Yes or No, then explain why"})
                promptList.append({"role": "user", "content": f"{full_code}"})

                answer = makeModelRequest(promptList)

                answers["phase1"] = answer

                for word in answer.lower().split():
                    if "yes" in word.strip():
                        results[0] = "Negative"
                        break

                    if "no" in word.strip():
                        results[0] = "Positive"
                        break

                if results[0] is not None:
                    print(results[0])

            except Exception as e:
                print("error1")

            try:
                # Phase 2 -----------------------------------------------------------------------------------------------
                promptList = []
                promptList.append({"role": "system",
                                   "content": "Is there an inconsistency between the following docstring and code. Answer first with Yes or No, then explain why"})
                promptList.append({"role": "user", "content": f"{full_code}"})

                answer = makeModelRequest(promptList)

                answers["phase2"] = answer

                for word in answer.lower().split():
                    if "yes" in word.strip():
                        results[1] = "Positive"
                        break

                    if "no" in word.strip():
                        results[1] = "Negative"
                        break

                if results[1] is not None:
                    print(results[1])

            except Exception as e:
                print("error2")

            try:
                # Phase 3 -----------------------------------------------------------------------------------------------
                full_code = build_context(d, doc=True) + code + "\n}\n"

                promptList = []
                promptList.append({"role": "system",
                                   "content": "You will get a snippet of a Java class. I want to know for a specific method if its code and documentation are consistent. Allways answer with Yes or No before you explain."})
                promptList.append({"role": "user",
                                   "content": f"{full_code}\n\n\nAre code and documentation of {d['signature']['name']} consistent? The Documentation is {d['doc']}\n\n Answer with Yes or No?"})

                answer = makeModelRequest(promptList)
                answers["phase3"] = answer

                for word in answer.lower().split():
                    if "yes" in word.strip():
                        results[2] = "Negative"
                        break

                    if "no" in word.strip():
                        results[2] = "Positive"
                        break

                if results[2] is not None:
                    print(results[2])

            except Exception as e:
                print("error3")

            try:
                # Phase 4 -----------------------------------------------------------------------------------------------
                promptList = []
                promptList.append({"role": "system",
                                   "content": "You will get a snippet of a Java class. I want to know for a specific method if there is an inconsistency between the documentation adn the code. Allways answer with Yes or No before you explain."})
                promptList.append({"role": "user",
                                   "content": f"{full_code}\n\n\n Is there an inconsistency between code and documentation of {d['signature']['name']}? The Documentation is {d['doc']}\n\n Answer with Yes or No?"})

                answer = makeModelRequest(promptList)
                answers["phase4"] = answer

                for word in answer.lower().split():
                    if "yes" in word.strip():
                        results[3] = "Positive"
                        break

                    if "no" in word.strip():
                        results[3] = "Negative"
                        break

                if results[3] is not None:
                    print(results[3])

            except Exception as e:
                print("error4")

            d["results"] = results
            d["answers"] = answers

            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
