#!/usr/bin/env bash

echo "================================================"
echo "== Configure Microsoft API 'common/UserRealm' =="
echo "================================================"

curl -v -X PUT "http://localhost:1080/mockserver/expectation" -d @- <<_EOF_
{
  "httpRequest": {
    "path": "/common/UserRealm/.*",
    "queryStringParameters" : {
	  "api-version" : [ "1.0" ]
	}
  },
  "httpResponse": {
    "statusCode": 200,
    "headers": {
      "content-type": [
        "application/json"
      ]
    },
    "body": {
      "type": "JSON",
      "json": "{
        \"ver\": \"1.0\",
        \"account_type\": \"Managed\",
        \"domain_name\": \"snbv.onmicrosoft.com\",
        \"cloud_instance_name\": \"microsoftonline.com\",
        \"cloud_audience_urn\": \"urn:federation:MicrosoftOnline\"
      }"
    }
  }
}
_EOF_


curl -v -X PUT "http://localhost:1080/mockserver/expectation" -d @- <<_EOF_
{
  "httpRequest": {
    "method": "POST",
    "path": "/some-fake-tenant/oauth2/token",
    "body": {
      "type": "REGEX",
      "regex": "grant_type=client_credentials.*"
    }
  },
  "httpResponse": {
    "statusCode": 200,
    "headers": {
      "content-type": [
        "application/json"
      ]
    },
    "body": {
      "type": "JSON",
      "json": "{
        \"token_type\": \"Bearer\",
        \"scope\": \"user_impersonation\",
        \"expires_in\": \"3599\",
        \"ext_expires_in\": \"3599\",
        \"expires_on\": \"1660000000\",
        \"not_before\": \"1560000000\",
        \"resource\": \"https://management.core.windows.net/\",
        \"access_token\": \"eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkN0ZlFDOExlLThOc0M3b0MyelFrWnBjcmZPYyIsImtpZCI6IkN0ZlFDOExlLThOc0M3b0MyelFrWnBjcmZPYyJ9.eyJhdWQiOiJodHRwczovL2RhdGFsYWtlLmF6dXJlLm5ldC8iLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC8yNzc3Njk4Mi1kODgyLTQxYjItOTVhYy0zMjJmMjhkNWEyY2UvIiwiaWF0IjoxNTYwODYzMzk3LCJuYmYiOjE1NjA4NjMzOTcsImV4cCI6MTU2MDg2NzI5NywiYWNyIjoiMSIsImFpbyI6IkFTUUEyLzhMQUFBQXc3bk5QNlVmdVFMMGtjcTVrU1F6M1h6RCtoUGZzanY4cWxHOWdmd0F3N009IiwiYW1yIjpbInB3ZCJdLCJhcHBpZCI6IjA0YjA3Nzk1LThkZGItNDYxYS1iYmVlLTAyZjllMWJmN2I0NiIsImFwcGlkYWNyIjoiMCIsImZ3ZCI6Ijc3LjI0MS4yMjkuMjQ2IiwiaXBhZGRyIjoiNzcuMjQxLjIyOS4yNDYiLCJuYW1lIjoiX3N2Y19zbmJ2YXowMTZfc2RoX3ZzdHNkZXYiLCJvaWQiOiJhMzVmOTcwNS0xNDhhLTQxNjMtYTljMC1lYmE4M2U4OTk2NTkiLCJwdWlkIjoiMTAwMzNGRkZBRDAyMTUzRCIsInNjcCI6InVzZXJfaW1wZXJzb25hdGlvbiIsInN1YiI6InlXQnlsLVpOUHNpRXJIZzlFMFhndXl0VWFUSEdmTkRlc05WWlZTTlZqT0EiLCJ0aWQiOiIyNzc3Njk4Mi1kODgyLTQxYjItOTVhYy0zMjJmMjhkNWEyY2UiLCJ1bmlxdWVfbmFtZSI6Il9zdmNfc25idmF6MDE2X3NkaF92c3RzZGV2QHNuYnYub25taWNyb3NvZnQuY29tIiwidXBuIjoiX3N2Y19zbmJ2YXowMTZfc2RoX3ZzdHNkZXZAc25idi5vbm1pY3Jvc29mdC5jb20iLCJ1dGkiOiIwbVFPaWdicnJFeXRGa1F6a1VVaUFBIiwidmVyIjoiMS4wIn0.WBgyxvaQ_Sm9OK4FyoLIc5C7Z4ofQOPOZnF2mf0hefWlryBDb1Q4e4UtNosifG_Kl8VQzlzMzzgD6uoL9ANL4HuBjxilgg-Ay0jqZs2glnJSYejwBKkOTa-_gzG9pKjabd44p8O_3aFiJb1ES54j_DBeeowPWcBJKJ6fzij1g2KJRtZ3AviImlniPHLZYqJj4DkOdQWlDwyZwhCLVS_Sy3XJ7op7XyIVVYNtIzHgkeB2sUAmUZCNCmxghe65aEpg_3hmTdedqmwMAP7QjBR_O5JRoCNqu5DeRaWO7urQM_WbExbkphhMP6skuSAm_q7UglB-cNWD7BCol-wx5CAaxQ\",
        \"refresh_token\": \"AQABAAAAAADCoMpjJXrxTq9VG9te-7FXvXwYFZq7V6xJwwvYS3BGisUcsS8zSWca9Tip9KS-HDg670h03-RXRCMKn0ioTZzwCG4qOoiXY_ybvgPs1QE8ktWUBaAyhsdopG92m9AhIbAmV6kR2LSiPIKN2gTPx1juxbtMHKSl9XsXW8s0FXQzUiOAzW9VCzoXHc1E9ipcGr-O42Ti-peXOH9oNuQIfrqlCkqliwaiNkSyHzOHtCzxTyp1BHaQXN0A2emLpmLBgLdSQhEKCsJv3ti_UQMIvas_XhPTcmWu5SBCLeRwcSdL-54pn0_2j7FwhQy4UkZDGNvRvW7PcS83-6KV9YBjnWo_Z2b3IomdFfLFTZN_DWk5NcSp3WvIAy4KjtOb8wl9YMR6t8mny3YfIXZ7qnd52Anp99p6_pacb3IYk5ley4K6VTEPFF7vBlnbdi0hyLkeltDBgHNbBz71A51bBwqAyaZ8yn2VUe59_Cye4jNJI_w0uC9AkDfzrQ-UZxPn5EJ1ghmlfWMWG14xpXuXC2-86jr6Jry1L8pxuQynuR7FFLRcolvo6_Ue-C4bjyk7UABP0yIyPQMCajKJ2QWfuk9f6dK4EZGfCBhyJCLJgQItfCl1JmlsASs19S4DO86ULxKbER56cOOQhjCbfj1mcNtJJQS8oKOyIZ2T7xzrOjTGY76o00VjRHwfeWYyNhr_TVDPPr6yTkLbszBzRCyDIZwfkRbxA9jjsVFRzx2t_d8K78O2zYXFI9rB9KyoAbeLf2qMl50gAA\",
        \"id_token\": \"eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiIwNGIwNzc5NS04ZGRiLTQ2MWEtYmJlZS0wMmY5ZTFiZjdiNDYiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC8yNzc3Njk4Mi1kODgyLTQxYjItOTVhYy0zMjJmMjhkNWEyY2UvIiwiaWF0IjoxNTYwODYzMzk3LCJuYmYiOjE1NjA4NjMzOTcsImV4cCI6MTU2MDg2NzI5NywiYW1yIjpbInB3ZCJdLCJpcGFkZHIiOiI3Ny4yNDEuMjI5LjI0MiIsIm5hbWUiOiJfc3ZjX3NuYnZhejAxNl9zZGhfdnN0c2RldiIsIm9pZCI6ImEzNWY5NzA1LTE0OGEtNDE2My1hOWMwLWViYTgzZTg5OTY1OSIsInN1YiI6IjdmMEhnRjFhVTZTN1ktdzgxcGVZd3RVaWI3bVJtaGl1NGhybTRuSnR3VlkiLCJ0aWQiOiIyNzc3Njk4Mi1kODgyLTQxYjItOTVhYy0zMjJmMjhkNWEyY2UiLCJ1bmlxdWVfbmFtZSI6Il9zdmNfc25idmF6MDE2X3NkaF92c3RzZGV2QHNuYnYub25taWNyb3NvZnQuY29tIiwidXBuIjoiX3N2Y19zbmJ2YXowMTZfc2RoX3ZzdHNkZXZAc25idi5vbm1pY3Jvc29mdC5jb20iLCJ2ZXIiOiIxLjAifQ.\"

      }"
    }
  }
}
_EOF_

echo "================================================"
echo "== Configure KeyVault secrets '/secrets' =="
echo "================================================"

curl -v -X PUT "http://localhost:1080/mockserver/expectation" -d @- <<_EOF_
{
  "httpRequest": {
    "method": "GET",
    "path": "/secrets",
    "queryStringParameters" : {
      "api-version" : [ "7.0" ]
      }
  },
  "httpResponseTemplate": {
    "template": "body = JSON.stringify(
     [
        {
          attributes: {
            created: '2018-11-16T08:00:00+00:00',
            enabled: true,
            expires: 'null',
            notBefore: 'null',
            recoveryLevel: 'Purgeable',
            updated: '2018-11-16T08:00:00+00:00'
          },
          contentType: 'null',
          id: 'https://keyvaultdev.vault.azure.net/secrets/azure-databricks-host',
          managed: 'null',
          tags: {
            'file-encoding': 'utf-8'
          }
        },
        {
          attributes: {
            created: '2018-11-16T08:00:00+00:00',
            enabled: true,
            expires: 'null',
            notBefore: 'null',
            recoveryLevel: 'Purgeable',
            updated: '2018-11-16T08:00:00+00:00'
          },
          contentType: 'null',
          id: 'https://keyvaultdev.vault.azure.net/secrets/azure-databricks-token',
          managed: 'null',
          tags: {
            'file-encoding': 'utf-8'
          }
        }
     ]
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
_EOF_

curl -v -X PUT "http://localhost:1080/mockserver/expectation" -d @- <<_EOF_
{
  "httpRequest": {
    "method": "GET",
    "path": "/secrets/azure-databricks-token",
    "queryStringParameters" : {
      "api-version" : [ "7.0" ]
      }
  },
  "httpResponseTemplate": {
    "template": "body = JSON.stringify(
     [
        {
          attributes: {
            created: '2018-11-16T08:00:00+00:00',
            enabled: true,
            expires: null,
            notBefore: null,
            recoveryLevel: 'Purgeable',
            updated: '2018-11-16T08:00:00+00:00'
          },
          contentType: null,
          id: 'https://keyvaultdev.vault.azure.net/secrets/azure-databricks-token',
          managed: null,
          tags: {
            'file-encoding': 'utf-8'
          }
          value: 'dbtoken'
        }
     ]
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
_EOF_

curl -v -X PUT "http://localhost:1080/mockserver/expectation" -d @- <<_EOF_
{
  "httpRequest": {
    "method": "GET",
    "path": "/secrets/azure-databricks-host",
    "queryStringParameters" : {
      "api-version" : [ "7.0" ]
      }
  },
  "httpResponseTemplate": {
    "template": "body = JSON.stringify(
     [
        {
          attributes: {
            created: '2018-11-16T08:00:00+00:00',
            enabled: true,
            expires: null,
            notBefore: null,
            recoveryLevel: 'Purgeable',
            updated: '2018-11-16T08:00:00+00:00'
          },
          contentType: null,
          id: 'https://keyvaultdev.vault.azure.net/secrets/azure-databricks-host',
          managed: null,
          tags: {
            'file-encoding': 'utf-8'
          }
          value: 'localhost:1080'
        }
     ]
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
_EOF_
