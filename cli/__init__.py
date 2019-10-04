import click

from cli import build_docker_image
from cli.util import extract_step, write_step


@click.group()
def main():
    pass


@click.group()
def step():
    pass


main.add_command(step)
step.add_command(build_docker_image)

if __name__ == "__main__":
    main()
