package com.smt.platform.device.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.device.model.entity.Device;
import com.smt.platform.device.service.DeviceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * DeviceController MockMvc 测试（standalone，不加载 Spring 上下文）。
 *
 * <p>仅验证分页接口的响应结构与 Result 包装。</p>
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
        mockMvc = MockMvcBuilders.standaloneSetup(deviceController).build();
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
}
