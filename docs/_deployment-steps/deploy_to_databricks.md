---
layout: page
title: Databricks jobs
date: 2019-09-13
summary: Deploy a streaming or batch job to Databricks
permalink: deployment-step/databricks-job
category: Databricks
---

# Deploy to Databricks

Deploys a [streaming or batch job to Databricks](https://docs.databricks.com/user-guide/jobs.html). In the process, if there 
was already an old version of the job running, this will shut down the old job and deploy the new version.

Most often is used in combination with [Deploy artifacts to Azure Blob](upload-to-blob), as this is where the jar or whl and `main.py` file
will be fetched from. This assumes Databricks has access to Azure blob to fetch these artifacts from. This should be after 
the [upload_to_blob](upload-to-blob) task if used together

## Deployment
Add the following task to ``deployment.yaml``:

```yaml
- task: deploy_to_databricks
  jobs:
  - main_name: "main.py"
    config_file: databricks.json.j2
    lang: python
    name: foo
    arguments:
    - eventhubs.consumer_group: "my-consumer-group"
```


{:.table}
| field | description | value
| ----- | ----------- 
| `jobs` | A list of job configurations | Must have at least one job |
| `jobs[].main_name` | When `lang` is `python` must be the path to the python main file. When `lang` is `scala` it must be a class name | For `python`: `main/main.py`, for `scala`: `com.databricks.ComputeModels`.
| `jobs[].config_file` | The path to a `json` [jinja templated](http://jinja.pocoo.org/) [Databricks job config](https://docs.databricks.com/api/latest/jobs.html#create) | defaults to `databricks.json.j2`
| `jobs[].name` (optional) | A postfix to identify your job on Databricks | A postfix of `foo` will name your job `application-name_foo-version`. Defaults to no postfix. This will name all the jobs (if you have multiple) the same.
| `jobs[].lang` (optional) | The language identifier of your project | One of `python`, `scala`, defaults to `python`
| `jobs[].arguments` (optional) | Key value pairs to be passed into your project | defaults to no arguments


The `json` file can use any of [supported keys](https://docs.databricks.com/api/latest/jobs.html#request-structure). 
During deployment the existence of the key `schedule` in the `json` file will determine if the job is streaming or batch. 
When `schedule` is present it is considered a batch job, otherwise a streaming job. A streaming job will be kicked off 
immediately upon deployment. A batch job will not.

An example of `databricks.json.pyspark.j2` 

```
{
  "name": "{% raw %}{{ application_name }}{% endraw %}",
  "new_cluster": {
    "spark_version": "4.3.x-scala2.11",
    "node_type_id": "Standard_DS4_v2",
    "spark_conf": {
      "spark.sql.warehouse.dir": "dbfs:/mnt/sdh/data/raw/managedtables",
      "spark.databricks.delta.preview.enabled": "true",
      "spark.sql.hive.metastore.jars": "builtin",
      "spark.sql.execution.arrow.enabled": "true",
      "spark.sql.hive.metastore.version": "1.2.1"
    },
    "spark_env_vars": {
      "PYSPARK_PYTHON": "/databricks/python3/bin/python3"
    },
    "num_workers": 1,
    "cluster_log_conf": {
      "dbfs": {
        "destination": "dbfs:/mnt/sdh/logs/{% raw %}{{ log_destination }}{% endraw %}"
      }
    }
  },
  "max_retries": 5,
  "libraries": [
    { 
      "egg": "{% raw %}{{ egg_file }}{% endraw %}"
    }
  ],
  "spark_python_task": {
    "python_file": "{% raw %}{{ python_file }}{% endraw %}",
    "parameters": {% raw %} {{ parameters | tojson }} {% endraw %}
  }
}
```

An explanation for the Jinja templated values. These values get resolved automatically during deployment.

{:.table}
| field | description 
| ----- | ----------- 
| `application_name` | `your-git-repo-version` (e.g. `flights-prediction-SNAPSHOT`)
| `log_destination` | `your-git-repo` (e.g. `flights-prediction`)
| `egg_file` | The location of the egg file uploaded by the task [upload_to_blob](upload-to-blob)
| `python_file` | The location the python main file uploaded by the task [upload_to_blob](upload-to-blob)

An example of `databricks.json.scalaspark.j2` 

```
{
  "name": "{% raw %}{{ application_name }}{% endraw %}",
  "new_cluster": {
    "spark_version": "4.3.x-scala2.11",
    "node_type_id": "Standard_DS4_v2",
    "spark_conf": {
      "spark.sql.warehouse.dir": "dbfs:/mnt/sdh/data/raw/managedtables",
      "spark.databricks.delta.preview.enabled": "true",
      "spark.sql.hive.metastore.jars": "builtin",
      "spark.sql.execution.arrow.enabled": "true",
      "spark.sql.hive.metastore.version": "1.2.1"
    },
    "spark_env_vars": {
      "PYSPARK_PYTHON": "/databricks/python3/bin/python3"
    },
    "num_workers": 1,
    "cluster_log_conf": {
      "dbfs": {
        "destination": "dbfs:/mnt/sdh/logs/{% raw %}{{ log_destination }}{% endraw %}"
      }
    }
  },
  "max_retries": 5,
  "libraries": [
    { 
      "jar": "{% raw %}{{ jar_file }}{% endraw %}"
    }
  ],
  "spark_jar_task": {
    "main_class_name": "{% raw %}{{ class_name }}{% endraw %}",
    "parameters": {% raw %} {{ parameters | tojson }} {% endraw %}
  }
}
```

An explanation for the Jinja templated values. These values get resolved automatically during deployment.

{:.table}
| field | description 
| ----- | ----------- 
| `application_name` | `your-git-repo-version` (e.g. `flights-prediction-SNAPSHOT`)
| `log_destination` | `your-git-repo` (e.g. `flights-prediction`)
| `jar_file` | The location of the jar file uploaded by the task [upload_to_blob](upload-to-blob)
| `class_name` | The class in the jar that should be ran

## Takeoff config
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:

  ```yaml
  azure_storage_account:
    account_name: "azure-shared-blob-username"
    account_key: "azure-shared-blob-password"
  ```
  
and these `takeoff_common` keys:
  ```yaml
  artifacts_shared_blob_container_name: libraries
  ```

