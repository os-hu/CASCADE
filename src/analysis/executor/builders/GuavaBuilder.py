import ast
import re
import os
import subprocess

from src.analysis.executor.builders.Builder import Builder
from src.analysis.executor.builders.MavenBuilder import MavenBuilder
from src.utils.DockerizedWrapper import DockerizedWrapper


class GuavaBuilder(MavenBuilder):
    def __init__(self, new_image_name):
        super().__init__(new_image_name)
        self.new_image_name = new_image_name

    def set_up(self, temp_dir, _):
        wrapper = DockerizedWrapper(debug=True)
        dock_context = {
            "image": "maven",
            "new_image": self.new_image_name,
            "directory": temp_dir,
            "command": "mvn install -DskipTests; rm -rf ../root/*;",
        }
        wrapper.setup_image(dock_context)

#executor debug an    neuer filter dazu