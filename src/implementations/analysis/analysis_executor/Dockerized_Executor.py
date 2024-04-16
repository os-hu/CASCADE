import docker
import tarfile
import io

from docker.models.containers import Container

from src.abstract_classes.Analysis_Executor import Analysis_Executor, succeeded, failed, errored


class Dockerized_Executor(Analysis_Executor):
    def __init__(self):
        pass


    """
    This executor creates a docker container for the prepared tests directory, copies the directory into the docker,
    executes the test command, then executes an evaluation command, and lastly kills and removes the container.
    
    This executor only works if context contains: image, directory, command, eval_function and eval_command
    
    image - image is the docker image to run
    directory - the prepared directory which contains everything to execute the test case
    command - the command which executes the actual test case
    eval_command - a command which returns information on the executed test cases
    eval_function - a function which parses the output of the eval_command into succeeded, failed, errored
    
    """
    def execute(self, code: str, tests: str, context: dict) -> (succeeded, failed, errored):
        container = self.setup(context)
        self.run(container, context)
        succeeded, failed, errored = self.eval(container, context)
        self.kill(container)
        return succeeded, failed, errored

    def setup(self, context: dict):
        client = docker.from_env()
        container = client.containers.run(context["image"], "tail -f /dev/null", detach=True)
        buffer = io.BytesIO()
        with tarfile.open(mode="w", fileobj=buffer) as tar:
            tar.add(context["directory"])
        container.put_archive("/root/", buffer)
        return container

    def run(self, container: Container, context: dict):
        container.exec_run("cd ~; " + context["command"])

    def eval(self, container: Container, context: dict):
        return context["eval_function"](container.exec_run('bash -c - "cd ~; ' + context["eval_command"] + '"').output)

    def kill(self, container: Container):
        container.kill()
        container.remove()
