FROM takeoff:it

RUN update-ca-certificates -f \
  && apt-get update \
  && apt-get install -y --no-install-recommends --reinstall build-essential \
  && apt-get install -y --no-install-recommends --allow-unauthenticated \
     software-properties-common \
     dnsutils \
     nginx \
  && apt-get clean \
  && apt-get autoremove -yqq --purge \
  && rm -rf /var/cache/apk/* /var/lib/apt/lists/* \
  && (find /usr/share/doc -type f -and -not -name copyright -print0 | xargs -0 -r rm)

# Make sure a ssl certificate is generated and configured. Nginx can be configured if needed from now on.
RUN mkdir -p /etc/nginx/ssl \
    && mkdir -p /etc/nginx/conf.d/locations.d \
    && openssl genrsa -des3 -passout pass:p4ssw0rd -out server.pass.key 2048 \
    && openssl rsa -passin pass:p4ssw0rd -in server.pass.key -out /etc/nginx/ssl/server.key \
	&& rm server.pass.key \
	&& openssl req -new -key /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.csr \
        -subj "/C=NL/ST=NoordHolland/L=Schiphol/O=TakeOff/OU=IT Department/CN=localhost" \
    && openssl x509 -req -days 3650 -in /etc/nginx/ssl/server.csr -signkey /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.crt \
    && openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048 \
    && cat /etc/nginx/ssl/server.key > /etc/nginx/ssl/server.pem \
    && cat /etc/nginx/ssl/server.crt >> /etc/nginx/ssl/server.pem \
    && ln -s /etc/nginx/ssl/server.crt /etc/ssl/certs/nginx_selfsigned.crt \
    && update-ca-certificates -f

# Make sure ssl verification is disabled
ADD nginx-ssl.conf /etc/nginx/conf.d/

ENV CURL_CA_BUNDLE=""
