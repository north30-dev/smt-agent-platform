package com.smt.platform.device.collect.mqtt;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
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

    @Nested
    @DisplayName("subscribe")
    class SubscribeTest {

        @Test
        @DisplayName("should invoke client subscribe when default")
        void shouldInvokeClientSubscribe_whenDefault() throws Exception {
            @SuppressWarnings("unchecked")
            BiConsumer<String, String> callback = mock(BiConsumer.class);

            manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

            verify(mockClient).subscribe("smt/device/1/temperature", 1);
        }

        @Test
        @DisplayName("should skip when topic is empty")
        void shouldSkip_whenEmptyTopic() {
            @SuppressWarnings("unchecked")
            BiConsumer<String, String> callback = mock(BiConsumer.class);

            manager.subscribe("", 1L, "temperature", callback);

            verifyNoInteractions(callback);
        }
    }

    @Nested
    @DisplayName("handleMessage")
    class HandleMessageTest {

        @Test
        @DisplayName("should route by topic and pass original payload when subscribed")
        void shouldRouteByTopicAndPassOriginalPayload_whenSubscribed() {
            @SuppressWarnings("unchecked")
            BiConsumer<String, String> callback = mock(BiConsumer.class);
            manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

            String payload = "{\"value\":\"75.5\",\"timestamp\":\"2026-06-27T10:00:00\"}";
            MqttMessage message = new MqttMessage(payload.getBytes(StandardCharsets.UTF_8));
            manager.handleMessage("smt/device/1/temperature", message);

            verify(callback).accept("temperature", payload);
        }

        @Test
        @DisplayName("should ignore when topic is not subscribed")
        void shouldIgnore_whenUnsubscribedTopic() {
            @SuppressWarnings("unchecked")
            BiConsumer<String, String> callback = mock(BiConsumer.class);
            manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

            MqttMessage message = new MqttMessage("test".getBytes(StandardCharsets.UTF_8));
            manager.handleMessage("smt/device/1/unknown", message);

            verifyNoInteractions(callback);
        }

        @Test
        @DisplayName("should not propagate when callback throws exception")
        void shouldNotPropagate_whenCallbackThrowsException() {
            @SuppressWarnings("unchecked")
            BiConsumer<String, String> callback = (code, payload) -> {
                throw new RuntimeException("模拟回调异常");
            };
            manager.subscribe("smt/device/1/temperature", 1L, "temperature", callback);

            MqttMessage message = new MqttMessage("test".getBytes(StandardCharsets.UTF_8));
            manager.handleMessage("smt/device/1/temperature", message);
        }
    }

    @Nested
    @DisplayName("publish")
    class PublishTest {

        @Test
        @DisplayName("should invoke client publish when default")
        void shouldInvokeClientPublish_whenDefault() throws Exception {
            manager.publish("smt/device/1/temperature", "{\"value\":\"80\"}");

            verify(mockClient).publish(eq("smt/device/1/temperature"), any(MqttMessage.class));
        }

        @Test
        @DisplayName("should skip when topic or payload is empty")
        void shouldSkip_whenEmptyTopicOrPayload() throws Exception {
            manager.publish("", "payload");
            manager.publish("smt/device/1/temperature", null);

            verify(mockClient, org.mockito.Mockito.never())
                    .publish(any(String.class), any(MqttMessage.class));
        }
    }

    @Nested
    @DisplayName("parsePayload")
    class ParsePayloadTest {

        @Test
        @DisplayName("should parse value and timestamp when standard JSON")
        void shouldParseValueAndTimestamp_whenStandardJson() {
            MqttSubscriberManager.ParsedPayload parsed =
                    manager.parsePayload("{\"value\":\"75.5\",\"timestamp\":\"2026-06-27T10:00:00\"}");

            assertThat(parsed.value).isEqualTo("75.5");
            assertThat(parsed.timestamp).isEqualTo(LocalDateTime.of(2026, 6, 27, 10, 0, 0));
        }

        @Test
        @DisplayName("should convert numeric value to string when default")
        void shouldConvertNumericValueToString_whenDefault() {
            MqttSubscriberManager.ParsedPayload parsed =
                    manager.parsePayload("{\"value\":75.5,\"timestamp\":\"2026-06-27T10:00:00\"}");

            assertThat(parsed.value).isEqualTo("75.5");
        }

        @Test
        @DisplayName("should use as value with current time when plain text")
        void shouldUseAsValueWithCurrentTime_whenPlainText() {
            MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("hello");

            assertThat(parsed.value).isEqualTo("hello");
            assertThat(parsed.timestamp).isNotNull();
        }

        @Test
        @DisplayName("should return empty value when payload is empty")
        void shouldReturnEmptyValue_whenPayloadIsEmpty() {
            MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("");

            assertThat(parsed.value).isEmpty();
        }

        @Test
        @DisplayName("should return empty value when payload is null")
        void shouldReturnEmptyValue_whenPayloadIsNull() {
            MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload(null);

            assertThat(parsed.value).isEmpty();
        }

        @Test
        @DisplayName("should use current time when timestamp is missing")
        void shouldUseCurrentTime_whenTimestampIsMissing() {
            MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("{\"value\":\"42\"}");

            assertThat(parsed.value).isEqualTo("42");
            assertThat(parsed.timestamp).isNotNull();
        }

        @Test
        @DisplayName("should treat as plain text when JSON is invalid")
        void shouldTreatAsPlainText_whenJsonIsInvalid() {
            MqttSubscriberManager.ParsedPayload parsed = manager.parsePayload("{broken");

            assertThat(parsed.value).isEqualTo("{broken");
        }
    }
}
