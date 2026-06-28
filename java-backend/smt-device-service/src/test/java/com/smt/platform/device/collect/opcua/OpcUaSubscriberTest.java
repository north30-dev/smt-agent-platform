package com.smt.platform.device.collect.opcua;

import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaMonitoredItem;
import org.eclipse.milo.opcua.sdk.client.api.subscriptions.UaSubscription.ItemCreationCallback;
import org.eclipse.milo.opcua.stack.core.types.builtin.DataValue;
import org.eclipse.milo.opcua.stack.core.types.builtin.Variant;
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
 *
 * <p>不依赖真实 OPC UA Server：直接验证 extractValue 与 buildItemCreationCallback 的回调逻辑，
 * 用 Mockito mock {@link UaMonitoredItem}（接口）捕获值变化消费者并触发，离线即可通过。</p>
 */
class OpcUaSubscriberTest {

    private final OpcUaSubscriber subscriber = new OpcUaSubscriber();

    // ---------------- extractValue ----------------

    @Test
    void extractValue_应将数值型Variant转为字符串() {
        DataValue dv = new DataValue(new Variant(75.5));
        assertThat(subscriber.extractValue(dv)).isEqualTo("75.5");
    }

    @Test
    void extractValue_应将字符串型Variant原样返回() {
        DataValue dv = new DataValue(new Variant("hello"));
        assertThat(subscriber.extractValue(dv)).isEqualTo("hello");
    }

    @Test
    void extractValue_应将布尔型Variant转为字符串() {
        DataValue dv = new DataValue(new Variant(true));
        assertThat(subscriber.extractValue(dv)).isEqualTo("true");
    }

    @Test
    void extractValue_null入参应返回null() {
        assertThat(subscriber.extractValue(null)).isNull();
    }

    @Test
    void extractValue_空Variant应返回null() {
        DataValue dv = new DataValue(Variant.NULL_VALUE);
        assertThat(subscriber.extractValue(dv)).isNull();
    }

    // ---------------- buildItemCreationCallback ----------------

    @Test
    @SuppressWarnings("unchecked")
    void buildItemCreationCallback_值变化时应按索引触发用户回调() {
        BiConsumer<String, String> userCallback = mock(BiConsumer.class);
        List<String> datapointCodes = List.of("DEV-TEMP", "DEV-VIB");

        ItemCreationCallback itemCallback =
                subscriber.buildItemCreationCallback(datapointCodes, userCallback);

        UaMonitoredItem item = mock(UaMonitoredItem.class);
        // 触发第 1 个监控项（index=0）的创建
        itemCallback.onItemCreated(item, 0);

        // 捕获注册到监控项上的值变化消费者
        ArgumentCaptorHolder<Consumer<DataValue>> holder = captureValueConsumer(item);
        // 模拟 OPC UA Server 推送值变化
        holder.captured.accept(new DataValue(new Variant(80.0)));

        verify(userCallback).accept("DEV-TEMP", "80.0");
    }

    @Test
    @SuppressWarnings("unchecked")
    void buildItemCreationCallback_应按正确索引匹配第二个采集点() {
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
    void buildItemCreationCallback_索引越界时不注册消费者也不触发回调() {
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
    void buildItemCreationCallback_值消费者收到空值时不应触发回调() {
        BiConsumer<String, String> userCallback = mock(BiConsumer.class);
        List<String> datapointCodes = List.of("DEV-TEMP");

        ItemCreationCallback itemCallback =
                subscriber.buildItemCreationCallback(datapointCodes, userCallback);

        UaMonitoredItem item = mock(UaMonitoredItem.class);
        itemCallback.onItemCreated(item, 0);

        ArgumentCaptorHolder<Consumer<DataValue>> holder = captureValueConsumer(item);
        // 推送空 Variant，extractValue 返回 null，不应触发回调
        holder.captured.accept(new DataValue(Variant.NULL_VALUE));

        verifyNoInteractions(userCallback);
    }

    /**
     * 捕获注册到 mock 监控项上的值变化消费者（Consumer&lt;DataValue&gt; 重载）。
     */
    @SuppressWarnings("unchecked")
    private ArgumentCaptorHolder<Consumer<DataValue>> captureValueConsumer(UaMonitoredItem item) {
        org.mockito.ArgumentCaptor<Consumer<DataValue>> captor =
                org.mockito.ArgumentCaptor.forClass(Consumer.class);
        verify(item).setValueConsumer(captor.capture());
        ArgumentCaptorHolder<Consumer<DataValue>> holder = new ArgumentCaptorHolder<>();
        holder.captured = captor.getValue();
        return holder;
    }

    /** 简单持有者，便于在方法间传递捕获到的消费者。 */
    private static class ArgumentCaptorHolder<T> {
        T captured;
    }
}
