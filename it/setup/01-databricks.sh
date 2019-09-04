#!/usr/bin/env bash

echo "============================================"
echo "== Configure Databricks API \"jobs/list\" =="
echo "============================================"

curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/list",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    }
  },
  "httpResponseTemplate": {
    "template": "body = JSON.stringify(
     {
       jobs: [
         {
           job_id: 1,
           settings: {
             name: 'takeoff-integration-tests'
           },
           created_time: 1557997134925,
           creator_user_name: 'creator of takeoff-integration-tests'
         },
         {
           job_id: 2,
           settings: {
             name: 'appname-some-branch'
           },
           created_time: 1557997134925,
           creator_user_name: 'creator of appname-some-branch'
         }
       ]
     }
    );
    return {
        statusCode: 200,
        headers: {
            'content-type': ['application/json']
        },
        body: body
    };",
    "templateType": "JAVASCRIPT"
  }
}
_EOF

echo "================================================="
echo "== Configure Databricks API \"jobs/runs/list\" =="
echo "================================================="

curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/runs/list",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    },
    "body": "{\"job_id\": 1, \"active_only\": true}"
  },
  "httpResponseTemplate": {
    "template": "body = JSON.stringify(
     {
      runs: [
      {
        job_id: 1,
        run_id: 42,
        number_in_job: 18,
        state: {
          life_cycle_state: 'RUNNING',
          state_message: 'Performing action'
        },
        task: {
          notebook_task: {
            notebook_path: '/Users/donald@duck.com/my-notebook'
          }
        },
        cluster_spec: {
          existing_cluster_id: '1201-my-cluster'
        },
        cluster_instance: {
          cluster_id: '1201-my-cluster',
          spark_context_id: '1102398-spark-context-id'
        },
        overriding_parameters: {
          jar_params: ['param1', 'param2']
        },
        start_time: 1457570074236,
        setup_duration: 259754,
        execution_duration: 3589020,
        cleanup_duration: 31038,
        trigger: 'PERIODIC'
      }
      ]
      }
    );
    return {
        statusCode: 200,
        headers: {
            'content-type': ['application/json']
        },
        body: body
    };",
    "templateType": "JAVASCRIPT"
  }
}
_EOF



echo "===================================================="
echo "== Configure Databricks API \"/jobs/runs/cancel\" =="
echo "===================================================="

curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/runs/cancel",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    },
    body: {
      "type" : "JSON",
      "json": "{\"run_id\": 42}",
      "matchType": "ONLY_MATCHING_FIELDS"
    }
  },
  "httpResponse" : {
    "statusCode" : 200,
    "headers": {
        "Content-Type": ["application/json"]
    },
    "body": "{}"
  }
}
_EOF

echo "===================================================="
echo "== Configure Databricks API \"/jobs/delete\" =="
echo "===================================================="

curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/delete",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    },
    body: {
      "type" : "JSON",
      "json": "{\"job_id\": 1}",
      "matchType": "ONLY_MATCHING_FIELDS"
    }
  },
  "httpResponse" : {
    "statusCode" : 200,
    "headers": {
        "Content-Type": ["application/json"]
    },
    "body": "{}"
  }
}
_EOF
echo "==============================================="
echo "== Configure Databricks API \"/jobs/create\" =="
echo "==============================================="

# Mock result for api/2.0/jobs/list endpoint
curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/create",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    },
    body: {
      "type" : "JSON",
      "json": "{\"name\": \"takeoff-integration-tests\", \"new_cluster\": {\"spark_version\": \"5.2.x-scala2.11\", \"node_type_id\": \"Standard_DS4_v2\", \"spark_conf\": {\"spark.sql.warehouse.dir\": \"dbfs:/data/\", \"spark.sql.hive.metastore.jars\": \"builtin\", \"spark.sql.hive.metastore.version\": \"1.2.1\"}, \"spark_env_vars\": {\"PYSPARK_PYTHON\": \"/databricks/python3/bin/python3\"}, \"num_workers\": 1}, \"max_retries\": 5, \"libraries\": [{\"whl\": \"dbfs://libraries/takeoff/takeoff-integration_tests-py3-none-any.whl\"}], \"spark_python_task\": {\"python_file\": \"dbfs://libraries/takeoff/takeoff-main-integration_tests.py\", \"parameters\": [\"--database\", \"dave\", \"--table\", \"mustaine\"]}}",
      "matchType": "ONLY_MATCHING_FIELDS"
    }
  },
  "httpResponse" : {
    "statusCode" : 200,
    "headers": {
        "Content-Type": ["application/json"]
    },
    "body": "{\"job_id\": 1}"
  }
}
_EOF

echo "================================================"
echo "== Configure Databricks API \"/jobs/run-now\" =="
echo "================================================"

# Mock result for api/2.0/jobs/list endpoint
curl -v -X PUT "http://localhost:80/mockserver/expectation" -d @- <<_EOF
{
  "httpRequest": {
    "path": "/api/2.0/jobs/run-now",
    "headers": {
        "Content-Type": ["text/json"],
        "Authorization": ["Bearer .*"]
    },
    body: {
      "type" : "JSON",
      "json": "{\"job_id\": 1}",
      "matchType": "ONLY_MATCHING_FIELDS"
    }
  },
  "httpResponse" : {
    "statusCode" : 200,
    "headers": {
        "Content-Type": ["application/json"]
    },
    "body": "{\"run_id\": 43}"
  }
}
_EOF
