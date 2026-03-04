---
title: exc
description: 当システムのビジネスロジックにおける例外定義を提供する。
---

## JAIROCloudGroupsManagerError
当システムのビジネスロジックにおける基底例外クラス。すべてのカスタム例外はこのクラスを継承する。

#### シグネチャ
```python[exc.py]
class JAIROCloudGroupsManagerError(Exception):
```

#### 継承元
`Exception`


## ConfigurationError
サーバー設定に関する例外クラス。

#### シグネチャ
```python[exc.py]
class ConfigurationError(JAIROCloudGroupsManagerError):
```

#### 継承元
`JAIROCloudGroupsManagerError`


## CertificatesError
証明書の操作に関する例外クラス。

#### シグネチャ
```python[exc.py]
class CertificatesError(JAIROCloudGroupsManagerError):
```

#### 継承元
`JAIROCloudGroupsManagerError`


## ServiceSettingsError
動的サービス設定の操作に関する基底例外クラス。

#### シグネチャ
```python[exc.py]
class ServiceSettingsError(JAIROCloudGroupsManagerError):
```

#### 継承元
`JAIROCloudGroupsManagerError`


## CredentialsError
クライアント認証情報の操作に関する例外クラス。

#### シグネチャ
```python[exc.py]
class CredentialsError(ServiceSettingsError):
```

#### 継承元
`ServiceSettingsError`


## OAuthTokenError
OAuth トークンの操作に関する例外クラス。

#### シグネチャ
```python[exc.py]
class OAuthTokenError(ServiceSettingsError):
```

#### 継承元
`ServiceSettingsError`


## DatabaseError
データベース操作に関する例外クラス。

#### シグネチャ
```python[exc.py]
class DatabaseError(JAIROCloudGroupsManagerError):
```

#### 継承元
`JAIROCloudGroupsManagerError`


## ApiClientError
API クライアントの操作に関する基底例外クラス。

#### シグネチャ
```python[exc.py]
class ApiClientError(JAIROCloudGroupsManagerError):
```

#### 継承元
`JAIROCloudGroupsManagerError`


## ResourceInvalid
API クライアント操作において、リソースが不正であることを示す例外クラス。

#### シグネチャ
```python[exc.py]
class ResourceInvalid(ApiClientError):
```

#### 継承元
`ApiClientError`


## ResourceNotFound
API クライアント操作において、リソースが見つからないことを示す例外クラス。

#### シグネチャ
```python[exc.py]
class ResourceNotFound(ApiClientError):
```

#### 継承元
`ApiClientError`


## UnexpectedResponseError
API クライアント操作において、予期しないレスポンスが返されたことを示す例外クラス。

#### シグネチャ
```python[exc.py]
class UnexpectedResponseError(ApiClientError):
```

#### 継承元
`ApiClientError`
