from runway import ApplicationVersion
from runway.util import load_runway_plugins


def get_resource_group_name(config: dict, env: ApplicationVersion):
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, "get_resource_group_name"):
            return plugin.get_resource_group_name(config, env)
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
