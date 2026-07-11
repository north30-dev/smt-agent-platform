# Java Device Service API

**版本**: v1.1 | **日期**: 2026-07-11 | **状态**: Phase 3-4

---

## 四、Java Device Service API

### 4.1 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | smt-device-service |
| 技术栈 | Spring Boot 3.x + MyBatis-Plus |
| 端口 | 8081 |
| 认证方式 | JWT Token（开发环境使用固定凭据） |
| API路径前缀 | `/api/device`（单数形式） |

### 4.2 认证API

#### 4.2.1 用户登录

**端点**: `POST /api/auth/login`

**请求体**:

```json
{
  "username": "admin",
  "password": "dev-only-admin"
}
```

**响应示例**:

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expireTime": "2026-07-08 01:00:00"
  }
}
```

**Token使用**:

```http
Authorization: Bearer <token>
```

### 4.3 设备管理API

#### 4.3.1 查询设备列表

**端点**: `GET /api/device/list`

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| size | int | 否 | 10 | 每页数量 |
| productionLine | string | 否 | - | 产线筛选 |
| deviceType | string | 否 | - | 设备类型筛选 |
| status | string | 否 | - | 设备状态筛选 |

**响应示例**:

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "records": [
      {
        "id": 1,
        "deviceCode": "DEV-001",
        "deviceName": "贴片机A",
        "deviceType": "贴片机",
        "productionLine": "LINE-1",
        "status": "RUNNING",
        "healthScore": 95
      }
    ],
    "total": 1,
    "size": 10,
    "current": 1,
    "pages": 1
  }
}
```

#### 4.3.2 查询设备详情

**端点**: `GET /api/device/{id}`

**响应示例**:

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "deviceCode": "DEV-001",
    "deviceName": "贴片机A",
    "deviceType": "贴片机",
    "productionLine": "LINE-1",
    "status": "RUNNING",
    "healthScore": 95
  }
}
```

#### 4.3.3 创建设备

**端点**: `POST /api/device`

**请求体**:

```json
{
  "deviceCode": "DEV-002",
  "deviceName": "回流焊炉B",
  "deviceType": "回流焊炉",
  "productionLine": "LINE-1",
  "ipAddress": "192.168.1.102",
  "protocolType": "OPC_UA",
  "status": "IDLE",
  "healthScore": 100
}
```

#### 4.3.4 更新设备

**端点**: `PUT /api/device/{id}`

> `deviceCode` 字段不可更新（唯一约束）

#### 4.3.5 删除设备

**端点**: `DELETE /api/device/{id}`

> 软删除（设置 deleted=1，不物理删除）

### 4.4 健康检查API

**端点**: `GET /actuator/health`

```json
{
  "status": "UP",
  "components": {
    "db": {"status": "UP"},
    "redis": {"status": "UP"},
    "diskSpace": {"status": "UP"}
  }
}
```

### 4.5 错误处理规范

**标准错误响应**:

```json
{
  "code": 500,
  "message": "系统内部错误",
  "data": null
}
```

**错误码定义**:

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| 200 | 操作成功 | 200 |
| 400 | 参数校验失败 | 400 |
| 401 | 认证失败 | 401 |
| 403 | 权限不足 | 403 |
| 404 | 资源不存在 | 404 |
| 500 | 系统内部错误 | 500 |
