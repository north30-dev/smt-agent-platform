package com.smt.platform.device.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.ThreadPoolExecutor;

/**
 * 异步任务配置（Batch 4）。
 *
 * <p>启用 Spring {@link EnableAsync}，为 {@code @Async} 注解提供线程池。
 * 定义两个独立线程池，避免互相影响：</p>
 *
 * <ul>
 *   <li>{@code deviceDataExecutor}：设备数据写入（{@link com.smt.platform.device.service.impl.DeviceDataServiceImpl#saveData}）</li>
 *   <li>{@code healthScoreExecutor}：健康评分重算（{@link com.smt.platform.device.health.HealthScoreCalculator#refreshHealthScore}）</li>
 * </ul>
 *
 * <p>统一使用 {@link ThreadPoolExecutor.CallerRunsPolicy} 拒绝策略：
 * 队列满时退化为调用线程同步执行，保证不丢任务（MQTT 高频写入场景下宁可阻塞也不丢数据），
 * 与"不修改原有功能"约束一致 — 最坏情况下行为与原同步实现等价。</p>
 */
@Configuration
@EnableAsync
public class AsyncConfig {

    /**
     * 设备数据写入线程池。
     *
     * <p>MQTT 高频写入场景下，corePoolSize=2 + maxPoolSize=8 + queueCapacity=500
     * 可承载约 500+8 个并发写入请求；超限后 CallerRunsPolicy 退化为同步执行。</p>
     */
    @Bean("deviceDataExecutor")
    public ThreadPoolTaskExecutor deviceDataExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(8);
        executor.setQueueCapacity(500);
        executor.setThreadNamePrefix("device-data-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }

    /**
     * 健康评分重算线程池。
     *
     * <p>评分重算为 CPU 密集型任务（PG select + 评分计算 + PG update），
     * corePoolSize=1 + maxPoolSize=2 + queueCapacity=100 即可承载；
     * 超限后 CallerRunsPolicy 退化为 MQTT 回调线程同步执行。</p>
     */
    @Bean("healthScoreExecutor")
    public ThreadPoolTaskExecutor healthScoreExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(2);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("health-score-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(15);
        executor.initialize();
        return executor;
    }
}
