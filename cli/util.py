import os

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


def __add(step, defaults: dict = {}):
    current = extract_step(step)
    if current == {}:
        current = {"task": step, **defaults}
    write_step(current)
