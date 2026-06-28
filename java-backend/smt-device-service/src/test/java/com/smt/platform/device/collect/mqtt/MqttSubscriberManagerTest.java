package com.smt.platform.device.collect.mqtt;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.function.BiConsumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * MqttSubscriberManager 单元测试。
 *
 * <p>用 Mockito mock {@link MqttClient}，不依赖真实 MQTT broker。
 * 验证 subscribe 回调路径（消息到达 -> 回调触发）与 payload 解析逻辑。</p>
 */
class MqttSubscriberManagerTest {

    private MqttSubscriberManager manager;
    private MqttClient mockClient;

    @BeforeEach
    void setUp() {
        mockClient = mock(MqttClient.class);
        when(mockClient.isConnected()).thenReturn(true);
        manager = new MqttSubscriberManager("tcp://localhost:1883", "test-", 1, new ObjectMapper());
        manager.setClient(mockClient);
    }

    // ---------------- subscribe 回调路径 ----------------

    @Test
    void subscribe_shouldInvokeClientSubscribe() throws Exception {
        @SuppressWarnings("unchecked")
        BiConsumer<String, String> callback = mock(BiConsumer.class);

        manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

        verify(mockClient).subscribe("smt/device/1/temperature", 1);
    }

    @Test
    void subscribe_emptyTopicShouldSkip() {
        @SuppressWarnings("unchecked")
        BiConsumer<String, String> callback = mock(BiConsumer.class);

        manager.subscribe("", 1L, "temperature", callback);

        verifyNoInteractions(callback);
    }

    @Test
    void handleMessage_shouldRouteByTopicAndPassOriginalPayload() {
        @SuppressWarnings("unchecked")
        BiConsumer<String, String> callback = mock(BiConsumer.class);
        manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

        String payload = "{\"value\":\"75.5\",\"timestamp\":\"2026-06-27T10:00:00\"}";
        MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
        manager.handleMessage("smt/device/1/temperature", message);

        verify(callback).accept("temperature", payload);
    }

    @Test
    void handleMessage_unsubscribedTopicShouldBeIgnored() {
        @SuppressWarnings("unchecked")
        BiConsumer<String, String> callback = mock(BiConsumer.class);
        manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

        MqttMessage message = new MqttMessage("test".getBytes(StandardCharsets.UTF_8));
        manager.handleMessage("smt/device/1/unknown", message);

        verifyNoInteractions(callback);
    }

    @Test
    void handleMessage_callbackExceptionShouldNotPropagate() {
        @SuppressWarnings("unchecked")
        BiConsumer<String, String> callback = (code, payload) -> {
            throw new RuntimeException("模拟回调异常");
        };
        manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

        MqttMessage message = new MqttMessage("test".getBytes(StandardCharsets.UTF_8));
        // 不应抛出异常
        manager.handleMessage("smt/device/1/temperature", message);
    }

    @Test
    void publish_shouldInvokeClientPublish() throws Exception {
        manager.publish("smt/device/1/temperature", "{\"value\":\"80\"}");

        verify(mockClient).publish(eq("smt/device/1/temperature"), any(MqttMessage.class));
    }

    @Test
    void publish_emptyTopicOrPayloadShouldSkip() throws Exception {
        manager.publish("", "payload");
        manager.publish("smt/device/1/temperature", null);

        verify(mockClient, org.mockito.Mockito.never())
                .publish(any(String.class), any(MqttMessage.class));
    }

    // ---------------- parsePayload 解析逻辑 ----------------

    @Test
    void parsePayload_standardJsonShouldParseValueAndTimestamp() {
        MqttSubscriberManager.ParsedPayload parsed =
                manager.parsePayload("{\"value\":\"75.5\",\"timestamp\":\"2026-06-27T10:00:00\"}");

        assertThat(parsed.value).isEqualTo("75.5");
        assertThat(parsed.timestamp).isEqualTo(LocalDateTime.of(2026, 6, 27, 10, 0, 0));
    }

    @Test
    void parsePayload_numericValueShouldBeConvertedToString() {
        MqttSubscriberManager.ParsedPayload parsed =
                manager.parsePayload("{\"value\":75.5,\"timestamp\":\"2026-06-27T10:00:00\"}");

        assertThat(parsed.value).isEqualTo("75.5");
    }

    @Test
    void parsePayload_plainTextShouldBeUsedAsValueWithCurrentTime() {
        MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("hello");

        assertThat(parsed.value).isEqualTo("hello");
        assertThat(parsed.timestamp).isNotNull();
    }

    @Test
    void parsePayload_emptyPayloadShouldReturnEmptyValue() {
        MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("");

        assertThat(parsed.value).isEmpty();
    }

    @Test
    void parsePayload_nullPayloadShouldReturnEmptyValue() {
        MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload(null);

        assertThat(parsed.value).isEmpty();
    }

    @Test
    void parsePayload_missingTimestampShouldUseCurrentTime() {
        MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("{\"value\":\"42\"}");

        assertThat(parsed.value).isEqualTo("42");
        assertThat(parsed.timestamp).isNotNull();
    }

    @Test
    void parsePayload_invalidJsonShouldBeTreatedAsPlainText() {
        MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("{broken");

        assertThat(parsed.value).isEqualTo("{broken");
    }
}
