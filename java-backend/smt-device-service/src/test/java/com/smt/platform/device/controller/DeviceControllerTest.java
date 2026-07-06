package com.smt.platform.device.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.exception.GlobalExceptionHandler;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.service.DeviceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * DeviceController MockMvc 测试（standalone，不加载 Spring 上下文）。
 *
 * <p>M8 修复：注册 {@link GlobalExceptionHandler} 到 standaloneSetup，使异常分支
 * （404/参数错误）可断言 HTTP 状态码 + body；补全 create/update/delete/getById 四个接口测试。</p>
 */
@ExtendWith(MockitoExtension.class)
class DeviceControllerTest {

    @Mock
    private DeviceService deviceService;

    @InjectMocks
    private DeviceController deviceController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        // M8/m6 修复：注册 GlobalExceptionHandler，使 BizException → 404 等异常分支可断言
        mockMvc = MockMvcBuilders.standaloneSetup(deviceController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void list_shouldReturnPageResult() throws Exception {
        Page<Device> page = new Page<>(1, 10);
        Device device = new Device();
        device.setId(1L);
        device.setDeviceCode("PRINTER-001");
        device.setDeviceName("1号线印刷机");
        page.setRecords(List.of(device));
        page.setTotal(1L);
        when(deviceService.pageList(1, 10, null, null, null)).thenReturn(page);

        mockMvc.perform(get("/api/device/list")
                        .param("page", "1")
                        .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.records[0].deviceCode").value("PRINTER-001"))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.page").value(1))
                .andExpect(jsonPath("$.data.size").value(10));
    }

    // -------- M8 补充：create / update / delete / getById --------

    @Test
    void create_shouldReturnCreatedDevice() throws Exception {
        Device created = new Device();
        created.setId(1L);
        created.setDeviceCode("PRINTER-001");
        created.setDeviceName("1号线印刷机");
        created.setDeviceType("PRINTER");
        created.setStatus("RUNNING");
        when(deviceService.create(any(Device.class))).thenReturn(created);

        String json = "{\"deviceCode\":\"PRINTER-001\",\"deviceName\":\"1号线印刷机\","
                + "\"deviceType\":\"PRINTER\",\"productionLine\":\"LINE-1\","
                + "\"ipAddress\":\"192.168.1.1\",\"protocolType\":\"MQTT\","
                + "\"status\":\"RUNNING\"}";

        mockMvc.perform(post("/api/device")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.deviceCode").value("PRINTER-001"))
                .andExpect(jsonPath("$.data.id").value(1));
    }

    @Test
    void update_shouldReturnUpdatedDevice() throws Exception {
        Device updated = new Device();
        updated.setId(1L);
        updated.setDeviceCode("PRINTER-001");
        updated.setDeviceName("新名称");
        updated.setStatus("STOPPED");
        when(deviceService.update(eq(1L), any(Device.class))).thenReturn(updated);

        String json = "{\"deviceName\":\"新名称\",\"status\":\"STOPPED\"}";

        mockMvc.perform(put("/api/device/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.deviceName").value("新名称"))
                .andExpect(jsonPath("$.data.status").value("STOPPED"));
    }

    @Test
    void update_shouldReturn404_whenNotExists() throws Exception {
        when(deviceService.update(eq(1L), any(Device.class)))
                .thenThrow(new BizException(ResultCode.NOT_FOUND, "设备不存在"));

        String json = "{\"deviceName\":\"新名称\"}";

        mockMvc.perform(put("/api/device/1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.message").value("设备不存在"));
    }

    @Test
    void delete_shouldReturnSuccess() throws Exception {
        when(deviceService.delete(1L)).thenReturn(true);

        mockMvc.perform(delete("/api/device/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    void getById_shouldReturnDevice() throws Exception {
        Device device = new Device();
        device.setId(1L);
        device.setDeviceCode("PRINTER-001");
        device.setDeviceName("1号线印刷机");
        when(deviceService.getByIdOrThrow(1L)).thenReturn(device);

        mockMvc.perform(get("/api/device/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").value(1))
                .andExpect(jsonPath("$.data.deviceCode").value("PRINTER-001"));
    }

    @Test
    void getById_shouldReturn404_whenNotExists() throws Exception {
        when(deviceService.getByIdOrThrow(999L))
                .thenThrow(new BizException(ResultCode.NOT_FOUND, "设备不存在"));

        mockMvc.perform(get("/api/device/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.message").value("设备不存在"));
    }
}
