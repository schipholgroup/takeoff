from runway.ApplicationVersion import ApplicationVersion


def dap() -> ApplicationVersion:
    return ApplicationVersion("env", "v", "master")
