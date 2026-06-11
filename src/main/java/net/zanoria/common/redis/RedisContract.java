package net.zanoria.common.redis;

public final class RedisContract {
    public static final String CHANNEL_MESSAGING = "zanoria:messaging";
    public static final String CHANNEL_ANTICHEAT = "zanoria:ac:alerts";
    public static final String CHANNEL_GAME_REGISTRY = "zanoria:games:updates";
    public static final String GAME_REGISTRY_SNAPSHOT = "zanoria:games:snapshot";

    private RedisContract() {
    }
}
