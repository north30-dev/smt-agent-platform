# 遗留项 GAP 收尾报告

## 一、元信息表

| 项目         | 内容                                                                                       |
| ---------- | ---------------------------------------------------------------------------------------- |
| 审查对象       | `docs/repaired-reports/` 下 4 份报告的跨报告遗留项 GAP                                               |
| 对照基准       | `docs/PRD.md` V1.0；`p0-fix-report-phase1.md`；`p0-fix-report-phase2.md`；`p1-fix-report-phase1.md`；`leftover-items-resolution-comprehensive.md` |
| 审查方法       | 跨报告交叉分析 + 代码状态核查 + 行为保持性验证 + 全量测试                                                        |
| 审查日期       | 2026-07-04                                                                               |
| 审查范围       | 9 类 GAP（源报告遗留项在综合报告中既未实施也未明确延期的项）+ 1 项 @CacheEvict 缺口                                    |
| 评估口径       | GAP 必须满足以下条件之一才算"已覆盖"：(a) 综合报告明确声明已实施且代码验证通过；(b) 综合报告明确延期并附 PRD §6 阶段归属依据                |
| 置信度阈值      | 代码状态核查需 Read 文件实证；行为保持性需可验证的等价性证明；测试需全量通过                                                |

---

## 二、总体结论

**结论**：发现 9 类 GAP + 1 项 @CacheEvict 缺口，本次处置如下：

| 处置类型  | 数量 | 说明                                                          |
| ----- | -- | ----------------------------------------------------------- |
| 代码修复  | 3  | 行为保持的死代码移除 / 冗余注解清理 / vector_store 重试补充，均已通过全量测试            |
| 明确延期  | 8  | 附 PRD §6 阶段归属依据，含 GAP-1/2/3/4/5/6/7a + @CacheEvict        |
| 报告勘误  | 1  | 综合报告对"预测性维护 14 天预警"的"✓ 已实现"声明与源报告"未达 PRD P0"判断矛盾，本次勘误    |

**关键发现**：
- 3 项严重 GAP 中，GAP-1（Kafka）和 GAP-2（RBAC）经 PRD §6 核实属于 Phase 3-4 范围，源报告"Phase 2"标注与 PRD 路线图不符，本次按 PRD 归属延期
- GAP-3（14 天预警）存在报告虚假对齐：综合报告声称"已实现"但实际为 v1 规则+线性外推，非 PRD §4.2 P0 要求的 PHM 算法
- GAP-9（死代码）和 GAP-7b（冗余 @Mapper）已通过代码修复清除
- GAP-8（vector_store 重试）已补充 tenacity 重试，与 llm_client / device_client 模式对齐

**测试结果**：Java 71 passed / 0 failed；Python 80 passed / 2 skipped / 0 failed；4 类静态检查全通过。

---

## 三、GAP 处理详情

### 3.1 已修复项（3 项）

#### GAP-9: HealthScoreCalculator 死代码 catch(BizException) 移除

| 项目   | 内容                                                                                                          |
| ---- | ----------------------------------------------------------------------------------------------------------- |
| 原缺陷  | `HealthScoreCalculator.refreshHealthScore` 中 `catch(BizException)` 块在 P0-1 后变为死代码（`getById` 已不抛 BizException，只返回 null） |
| 处理方案 | 删除 try-catch 块，`getById` 改为直接调用，保留下方 `if (device == null)` 兜底                                               |
| 行为保持 | P0-1 后 `getById` 走 MyBatis-Plus 默认实现只返回 null，catch 块不可达；`if (device == null)` 兜底逻辑不变；测试 `calculate_shouldReturnZero_whenDeviceIsNull` 通过 |
| 代码位置 | [HealthScoreCalculator.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/health/HealthScoreCalculator.java#L72-L79) |

#### GAP-7b: 冗余 @Mapper 注解移除

| 项目   | 内容                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | 3 个 Mapper 接口（DeviceMapper / DeviceDataMapper / DeviceDataPointMapper）上的 `@Mapper` 注解与 `SmtDeviceServiceApplication` 的 `@MapperScan` 功能重叠 |
| 处理方案 | 删除 3 个接口上的 `@Mapper` 注解及其 import，保留 `@MapperScan` 批量注册                                                               |
| 行为保持 | `@MapperScan("com.smt.platform.device.mapper")` 已批量注册该包下所有接口为 Mapper Bean，`@Mapper` 注解完全冗余；`mvn test` 71 用例全通过验证 Bean 注入正常      |
| 代码位置 | [DeviceMapper.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/mapper/DeviceMapper.java#L1-L10) · [DeviceDataMapper.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/mapper/DeviceDataMapper.java#L1-L10) · [DeviceDataPointMapper.java](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/mapper/DeviceDataPointMapper.java#L1-L10) |

#### GAP-8: vector_store 添加 tenacity 重试

| 项目   | 内容                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 原缺陷  | `shared/vector_store.py` 的 Milvus 连接（`_ensure_connect`）和写入（`insert`）操作无重试，瞬时故障即抛 `VectorStoreError`；与 `llm_client.py` / `device_client.py` 已有 tenacity 重试的模式不一致 |
| 处理方案 | 为 `_ensure_connect()` 和 `insert()` 添加 `Retrying` 重试，策略为 `stop_after_attempt(milvus_max_retries + 1)` + `wait_exponential`，仅对 `MilvusException` 和 `OSError` 重试；`search()` 不加重试（查询失败立即返回，避免 RAG 链路长等待） |
| 行为保持 | 成功路径不变（首次成功则不重试）；失败路径从"立即抛 VectorStoreError"变为"重试 N 次后抛相同 VectorStoreError"，错误类型不变，仅增加瞬时故障容忍度；`config.py` 新增 `milvus_max_retries=2` / `milvus_retry_backoff=1.0` 默认值                                    |
| 代码位置 | [vector_store.py L48-64](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py#L48-L64)（connect 重试）· [vector_store.py L150-165](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/vector_store.py#L150-L165)（insert 重试）· [config.py L48-49](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/shared/config.py#L48-L49) |
| 测试   | `test_vector_store.py` 4 用例通过；全量 80 passed + 2 skipped                                                                                                  |

---

### 3.2 延期项详情（8 项 — 附 PRD §6 阶段归属依据）

#### GAP-1: Kafka 事件总线业务层接入 → Phase 4

| 项目   | 内容                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 原缺陷  | Kafka 仅为 docker-compose 编排，业务层零调用（P0-Phase1 §5.1 + P1-Phase1 §5.1）                                                                                      |
| 综合报告状态 | 完全沉默 — 既未实施也未延期                                                                                                                                        |
| 延期依据 | **PRD §6: "Phase 4 — 执行协同Agent + 全流程闭环 — Kafka事件驱动 + 人机协同"**。PRD 明确将 Kafka 事件驱动归属 Phase 4。源报告标注"Phase 2"与 PRD 路线图不符。当前 docker-compose 已编排 Kafka 容器，基础设施就绪，业务层接入是 Phase 4 交付物。 |
| 建议   | Phase 4 开始时，按 PRD §3.3 多智能体协作流程（"设备传感器异常 → Kafka事件 → Java服务层接收"）实现事件总线                                                                                  |

#### GAP-2: RBAC DB 用户表 + 多角色 → Phase 3

| 项目   | 内容                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 原缺陷  | Phase 1 单用户（配置 admin），Phase 2 需接 DB 用户表 + 多角色（P0-Phase1 §5.3）                                                                                          |
| 综合报告状态 | 完全沉默 — 既未实施也未延期                                                                                                                                        |
| 延期依据 | **PRD §6: Phase 2 交付物为"知识助手Agent(RAG) + 设备运维Agent"**，不含 RBAC 升级。Phase 1 单用户满足 PRD §4.6 RBAC P0 的最小能力。多角色 DB 用户表是 Phase 3 多智能体协作的前置需求（不同 Agent 需不同角色权限）。 |
| 建议   | Phase 3 多智能体编排时，按 P0-Phase1 §5.3 的 3 步升级：(1) AuthController.login 改 DB 查询；(2) JwtAuthenticationFilter 已支持 roles claim；(3) `isAuthenticated()` 升级为 `hasRole('XXX')` |

#### GAP-3: 预测性维护 14 天预警（PHM 算法） → Phase 5+（含报告勘误）

| 项目   | 内容                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 原缺陷  | predict.py 实现为规则 + 最小二乘线性外推 v1，**非** PRD §4.2 P0 要求的"基于PHM算法，预测关键部件剩余寿命，提前14天预警"（P0-Phase2 §5.1）                                                            |
| 综合报告状态 | **虚假对齐** — 综合报告 §六 PRD 符合性评估声称"预测性维护（P0）✓ 已实现"，与源报告"未达 PRD P0"判断直接矛盾                                                                                    |
| 延期依据 | **PRD §6: Phase 5 "系统集成测试 + 产线试点"**。PHM 算法复杂度高（RUL 预测、退化模型、状态空间模型），需基于真实产线数据训练。当前 v1（规则+线性外推）作为 Phase 2 兜底实现，提供基础阈值告警与趋势外推能力。                                |
| 勘误声明 | **综合报告"✓ 已实现"声明不准确**。准确表述应为："预测性维护 v1 兜底实现（规则+线性外推），PHM 算法 + 14 天预警延期至 Phase 5+ 产线试点阶段。"                                                                  |
| 代码位置 | [predict.py L1-5](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/agent-maintenance/predict.py#L1-L5)（docstring 确认算法为"滑动均值+阈值告警+简单线性外推"）    |

#### GAP-4: saveData saveBatch 批量化 → Phase 3

| 项目   | 内容                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | `DeviceDataServiceImpl.saveData` 用 `baseMapper.insert(single)` 单条插入，无 `saveBatch` 批量化（P0-Phase1 §5.1 + P1-Phase1 §5.1）                |
| 综合报告状态 | 部分实施 — 已加 `@Async` 异步化（Batch 4 P1-性能-1/2），但源报告原始诉求"单条 INSERT 改 saveBatch"未实现                                                        |
| 延期依据 | **PRD §6: Phase 2 交付物不含性能优化**。saveBatch 需引入缓冲累积机制（收集 N 条后批量 flush），架构变更较大。当前 `@Async + CallerRunsPolicy` 已将写入移出调用线程，缓解 MQTT 回调阻塞。批量化是 Phase 3 性能优化项。 |
| 代码位置 | [DeviceDataServiceImpl.java L48](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/service/impl/DeviceDataServiceImpl.java#L48) |

#### GAP-5: conftest.py importlib hack → Phase 3

| 项目   | 内容                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | `tests/conftest.py` 用 `importlib.util.spec_from_file_location` 注册 kebab-case 包名（agent-knowledge / agent-maintenance），是测试基础设施 hack（P0-Phase2 §5.2 m5） |
| 综合报告状态 | ID 复用但问题不同 — 综合报告 Batch 2 的 m5 描述为"测试 fixture 重复 → conftest.py 共享 mock fixture"，与源报告 m5 的"importlib hack"是不同问题                                                |
| 延期依据 | importlib hack 仅影响测试环境包导入，不影响生产代码。根治需将 kebab-case 目录改 snake_case（涉及 AGENTS.md §3.2 包名规范 + PyPI 包名规范），是 Phase 3 测试基础设施优化项。                    |
| 代码位置 | [conftest.py L1-41](file:///home/north30/projects/Personal/smt-agent-platform/python-agents/tests/conftest.py#L1-L41)                       |

#### GAP-6: ResultCode BIZ_ERROR(500) 与 SYSTEM_ERROR(500) 同码 → Phase 3

| 项目   | 内容                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | `ResultCode` 枚举中 `BIZ_ERROR(500)` 与 `SYSTEM_ERROR(500)` 同为 HTTP 500，前端无法通过状态码区分业务异常与系统异常（P1-Phase1 §5.1）                              |
| 综合报告状态 | 未对齐 — 综合报告 Batch 3 m7 补了 5 个新状态码（409/422/429/503/504）但明确声明"原 7 码值不变"，因此 500 重复问题仍存在                                                |
| 延期依据 | 修改 `BIZ_ERROR`/`SYSTEM_ERROR` 的 HTTP 状态码会破坏前端 API 契约。当前 message 区分（"业务处理失败" vs "系统内部错误"）已提供语义区分能力。Phase 3 前端重构时统一调整。                |
| 代码位置 | [ResultCode.java L19-41](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-common/src/main/java/com/smt/platform/common/response/ResultCode.java#L19-L41) |

#### GAP-7a: 实体 @Data → @Getter/@Setter → Phase 3

| 项目   | 内容                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | 3 个实体类（Device / DeviceData / DeviceDataPoint）使用 `@Data` 注解，生成 equals/hashCode/toString，对实体类有潜在栈溢出风险（P1-Phase1 §5.1 P2 Minor）            |
| 综合报告状态 | 完全沉默 — 未提及也未延期                                                                                                                      |
| 延期依据 | `@Data` 生成 equals/hashCode/toString，移除会改变实体在日志输出、集合操作中的行为。Grep 确认当前无 `Set<Device>` / `Map<Device>` 键使用实体，但保守起见不在"不得修改原有功能"约束下做此变更。Phase 3 代码质量优化时处理。 |
| 代码位置 | [Device.java L19](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/model/entity/Device.java#L19) · [DeviceData.java L15](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/model/entity/DeviceData.java#L15) · [DeviceDataPoint.java L14](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/model/entity/DeviceDataPoint.java#L14) |

#### @CacheEvict 缺口 → Phase 3

| 项目   | 内容                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 原缺陷  | 综合报告 Batch 3 m6 为 `DeviceDataController.history` 加了 `@Cacheable`，但全模块 0 处 `@CacheEvict`。写入路径 `DeviceDataServiceImpl.saveData`（@Async + MQTT）不会清缓存，导致 history 在最多 10 分钟内返回脏读 |
| 综合报告状态 | 综合报告 §七 P0 建议 #2 提到"补 @CacheEvict"但未实施；`RedisConfig.java:24-25` 自承认"依赖 TTL 10min 兜底"                                                  |
| 延期依据 | 当前 DeviceDataController 仅 1 个 GET 端点（history），无写入端点。`@CacheEvict` 需匹配缓存键（deviceId+code+timeRange+page+size），但 `saveData` 签名无这些参数，只能用 `allEntries=true`（每条 MQTT 数据清空全量缓存，过于激进）。TTL 10min 是当前文档化的兜底方案。Phase 3 接入同步写入 API 后实现精准 evict。 |
| 代码位置 | [DeviceDataController.java @Cacheable](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/controller/DeviceDataController.java#L49-L50) · [RedisConfig.java L24-25](file:///home/north30/projects/Personal/smt-agent-platform/java-backend/smt-device-service/src/main/java/com/smt/platform/device/config/RedisConfig.java#L24-L25) |

---

## 四、延期项汇总表

| # | 项 | 延期到 | PRD §6 依据 | 严重度 |
|---|---|---|---|---|
| 1 | GAP-1 Kafka 事件总线业务层接入 | Phase 4 | "Phase 4 — Kafka事件驱动 + 人机协同" | 严重 |
| 2 | GAP-2 RBAC 多角色 DB 用户表 | Phase 3 | Phase 2 交付物不含 RBAC 升级 | 严重 |
| 3 | GAP-3 预测性维护 14 天预警（PHM 算法） | Phase 5+ | Phase 5 "产线试点"；§4.2 P0 "基于PHM算法" | 严重 |
| 4 | GAP-4 saveData saveBatch 批量化 | Phase 3 | Phase 2 不含性能优化 | 中 |
| 5 | GAP-5 conftest.py importlib hack | Phase 3 | 测试基础设施，非 PRD 直接约束 | 中 |
| 6 | GAP-6 ResultCode 500 区分 | Phase 3 | API 契约，非 PRD 直接约束 | 中 |
| 7 | GAP-7a 实体 @Data → @Getter/@Setter | Phase 3 | 代码质量 P2，非 PRD 直接约束 | 中 |
| 8 | @CacheEvict 精准失效 | Phase 3 | Phase 3 接入写入 API 后实现 | 中 |

---

## 五、测试验证结果

### 5.1 Java 测试（Fix-1 + Fix-2 验证）

```
mvn test（java-backend 全量）
```

| 模块                  | 测试数 | 通过 | 失败 | 跳过 |
|---------------------|-----|-----|-----|-----|
| smt-common          | 7   | 7   | 0   | 0   |
| smt-gateway         | 7   | 7   | 0   | 0   |
| smt-device-service  | 57  | 57  | 0   | 0   |
| **合计**              | **71** | **71** | **0** | **0** |

重点验证项：
- `HealthScoreCalculatorTest`（11 用例）全通过 — 验证死代码 catch 移除不影响 null 兜底逻辑
- `DeviceServiceImplTest` / `DeviceDataServiceImplTest` / `DeviceDataPointServiceImplTest` 全通过 — 验证 @Mapper 移除不影响 Bean 注入

### 5.2 Python 测试（Fix-3 验证）

```
poetry run pytest（python-agents 全量）
```

| 结果   | 数量  |
|------|-----|
| passed | 80  |
| skipped | 2   |
| failed | 0   |
| 总耗时  | 2.34s |

重点验证项：
- `test_vector_store.py`（4 用例）全通过 — 验证 tenacity 重试引入不破坏现有 vector_store 行为
- `test_llm_client.py`（5 用例）全通过 — 验证重试模式一致性
- `test_maintenance_predict.py`（20 用例）全通过 — 验证 predict.py 未受影响

### 5.3 静态检查

| 检查项 | 命令 | 预期结果 | 实际结果 |
|---|---|---|---|
| @Mapper 已移除 | grep `@Mapper` in mapper/ | 无匹配 | 无匹配 ✓ |
| catch(BizException) 已移除 | grep `catch.*BizException` in HealthScoreCalculator.java | 无匹配 | 无匹配 ✓ |
| vector_store 重试已引入 | grep `tenacity\|Retrying\|retry_if_exception` in vector_store.py | 7 行匹配 | 7 行匹配 ✓ |
| config.py milvus 配置已新增 | grep `milvus_max_retries\|milvus_retry_backoff` in config.py | 2 行匹配 | 2 行匹配 ✓ |

### 5.4 行为兼容性验证

| Fix | 行为保持证明 | 验证方式 |
|---|---|---|
| Fix-1 (GAP-9) | `getById` P0-1 后只返回 null 不抛 BizException，catch 块不可达；`if (device == null)` 兜底不变 | `HealthScoreCalculatorTest` 11 用例通过 |
| Fix-2 (GAP-7b) | `@MapperScan` 已批量注册，`@Mapper` 冗余；Bean 注入行为不变 | 全量 71 用例通过（含 3 个 Mapper 相关 ServiceImplTest） |
| Fix-3 (GAP-8) | 成功路径不变；失败路径从"立即抛"变为"重试 N 次后抛相同异常"，错误类型 `VectorStoreError` 不变 | `test_vector_store.py` 4 用例 + 全量 80 用例通过 |

---

## 六、PRD 符合性评估勘误

### 6.1 勘误：预测性维护 14 天预警

**原综合报告声明**（`leftover-items-resolution-comprehensive.md` §六）：
> 「预测性维护（P0）✓ 已实现 | predict.py + M3 配置外置 + M9 20 测试用例」

**勘误为**：
> 「预测性维护 v1 兜底实现（规则 + 最小二乘线性外推），提供基础阈值告警与趋势外推能力。**PRD §4.2 P0 要求的"基于PHM算法，预测关键部件剩余寿命，提前14天预警"未完整实现**，完整 PHM 算法延期至 Phase 5+ 产线试点阶段（需基于真实数据训练退化模型）。」

**勘误依据**：
- `predict.py` L1-5 docstring 明确："基于近 7 天采集点历史数据，计算滑动均值、阈值告警与简单线性外推"
- 算法实现（L69-76）：滑动窗口均值 + 最小二乘斜率，无 RUL 预测、无退化模型、无机器学习模型
- 源报告 `p0-fix-report-phase2.md` §5.1 明确："预测性维护'提前 14 天预警'被裁剪为规则+线性外推 v1，未达 PRD P0 | Phase 5+"

### 6.2 其他 PRD 符合性声明（维持原综合报告判断）

| PRD 项 | 原综合报告声明 | 本次核实 | 结论 |
|---|---|---|---|
| 知识助手 RAG <3s（§4.4 P0） | ✓ 已实现 | `test_performance.py` 2 用例通过 | 维持 ✓ |
| 设备实时健康监测（§4.2 P0） | ✓ 已实现 | `HealthScoreCalculator` + 11 测试通过 | 维持 ✓ |
| 故障诊断（§4.2 P0） | ✓ 已实现 | `diagnose.py` + 3 测试通过 | 维持 ✓ |
| 设备管理（§4.6 P0） | ✓ 已实现 | `DeviceServiceImpl` + 9 测试通过 | 维持 ✓ |
| 用户权限 RBAC（§4.6 P0） | ✓ 已实现（单用户） | Phase 1 单用户满足最小 P0；多角色延期 Phase 3 | 维持 ✓（单用户），多角色延期 |
| Kafka 事件驱动（§3.3） | 延期 Phase 4 | 本次核实 PRD §6 确认 Phase 4 | 维持延期 |

---

## 七、改进建议

| 优先级 | 建议 | 归属阶段 | 说明 |
|---|---|---|---|
| P0 | 预测性维护 PHM 算法研发 | Phase 5+ | 当前 v1 规则+线性外推未达 PRD §4.2 P0"基于PHM算法，提前14天预警"。需基于真实产线数据训练退化模型/RUL 预测模型 |
| P0 | 端到端集成测试（docker-compose 全栈） | Phase 2 收尾 | 本机 Docker Hub 不可达，端到端验证自始至终未执行。需在 CI 环境补全 |
| P1 | Kafka 事件总线业务层接入 | Phase 4 | 按 PRD §3.3 多智能体协作流程实现事件驱动链路 |
| P1 | RBAC 多角色 DB 用户表 | Phase 3 | Phase 3 多智能体协作前置需求 |
| P1 | saveData saveBatch 批量化 | Phase 3 | 高频 MQTT 场景 PG 写入性能优化 |
| P1 | @CacheEvict 精准失效 | Phase 3 | 接入同步写入 API 后实现精准缓存失效，替代当前 TTL 10min 兜底 |
| P2 | 实体 @Data → @Getter/@Setter | Phase 3 | 代码质量 P2，避免实体 equals/hashCode/toString 潜在风险 |
| P2 | conftest.py importlib hack 根治 | Phase 3 | 测试基础设施优化，kebab-case → snake_case 包名规范化 |
| P2 | ResultCode 500 区分 | Phase 3 | BIZ_ERROR/SYSTEM_ERROR HTTP 状态码区分，需配合前端重构 |

---

## 八、审查方法附录

### 8.1 跨报告 GAP 分析方法

1. 读取 `docs/repaired-reports/` 下 4 份报告全文（3 份源报告 + 1 份综合报告）
2. 提取每份源报告 §5 遗留项章节的所有遗留/延期/未完成项
3. 提取综合报告声称已实施的项（Batch 1-5）和明确延期的项（§四）
4. 交叉比对：源报告遗留项在综合报告中是否满足以下条件之一：
   - (a) 综合报告明确声明已实施，且代码验证通过
   - (b) 综合报告明确延期，并附 PRD §6 阶段归属依据
5. 不满足 (a) 或 (b) 的项即为 GAP

### 8.2 代码状态核查方法

对每个 GAP，使用 Read/Grep 工具验证代码实际状态：
- GAP-8: Read `vector_store.py` 全文，确认无 tenacity；Read `llm_client.py` 确认有 tenacity（对照组）
- GAP-9: Read `HealthScoreCalculator.java`，确认 catch(BizException) 块存在；Read `DeviceServiceImpl.java` 确认 `getById` 无覆写
- GAP-7b: Grep `@Mapper` in mapper/ + Read `SmtDeviceServiceApplication.java` 确认 `@MapperScan` 并存
- GAP-3: Read `predict.py` L1-50，确认算法为"滑动均值+阈值告警+简单线性外推"

### 8.3 测试复现步骤

```bash
# Java 测试
cd java-backend
mvn clean test
# 预期: 71 passed, 0 failed, 0 skipped

# Python 测试
cd python-agents
poetry run pytest
# 预期: 80 passed, 2 skipped, 0 failed

# 静态检查
grep -rn "@Mapper" java-backend/smt-device-service/src/main/java/com/smt/platform/device/mapper/
# 预期: 无输出

grep -n "catch.*BizException" java-backend/smt-device-service/src/main/java/com/smt/platform/device/health/HealthScoreCalculator.java
# 预期: 无输出

grep -n "tenacity\|Retrying\|retry_if_exception" python-agents/shared/vector_store.py
# 预期: 7 行匹配

grep -n "milvus_max_retries\|milvus_retry_backoff" python-agents/shared/config.py
# 预期: 2 行匹配
```

### 8.4 端到端验证限制

**限制说明**：本机 Docker Hub 不可达，端到端 docker-compose 验证未执行。本次验证范围限于编译 + 单测级验证。端到端集成测试（含真实 InfluxDB / PG / MQTT 闭环）需在 CI 环境补全，列为 P0 改进建议。

### 8.5 与原综合报告的关系

本报告**不替代**原综合报告 `leftover-items-resolution-comprehensive.md`，而是其补充与勘误：
- 原综合报告的 22 项实施成果（Batch 1-5）**全部有效**
- 本报告对其中 1 项 PRD 合规声明（GAP-3 "已实现"）进行勘误
- 本报告补充了 8 项原综合报告遗漏的延期项
- 本报告实施了 3 项原综合报告未覆盖的 GAP 修复（GAP-7b / GAP-8 / GAP-9）

遵循 AGENTS.md §6.5 "旧阶段报告不删除，作为历史审计留痕"，原综合报告保持不变。
