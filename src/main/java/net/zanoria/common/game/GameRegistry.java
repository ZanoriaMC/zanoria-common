package net.zanoria.common.game;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class GameRegistry {
    private final long revision;
    private final List<GameMode> modes;
    private final Map<String, GameMode> byLookup;

    public GameRegistry(long revision, Collection<GameMode> modes) {
        if (revision < 0) {
            throw new IllegalArgumentException("revision must not be negative");
        }
        if (modes == null || modes.isEmpty()) {
            throw new IllegalArgumentException("At least one game mode is required");
        }

        this.revision = revision;
        this.modes = List.copyOf(modes);
        Map<String, GameMode> lookups = new LinkedHashMap<>();
        for (GameMode mode : this.modes) {
            register(lookups, GameMode.normalizeAlias(mode.id()), mode);
            for (String alias : mode.aliases()) {
                register(lookups, alias, mode);
            }
        }
        this.byLookup = Map.copyOf(lookups);
    }

    public long revision() {
        return revision;
    }

    public List<GameMode> modes() {
        return modes;
    }

    public List<GameMode> enabledModes() {
        return modes.stream().filter(GameMode::enabled).toList();
    }

    public Optional<GameMode> find(String idOrAlias) {
        if (idOrAlias == null || idOrAlias.isBlank()) {
            return Optional.empty();
        }
        return Optional.ofNullable(byLookup.get(GameMode.normalizeAlias(idOrAlias)));
    }

    public GameMode require(String idOrAlias) {
        return find(idOrAlias).orElseThrow(
                () -> new IllegalArgumentException("Unknown game mode: " + idOrAlias));
    }

    public static GameRegistry defaults() {
        return new GameRegistry(1, List.of(
                new GameMode("RELICWARS_1V1", "RelicWars 1v1", "relicwars", "relicwars1v1",
                        2, 2, 1, true, List.of("1v1", "relicwars1v1", "relicwars_1v1")),
                new GameMode("RELICWARS_8X2", "RelicWars 8x2", "relicwars", "relicwars8x2",
                        8, 16, 2, true, List.of("8x2", "relicwars", "rw", "relicwars8x2", "relicwars_8x2")),
                new GameMode("RELICWARS_4X4", "RelicWars 4v4v4v4", "relicwars", "relicwars4x4",
                        16, 16, 4, true, List.of("4v4v4v4", "4x4", "relicwars4x4", "relicwars_4x4"))
        ));
    }

    private static void register(Map<String, GameMode> lookups, String lookup, GameMode mode) {
        GameMode existing = lookups.putIfAbsent(lookup, mode);
        if (existing != null && !existing.id().equals(mode.id())) {
            throw new IllegalArgumentException(
                    "Lookup '" + lookup + "' is used by " + existing.id() + " and " + mode.id());
        }
    }
}
