import ast
import json
import subprocess

from src.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from src.analysis.executor.JavaExecutor import JavaExecutor
from src.analysis.executor.builders.GuavaBuilder import GuavaBuilder
from src.analysis.executor.builders.MavenBuilder import MavenBuilder
from src.utils.DockerizedWrapper import DockerizedWrapper

import os
import tempfile
import shutil


class GuavaJavaExecutor(JavaExecutor):
    def __init__(self, debug=False, new_image_name="maven_modified"):
        super().__init__(debug, GuavaBuilder(new_image_name=new_image_name))
