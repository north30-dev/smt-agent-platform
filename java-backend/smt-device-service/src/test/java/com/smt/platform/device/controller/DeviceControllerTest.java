package com.smt.platform.device.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.exception.GlobalExceptionHandler;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.service.DeviceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
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
        mockMvc = MockMvcBuilders.standaloneSetup(deviceController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Nested
    @DisplayName("list")
    class ListTest {

        @Test
        @DisplayName("should return page result when default")
        void shouldReturnPageResult_whenDefault() throws Exception {
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
    }

    @Nested
    @DisplayName("create")
    class CreateTest {

        @Test
        @DisplayName("should return created device when default")
        void shouldReturnCreatedDevice_whenDefault() throws Exception {
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
    }

    @Nested
    @DisplayName("update")
    class UpdateTest {

        @Test
        @DisplayName("should return updated device when device exists")
        void shouldReturnUpdatedDevice_whenExists() throws Exception {
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
        @DisplayName("should return 404 when device does not exist")
        void shouldReturn404_whenNotExists() throws Exception {
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
    }

    @Nested
    @DisplayName("delete")
    class DeleteTest {

        @Test
        @DisplayName("should return success when default")
        void shouldReturnSuccess_whenDefault() throws Exception {
            when(deviceService.delete(1L)).thenReturn(true);

            mockMvc.perform(delete("/api/device/1"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200));
        }
    }

    @Nested
    @DisplayName("getById")
    class GetByIdTest {

        @Test
        @DisplayName("should return device when device exists")
        void shouldReturnDevice_whenExists() throws Exception {
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
        @DisplayName("should return 404 when device does not exist")
        void shouldReturn404_whenNotExists() throws Exception {
            when(deviceService.getByIdOrThrow(999L))
                    .thenThrow(new BizException(ResultCode.NOT_FOUND, "设备不存在"));

            mockMvc.perform(get("/api/device/999"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.code").value(404))
                    .andExpect(jsonPath("$.message").value("设备不存在"));
        }
    }
}
