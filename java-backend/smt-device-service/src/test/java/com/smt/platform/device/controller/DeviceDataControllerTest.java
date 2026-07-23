package com.smt.platform.device.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.smt.platform.common.exception.GlobalExceptionHandler;
import com.smt.platform.device.model.entity.DeviceData;
import com.smt.platform.device.service.DeviceDataService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * DeviceDataController MockMvc 测试（standalone，不加载 Spring 上下文）。
 */
@ExtendWith(MockitoExtension.class)
class DeviceDataControllerTest {

    @Mock
    private DeviceDataService deviceDataService;

    @InjectMocks
    private DeviceDataController deviceDataController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(deviceDataController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Nested
    @DisplayName("history")
    class HistoryTest {

        @Test
        @DisplayName("should return page when query history data")
        void shouldReturnPage_whenQueryHistoryData() throws Exception {
            Page<DeviceData> page = new Page<>(1, 100);
            DeviceData data = new DeviceData();
            data.setId(1L);
            data.setDeviceId(1L);
            data.setDatapointCode("TEMP-001");
            page.setRecords(List.of(data));
            page.setTotal(1L);
            when(deviceDataService.queryHistory(
                    eq(1L), eq("TEMP-001"), any(LocalDateTime.class), any(LocalDateTime.class),
                    eq(1), eq(100)))
                    .thenReturn(page);

            mockMvc.perform(get("/api/device/1/data")
                            .param("datapointCode", "TEMP-001")
                            .param("startTime", "2026-07-01T00:00:00")
                            .param("endTime", "2026-07-22T23:59:59")
                            .param("page", "1")
                            .param("size", "100"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data.records[0].datapointCode").value("TEMP-001"))
                    .andExpect(jsonPath("$.data.total").value(1));
        }

        @Test
        @DisplayName("should return empty page when no data")
        void shouldReturnEmptyPage_whenNoData() throws Exception {
            Page<DeviceData> page = new Page<>(1, 100);
            page.setRecords(List.of());
            page.setTotal(0L);
            when(deviceDataService.queryHistory(
                    anyLong(), anyString(), any(LocalDateTime.class), any(LocalDateTime.class),
                    anyInt(), anyInt()))
                    .thenReturn(page);

            mockMvc.perform(get("/api/device/1/data")
                            .param("datapointCode", "TEMP-001")
                            .param("startTime", "2026-07-01T00:00:00")
                            .param("endTime", "2026-07-22T23:59:59"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data.records").isEmpty())
                    .andExpect(jsonPath("$.data.total").value(0));
        }
    }
}
