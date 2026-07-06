package com.smt.platform.device.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

/**
 * Redis 配置（m6）。
 *
 * <p>启用 Spring Cache ({@link EnableCaching})，提供 {@link RedisTemplate} 与
 * {@link RedisCacheManager} Bean，使 {@code @Cacheable} 注解生效。</p>
 *
 * <p>Redis 连接由 spring-boot-starter-data-redis 自动配置（application.yml spring.data.redis.*），
 * 本类只负责序列化策略与缓存默认 TTL（10 分钟，兜底防止脏读长期残留）。</p>
 *
 * <p>注：Phase 2 device-service 的 history 查询为只读接口，无写入端触发 @CacheEvict，
 * 依赖 TTL 10min 兜底；Phase 3 接入写入接口后改为主动 evict。</p>
 */
@Configuration
@EnableCaching
public class RedisConfig {

    /** 缓存默认 TTL（分钟），兜底防止脏读长期残留 */
    private static final long DEFAULT_TTL_MINUTES = 10L;

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        StringRedisSerializer stringSerializer = new StringRedisSerializer();
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();
        template.setKeySerializer(stringSerializer);
        template.setHashKeySerializer(stringSerializer);
        template.setValueSerializer(jsonSerializer);
        template.setHashValueSerializer(jsonSerializer);
        template.afterPropertiesSet();
        return template;
    }

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(DEFAULT_TTL_MINUTES))
                .disableCachingNullValues();
        return RedisCacheManager.builder(factory).cacheDefaults(config).build();
    }
}
