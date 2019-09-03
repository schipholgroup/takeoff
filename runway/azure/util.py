from runway import ApplicationVersion
from runway.util import load_runway_plugins


def _get_naming_function(function_name, default: callable) -> callable:
    for plugin in load_runway_plugins().values():
        if hasattr(plugin, function_name):
            return getattr(plugin, function_name)
    return default


def default_naming(key):
    def _format(config: dict, env: ApplicationVersion):
        return config["azure"][key].format(env=env.environment_lower)

    return _format


def get_resource_group_name(config: dict, env: ApplicationVersion):
    f = _get_naming_function(
        "get_resource_group_name", default=default_naming("resource_group_naming")
    )
    return f(config, env)


def get_keyvault_name(config: dict, env: ApplicationVersion):
    f = _get_naming_function("get_keyvault_name", default=default_naming("keyvault_naming"))
    return f(config, env)


def get_cosmos_name(config: dict, env: ApplicationVersion):
    f = _get_naming_function("get_cosmos_name", default=default_naming("cosmos_naming"))
    return f(config, env)


def get_eventhub_name(config: dict, env: ApplicationVersion):
    f = _get_naming_function("get_eventhub_name", default=default_naming("eventhub_naming"))
    return f(config, env)


def get_kubernetes_name(config: dict, env: ApplicationVersion):
    f = _get_naming_function("get_kubernetes_name", default=default_naming("kubernetes_naming"))
    return f(config, env)
