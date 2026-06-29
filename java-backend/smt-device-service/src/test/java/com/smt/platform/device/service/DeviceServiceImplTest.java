package com.smt.platform.device.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.device.mapper.DeviceMapper;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.service.impl.DeviceServiceImpl;
import org.junit.jupiter.api.BeforeEach;
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
 * DeviceServiceImpl 单元测试（Mockito mock DeviceMapper，不依赖真实数据库）。
 */
@ExtendWith(MockitoExtension.class)
class DeviceServiceImplTest {

    @Mock
    private DeviceMapper deviceMapper;

    @InjectMocks
    private DeviceServiceImpl deviceService;

    @BeforeEach
    void setUp() {
        // ServiceImpl.baseMapper 为父类声明的泛型字段（运行期擦除为 BaseMapper），
        // @InjectMocks 字段注入无法可靠注入，这里显式设置。
        ReflectionTestUtils.setField(deviceService, "baseMapper", deviceMapper);
    }

    @Test
    void create_shouldInsert_whenCodeNotExists() {
        Device device = new Device();
        device.setDeviceCode("PRINTER-001");
        device.setDeviceName("1号线印刷机");
        when(deviceMapper.selectCount(any())).thenReturn(0L);
        when(deviceMapper.insert(any(Device.class))).thenReturn(1);

        Device created = deviceService.create(device);

        assertThat(created.getDeviceCode()).isEqualTo("PRINTER-001");
        assertThat(created.getStatus()).isEqualTo("RUNNING");
        assertThat(created.getHealthScore()).isEqualTo(100);
        assertThat(created.getDeleted()).isEqualTo(0);
        assertThat(created.getCreateTime()).isNotNull();
        verify(deviceMapper).insert(any(Device.class));
    }

    @Test
    void create_shouldThrow_whenCodeExists() {
        Device device = new Device();
        device.setDeviceCode("PRINTER-001");
        when(deviceMapper.selectCount(any())).thenReturn(1L);

        assertThatThrownBy(() -> deviceService.create(device))
                .isInstanceOf(BizException.class)
                .hasMessageContaining("设备编码已存在");
    }

    @Test
    void pageList_shouldReturnPage() {
        Page<Device> page = new Page<>(1, 10);
        Device device = new Device();
        device.setId(1L);
        page.setRecords(List.of(device));
        page.setTotal(1L);
        when(deviceMapper.selectPage(any(), any())).thenReturn(page);

        IPage<Device> result = deviceService.pageList(1, 10, null, null, null);

        assertThat(result.getRecords()).hasSize(1);
        assertThat(result.getTotal()).isEqualTo(1L);
    }

    @Test
    void delete_shouldSoftDelete_whenExists() {
        Device existing = new Device();
        existing.setId(1L);
        when(deviceMapper.selectById(1L)).thenReturn(existing);
        when(deviceMapper.deleteById(1L)).thenReturn(1);

        boolean ok = deviceService.delete(1L);

        assertThat(ok).isTrue();
        verify(deviceMapper).deleteById(1L);
    }

    @Test
    void delete_shouldThrow_whenNotExists() {
        when(deviceMapper.selectById(1L)).thenReturn(null);

        assertThatThrownBy(() -> deviceService.delete(1L))
                .isInstanceOf(BizException.class)
                .hasMessageContaining("设备不存在");
    }

    // -------- M8 补充：update + getByIdOrThrow --------

    @Test
    void update_shouldUpdateFields_whenExists() {
        Device existing = new Device();
        existing.setId(1L);
        existing.setDeviceCode("PRINTER-001");
        existing.setDeviceName("旧名称");
        existing.setDeviceType("PRINTER");
        existing.setStatus("RUNNING");
        existing.setHealthScore(100);
        when(deviceMapper.selectById(1L)).thenReturn(existing);

        Device patch = new Device();
        patch.setDeviceName("新名称");
        patch.setStatus("STOPPED");
        when(deviceMapper.updateById(any(Device.class))).thenReturn(1);

        Device updated = deviceService.update(1L, patch);

        assertThat(updated.getDeviceName()).isEqualTo("新名称");
        assertThat(updated.getStatus()).isEqualTo("STOPPED");
        // 未传字段保持原值
        assertThat(updated.getDeviceCode()).isEqualTo("PRINTER-001");
        assertThat(updated.getDeviceType()).isEqualTo("PRINTER");
        assertThat(updated.getHealthScore()).isEqualTo(100);
        assertThat(updated.getUpdateTime()).isNotNull();
        verify(deviceMapper).updateById(any(Device.class));
    }

    @Test
    void update_shouldThrow_whenNotExists() {
        when(deviceMapper.selectById(1L)).thenReturn(null);

        Device patch = new Device();
        patch.setDeviceName("新名称");

        assertThatThrownBy(() -> deviceService.update(1L, patch))
                .isInstanceOf(BizException.class)
                .hasMessageContaining("设备不存在");
    }

    @Test
    void getByIdOrThrow_shouldReturnDevice_whenExists() {
        Device device = new Device();
        device.setId(1L);
        device.setDeviceCode("PRINTER-001");
        when(deviceMapper.selectById(1L)).thenReturn(device);

        Device result = deviceService.getByIdOrThrow(1L);

        assertThat(result).isNotNull();
        assertThat(result.getId()).isEqualTo(1L);
        assertThat(result.getDeviceCode()).isEqualTo("PRINTER-001");
    }

    @Test
    void getByIdOrThrow_shouldThrow_whenNotExists() {
        when(deviceMapper.selectById(1L)).thenReturn(null);

        assertThatThrownBy(() -> deviceService.getByIdOrThrow(1L))
                .isInstanceOf(BizException.class)
                .hasMessageContaining("设备不存在");
    }
}
