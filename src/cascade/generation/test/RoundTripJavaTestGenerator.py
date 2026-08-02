import copy
import json
import os
import re

from cascade.generation.test.MultiStepJavaTestGenerator import MultiStepJavaTestGenerator
from cascade.utils.JavaUtils import build_signature, build_api_context


class RoundTripJavaTestGenerator(MultiStepJavaTestGenerator):
    """
    Extends MultiStepJavaTestGenerator with a round-trip consistency check between test
    generation Phase 1 (test ideas) and Phase 2 (the final JUnit test class).

    After the test ideas are extracted from the documentation, a short description of the
    behavior that is implicitly checked by these test ideas alone is reconstructed by the
    model. This reconstructed description is then compared against the behavior description
    that was originally derived from the documentation in Phase 1. If missing, superfluous,
    or changed behavior assumptions are found, the test ideas are revised before Phase 2 is
    entered.

    This check is not a formal proof of semantic equivalence. It is meant as a pragmatic
    control step to catch too weak tests or undocumented assumptions early, before the tests
    are compiled and executed. To bound the additional cost, at most 'max_roundtrips' rounds
    are performed. The model can stop earlier if no relevant deviations are found anymore.
    """

    def __init__(self,
                 model="gpt-4o-mini-2024-07-18",
                 max_attempts=1, delay=3,
                 max_tokens=16000,
                 temperature=0,
                 max_prompt_tokens=8000,
                 freq_penalty=0.0, dummy=False,
                 base_url=None, api_key=None, #Base url if used with vllm,  for example: "http://127.0.0.1:8000/v1"
                 max_roundtrips=2,
                 extra_body=None  # e.g. {"chat_template_kwargs": {"enable_thinking": True}}
                 ):

        super().__init__(model=model, max_attempts=max_attempts, delay=delay,
                          max_tokens=max_tokens, temperature=temperature,
                          max_prompt_tokens=max_prompt_tokens, freq_penalty=freq_penalty,
                          dummy=dummy, base_url=base_url, api_key=api_key, extra_body=extra_body)

        self.max_roundtrips = max_roundtrips

    def generate(self, context, input_path, output_path):
        results_path = os.path.join(output_path, "results.txt")
        errors_path = os.path.join(output_path, "errors.txt")

        # Built once here and reused by the round-trip check and Phase 2 through
        # self._fit_api_context,
        # which falls back to "" on its own if no context was available to build.
        context["api_context"] = build_api_context(context, output_path)
        context["api_context_light"] = build_api_context(context, output_path, include_siblings=False)

        chat_history = []
        print("      Test generation Phase 1")
        # first given the method documentation and signature, we want to extract possible testcases or properties.
        step1_user = (
            f"Give a complete description of the behavior that we should test when we want to asure that the code matches its documentation from the following Java method:\n```java\n{build_signature(context, doc=True)}\n```\n\nMake sure you consider the entire functionality exactly as described in the documentation, and cover all edge cases but make no assumptions that are not stated in the documentation. If a documented behavior, condition, or exception seems unusual or unlikely, still specify a test for it exactly as written — do not skip it as an impossible precondition or treat it as a typo to fix."
        )
        prompt_step1 = [
            {"role": "system",
             "content": "You are an expert Java developer and requirements engineer. You will be given a method signature and its documentation. The documentation is the specification to test against: extract, from the documentation alone, behavior specifications that can be turned into unit tests checking whether the code does what the documentation says. Treat every statement — including examples and stated exceptions — as the literal contract, even if it looks mistaken, contradicts the method name, or differs from how a similar API usually behaves. Do not correct, complete, or second-guess the documentation: it may or may not match the code, and that is precisely what running these tests will reveal — it is not yours to decide. Apply this uniformly to all parts of the documentation."},
            {"role": "user",
             "content": step1_user}
        ]

        chat_history.append(copy.deepcopy(prompt_step1))
        response_step1a = self.prompt_executor.execute(prompt_step1).model_dump()
        chat_history.append(response_step1a)

        if not response_step1a["choices"]:
            print("      error during generation")
            with open(errors_path, "a") as f:
                f.write(f"error during test generation of {context["signature"]["name"]}")

            return "", chat_history

        prompt_step1.append(response_step1a["choices"][0]["message"])
        behavior_description = response_step1a["choices"][0]["message"]["content"]

        # now the goal is to convert this text into a usable format and extract the testable properties
        prompt_json_list = {"role": "user", "content": "Now turn this into a JSON array of unit tests we should write for test driven development. Each entry in the array should have: \"test_name\": a descriptive test method name starting with 'test' and \"test_description\": a detailed description for the developer of what this tests should do and which specific behavior from the documentation it tests. In particular, I want testable statements of the 'if this then that' type.\nFocus on those tests that follow directly from the documentation, e.g. no performance based ones.\nRespond with a single ```json ... ``` code block containing the array, nothing else."}

        prompt_step1.append(prompt_json_list)

        response_step1b = self.prompt_executor.execute(prompt_step1).model_dump()
        response_text = response_step1b["choices"][0]["message"]["content"]

        test_list = self.extract_json_list(output_path, response_text)

        chat_history.append(copy.deepcopy(prompt_step1))
        chat_history.append(response_step1b)

        if not test_list:
            with open(errors_path, "a") as f:
                f.write("error during test extraction from json")
            return "", chat_history

        print("      Test generation Phase 1.5 - Round-trip consistency check")
        test_list, roundtrip_history = self.round_trip_refine(context, behavior_description, test_list, output_path)
        chat_history.extend(roundtrip_history)

        context["test_list"] = test_list

        print("      Test generation Phase 2")
        # now we have a list of testable properties, we want to generate a testclass filled with these.
        prompt_step2 = self.build_prompt(context)

        response_step2a = self.prompt_executor.execute(prompt_step2).model_dump()

        prompt_step2.append(response_step2a["choices"][0]["message"])

        prompt_step2.append({"role": "user", "content": (
            "Make sure that this class compiles without errors. "
            "Check all imports are present and all checked exceptions are caught or declared. "
            "For JUnit assertEquals with numeric types, add explicit casts to avoid overload ambiguity "
            "(e.g. assertEquals((long) expected, (long) actual)). "
            "Even if no changes are needed, reply with the entire class verbatim inside a single ```java ... ``` code block."
        )})

        response_step2b = self.prompt_executor.execute(prompt_step2).model_dump()
        chat_history.append(copy.deepcopy(prompt_step2))
        chat_history.append(response_step2b)

        new_tests = self.extract_tests(response_step2b["choices"][0]["message"]["content"], context, response_step2b, output_path)

        # this is a fallback if the second reply did not include a code block
        if new_tests == "":
            new_tests = self.extract_tests(response_step2a["choices"][0]["message"]["content"], context, response_step2b, output_path)

        if new_tests == "":
            with open(results_path, "w") as f:
                f.write("Negative, No syntactically correct test class generated")
            with open(errors_path, "w") as f:
                f.write(f"No syntactically correct test class generated \nResponse text:\n{response_text}")
        print("      Test generation finished")
        return new_tests, chat_history

    def round_trip_refine(self, context, behavior_description, test_list, output_path):
        """
        Performs at most 'self.max_roundtrips' rounds of round-trip consistency checking on
        'test_list'. In each round, a short description of the behavior implicitly checked by
        the current test ideas is reconstructed from the test artifacts alone (Step A), and
        compared against 'behavior_description', which was derived from the original
        documentation in Phase 1 (Step B). If missing, superfluous, or changed behavior
        assumptions are reported, the test ideas are revised accordingly (Step C) and the next
        round starts on the revised list. The loop stops early once a round reports no relevant
        deviations anymore.

        Step A and Step B only reason over text descriptions and are kept free of the API
        context to keep them focused and cheap. Step C regenerates test ideas, so it is given
        API context via self._fit_api_context (already set up on 'context' by 'generate')
        so that revised tests don't invent behavior around methods
        that don't actually exist. If no API context is available, this is a no-op.

        :param context: the method context, used only to look up 'api_context'/'api_context_light'.
        :param behavior_description: the behavior description derived from the documentation in Phase 1.
        :param test_list: the current list of test ideas (dicts with "test_name" and "test_description").
        :param output_path: the output folder to log round-trip results and errors to.
        :return: a tuple of (possibly revised test_list, chat_history of this round-trip check).
        """
        roundtrip_path = os.path.join(output_path, "roundtrip.txt")
        errors_path = os.path.join(output_path, "errors.txt")
        history = []

        for round_num in range(1, self.max_roundtrips + 1):
            print(f"        round-trip {round_num}/{self.max_roundtrips}")

            # Step A: reconstruct the implicitly tested behavior from the test artifacts alone.
            reconstruct_prompt = [
                {"role": "system",
                 "content": "You are an expert Java developer and requirements engineer. You will be given only a list of test names and test descriptions, without access to the original documentation. Your task is to reconstruct, in your own words, the behavior that this set of tests implicitly checks."},
                {"role": "user",
                 "content": "Here is a JSON array of test ideas that were derived from the documentation of a method:\n```json\n" + json.dumps(test_list, indent=2) + "\n```\n\nGive a concise description of the behavior that these tests, taken together, implicitly verify. Do not speculate about behavior that none of the tests actually covers."}
            ]

            response_reconstruct = self.prompt_executor.execute(reconstruct_prompt).model_dump()
            history.append(copy.deepcopy(reconstruct_prompt))
            history.append(response_reconstruct)

            if not response_reconstruct["choices"]:
                with open(errors_path, "a") as f:
                    f.write(f"round-trip {round_num}: error during behavior reconstruction, aborting round-trip check\n")
                break

            reconstructed_description = response_reconstruct["choices"][0]["message"]["content"]

            # Step B: compare the reconstructed behavior with the documentation-derived one.
            compare_prompt = [
                {"role": "system",
                 "content": "You are an expert Java developer and requirements engineer performing a round-trip consistency check. You will compare two behavior descriptions of the same method: one derived from the original documentation, and one reconstructed only from a set of generated tests. Your task is to identify missing, superfluous, or changed behavior assumptions between the two. This is not about wording differences, only about differences that would affect whether the tests correctly enforce the documented behavior."},
                {"role": "user",
                 "content": f"Original behavior description (from the documentation):\n{behavior_description}\n\nReconstructed behavior description (from the generated tests only):\n{reconstructed_description}\n\nReply with a JSON object with the keys: \"consistent\" (boolean, true if there are no relevant deviations), \"missing\" (array of behavior assumptions present in the original but not covered by any test), \"superfluous\" (array of behavior assumptions the tests check that are not stated in the original documentation), \"changed\" (array of behavior assumptions that are tested differently than documented). Ignore purely stylistic differences. Reply with a single ```json ... ``` code block containing the object, nothing else."}
            ]

            response_compare = self.prompt_executor.execute(compare_prompt).model_dump()
            history.append(copy.deepcopy(compare_prompt))
            history.append(response_compare)

            if not response_compare["choices"]:
                with open(errors_path, "a") as f:
                    f.write(f"round-trip {round_num}: error during comparison step, aborting round-trip check\n")
                break

            comparison = self.extract_comparison_json(output_path, response_compare["choices"][0]["message"]["content"])

            with open(roundtrip_path, "a") as f:
                f.write(f"round-trip {round_num}:\n{json.dumps(comparison, indent=2)}\n\n")

            if comparison is None:
                # comparison could not be parsed, keep the current test ideas and stop refining.
                break

            deviations = comparison.get("missing", []) or comparison.get("superfluous", []) or comparison.get("changed", [])
            if comparison.get("consistent", False) or not deviations:
                print("        no relevant deviations found, stopping round-trip refinement")
                break

            print(f"        deviations found (missing: {len(comparison.get('missing', []))}, superfluous: {len(comparison.get('superfluous', []))}, changed: {len(comparison.get('changed', []))}), revising test ideas")

            # Step C: revise the test ideas based on the discrepancies found.
            revise_user = (
                "Original behavior description (from the documentation):\n" + behavior_description +
                "\n\nCurrent test ideas:\n```json\n" + json.dumps(test_list, indent=2) + "\n```\n\n"
                "The round-trip consistency check found the following issues:\n```json\n" + json.dumps(comparison, indent=2) + "\n```\n\n"
                "Revise the test ideas: add tests for missing behavior assumptions, remove or adjust superfluous tests that assume behavior not stated in the documentation, and correct tests whose description does not match the documented behavior. "
                "Reply with the complete revised JSON array of unit tests. Each entry should have: \"test_name\": a descriptive test method name starting with 'test' and \"test_description\": a detailed description for the developer of what this test should do and which specific behavior from the documentation it tests. Reply with a single ```json ... ``` code block containing the array, nothing else."
            )
            # same API context (if available) as Phase 1, so revised tests stay grounded in
            # the actual API surface instead of assuming methods that don't exist.
            revise_user += self._fit_api_context(context, revise_user)

            revise_prompt = [
                {"role": "system",
                 "content": "You are an expert Java developer and requirements engineer. You will revise a JSON array of unit test ideas so that it more faithfully reflects the documented behavior of a method, based on a round-trip consistency check."},
                {"role": "user", "content": revise_user}
            ]

            response_revise = self.prompt_executor.execute(revise_prompt).model_dump()
            history.append(copy.deepcopy(revise_prompt))
            history.append(response_revise)

            if not response_revise["choices"]:
                with open(errors_path, "a") as f:
                    f.write(f"round-trip {round_num}: error during test revision, keeping previous test ideas\n")
                break

            revised_test_list = self.extract_json_list(output_path, response_revise["choices"][0]["message"]["content"])

            if not revised_test_list:
                with open(errors_path, "a") as f:
                    f.write(f"round-trip {round_num}: revised test ideas could not be parsed, keeping previous test ideas\n")
                break

            test_list = revised_test_list

        return test_list, history

    def extract_comparison_json(self, output_path, response_text):
        # extract the comparison JSON object from a round-trip response, analogous to extract_json_list.
        errors_path = os.path.join(output_path, "errors.txt")
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", response_text, flags=re.DOTALL)

        if not json_blocks:
            bare = re.search(r'(\{.*\})', response_text, flags=re.DOTALL)
            if bare:
                json_blocks = [bare.group(1)]

        if not json_blocks:
            with open(errors_path, "a") as f:
                f.write(f"Could not extract JSON block from round-trip comparison response:\nResponse text:\n{response_text}")
            return None

        try:
            comparison = json.loads(json_blocks[0].strip())
        except json.JSONDecodeError as e:
            with open(errors_path, "a") as f:
                f.write(f"Could not parse round-trip comparison JSON: {e}\nResponse text:\n{response_text}")
            return None

        return comparison