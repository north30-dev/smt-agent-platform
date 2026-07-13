package com.smt.platform.device.collect.opcua;

import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaMonitoredItem;
import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaSubscription.ItemCreationCallback;
import org.eclipse.milo.opcua.stack.core.types.builtin.DataValue;
import org.eclipse.milo.opcua.stack.core.types.builtin.Variant;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * OpcUaSubscriber 单元测试。
 */
class OpcUaSubscriberTest {

    private final OpcUaSubscriber subscriber = new OpcUaSubscriber(new OpcUaProperties());

    @Nested
    @DisplayName("extractValue")
    class ExtractValueTest {

        @Test
        @DisplayName("should convert numeric variant to string when default")
        void shouldConvertNumericVariantToString_whenDefault() {
            DataValue dv = new DataValue(new Variant(75.5));
            assertThat(subscriber.extractValue(dv)).isEqualTo("75.5");
        }

        @Test
        @DisplayName("should return string variant as-is when default")
        void shouldReturnStringVariantAsIs_whenDefault() {
            DataValue dv = new DataValue(new Variant("hello"));
            assertThat(subscriber.extractValue(dv)).isEqualTo("hello");
        }

        @Test
        @DisplayName("should convert boolean variant to string when default")
        void shouldConvertBooleanVariantToString_whenDefault() {
            DataValue dv = new DataValue(new Variant(true));
            assertThat(subscriber.extractValue(dv)).isEqualTo("true");
        }

        @Test
        @DisplayName("should return null when input is null")
        void shouldReturnNull_whenInputIsNull() {
            assertThat(subscriber.extractValue(null)).isNull();
        }

        @Test
        @DisplayName("should return null when variant is empty")
        void shouldReturnNull_whenVariantIsEmpty() {
            DataValue dv = new DataValue(Variant.NULL_VALUE);
            assertThat(subscriber.extractValue(dv)).isNull();
        }
    }

    @Nested
    @DisplayName("buildItemCreationCallback")
    class BuildItemCreationCallbackTest {

        @Test
        @SuppressWarnings("unchecked")
        @DisplayName("should trigger user callback by index when value changes")
        void shouldTriggerUserCallbackByIndex_whenValueChanges() {
            BiConsumer<String, String> userCallback = mock(BiConsumer.class);
            List<String> datapointCodes = List.of("DEV-TEMP", "DEV-VIB");

            ItemCreationCallback itemCallback =
                    subscriber.buildItemCreationCallback(datapointCodes, userCallback);

            UaMonitoredItem item = mock(UaMonitoredItem.class);
            itemCallback.onItemCreated(item, 0);

            ArgumentCaptorHolder<Consumer<DataValue>> holder = captureValueConsumer(item);
            holder.captured.accept(new DataValue(new Variant(80.0)));

            verify(userCallback).accept("DEV-TEMP", "80.0");
        }

        @Test
        @SuppressWarnings("unchecked")
        @DisplayName("should match second datapoint by index when value changes")
        void shouldMatchSecondDatapointByIndex_whenValueChanges() {
            BiConsumer<String, String> userCallback = mock(BiConsumer.class);
            List<String> datapointCodes = List.of("DEV-TEMP", "DEV-VIB");

            ItemCreationCallback itemCallback =
                    subscriber.buildItemCreationCallback(datapointCodes, userCallback);

            UaMonitoredItem item = mock(UaMonitoredItem.class);
            itemCallback.onItemCreated(item, 1);

            ArgumentCaptorHolder<Consumer<DataValue>> holder = captureValueConsumer(item);
            holder.captured.accept(new DataValue(new Variant(6.2)));

            verify(userCallback).accept("DEV-VIB", "6.2");
        }

        @Test
        @DisplayName("should not register or trigger when index is out of bounds")
        void shouldNotRegisterOrTrigger_whenIndexOutOfBounds() {
            BiConsumer<String, String> userCallback = mock(BiConsumer.class);
            List<String> datapointCodes = List.of("DEV-TEMP");

            ItemCreationCallback itemCallback =
                    subscriber.buildItemCreationCallback(datapointCodes, userCallback);

            UaMonitoredItem item = mock(UaMonitoredItem.class);
            itemCallback.onItemCreated(item, 99);

            verifyNoInteractions(item);
            verifyNoInteractions(userCallback);
        }

        @Test
        @SuppressWarnings("unchecked")
        @DisplayName("should not trigger callback when value is null")
        void shouldNotTriggerCallback_whenValueIsNull() {
            BiConsumer<String, String> userCallback = mock(BiConsumer.class);
            List<String> datapointCodes = List.of("DEV-TEMP");

            ItemCreationCallback itemCallback =
                    subscriber.buildItemCreationCallback(datapointCodes, userCallback);

            UaMonitoredItem item = mock(UaMonitoredItem.class);
            itemCallback.onItemCreated(item, 0);

            ArgumentCaptorHolder<Consumer<DataValue>> holder = captureValueConsumer(item);
            holder.captured.accept(new DataValue(Variant.NULL_VALUE));

            verifyNoInteractions(userCallback);
        }
    }

    @SuppressWarnings("unchecked")
    private ArgumentCaptorHolder<Consumer<DataValue>> captureValueConsumer(UaMonitoredItem item) {
        org.mockito.ArgumentCaptor<Consumer<DataValue>> captor =
                org.mockito.ArgumentCaptor.forClass(Consumer.class);
        verify(item).setValueConsumer(captor.capture());
        ArgumentCaptorHolder<Consumer<DataValue>> holder = new ArgumentCaptorHolder<>();
        holder.captured = captor.getValue();
        return holder;
    }

    private static class ArgumentCaptorHolder<T> {
        T captured;
    }
}
