# DeviceService

> 设备管理业务逻辑接口，定义设备 CRUD 和分页查询操作。

**包路径**: `com.smt.platform.device.service`
**源文件**: `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/service/DeviceService.java`

---

## 接口签名

```java
public interface DeviceService extends IService<Device>
```

**父接口**: `com.baomidou.mybatisplus.extension.service.IService<Device>`

---

## 方法

### `create(Device device)`

> 新增设备（deviceCode 全局唯一）

**签名**: `Device create(Device device)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device` | `Device` | 是 | 设备实体 |

**返回值**: `Device` — 创建后的设备（含自增 ID）

**异常**: `BizException(CONFLICT)` — deviceCode 重复时

---

### `update(Long id, Device device)`

> 部分字段更新设备（deviceCode 不可修改）

**签名**: `Device update(Long id, Device device)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `Long` | 是 | 设备 ID |
| `device` | `Device` | 是 | 更新字段（null 字段不更新） |

**返回值**: `Device` — 更新后的设备

**异常**: `BizException(NOT_FOUND)` — 设备不存在时

---

### `delete(Long id)`

> 软删除设备

**签名**: `boolean delete(Long id)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `Long` | 是 | 设备 ID |

**返回值**: `boolean` — 删除是否成功

**异常**: `BizException(NOT_FOUND)` — 设备不存在时

---

### `getByIdOrThrow(Serializable id)`

> 按 ID 查询设备，不存在抛异常

**签名**: `Device getByIdOrThrow(Serializable id)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `Serializable` | 是 | 设备 ID |

**返回值**: `Device` — 设备实体

**异常**: `BizException(NOT_FOUND)` — 设备不存在时

---

### `pageList(int page, int size, String productionLine, String deviceType, String status)`

> 分页查询设备列表

**签名**: `IPage<Device> pageList(int page, int size, String productionLine, String deviceType, String status)`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | `int` | 是 | 页码 |
| `size` | `int` | 是 | 每页条数 |
| `productionLine` | `String` | 否 | 产线筛选 |
| `deviceType` | `String` | 否 | 设备类型筛选 |
| `status` | `String` | 否 | 状态筛选 |

**返回值**: `IPage<Device>` — 分页结果

---

## 实现类

- **DeviceServiceImpl** — `file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/service/impl/DeviceServiceImpl.java`
