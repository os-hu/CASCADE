from cascade.analysis.executor.JavaExecutor import JavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder

import uuid

class MavenJavaExecutor(JavaExecutor):
    def __init__(self, debug=False, maven_args="", set_up_maven_command="test", set_up_maven_args="", image="maven"):

        image_name_id = str(uuid.uuid4())

        standard_java_args = " -fae -Drat.skip=true -DforkMode=never -Dsurefire.failIfNoSpecifiedTests=false"
        if maven_args == "":
            maven_args = standard_java_args
        if set_up_maven_args == "":
            set_up_maven_args = standard_java_args

        super().__init__(debug,
                         MavenBuilder(
                             new_image_name=image_name_id,
                             maven_args=maven_args,
                             image=image,
                             set_up_maven_command=set_up_maven_command,
                             set_up_maven_args=set_up_maven_args
                         ))
