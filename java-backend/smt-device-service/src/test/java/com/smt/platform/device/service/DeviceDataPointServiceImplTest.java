package com.smt.platform.device.service;

import com.smt.platform.common.exception.BizException;
import com.smt.platform.device.mapper.DeviceDataPointMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.impl.DeviceDataPointServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * DeviceDataPointServiceImpl 单元测试。
 */
@ExtendWith(MockitoExtension.class)
class DeviceDataPointServiceImplTest {

    @Mock
    private DeviceMapper deviceMapper;

    @Mock
    private DeviceDataPointMapper deviceDataPointMapper;

    @InjectMocks
    private DeviceDataPointServiceImpl service;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "baseMapper", deviceDataPointMapper);
    }

    @Nested
    @DisplayName("create")
    class CreateTest {

        @Test
        @DisplayName("should insert datapoint when device exists")
        void shouldInsert_whenDeviceExists() {
            Device existing = new Device();
            existing.setId(1L);
            when(deviceMapper.selectById(1L)).thenReturn(existing);
            when(deviceDataPointMapper.insert(any(DeviceDataPoint.class))).thenReturn(1);

            DeviceDataPoint datapoint = new DeviceDataPoint();
            datapoint.setDatapointCode("TEMP-01");
            datapoint.setDatapointName("印刷机温度");
            datapoint.setNodePath("ns=2;s=Temperature");
            datapoint.setDataType("NUMBER");
            datapoint.setSampleIntervalMs(1000);

            DeviceDataPoint created = service.create(1L, datapoint);

            assertThat(created.getDeviceId()).isEqualTo(1L);
            assertThat(created.getDatapointCode()).isEqualTo("TEMP-01");
            assertThat(created.getCreateTime()).isNotNull();
            verify(deviceDataPointMapper).insert(any(DeviceDataPoint.class));
        }

        @Test
        @DisplayName("should throw BizException when device does not exist")
        void shouldThrowBizException_whenDeviceNotExists() {
            when(deviceMapper.selectById(1L)).thenReturn(null);

            DeviceDataPoint datapoint = new DeviceDataPoint();
            datapoint.setDatapointCode("TEMP-01");

            assertThatThrownBy(() -> service.create(1L, datapoint))
                    .isInstanceOf(BizException.class)
                    .hasMessageContaining("设备不存在");
        }
    }

    @Nested
    @DisplayName("listByDeviceId")
    class ListByDeviceIdTest {

        @Test
        @DisplayName("should return list when default")
        void shouldReturnList_whenDefault() {
            DeviceDataPoint datapoint = new DeviceDataPoint();
            datapoint.setDeviceId(1L);
            datapoint.setDatapointCode("TEMP-01");
            when(deviceDataPointMapper.selectList(any())).thenReturn(List.of(datapoint));

            List<DeviceDataPoint> list = service.listByDeviceId(1L);

            assertThat(list).hasSize(1);
            assertThat(list.get(0).getDatapointCode()).isEqualTo("TEMP-01");
        }
    }
}
