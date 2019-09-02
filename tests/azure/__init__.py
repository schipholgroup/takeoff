import yaml


def runway_config():
    with open('tests/test_runway_config.yaml', 'r') as f:
        return yaml.safe_load(f.read())
