from pyspark_streaming_deployment import deploy_to_databricks as victim

jobs = [
    victim.JobConfig('foo-SNAPSHOT', 1),
    victim.JobConfig('bar-0.3.1', 2),
    victim.JobConfig('foobar-0.0.2', 3),
    victim.JobConfig('barfoo-0.0.2', 4),
]


def test_find_application_job_id_if_snapshot():
    assert victim.__application_job_id('foo', jobs) == 1


def test_find_application_job_id_if_version():
    assert victim.__application_job_id('bar', jobs) == 2


def test_is_streaming_job():
    job_config = victim.__construct_job_config(
        fn='tests/test_job_config.json',
        name='app',
        version='42',
        dtap='whatevs',
        egg='some.egg',
        python_file='some.py',
    )
    assert victim._job_is_streaming(job_config) is True

    job_config = victim.__construct_job_config(
        fn='tests/test_job_config_scheduled.json',
        name='app',
        version='42',
        dtap='whatevs',
        egg='some.egg',
        python_file='some.py',
    )
    assert victim._job_is_streaming(job_config) is False


def test_construct_job_config():
    job_config = victim.__construct_job_config(
        fn="tests/test_job_config.json",
        name="app",
        version="42",
        dtap="whatevs",
        egg="some.egg",
        python_file="some.py",
    )

    assert {"name": "app-42",
            "libraries": [
                {'jar': 'some.jar'},
                {'egg': 'some.egg'},
            ],
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": '/some_whatevs',
                    "some.setting": "true"
                },
                "cluster_log_conf": {
                    "dbfs": {
                        "destination": "dbfs:/mnt/sdhwhatevs/logs/app"
                    }
                }
            },
            "some_int": 5,
            "spark_python_task": {
                "python_file": "some.py"
            }
            } == job_config
