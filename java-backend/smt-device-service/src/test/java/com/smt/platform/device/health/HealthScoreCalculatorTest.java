package com.smt.platform.device.health;

import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * HealthScoreCalculator 单元测试。
 */
@ExtendWith(MockitoExtension.class)
class HealthScoreCalculatorTest {

    @Mock
    private DeviceService deviceService;

    @Mock
    private DeviceMapper deviceMapper;

    @Mock
    private DeviceDataMapper deviceDataMapper;

    @Mock
    private HealthScoreProperties props;

    @InjectMocks
    private HealthScoreCalculator calculator;

    @BeforeEach
    void setUp() {
        lenient().when(props.getScoreMaintenance()).thenReturn(30);
        lenient().when(props.getScoreStopped()).thenReturn(50);
        lenient().when(props.getBaseScore()).thenReturn(100);
        lenient().when(props.getScoreMax()).thenReturn(100);
        lenient().when(props.getScoreMin()).thenReturn(0);
        lenient().when(props.getRecentWindowMinutes()).thenReturn(5L);
        lenient().when(props.getTempThresholdLow()).thenReturn(80.0);
        lenient().when(props.getTempThresholdHigh()).thenReturn(100.0);
        lenient().when(props.getVibThresholdLow()).thenReturn(10.0);
        lenient().when(props.getVibThresholdHigh()).thenReturn(20.0);
        lenient().when(props.getDeductionHigh()).thenReturn(40);
        lenient().when(props.getDeductionLow()).thenReturn(20);
    }

    @Nested
    @DisplayName("calculate")
    class CalculateTest {

        @Test
        @DisplayName("should return 100 when running and no data")
        void shouldReturn100_whenRunningAndNoData() {
            Device d = buildDevice("RUNNING");
            assertThat(calculator.calculate(d, List.of())).isEqualTo(100);
        }

        @Test
        @DisplayName("should return 80 when temperature above 80")
        void shouldReturn80_whenTempAbove80() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(buildData("TEMP-01", "85"));
            assertThat(calculator.calculate(d, data)).isEqualTo(80);
        }

        @Test
        @DisplayName("should return 60 when temperature above 100")
        void shouldReturn60_whenTempAbove100() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(buildData("TEMP-01", "105"));
            assertThat(calculator.calculate(d, data)).isEqualTo(60);
        }

        @Test
        @DisplayName("should return 80 when vibration above 10")
        void shouldReturn80_whenVibrationAbove10() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(buildData("VIBRATION-01", "15"));
            assertThat(calculator.calculate(d, data)).isEqualTo(80);
        }

        @Test
        @DisplayName("should return 40 when temperature 85 and vibration 25")
        void shouldReturn40_whenTemp85AndVibration25() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(
                    buildData("TEMP-01", "85"),
                    buildData("VIBRATION-01", "25")
            );
            assertThat(calculator.calculate(d, data)).isEqualTo(40);
        }

        @Test
        @DisplayName("should return 30 when maintenance")
        void shouldReturn30_whenMaintenance() {
            Device d = buildDevice("MAINTENANCE");
            assertThat(calculator.calculate(d, List.of())).isEqualTo(30);
        }

        @Test
        @DisplayName("should return 50 when stopped")
        void shouldReturn50_whenStopped() {
            Device d = buildDevice("STOPPED");
            assertThat(calculator.calculate(d, List.of())).isEqualTo(50);
        }

        @Test
        @DisplayName("should ignore non-numeric value when default")
        void shouldIgnoreNonNumericValue_whenDefault() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(buildData("TEMP-01", "abc"));
            assertThat(calculator.calculate(d, data)).isEqualTo(100);
        }

        @Test
        @DisplayName("should only use latest value per datapoint when duplicate exists")
        void shouldOnlyUseLatestPerDatapoint_whenDuplicateExists() {
            Device d = buildDevice("RUNNING");
            List<DeviceData> data = List.of(
                    buildData("TEMP-01", "85", LocalDateTime.of(2026, 6, 27, 10, 0)),
                    buildData("TEMP-01", "90", LocalDateTime.of(2026, 6, 27, 10, 5))
            );
            assertThat(calculator.calculate(d, data)).isEqualTo(80);
        }
    }

    @Nested
    @DisplayName("refreshHealthScore")
    class RefreshHealthScoreTest {

        @Test
        @DisplayName("should skip and not update when device does not exist")
        void shouldSkipAndNotUpdate_whenDeviceNotExists() {
            when(deviceService.getById(1L)).thenReturn(null);

            calculator.refreshHealthScore(1L);

            verify(deviceMapper, never()).updateById(any(Device.class));
        }

        @Test
        @DisplayName("should update health score when maintenance")
        void shouldUpdateHealthScore_whenMaintenance() {
            Device d = buildDevice("MAINTENANCE");
            when(deviceService.getById(1L)).thenReturn(d);

            calculator.refreshHealthScore(1L);

            ArgumentCaptor<Device> captor = ArgumentCaptor.forClass(Device.class);
            verify(deviceMapper).updateById(captor.capture());
            Device updated = captor.getValue();
            assertThat(updated.getId()).isEqualTo(1L);
            assertThat(updated.getHealthScore()).isEqualTo(30);
        }
    }

    private Device buildDevice(String status) {
        Device d = new Device();
        d.setId(1L);
        d.setStatus(status);
        return d;
    }

    private DeviceData buildData(String code, String value) {
        return buildData(code, value, null);
    }

    private DeviceData buildData(String code, String value, LocalDateTime timestamp) {
        DeviceData d = new DeviceData();
        d.setDatapointCode(code);
        d.setValue(value);
        d.setTimestamp(timestamp);
        return d;
    }
}
