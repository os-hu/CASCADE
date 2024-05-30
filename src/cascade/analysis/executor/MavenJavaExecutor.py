from cascade.analysis.executor.JavaExecutor import JavaExecutor
from cascade.analysis.executor.builders.MavenBuilder import MavenBuilder


class MavenJavaExecutor(JavaExecutor):
    def __init__(self,
                 debug=False,
                 new_image_name="maven_modified",
                 maven_args="",
                 set_up_maven_command="dependency:go-offline",
                 set_up_maven_args="",
                 image="maven"
                 ):

        super().__init__(debug,
                         MavenBuilder(
                             new_image_name=new_image_name,
                             maven_args=maven_args,
                             image=image,
                             set_up_maven_command=set_up_maven_command,
                             set_up_maven_args=set_up_maven_args
                         ))
