package com.smt.platform.device.health;

import com.smt.platform.device.mapper.DeviceDataMapper;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceService;
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
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * HealthScoreCalculator 单元测试。
 *
 * <p>覆盖：运行态无数据 / 温度超阈值 / 振动超阈值 / 温度+振动叠加 /
 * 维修态 / 停机态 / 非数字 value 忽略 / 同一采集点去重 / 设备不存在 /
 * refreshHealthScore 触发 updateById 等场景。</p>
 */
@ExtendWith(MockitoExtension.class)
class HealthScoreCalculatorTest {

    @Mock
    private DeviceService deviceService;

    @Mock
    private DeviceMapper deviceMapper;

    @Mock
    private DeviceDataMapper deviceDataMapper;

    @InjectMocks
    private HealthScoreCalculator calculator;

    // -------- calculate 评分逻辑 --------

    @Test
    void calculate_shouldReturn100_whenRunningAndNoData() {
        Device d = buildDevice("RUNNING");
        assertThat(calculator.calculate(d, List.of())).isEqualTo(100);
    }

    @Test
    void calculate_shouldReturn80_whenTempAbove80() {
        Device d = buildDevice("RUNNING");
        List<DeviceData> data = List.of(buildData("TEMP-01", "85"));
        assertThat(calculator.calculate(d, data)).isEqualTo(80);
    }

    @Test
    void calculate_shouldReturn60_whenTempAbove100() {
        Device d = buildDevice("RUNNING");
        List<DeviceData> data = List.of(buildData("TEMP-01", "105"));
        assertThat(calculator.calculate(d, data)).isEqualTo(60);
    }

    @Test
    void calculate_shouldReturn80_whenVibrationAbove10() {
        Device d = buildDevice("RUNNING");
        List<DeviceData> data = List.of(buildData("VIBRATION-01", "15"));
        assertThat(calculator.calculate(d, data)).isEqualTo(80);
    }

    @Test
    void calculate_shouldReturn40_whenTemp85AndVibration25() {
        Device d = buildDevice("RUNNING");
        List<DeviceData> data = List.of(
                buildData("TEMP-01", "85"),
                buildData("VIBRATION-01", "25")
        );
        // 100 - 20（温度 >80）- 40（振动 >20）= 40
        assertThat(calculator.calculate(d, data)).isEqualTo(40);
    }

    @Test
    void calculate_shouldReturn30_whenMaintenance() {
        Device d = buildDevice("MAINTENANCE");
        assertThat(calculator.calculate(d, List.of())).isEqualTo(30);
    }

    @Test
    void calculate_shouldReturn50_whenStopped() {
        Device d = buildDevice("STOPPED");
        assertThat(calculator.calculate(d, List.of())).isEqualTo(50);
    }

    @Test
    void calculate_shouldIgnoreNonNumericValue() {
        Device d = buildDevice("RUNNING");
        List<DeviceData> data = List.of(buildData("TEMP-01", "abc"));
        assertThat(calculator.calculate(d, data)).isEqualTo(100);
    }

    @Test
    void calculate_shouldOnlyUseLatestPerDatapoint() {
        Device d = buildDevice("RUNNING");
        // 同一采集点 TEMP-01 两条记录，仅取 timestamp 最大者（90，>80）扣 20
        List<DeviceData> data = List.of(
                buildData("TEMP-01", "85", LocalDateTime.of(2026, 6, 27, 10, 0)),
                buildData("TEMP-01", "90", LocalDateTime.of(2026, 6, 27, 10, 5))
        );
        assertThat(calculator.calculate(d, data)).isEqualTo(80);
    }

    // -------- refreshHealthScore 集成 --------

    @Test
    void refreshHealthScore_shouldSkipAndNotUpdate_whenDeviceNotExists() {
        when(deviceService.getById(1L)).thenReturn(null);

        calculator.refreshHealthScore(1L);

        verify(deviceMapper, never()).updateById(any(Device.class));
    }

    @Test
    void refreshHealthScore_shouldUpdateHealthScore_whenMaintenance() {
        Device d = buildDevice("MAINTENANCE");
        when(deviceService.getById(1L)).thenReturn(d);

        calculator.refreshHealthScore(1L);

        ArgumentCaptor<Device> captor = ArgumentCaptor.forClass(Device.class);
        verify(deviceMapper).updateById(captor.capture());
        Device updated = captor.getValue();
        assertThat(updated.getId()).isEqualTo(1L);
        assertThat(updated.getHealthScore()).isEqualTo(30);
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
