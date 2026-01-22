# Shibboleth Nginx Configuration include by default.conf

# Shibboleth FastCGI Authorizer
location /shibauthorizer {
  internal;
  include fastcgi_params;
  fastcgi_pass unix:/opt/shibboleth/shibauthorizer.sock;

  fastcgi_param SCRIPT_NAME /shibauthorizer;
  fastcgi_param PATH_INFO $uri;
  fastcgi_param REQUEST_METHOD $request_method;
  fastcgi_param QUERY_STRING $query_string;
  fastcgi_param SERVER_NAME $server_name;
  fastcgi_param SERVER_PORT $server_port;
  fastcgi_param SERVER_PROTOCOL $server_protocol;
}

# Shibboleth FastCGI Responder
location /shibresponder {
  internal;
  include fastcgi_params;
  fastcgi_pass unix:/opt/shibboleth/shibresponder.sock;

  fastcgi_param SCRIPT_NAME /shibresponder;
  fastcgi_param PATH_INFO $uri;
  fastcgi_param REQUEST_METHOD $request_method;
  fastcgi_param QUERY_STRING $query_string;
  fastcgi_param SERVER_NAME $server_name;
  fastcgi_param SERVER_PORT $server_port;
  fastcgi_param SERVER_PROTOCOL $server_protocol;
}

# Handling Shibboleth SSO requests
location ~ Shibboleth.sso/ {
  include fastcgi_params;
  fastcgi_pass unix:/opt/shibboleth/shibresponder.sock;
}

location /secure {
    limit_except GET { deny all; }
    shib_request /shibauthorizer;
    shib_request_use_headers on;

    more_clear_input_headers 'EPPN' 'DisplayName' 'JaDisplayName' 'IsMemberOf';

    uwsgi_pass unix:/run/uwsgi/app.sock;
    include uwsgi_params;

    uwsgi_param Host              $host;
    uwsgi_param X-Forwarded-For   $proxy_add_x_forwarded_for;
    uwsgi_param X-Forwarded-Proto $scheme;

    uwsgi_param SCRIPT_NAME "";
    uwsgi_param PATH_INFO "/api/auth/login";
    uwsgi_param QUERY_STRING $query_string;

    uwsgi_param HTTP_EPPN          $http_eppn;
    uwsgi_param HTTP_IsMemberOf    $http_ismemberof;
    uwsgi_param HTTP_DisplayName   $http_displayname;
    uwsgi_param HTTP_JaDisplayName $http_jadisplayname;
}

