import pprint

import click

from cli import build_docker_image
from cli.util import load_yaml


@click.group()
def main():
    pass


@click.group()
def step():
    pass


@step.command()
def show():
    pprint.pprint(load_yaml())


main.add_command(step)
step.add_command(build_docker_image.build_docker_image)

if __name__ == "__main__":
    main()
