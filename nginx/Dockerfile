# syntax=docker/dockerfile:1

ARG NGINX_VERSION=1.29.3

# ============================
# Build stage: Build nginx-http-shibboleth module
# ============================
FROM debian:trixie-slim AS build

ARG NGINX_VERSION
ENV NGINX_VERSION=${NGINX_VERSION}
WORKDIR /usr/src

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential git wget ca-certificates \
    libpcre2-dev zlib1g-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && \
    tar xzf nginx-${NGINX_VERSION}.tar.gz
RUN wget https://github.com/nginx-shib/nginx-http-shibboleth/archive/v2.0.2.tar.gz && \
    tar xzf v2.0.2.tar.gz

WORKDIR /usr/src/nginx-${NGINX_VERSION}
RUN ./configure --with-compat --add-dynamic-module=../nginx-http-shibboleth-2.0.2 && \
    make modules


# ============================
# Runtime stage: Nginx + Shibboleth SP
# ============================
FROM nginx:${NGINX_VERSION}-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    libapache2-mod-shib \
    shibboleth-sp-utils \
    shibboleth-sp-common \
    xmlsec1 &&\
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/shibboleth /var/log/supervisor && \
    chown nginx:nginx /opt/shibboleth /var/log/supervisor
RUN mkdir -p /var/run/shibboleth && \
    chown _shibd:_shibd /var/run/shibboleth

# nginx-http-shibboleth
COPY --from=build /usr/src/nginx-${NGINX_VERSION}/objs/ngx_http_shibboleth_module.so /etc/nginx/modules/

COPY supervisord.conf /etc/supervisord.conf
COPY shibboleth2.xml /etc/shibboleth/shibboleth2.xml

COPY ./conf.d /etc/nginx/conf.d
COPY ./ssl/server.crt /etc/nginx/server.crt
COPY ./ssl/server.key /etc/nginx/server.key

COPY ./ssl/server.crt /etc/shibboleth/server.crt
COPY ./ssl/server.key /etc/shibboleth/server.key

RUN sed -i '1s|^|load_module modules/ngx_http_shibboleth_module.so;\n|' /etc/nginx/nginx.conf


EXPOSE 80 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
