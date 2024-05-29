#TODO DEPRECATED   DELETE

from src.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from src.analysis.executor.JavaExecutor import JavaExecutor
from src.analysis.executor.builders.GuavaBuilder import GuavaBuilder
from src.analysis.executor.builders.MavenBuilder import MavenBuilder
from src.utils.DockerizedWrapper import DockerizedWrapper

import os
import tempfile
import shutil


class GuavaJavaExecutor(JavaExecutor):
    def __init__(self, debug=False, new_image_name="maven_modified", maven_args="", set_up_maven_args="", image="maven"):
        super().__init__(debug, GuavaBuilder(new_image_name=new_image_name, maven_args=maven_args, image=image, set_up_maven_args=set_up_maven_args))
