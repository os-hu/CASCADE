import os
import re
import shutil
import tempfile

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.extraction.JavaExtraction import JavaExtraction

from cascade.generation.Generation import Generation
from cascade.utils.Utils import load_json_from_path, log, save_dicts_list_to_json

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class PrepareDatasetAnalysis(Analysis):
    def __init__(self, generator: Generation, executor: Execution, regenerate=False, reexecute=False, image="maven" , debug=0, step_size=1):
        super().__init__(generator, executor)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.debug = debug
        self.image = image

    def extract_junit_version(self, input_path, output_path):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                shutil.copytree(input_path, temp_dir, dirs_exist_ok=True)

            except Exception as e:
                print("could not copy root path")
                print(e)

            dock_ex = DockerizedWrapper(debug=0)

            # get the effective pom file, which usually contains the used junit version
            dock_context = {
                "image" : self.image,
                "directory" : temp_dir,
                "command" : "mvn help:effective-pom -Doutput=effective-pom.xml",
                "path" : "/root/effective-pom.xml"
            }

            dock_ex.execute(dock_context, output_path, copy=True)

        try:
            tree = ET.parse(os.path.join(output_path, "effective-pom.xml"))
            root = tree.getroot()

            # Define namespaces, if they exist in your pom.xml
            namespaces = {'m': 'http://maven.apache.org/POM/4.0.0'}  # Default Maven namespace

            # Initialize variables for return values
            junit_version = "JUnit dependency not found"
            source_dir = "Source directory not specified"
            test_source_dir = "Test source directory not specified"

            # Search for JUnit dependency
            for dependency in root.findall(".//m:dependency", namespaces):
                group_id = dependency.find("m:groupId", namespaces)
                artifact_id = dependency.find("m:artifactId", namespaces)
                if group_id is not None and artifact_id is not None:
                    if group_id.text == "junit" and artifact_id.text == "junit":
                        version = dependency.find("m:version", namespaces)
                        if version is not None:
                            junit_version = version.text
                        else:
                            junit_version = "Version not specified"

            # Extract source and test source directories
            build = root.find(".//m:build", namespaces)
            if build is not None:
                source_directory = build.find("m:sourceDirectory", namespaces)
                test_source_directory = build.find("m:testSourceDirectory", namespaces)

                if source_directory is not None:
                    source_dir = source_directory.text
                if test_source_directory is not None:
                    test_source_dir = test_source_directory.text

            # Return a 3-tuple with JUnit version, source directory, and test source directory
            return junit_version, source_dir, test_source_dir

        except ET.ParseError as e:
            return f"Error parsing pom.xml: {e}", None, None

    def analyse(self, data: list, input_path, output_path):
        """
        This is used to prepare the dataset for the main dataset analysis. It has to be run once if the dataset is freshly collected.
        """
        ana_path = os.path.join(output_path, "analyzed.json")
        data = load_json_from_path(ana_path)
        d = data[0]

        if "junit_version" not in d or "test_file_path" not in d:
            print(output_path)
            print("extracting Junit version")
            junit_version, source_dir, test_source_dir = self.extract_junit_version(input_path, output_path )
            print("Junit version: ", junit_version)

            if test_source_dir is not None and source_dir is not None:
                d["test_file_path"] = d["code_file_path"].replace(source_dir.replace("/root/" , ""), test_source_dir.replace("/root/" , ""))
                d["test_file_path"] = d["test_file_path"].replace(".java", "Test.java")
            else:
                d["test_file_path"] = d["code_file_path"].replace(".java", "Test.java")

            d["junit_version"] = junit_version
            save_dicts_list_to_json([d], ana_path)

            # basically a one step thing to run once over the dataset to provide all nesscary information. thats why we return here.
            return

        else:
            junit_version = d["junit_version"]

        test_class_real_name = d["test_file_path"].split("/")[-1].split(".")[0]
        test_class_unique_name = "THIS_IS_A_UNIQUE_NAME_Test"

        # found junit version in imports ?
        junit_found = False

        if not "test_package" in d:
            print("no original tests were found for this method")
            d["test_package"] = d["package"]

        else:
            for imp in d["test_imports"]:
                if "junit" in imp:
                    junit_found = True
                    break

        if not junit_found:
            if junit_version.startswith("3"):
                d["test_imports"] = ["import junit.framework.*;\n"]
            elif junit_version.startswith("4."):
                d["test_imports"] = ["import org.junit.*;\n" , "import static org.junit.Assert.*;\n"]
            else:
                d["test_imports"] = ["import org.junit.jupiter.api.*;\n"]

        save_dicts_list_to_json([d], ana_path)
