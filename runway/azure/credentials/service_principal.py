import http.client
import logging

from msrestazure.azure_active_directory import ServicePrincipalCredentials as SpCredentials

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename, _in_dev_mode

# Debug logging
http.client.HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
req_log = logging.getLogger('requests.packages.urllib3')
req_log.setLevel(logging.DEBUG)
req_log.propagate = True


class ServicePrincipalCredentials(EnvironmentCredentialsMixin):
    def credentials(self, config, env) -> SpCredentials:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config[f"ci_environment_keys_{env}"][current_filename(__file__)]
        )
        logging.info(credential_kwargs)
        return SpCredentials(**credential_kwargs, verify=_in_dev_mode())
