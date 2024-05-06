import ast
import json
import subprocess

from src.analysis.executor.AnalysisExecutor import AnalysisExecutor, succeeded, failed, errored
from src.analysis.executor.JavaExecutor import JavaExecutor
from src.analysis.executor.builders.MavenBuilder import MavenBuilder
from src.utils.DockerizedWrapper import DockerizedWrapper

import os
import tempfile
import shutil


class MavenJavaExecutor(JavaExecutor):
    def __init__(self, debug=False):
        super().__init__(debug, MavenBuilder())
