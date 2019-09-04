#!/usr/bin/env bash

bash -c 'echo -e 127.0.0.1\\tlogin.microsoftonline.com >> /etc/hosts'
bash -c 'echo -e 127.0.0.1\\tlogin.microsoft.com >> /etc/hosts'
bash -c 'echo -e 127.0.0.1\\tmanagement.azure.com >> /etc/hosts'

bash -c 'cat > /etc/nginx/conf.d/locations.d/databricks-https-proxy.conf' << EOF
  location ~* /api/ {
    proxy_pass http://localhost:1081;
  }
EOF

bash -c 'cat > /etc/nginx/conf.d/locations.d/microsoft-https-proxy.conf' << EOF
  location ~* /common/ {
    proxy_pass http://localhost:1081;
  }
  location ~* /some-fake-tenant/oauth2/token {
    proxy_pass http://localhost:1081;
  }
EOF

nginx -t && service nginx restart
