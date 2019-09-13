from typing import Callable

from takeoff.application_version import ApplicationVersion
from takeoff.util import load_takeoff_plugins


def _get_naming_function(function_name: str, default: Callable) -> Callable:
    """Find the right naming function

    Args:
        function_name: the name of the Takeoff plugin function to search for
        default: A default naming function

    Returns:
        A function that maps the Takeoff config and application version to the resource name. If
        a plugin was found it returns that function, otherwise the `default` provided.
    """
    for plugin in load_takeoff_plugins().values():
        if hasattr(plugin, function_name):
            return getattr(plugin, function_name)
    return default


def default_naming(key: str) -> Callable[[dict, ApplicationVersion], str]:
    """The default naming convention

    Args:
        The fieldname in `.takeoff/config.yml` under `azure:` containing the
        naming rule.

    Returns:
        A function that maps the Takeoff config and application version to the resource name
    """

    def _format(config: dict, env: ApplicationVersion):
        return config["azure"][key].format(env=env.environment_formatted)

    return _format


def get_resource_group_name(config: dict, env: ApplicationVersion) -> str:
    """Returns the resource group name

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version

    Returns:
        The resource group name
    """
    f = _get_naming_function("get_resource_group_name", default=default_naming("resource_group_naming"))
    return f(config, env)


def get_keyvault_name(config: dict, env: ApplicationVersion) -> str:
    """Returns the KeyVault name

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version
    """
    f = _get_naming_function("get_keyvault_name", default=default_naming("keyvault_naming"))
    return f(config, env)


def get_cosmos_name(config: dict, env: ApplicationVersion) -> str:
    """Returns the Cosmos service name.

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version
    """
    f = _get_naming_function("get_cosmos_name", default=default_naming("cosmos_naming"))
    return f(config, env)


def get_eventhub_name(config: dict, env: ApplicationVersion) -> str:
    """Returns the Eventhub namespace name

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version
    """
    f = _get_naming_function("get_eventhub_name", default=default_naming("eventhub_naming"))
    return f(config, env)


def get_eventhub_entity_name(eventhub_entity_naming: str, env: ApplicationVersion) -> str:
    """Returns the Eventhub entity name

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version
    """

    def _format(naming: str, env: ApplicationVersion) -> str:
        return naming.format(env=env.environment_formatted)

    f = _get_naming_function("get_eventhub_entity_name", default=_format)
    return f(eventhub_entity_naming, env)


def get_kubernetes_name(config: dict, env: ApplicationVersion) -> str:
    """Returns the Kubernetes service name

    If no plugin is provided this uses the default naming convention (as specified in
    the `.takeoff/config.yml`) and resolves the `{env}` parameter based on the ApplicationVersion.

    Args:
        config: The Takeoff config
        env: The application version
    """
    f = _get_naming_function("get_kubernetes_name", default=default_naming("kubernetes_naming"))
    return f(config, env)
