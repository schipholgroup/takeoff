from takeoff import schemas


def test_custom_ci_keys():
    conf = {
        "environment_keys": {
            "application_name": "CI_PROJECT_NAME",
            "branch_name": "CI_BRANCH"
        },
        "ci_environment_keys_acp": {
            "creds": {
                "username": "USERNAME"
            }
        }
    }
    schemas.TAKEOFF_BASE_SCHEMA(conf)
