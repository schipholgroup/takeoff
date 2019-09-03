import inspect

from runway import ApplicationVersion
from runway.util import load_runway_plugins


def _get_plugin_function():
    caller = inspect.stack()[2][3]
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, caller):
            return getattr(plugin, caller)
    return None


def get_resource_group_name(config: dict, env: ApplicationVersion):
    f = _get_plugin_function()
    if f:
        f(config, env)
    return config["azure"]["resource_group_naming"].format(env=env.environment_lower)


def get_keyvault_name(config: dict, env: ApplicationVersion):
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, "get_keyvault_name"):
            return plugin.get_keyvault_name(config, env)
    return config["azure"]["keyvault_naming"].format(env=env.environment_lower)


def get_cosmos_name(config: dict, env: ApplicationVersion):
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, "get_cosmos_name"):
            return plugin.get_cosmos_name(config, env)
    return config["azure"]["cosmos_naming"].format(env=env.environment_lower)


def get_eventhub_name(config: dict, env: ApplicationVersion):
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, "get_eventhub_name"):
            return plugin.get_eventhub_name(config, env)
    return config["azure"]["eventhub_naming"].format(env=env.environment_lower)


def get_kubernetes_name(config: dict, env: ApplicationVersion):
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, "get_kubernetes_name"):
            return plugin.get_kubernetes_name(config, env)
    return config["azure"]["kubernetes_naming"].format(env=env.environment_lower)
