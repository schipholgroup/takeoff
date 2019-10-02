from takeoff.application_version import ApplicationVersion


def deploy_env_logic(config) -> ApplicationVersion:
    return ApplicationVersion("env", "v", "master")
