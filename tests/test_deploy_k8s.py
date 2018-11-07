import unittest

from sdh_deployment.deploy_to_k8s import DeployToK8s as victim


class TestDeployToK8s(unittest.TestCase):

    def test_k8s_resource_exists(self):
        haystack = {
            'items': [
                {
                    'metadata': {
                        'name': 'my-needle'
                    }
                }
            ]
        }
        needle = 'my-needle'

        self.assertTrue(victim._find_needle(needle, haystack))

    def test_k8s_resource_does_not_exist(self):
        haystack = {
            'items': [
                {
                    'metadata': {
                        'name': 'my-needle'
                    }
                }
            ]
        }
        needle = 'my-unfindable-needle'

        self.assertFalse(victim._find_needle(needle, haystack))
