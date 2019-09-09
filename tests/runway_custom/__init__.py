from runway.application_version import ApplicationVersion


def deploy_env_logic() -> ApplicationVersion:
    return ApplicationVersion("env", "v", "master")
