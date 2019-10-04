import pprint

import click

from cli.util import write_step, extract_step, __add


@click.group()
def build_docker_image():
    pass


@build_docker_image.command()
def show():
    click.echo(click.style("Current configuration", fg='green'))
    click.echo(pprint.pformat(extract_step("build_docker_image")))


@build_docker_image.command()
def add():
    __add("build_docker_image")


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


build_docker_image.add_command(add)
build_docker_image.add_command(show)
build_docker_image.add_command(add_docker_file)
