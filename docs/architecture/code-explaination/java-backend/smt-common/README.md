# smt-common 模块

> SMT 平台公共基础模块，提供统一响应封装、异常处理、安全认证、ORM 自动填充等跨模块复用能力。

**模块路径**: `java-backend/smt-common/`
**包根路径**: `com.smt.platform.common`

## 职责

- 统一 REST API 响应格式（`Result<T>` + `ResultCode`）
- 业务异常定义与全局异常处理
- Spring Security + JWT 认证过滤链
- MyBatis-Plus 自动填充（创建时间/更新时间/软删除）
- Jackson 序列化配置（日期格式/时区）
- 开发环境 CORS 跨域配置

## 包结构

```
com.smt.platform.common/
├── response/          ← 统一响应封装
│   ├── Result.java
│   └── ResultCode.java
├── exception/         ← 异常处理
│   ├── BizException.java
│   └── GlobalExceptionHandler.java
├── entity/            ← 实体基类
│   └── BaseEntity.java
├── config/            ← 配置类
│   ├── JacksonConfig.java
│   ├── CorsConfig.java
│   └── MyMetaObjectHandler.java
├── utils/             ← 工具类
│   └── JwtUtil.java
└── security/          ← 安全认证
    ├── SecurityConfig.java
    ├── JwtAuthenticationFilter.java
    └── AuthErrorHandlers.java
```

## 依赖关系

- **被依赖**: `smt-gateway`, `smt-device-service` 等所有 Java 模块
- **外部依赖**: Spring Security, Spring Web, MyBatis-Plus, JJWT, Lombok, Hutool

## 快速导航

| 包 | 文档 | 说明 |
|---|------|------|
| response | [Result](response/Result.md), [ResultCode](response/ResultCode.md) | 统一响应体与状态码 |
| exception | [BizException](common/../../exception/../common/BizException.md) | 业务异常 |
| exception | [GlobalExceptionHandler](common/../../exception/../common/GlobalExceptionHandler.md) | 全局异常处理 |
| entity | [BaseEntity](common/BaseEntity.md) | 实体基类（审计字段+软删除） |
| config | [JacksonConfig](config/JacksonConfig.md), [CorsConfig](config/CorsConfig.md) | 序列化与跨域 |
| config | [MyMetaObjectHandler](common/../../config/../common/MyMetaObjectHandler.md) | MyBatis-Plus 自动填充 |
| utils | [JwtUtil](common/../../utils/../common/JwtUtil.md) | JWT 签发与验证 |
| security | [SecurityConfig](common/../../security/../common/SecurityConfig.md), [JwtAuthenticationFilter](common/../../security/../common/JwtAuthenticationFilter.md), [AuthErrorHandlers](common/../../security/../common/AuthErrorHandlers.md) | 安全配置与过滤链 |
