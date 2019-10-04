import os
import pprint

import click
import yaml

FILE = ".takeoff/deployment.yml"

if not os.path.isfile(FILE):
    with open(FILE, 'a') as f:
        os.utime(FILE, None)


def load_yaml():
    with open(FILE, 'r') as f:
        deployment = yaml.load(f, Loader=yaml.FullLoader)
        return {} if not deployment else deployment


def extract_step(task):
    deployment = load_yaml()
    if "steps" in deployment:
        for i, tsk in enumerate(deployment["steps"]):
            if tsk["task"] == task:
                return tsk
    return {}


def write_step(task):
    deployment = load_yaml()
    if "steps" in deployment:
        for i, tsk in enumerate(deployment["steps"]):
            if tsk["task"] == task["task"]:
                deployment["steps"][i] = task
    else:
        deployment["steps"] = []
        deployment["steps"].append(task)
    with open(FILE, 'w') as f:
        yaml.dump(deployment, f)


@click.group()
def main():
    pass


@click.group()
def step():
    pass


@click.group()
def build_docker_image():
    pass


@build_docker_image.command()
def show():
    click.echo(click.style("Current configuration", fg='green'))
    click.echo(pprint.pformat(extract_step("build_docker_image")))


@build_docker_image.command()
def add():
    current = extract_step("build_docker_image")
    if current == {}:
        current = {"task": "build_docker_image"}
    write_step(current)


@build_docker_image.command()
@click.option("--file", default="Dockerfile")
@click.option("--postfix", default=None)
@click.option("--custom_image_name", default=None)
def add_docker_file(file, postfix, custom_image_name):
    d = {}
    if file:
        d.update({"file": file})
    if postfix:
        d.update({"postfix": postfix})
    if custom_image_name:
        d.update({"custom_image_name": custom_image_name})

    current = extract_step("build_docker_image")
    new = {"task": "build_docker_image"}

    if "dockerfiles" not in current:
        current["dockerfiles"] = []
    new.update({"dockerfiles": current["dockerfiles"] + [d]})

    write_step(new)
    click.echo(click.style("New configuration", fg='green'))
    click.echo(pprint.pformat(new))


main.add_command(step)
step.add_command(build_docker_image)
build_docker_image.add_command(add)
build_docker_image.add_command(show)
build_docker_image.add_command(add_docker_file)

if __name__ == "__main__":
    main()
