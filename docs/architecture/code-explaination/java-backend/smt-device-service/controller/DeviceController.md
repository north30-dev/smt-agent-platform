# DeviceController

> 设备管理 REST 控制器，提供设备的增删改查接口。

**包路径**: `com.smt.platform.device.controller`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/controller/DeviceController.java`

---

## 类签名

```java
@RestController
@RequestMapping("/api/device")
public class DeviceController
```

**父类**: `Object`
**实现接口**: 无
**Spring 注解**: `@RestController`, `@RequestMapping("/api/device")`

---

## 字段

| 字段 | 类型 | 修饰符 | 说明 |
|------|------|--------|------|
| `deviceService` | `DeviceService` | `private final` | 设备业务服务 |

---

## 构造方法

```java
public DeviceController(DeviceService deviceService)
```

构造器注入 `DeviceService`。

---

## REST 端点

### `POST /api/device` — 创建设备

**方法**: `public Result<Device> create(@Valid @RequestBody DeviceCreateDTO dto)`

**注解**: `@PostMapping`, `@PreAuthorize("isAuthenticated()")`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `dto` | `DeviceCreateDTO` | Request Body | 设备创建 DTO（含校验注解） |

**返回值**: `Result<Device>` — 创建成功的设备信息

**逻辑**: DTO → `BeanUtils.copyProperties` → `DeviceService.create`

---

### `PUT /api/device/{id}` — 更新设备

**方法**: `public Result<Device> update(@PathVariable Long id, @Valid @RequestBody DeviceUpdateDTO dto)`

**注解**: `@PutMapping("/{id}")`, `@PreAuthorize("isAuthenticated()")`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `id` | `Long` | Path | 设备 ID |
| `dto` | `DeviceUpdateDTO` | Request Body | 设备更新 DTO |

**返回值**: `Result<Device>` — 更新后的设备信息

**逻辑**: DTO → `BeanUtils.copyProperties` → `DeviceService.update(id, device)`

---

### `DELETE /api/device/{id}` — 删除设备

**方法**: `public Result<Void> delete(@PathVariable Long id)`

**注解**: `@DeleteMapping("/{id}")`, `@PreAuthorize("isAuthenticated()")`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `id` | `Long` | Path | 设备 ID |

**返回值**: `Result<Void>` — 删除结果

**逻辑**: 调用 `DeviceService.delete(id)`

---

### `GET /api/device/{id}` — 查询设备详情

**方法**: `public Result<Device> getById(@PathVariable Long id)`

**注解**: `@GetMapping("/{id}")`

**参数**:

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `id` | `Long` | Path | 设备 ID |

**返回值**: `Result<Device>` — 设备详情

**逻辑**: 调用 `DeviceService.getByIdOrThrow(id)`

---

### `GET /api/device/list` — 分页查询设备列表

**方法**: `public Result<PageVO<Device>> list(@RequestParam int page, @RequestParam int size, @RequestParam(required = false) String productionLine, @RequestParam(required = false) String deviceType, @RequestParam(required = false) String status)`

**注解**: `@GetMapping("/list")`, `@Positive`, `@Max(200)`

**参数**:

| 参数 | 类型 | 位置 | 必填 | 说明 |
|------|------|------|------|------|
| `page` | `int` | Query | 是 | 页码（>0） |
| `size` | `int` | Query | 是 | 每页条数（≤200） |
| `productionLine` | `String` | Query | 否 | 产线筛选 |
| `deviceType` | `String` | Query | 否 | 设备类型筛选 |
| `status` | `String` | Query | 否 | 状态筛选 |

**返回值**: `Result<PageVO<Device>>` — 分页设备列表

**逻辑**: 调用 `DeviceService.pageList(...)` → `PageVO.of(page)`
