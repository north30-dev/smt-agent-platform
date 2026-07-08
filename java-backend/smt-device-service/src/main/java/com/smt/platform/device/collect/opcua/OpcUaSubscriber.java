package com.smt.platform.device.collect.opcua;

import jakarta.annotation.PreDestroy;
import org.eclipse.milo.opcua.sdk.client.OpcUaClient;
import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaMonitoredItem;
import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaSubscription;
import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaSubscription.ItemCreationCallback;
import org.eclipse.milo.opcua.stack.core.AttributeId;
import org.eclipse.milo.opcua.stack.core.types.builtin.DataValue;
import org.eclipse.milo.opcua.stack.core.types.builtin.NodeId;
import org.eclipse.milo.opcua.stack.core.types.builtin.QualifiedName;
import org.eclipse.milo.opcua.stack.core.types.builtin.StatusCode;
import org.eclipse.milo.opcua.stack.core.types.builtin.Variant;
import org.eclipse.milo.opcua.stack.core.types.builtin.unsigned.UInteger;
import org.eclipse.milo.opcua.stack.core.types.builtin.unsigned.Unsigned;
import org.eclipse.milo.opcua.stack.core.types.enumerated.MonitoringMode;
import org.eclipse.milo.opcua.stack.core.types.enumerated.TimestampsToReturn;
import org.eclipse.milo.opcua.stack.core.types.structured.MonitoredItemCreateRequest;
import org.eclipse.milo.opcua.stack.core.types.structured.MonitoringParameters;
import org.eclipse.milo.opcua.stack.core.types.structured.ReadValueId;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.BiConsumer;

/**
 * OPC UA 订阅封装（基于 Eclipse Milo 0.6.x）。
 *
 * <p>封装 {@link OpcUaClient} 的连接、订阅、监控项创建流程，节点值变化时通过回调
 * 把（采集点编码, 值字符串）交给上层。连接异常仅记录日志不抛出，避免影响其他设备订阅。</p>
 *
 * <p>P0-6 修复：采样参数从硬编码 500ms/1000ms 改为 {@link OpcUaProperties} 注入，
 * 默认值 100ms/50ms 符合 PRD &lt;100ms 契约；新增 {@code @PreDestroy} 销毁回调，
 * 应用关闭时显式释放所有 OpcUaClient 连接，避免连接泄漏。</p>
 */
@Component
public class OpcUaSubscriber {

    private static final Logger log = LoggerFactory.getLogger(OpcUaSubscriber.class);

    /** OPC UA 采样参数（P0-6 配置化，替代原硬编码常量） */
    private final OpcUaProperties properties;

    /** endpointUrl -> client，用于去重与关闭 */
    private final Map<String, OpcUaClient> clients = new ConcurrentHashMap<>();

    public OpcUaSubscriber(OpcUaProperties properties) {
        this.properties = properties;
    }

    /**
     * 连接 OPC UA Server 并对指定节点建立订阅，节点值变化时回调 callback。
     *
     * <p>nodeIdToDatapointCode 的遍历顺序与 createMonitoredItems 返回的监控项顺序一致，
     * 回调通过 {@link ItemCreationCallback} 的 index 参数匹配采集点编码。</p>
     *
     * @param endpointUrl           OPC UA 端点 URL
     * @param nodeIdToDatapointCode NodeId 字符串 -> 采集点编码
     * @param deviceId              设备 ID（仅用于日志）
     * @param callback              值变化回调：accept(datapointCode, value)
     */
    public void subscribe(String endpointUrl, Map<String, String> nodeIdToDatapointCode,
                          Long deviceId, BiConsumer<String, String> callback) {
        if (endpointUrl == null || endpointUrl.isBlank()) {
            log.warn("OPC UA 订阅跳过：endpointUrl 为空 deviceId={}", deviceId);
            return;
        }
        if (nodeIdToDatapointCode == null || nodeIdToDatapointCode.isEmpty()) {
            log.warn("OPC UA 订阅跳过：采集点为空 deviceId={} endpoint={}", deviceId, endpointUrl);
            return;
        }
        try {
            OpcUaClient client = createClient(endpointUrl);
            client.connect().get();
            clients.put(endpointUrl, client);

            UaSubscription subscription = client.getSubscriptionManager()
                    .createSubscription(properties.getPublishingIntervalMs()).get();

            List<String> nodeIds = new ArrayList<>(nodeIdToDatapointCode.keySet());
            List<String> datapointCodes = new ArrayList<>(nodeIdToDatapointCode.values());
            List<MonitoredItemCreateRequest> requests = new ArrayList<>(nodeIds.size());
            for (String nodeIdStr : nodeIds) {
                NodeId nodeId = NodeId.parseOrNull(nodeIdStr);
                if (nodeId == null) {
                    log.warn("OPC UA NodeId 解析失败，跳过 deviceId={} nodeId={}", deviceId, nodeIdStr);
                    continue;
                }
                ReadValueId readValueId = new ReadValueId(
                        nodeId, AttributeId.Value.uid(), null, QualifiedName.NULL_VALUE);
                UInteger clientHandle = subscription.nextClientHandle();
                MonitoringParameters parameters = new MonitoringParameters(
                        clientHandle, properties.getSamplingIntervalMs(), null,
                        Unsigned.uint(properties.getQueueSize()), true);
                requests.add(new MonitoredItemCreateRequest(
                        readValueId, MonitoringMode.Reporting, parameters));
            }
            if (requests.isEmpty()) {
                log.warn("OPC UA 无可用监控项，关闭连接 deviceId={} endpoint={}", deviceId, endpointUrl);
                client.disconnect();
                clients.remove(endpointUrl);
                return;
            }

            ItemCreationCallback itemCallback = buildItemCreationCallback(datapointCodes, callback);
            subscription.createMonitoredItems(TimestampsToReturn.Both, requests, itemCallback).get();

            log.info("OPC UA 订阅建立成功 deviceId={} endpoint={} 监控项数={} publishingMs={} samplingMs={}",
                    deviceId, endpointUrl, requests.size(),
                    properties.getPublishingIntervalMs(), properties.getSamplingIntervalMs());
        } catch (Exception e) {
            // 连接/订阅失败仅记录日志，不抛出，避免影响其他设备订阅
            log.error("OPC UA 订阅建立失败 deviceId={} endpoint={} 原因={}",
                    deviceId, endpointUrl, e.getMessage(), e);
        }
    }

    /**
     * 关闭指定 endpoint 的连接。
     *
     * @param endpointUrl OPC UA 端点 URL
     */
    public void disconnect(String endpointUrl) {
        OpcUaClient client = clients.remove(endpointUrl);
        if (client != null) {
            try {
                client.disconnect().get(30, TimeUnit.SECONDS);
                log.info("OPC UA 连接已关闭 endpoint={}", endpointUrl);
            } catch (Exception e) {
                log.error("OPC UA 连接关闭失败 endpoint={} 原因={}", endpointUrl, e.getMessage(), e);
            }
        }
    }

    /**
     * 关闭全部已建立的连接。
     */
    public void disconnectAll() {
        for (String endpointUrl : new HashSet<>(clients.keySet())) {
            disconnect(endpointUrl);
        }
    }

    /**
     * 应用关闭时显式释放所有 OpcUaClient 连接（P0-6 修复，避免连接泄漏）。
     *
     * <p>Spring 容器销毁时由 {@link PreDestroy} 回调触发。</p>
     */
    @PreDestroy
    public void destroy() {
        log.info("OPC UA Subscriber 销毁：关闭所有连接 count={}", clients.size());
        disconnectAll();
    }

    /**
     * 构造监控项创建回调：在监控项创建时，按 index 匹配采集点编码并注册值变化消费者。
     *
     * <p>包级可见以便单元测试直接验证回调逻辑，无需真实 OPC UA Server。</p>
     *
     * @param datapointCodes 与 createMonitoredItems 请求顺序对齐的采集点编码列表
     * @param callback       值变化回调
     * @return Milo 监控项创建回调
     */
    ItemCreationCallback buildItemCreationCallback(List<String> datapointCodes,
                                                   BiConsumer<String, String> callback) {
        return (UaMonitoredItem item, int index) -> {
            if (index < 0 || index >= datapointCodes.size()) {
                log.warn("OPC UA 监控项索引越界 index={} size={}", index, datapointCodes.size());
                return;
            }
            String datapointCode = datapointCodes.get(index);
            item.setValueConsumer((DataValue value) -> {
                String strValue = extractValue(value);
                if (strValue != null) {
                    callback.accept(datapointCode, strValue);
                }
            });
        };
    }

    /**
     * 将 {@link DataValue} 转换为字符串值。
     *
     * <p>空值或状态非 Good 时返回 null。包级可见以便单元测试。</p>
     *
     * @param value Milo 数据值
     * @return 字符串形式的值；不可用返回 null
     */
    String extractValue(DataValue value) {
        if (value == null) {
            return null;
        }
        Variant variant = value.getValue();
        if (variant == null || variant.isNull()) {
            return null;
        }
        Object v = variant.getValue();
        if (v == null) {
            return null;
        }
        StatusCode status = value.getStatusCode();
        if (status != null && !status.isGood()) {
            log.debug("OPC UA 数据状态非 Good，跳过 status={}", status);
            return null;
        }
        return String.valueOf(v);
    }

    /**
     * 客户端工厂方法，可由子类/测试覆写以注入 mock 客户端。
     *
     * @param endpointUrl OPC UA 端点 URL
     * @return 已配置未连接的 OpcUaClient
     * @throws Exception 创建失败时抛出
     */
    protected OpcUaClient createClient(String endpointUrl) throws Exception {
        return OpcUaClient.create(endpointUrl);
    }
}
