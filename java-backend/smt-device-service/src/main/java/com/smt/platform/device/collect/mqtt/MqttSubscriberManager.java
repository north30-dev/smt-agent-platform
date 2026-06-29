package com.smt.platform.device.collect.mqtt;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PreDestroy;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;

/**
 * MQTT 订阅管理器（基于 Eclipse Paho 1.2.5）。
 *
 * <p>封装 {@link MqttClient} 的连接、订阅、发布流程。设备数据到达时通过回调
 * 把（采集点编码, 原始 payload 字符串）交给上层。连接失败仅记录日志不抛出，
 * 避免阻断应用启动或其他设备订阅。docker-compose 当前未编排 MQTT broker，
 * 但本组件代码需支持连接，broker 不可用时仅记日志。</p>
 */
@Component
public class MqttSubscriberManager {

    private static final Logger log = LoggerFactory.getLogger(MqttSubscriberManager.class);

    private final String broker;
    private final String clientIdPrefix;
    private final int qos;
    private final ObjectMapper objectMapper;

    /** topic -> 订阅信息，用于消息到达时路由回调 */
    private final Map<String, SubscriptionInfo> subscriptions = new ConcurrentHashMap<>();

    /** Paho 客户端，懒加载 */
    private MqttClient client;

    public MqttSubscriberManager(
            @Value("${smt.mqtt.broker:tcp://localhost:1883}") String broker,
            @Value("${smt.mqtt.client-id-prefix:smt-device-}") String clientIdPrefix,
            @Value("${smt.mqtt.qos:1}") int qos,
            ObjectMapper objectMapper) {
        this.broker = broker;
        this.clientIdPrefix = clientIdPrefix;
        this.qos = qos;
        this.objectMapper = objectMapper;
    }

    /**
     * 订阅指定 topic，消息到达时回调 callback。
     *
     * @param topic         MQTT topic
     * @param deviceId      设备 ID（仅用于日志）
     * @param datapointCode 采集点编码
     * @param callback      消息回调：accept(datapointCode, payload)
     */
    public void subscribe(String topic, Long deviceId, String datapointCode,
                          BiConsumer<String, String> callback) {
        if (topic == null || topic.isBlank()) {
            log.warn("MQTT 订阅跳过：topic 为空 deviceId={}", deviceId);
            return;
        }
        ensureConnected();
        if (!isConnected()) {
            log.warn("MQTT 未连接，跳过订阅 topic={} deviceId={}", topic, deviceId);
            return;
        }
        try {
            client.subscribe(topic, qos);
            subscriptions.put(topic, new SubscriptionInfo(deviceId, datapointCode, callback));
            log.info("MQTT 订阅成功 topic={} deviceId={} datapointCode={}", topic, deviceId, datapointCode);
        } catch (MqttException e) {
            log.error("MQTT 订阅失败 topic={} deviceId={} 原因={}", topic, deviceId, e.getMessage(), e);
        }
    }

    /**
     * 向指定 topic 发布消息（供 MockMqttPublisher 等复用同一客户端连接）。
     *
     * @param topic   MQTT topic
     * @param payload 消息内容
     */
    public void publish(String topic, String payload) {
        if (topic == null || topic.isBlank() || payload == null) {
            log.warn("MQTT 发布跳过：topic 或 payload 为空 topic={}", topic);
            return;
        }
        ensureConnected();
        if (!isConnected()) {
            log.warn("MQTT 未连接，跳过发布 topic={}", topic);
            return;
        }
        try {
            MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
            message.setQos(qos);
            client.publish(topic, message);
        } catch (MqttException e) {
            log.error("MQTT 发布失败 topic={} 原因={}", topic, e.getMessage(), e);
        }
    }

    /**
     * 解析 MQTT payload 为统一数据点。
     *
     * <p>支持两种格式：</p>
     * <ul>
     *   <li>JSON：{@code {"value":"xxx","timestamp":"2026-06-27T10:00:00"}}，
     *       解析出 value 与 timestamp（timestamp 缺失时取当前时间）</li>
     *   <li>纯文本：直接作为 value，timestamp 取当前时间</li>
     * </ul>
     *
     * <p>公开以便 {@link com.smt.platform.device.collect.MqttDataCollector} 复用，
     * 亦便于单元测试直接验证解析逻辑。</p>
     *
     * @param payload 原始 payload
     * @return 解析结果
     */
    public ParsedPayload parsePayload(String payload) {
        if (payload == null || payload.isBlank()) {
            return new ParsedPayload("", LocalDateTime.now());
        }
        String trimmed = payload.trim();
        if (trimmed.startsWith("{")) {
            try {
                JsonNode node = objectMapper.readTree(trimmed);
                String value = node.hasNonNull("value") ? node.get("value").asText() : "";
                LocalDateTime timestamp = node.hasNonNull("timestamp")
                        ? parseTimestamp(node.get("timestamp").asText())
                        : LocalDateTime.now();
                return new ParsedPayload(value, timestamp);
            } catch (Exception e) {
                log.warn("MQTT payload JSON 解析失败，作为纯文本处理 payload={} 原因={}",
                        payload, e.getMessage());
            }
        }
        return new ParsedPayload(trimmed, LocalDateTime.now());
    }

    private LocalDateTime parseTimestamp(String text) {
        try {
            return LocalDateTime.parse(text);
        } catch (DateTimeParseException e) {
            log.warn("MQTT timestamp 解析失败，使用当前时间 text={} 原因={}", text, e.getMessage());
            return LocalDateTime.now();
        }
    }

    /**
     * 应用关闭时显式断开 MQTT 连接（M5 收尾，避免连接残留）。
     *
     * <p>Spring 容器销毁时由 {@link PreDestroy} 回调触发。
     * client 未创建或未连接时跳过，不抛异常。</p>
     */
    @PreDestroy
    public void destroy() {
        if (client != null && client.isConnected()) {
            try {
                client.disconnect();
                log.info("MQTT 客户端已断开 broker={}", broker);
            } catch (MqttException e) {
                log.warn("MQTT 客户端断开异常 原因={}", e.getMessage());
            }
        }
    }

    /**
     * 确保客户端已连接（懒创建 + 连接）。连接失败仅记录日志，不抛出异常。
     */
    private synchronized void ensureConnected() {
        if (client != null && client.isConnected()) {
            return;
        }
        try {
            if (client == null) {
                String clientId = clientIdPrefix + System.currentTimeMillis();
                client = createClient(broker, clientId);
                client.setCallback(new MqttMessageHandler());
            }
            if (!client.isConnected()) {
                client.connect();
                log.info("MQTT 连接成功 broker={}", broker);
            }
        } catch (MqttException e) {
            log.error("MQTT 连接失败 broker={} 原因={}", broker, e.getMessage(), e);
        }
    }

    private boolean isConnected() {
        return client != null && client.isConnected();
    }

    /**
     * 创建 Paho 客户端。protected 以便单元测试覆写注入 mock 客户端。
     *
     * @param broker   broker 地址
     * @param clientId 客户端 ID
     * @return 未连接的 MqttClient
     * @throws MqttException 创建失败时抛出
     */
    protected MqttClient createClient(String broker, String clientId) throws MqttException {
        return new MqttClient(broker, clientId, new MemoryPersistence());
    }

    /**
     * 注入客户端（仅供单元测试使用，绕过真实连接）。
     *
     * @param client 已 mock 的客户端
     */
    void setClient(MqttClient client) {
        this.client = client;
    }

    /**
     * 处理收到的 MQTT 消息：按 topic 路由到已注册的回调。
     * 包级可见以便单元测试直接触发，无需真实 broker。
     *
     * @param topic   消息 topic
     * @param message Paho 消息
     */
    void handleMessage(String topic, MqttMessage message) {
        SubscriptionInfo info = subscriptions.get(topic);
        if (info == null) {
            log.debug("MQTT 收到未订阅 topic 的消息，忽略 topic={}", topic);
            return;
        }
        String payload = new String(message.getPayload(), StandardCharsets.UTF_8);
        try {
            info.callback.accept(info.datapointCode, payload);
        } catch (Exception e) {
            // 单条消息回调异常不影响后续消息处理
            log.error("MQTT 消息回调处理异常 topic={} datapointCode={} 原因={}",
                    topic, info.datapointCode, e.getMessage(), e);
        }
    }

    /** 订阅信息 */
    private static class SubscriptionInfo {

        final Long deviceId;
        final String datapointCode;
        final BiConsumer<String, String> callback;

        SubscriptionInfo(Long deviceId, String datapointCode, BiConsumer<String, String> callback) {
            this.deviceId = deviceId;
            this.datapointCode = datapointCode;
            this.callback = callback;
        }
    }

    /** 解析后的 payload（统一数据点） */
    public static class ParsedPayload {

        public final String value;
        public final LocalDateTime timestamp;

        public ParsedPayload(String value, LocalDateTime timestamp) {
            this.value = value;
            this.timestamp = timestamp;
        }
    }

    /** Paho 回调实现，将消息委托给 {@link #handleMessage} */
    private class MqttMessageHandler implements MqttCallback {

        @Override
        public void connectionLost(Throwable cause) {
            log.warn("MQTT 连接断开 原因={}", cause == null ? "" : cause.getMessage());
        }

        @Override
        public void messageArrived(String topic, MqttMessage message) {
            handleMessage(topic, message);
        }

        @Override
        public void deliveryComplete(IMqttDeliveryToken token) {
            // 发布完成回调，无需处理
        }
    }
}
