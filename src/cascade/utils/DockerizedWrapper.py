import os.path
from unittest.mock import open_spec

import docker
import tarfile
import io

from docker.models.containers import Container

from cascade.analysis.executor.AnalysisExecutor import succeeded, failed, errored


class DockerizedWrapper:
    """
    This executor creates a docker container for the prepared tests directory, copies the directory into the docker,
    executes the test command, then executes an evaluation command, and lastly kills and removes the container.

    This executor only works if context contains: image, directory, command, eval_function and eval_command

    image - image is the docker image to run

    directory - the prepared directory which contains everything to execute the test case, it will be copied into /root/

    command - the command which executes the actual test case

    eval_command - a command which returns information on the executed test cases

    eval_function - a function which parses the output of the eval_command into succeeded, failed, errored

    """

    def __init__(self, debug=False):
        self.debug=debug
        pass

    def execute(self, context: dict, output_path: str) -> (succeeded, failed, errored):
        container = None
        try:
            container = self.setup(context)
            self.run(container, context, output_path)
            succeeded, failed, errored = self.eval(container, context, output_path)
        finally:
            if container:
                self.kill(container)

        return succeeded, failed, errored

    def setup_image(self, context: dict, output_path: str):
        container = None
        client = docker.from_env(timeout=240)
        images = client.images.list(context["new_image"])
        exit_code = False
        try:
            if images:
                self.remove_image(context)
            container = self.setup(context)
            exit_code = self.run(container, context, output_path)
            container.commit(context["new_image"])
        finally:
            if not images and container:
                self.kill(container)
            return exit_code

    def remove_image(self, context: dict):
        client = docker.from_env(timeout=240)
        try:
            client.images.remove(context["new_image"], force=True)
        except Exception as e:
            print(f"Could not remove image because of Exception: {e}")

    def setup(self, context: dict):
        client = docker.from_env(timeout=240)
        container = client.containers.run(context["image"], "tail -f /dev/null", detach=True)
        buffer = io.BytesIO()
        with tarfile.open(mode="w", fileobj=buffer) as tar:
            tar.add(context["directory"], arcname="")
        buffer.seek(0)
        container.put_archive("/root/", buffer)
        return container

    def run(self, container: Container, context: dict, path):
        res = container.exec_run('bash -c - "cd ~; ' + context["command"].replace('"', "\\\"") + '"')
        with open(os.path.join(path, "log.txt"), "a") as file:
            file.write("Command: " + context["command"] + "\n")
            file.write(str(res.exit_code) + "\n")
            file.write(str(res.output, "utf-8") + "\n")
        if self.debug:
            print("Command:", context["command"])
            print(res.exit_code)
            print(str(res.output, "utf-8"))
        return res.exit_code == 0

    def eval(self, container: Container, context: dict, path) -> (succeeded, failed, errored):
        res = container.exec_run('bash -c - "cd ~; ' + context["eval_command"].replace('"', "\\\"") + '"')
        with open(os.path.join(path, "log.txt"), "a") as file:
            file.write("Eval Command: " + context["eval_command"] + "\n")
            file.write(str(res.exit_code) + "\n")
            file.write(str(res.output, "utf-8") + "\n")
        if self.debug:
            print(res.exit_code)
            print(str(res.output, "utf-8"))
        return context["eval_function"](str(res.output, "utf-8"))

    def kill(self, container: Container):
        container.kill()
        container.remove()
