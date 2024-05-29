#TODO DEPRECATED   DELETE

import ast
import re
import os
import subprocess

from src.analysis.executor.builders.Builder import Builder
from src.analysis.executor.builders.MavenBuilder import MavenBuilder
from src.utils.DockerizedWrapper import DockerizedWrapper


class GuavaBuilder(MavenBuilder):
    def __init__(self, new_image_name, maven_args="", set_up_maven_args="", image="maven"):
        super().__init__(new_image_name, maven_args, set_up_maven_args, image)

    def set_up(self, temp_dir, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "image": "maven",
            "new_image": self.image,
            "directory": temp_dir,
            "command": f"mvn install -DskipTests {self.set_up_maven_args}; rm -rf ../root/*;",
        }
        wrapper.setup_image(dock_context)

