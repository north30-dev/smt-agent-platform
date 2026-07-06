package com.smt.platform.device.health;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 健康评分规则配置（m8）。
 *
 * <p>从 {@link HealthScoreCalculator} 的 11 个硬编码常量抽取为可配置属性，
 * 默认值与原硬编码完全一致，保证行为兼容。</p>
 *
 * <p>配置前缀 {@code smt.health.score.*}，可在 application.yml 中按设备/产线差异化配置。</p>
 */
@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "smt.health.score")
public class HealthScoreProperties {

    /** 维修态固定评分（原 SCORE_MAINTENANCE=30） */
    private int scoreMaintenance = 30;

    /** 停机态固定评分（原 SCORE_STOPPED=50） */
    private int scoreStopped = 50;

    /** 运行态基础评分（原 BASE_SCORE=100） */
    private int baseScore = 100;

    /** 评分上限（原 SCORE_MAX=100） */
    private int scoreMax = 100;

    /** 评分下限（原 SCORE_MIN=0） */
    private int scoreMin = 0;

    /** 最近数据时间窗（分钟，原 RECENT_WINDOW_MINUTES=5L） */
    private long recentWindowMinutes = 5L;

    /** 温度一级阈值（>80 扣 20，原 TEMP_THRESHOLD_LOW=80.0） */
    private double tempThresholdLow = 80.0;

    /** 温度二级阈值（>100 扣 40，原 TEMP_THRESHOLD_HIGH=100.0） */
    private double tempThresholdHigh = 100.0;

    /** 振动一级阈值（>10 扣 20，原 VIB_THRESHOLD_LOW=10.0） */
    private double vibThresholdLow = 10.0;

    /** 振动二级阈值（>20 扣 40，原 VIB_THRESHOLD_HIGH=20.0） */
    private double vibThresholdHigh = 20.0;

    /** 二级阈值扣分（原魔法数字 40） */
    private int deductionHigh = 40;

    /** 一级阈值扣分（原魔法数字 20） */
    private int deductionLow = 20;
}
