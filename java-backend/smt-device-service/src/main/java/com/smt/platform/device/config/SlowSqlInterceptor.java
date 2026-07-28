package com.smt.platform.device.config;

import org.apache.ibatis.executor.statement.StatementHandler;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Plugin;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.sql.Statement;
import java.util.Properties;

/**
 * 慢 SQL 拦截器（P0-7 可观测性）。
 *
 * <p>拦截 MyBatis StatementHandler 的 query 与 update 方法，记录执行耗时超过阈值的 SQL
 * 到独立 logger {@code slow-sql}（在 logback-spring.xml 中配置为独立文件 logs/slow-sql.log）。</p>
 *
 * <p>阈值默认 100ms，可通过配置项 {@code smt.observation.slow-sql-threshold-ms} 覆盖。</p>
 */
@Intercepts({
        @Signature(type = StatementHandler.class, method = "update",
                args = {Statement.class}),
        @Signature(type = StatementHandler.class, method = "query",
                args = {Statement.class, ResultHandler.class})
})
@Slf4j
@Component
public class SlowSqlInterceptor implements Interceptor {

    private static final org.slf4j.Logger slowSqlLogger = LoggerFactory.getLogger("slow-sql");

    /** 慢 SQL 阈值（毫秒），默认 100ms */
    @Value("${smt.observation.slow-sql-threshold-ms:100}")
    private long slowSqlThresholdMs;

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        long startTime = System.currentTimeMillis();
        Object result;
        try {
            result = invocation.proceed();
        } finally {
            long elapsed = System.currentTimeMillis() - startTime;
            if (elapsed >= slowSqlThresholdMs) {
                String sql = extractSql(invocation);
                slowSqlLogger.warn("SLOW SQL [{}ms] {}", elapsed, sql);
                if (log.isDebugEnabled()) {
                    log.debug("慢 SQL 拦截 elapsed={}ms threshold={}ms sql={}",
                            elapsed, slowSqlThresholdMs, sql);
                }
            }
        }
        return result;
    }

    /**
     * 从 Invocation 中提取 SQL 文本（含参数占位符）。
     */
    private String extractSql(Invocation invocation) {
        try {
            Object target = invocation.getTarget();
            if (target instanceof StatementHandler handler) {
                BoundSql boundSql = handler.getBoundSql();
                if (boundSql != null) {
                    return boundSql.getSql();
                }
            }
        } catch (Exception e) {
            log.debug("提取 SQL 文本失败", e);
        }
        return "[unavailable]";
    }

    @Override
    public Object plugin(Object target) {
        return target instanceof StatementHandler ? Plugin.wrap(target, this) : target;
    }

    @Override
    public void setProperties(Properties properties) {
        // no-op
    }
}
