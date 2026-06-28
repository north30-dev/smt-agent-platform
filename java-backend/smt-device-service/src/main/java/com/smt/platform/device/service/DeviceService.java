package com.smt.platform.device.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.smt.platform.device.model.entity.Device;

import java.io.Serializable;

/**
 * 设备台账服务接口。
 *
 * <p>P0-1 修复：移除对 {@link IService#getById(Serializable)} 的覆写声明，
 * 恢复"不存在返回 null"的契约语义；新增 {@link #getByIdOrThrow(Serializable)}
 * 承担"不存在抛 {@code BizException}"的语义。</p>
 */
public interface DeviceService extends IService<Device> {

    /**
     * 新增设备。
     *
     * @param device 设备信息（deviceCode 必须全局唯一）
     * @return 写入后的设备（含生成的 id）
     */
    Device create(Device device);

    /**
     * 更新设备（部分字段更新，deviceCode 不允许修改）。
     *
     * @param id     设备 ID
     * @param device 待更新字段
     * @return 更新后的设备完整信息
     */
    Device update(Long id, Device device);

    /**
     * 软删除设备。
     *
     * @param id 设备 ID
     * @return 是否删除成功
     */
    boolean delete(Long id);

    /**
     * 根据 ID 查询设备详情，不存在时抛出业务异常（{@code ResultCode.NOT_FOUND}）。
     *
     * <p>与 {@link IService#getById(Serializable)} 的"返回 null"语义解耦：
     * 调用方需要"找不到即报错"时用本方法；调用方需要"找不到返回 null"时用 {@code getById}。</p>
     *
     * @param id 设备 ID
     * @return 设备实体
     * @throws com.smt.platform.common.exception.BizException 设备不存在时抛出
     */
    Device getByIdOrThrow(Serializable id);

    /**
     * 分页查询设备列表，支持按产线/类型/状态筛选，按 createTime 倒序。
     *
     * @param page           页码，从 1 开始
     * @param size           每页条数
     * @param productionLine 产线（可选）
     * @param deviceType     设备类型（可选）
     * @param status         设备状态（可选）
     * @return 分页结果
     */
    IPage<Device> pageList(int page, int size, String productionLine, String deviceType, String status);
}
