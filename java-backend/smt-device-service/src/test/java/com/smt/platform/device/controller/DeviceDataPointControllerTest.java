package com.smt.platform.device.controller;

import com.smt.platform.common.exception.BizException;
import com.smt.platform.common.exception.GlobalExceptionHandler;
import com.smt.platform.common.response.ResultCode;
import com.smt.platform.device.model.dto.DataPointCreateDTO;
import com.smt.platform.device.model.entity.DeviceDataPoint;
import com.smt.platform.device.service.DeviceDataPointService;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * DeviceDataPointController MockMvc 测试（standalone，不加载 Spring 上下文）。
 */
@ExtendWith(MockitoExtension.class)
class DeviceDataPointControllerTest {

    @Mock
    private DeviceDataPointService deviceDataPointService;

    @InjectMocks
    private DeviceDataPointController deviceDataPointController;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(deviceDataPointController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Nested
    @DisplayName("list")
    class ListTest {

        @Test
        @DisplayName("should return datapoints when device exists")
        void shouldReturnDatapoints_whenDeviceExists() throws Exception {
            DeviceDataPoint dp1 = new DeviceDataPoint();
            dp1.setId(1L);
            dp1.setDatapointCode("TEMP-001");
            dp1.setDeviceId(1L);
            DeviceDataPoint dp2 = new DeviceDataPoint();
            dp2.setId(2L);
            dp2.setDatapointCode("VIB-001");
            dp2.setDeviceId(1L);
            when(deviceDataPointService.listByDeviceId(1L)).thenReturn(List.of(dp1, dp2));

            mockMvc.perform(get("/api/device/1/datapoints"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data.length()").value(2))
                    .andExpect(jsonPath("$.data[0].datapointCode").value("TEMP-001"))
                    .andExpect(jsonPath("$.data[1].datapointCode").value("VIB-001"));
        }

        @Test
        @DisplayName("should return empty list when no datapoints")
        void shouldReturnEmptyList_whenNoDatapoints() throws Exception {
            when(deviceDataPointService.listByDeviceId(999L)).thenReturn(List.of());

            mockMvc.perform(get("/api/device/999/datapoints"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data").isEmpty());
        }
    }

    @Nested
    @DisplayName("create")
    class CreateTest {

        @Test
        @DisplayName("should return created datapoint when valid request")
        void shouldReturnCreatedDatapoint_whenValidRequest() throws Exception {
            DeviceDataPoint created = new DeviceDataPoint();
            created.setId(1L);
            created.setDatapointCode("TEMP-001");
            created.setDeviceId(1L);
            when(deviceDataPointService.create(eq(1L), any(DeviceDataPoint.class))).thenReturn(created);

            String json = "{\"datapointCode\":\"TEMP-001\",\"datapointName\":\"温度传感器\","
                    + "\"nodePath\":\"smt/device/1/temperature\",\"dataType\":\"NUMBER\","
                    + "\"sampleIntervalMs\":1000}";

            mockMvc.perform(post("/api/device/1/datapoints")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.code").value(200))
                    .andExpect(jsonPath("$.data.id").value(1))
                    .andExpect(jsonPath("$.data.datapointCode").value("TEMP-001"));
        }

        @Test
        @DisplayName("should return 404 when device does not exist")
        void shouldReturn404_whenDeviceDoesNotExist() throws Exception {
            when(deviceDataPointService.create(eq(999L), any(DeviceDataPoint.class)))
                    .thenThrow(new BizException(ResultCode.NOT_FOUND, "设备不存在"));

            String json = "{\"datapointCode\":\"TEMP-001\",\"datapointName\":\"温度传感器\","
                    + "\"nodePath\":\"smt/device/1/temperature\",\"dataType\":\"NUMBER\","
                    + "\"sampleIntervalMs\":1000}";

            mockMvc.perform(post("/api/device/999/datapoints")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(json))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.code").value(404))
                    .andExpect(jsonPath("$.message").value("设备不存在"));
        }
    }
}
