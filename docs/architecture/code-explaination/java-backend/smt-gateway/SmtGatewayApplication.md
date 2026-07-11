# SmtGatewayApplication

> Spring Cloud Gateway 启动类，引导网关应用。

**包路径**: `com.smt.platform.gateway`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-gateway/src/main/java/com/smt/platform/gateway/SmtGatewayApplication.java`

---

## 类签名

```java
@SpringBootApplication
public class SmtGatewayApplication
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@SpringBootApplication`（扫描范围限定为 `com.smt.platform.gateway` 子包）

---

## 方法

### `main(String[] args)`

> 应用入口

**签名**: `public static void main(String[] args)`

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `args` | `String[]` | 命令行参数 |

**逻辑**: 调用 `SpringApplication.run(SmtGatewayApplication.class, args)` 启动 Spring Boot 应用

---

## 注意事项

- `scanBasePackages` 未显式设置，默认扫描 `com.smt.platform.gateway` 及其子包
- 由于网关使用响应式栈（WebFlux），不会加载 `smt-common` 中的 Servlet 相关配置
