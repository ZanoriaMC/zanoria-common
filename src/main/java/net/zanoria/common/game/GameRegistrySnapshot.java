package net.zanoria.common.game;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.util.List;

public final class GameRegistrySnapshot {
    private static final Gson GSON = new GsonBuilder().disableHtmlEscaping().create();

    private GameRegistrySnapshot() {
    }

    public static String encode(GameRegistry registry) {
        return GSON.toJson(new Snapshot(registry.revision(), registry.modes()));
    }

    public static GameRegistry decode(String json) {
        if (json == null || json.isBlank()) {
            throw new IllegalArgumentException("Registry snapshot must not be blank");
        }
        Snapshot snapshot = GSON.fromJson(json, Snapshot.class);
        if (snapshot == null || snapshot.modes == null) {
            throw new IllegalArgumentException("Invalid registry snapshot");
        }
        return new GameRegistry(snapshot.revision, snapshot.modes);
    }

    private record Snapshot(long revision, List<GameMode> modes) {
    }
}
