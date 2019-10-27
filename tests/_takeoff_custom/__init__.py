from takeoff.application_version import ApplicationVersion


def deploy_env_logic(config: dict) -> ApplicationVersion:
    return ApplicationVersion("env", "v", "master")
