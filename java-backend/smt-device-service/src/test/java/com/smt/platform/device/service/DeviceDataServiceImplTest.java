package com.smt.platform.device.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.repository.InfluxDBRepository;
import com.smt.platform.device.service.impl.DeviceDataServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * DeviceDataServiceImpl 单元测试。
 */
@ExtendWith(MockitoExtension.class)
class DeviceDataServiceImplTest {

    @Mock
    private DeviceMapper deviceMapper;

    @Mock
    private DeviceDataMapper deviceDataMapper;

    @Mock
    private InfluxDBRepository influxDBRepository;

    @InjectMocks
    private DeviceDataServiceImpl service;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "baseMapper", deviceDataMapper);
    }

    @Nested
    @DisplayName("saveData")
    class SaveDataTest {

        @Test
        @DisplayName("should insert data when default")
        void shouldInsert_whenDefault() {
            when(deviceDataMapper.insert(any(DeviceData.class))).thenReturn(1);

            LocalDateTime ts = LocalDateTime.now();
            service.saveData(1L, "TEMP-01", "42.5", ts);

            verify(deviceDataMapper).insert(any(DeviceData.class));
            verify(influxDBRepository).writeDeviceData(1L, "TEMP-01", "42.5", ts);
        }
    }

    @Nested
    @DisplayName("queryHistory")
    class QueryHistoryTest {

        @Test
        @DisplayName("should return page when device exists")
        void shouldReturnPage_whenDeviceExists() {
            Device existing = new Device();
            existing.setId(1L);
            when(deviceMapper.selectById(1L)).thenReturn(existing);
            Page<DeviceData> page = new Page<>(1, 100);
            page.setRecords(List.of(new DeviceData()));
            page.setTotal(1L);
            when(deviceDataMapper.selectPage(any(), any())).thenReturn(page);

            IPage<DeviceData> result = service.queryHistory(1L, "TEMP-01",
                    LocalDateTime.of(2026, 6, 27, 0, 0),
                    LocalDateTime.of(2026, 6, 27, 23, 59), 1, 100);

            assertThat(result.getRecords()).hasSize(1);
            assertThat(result.getTotal()).isEqualTo(1L);
        }

        @Test
        @DisplayName("should throw BizException when device does not exist")
        void shouldThrowBizException_whenDeviceNotExists() {
            when(deviceMapper.selectById(1L)).thenReturn(null);

            assertThatThrownBy(() -> service.queryHistory(1L, "TEMP-01",
                    LocalDateTime.of(2026, 6, 27, 0, 0),
                    LocalDateTime.of(2026, 6, 27, 23, 59), 1, 100))
                    .isInstanceOf(BizException.class)
                    .hasMessageContaining("设备不存在");
        }

        @Test
        @DisplayName("should throw BizException when time is inverted")
        void shouldThrowBizException_whenTimeInverted() {
            assertThatThrownBy(() -> service.queryHistory(1L, "TEMP-01",
                    LocalDateTime.of(2026, 6, 27, 23, 59),
                    LocalDateTime.of(2026, 6, 27, 0, 0), 1, 100))
                    .isInstanceOf(BizException.class)
                    .hasMessageContaining("起始时间不能晚于结束时间");
        }
    }
}
