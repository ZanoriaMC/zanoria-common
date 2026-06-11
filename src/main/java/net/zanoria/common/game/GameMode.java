package net.zanoria.common.game;

import java.util.List;
import java.util.Locale;

public record GameMode(
        String id,
        String displayName,
        String templateId,
        String modeId,
        int neededPlayers,
        int maxPlayers,
        int teamSize,
        boolean enabled,
        List<String> aliases
) {
    public GameMode {
        id = normalizeId(id);
        displayName = requireText(displayName, "displayName");
        templateId = normalizePathId(templateId, "templateId");
        modeId = normalizePathId(modeId, "modeId");
        if (neededPlayers < 1 || maxPlayers < neededPlayers) {
            throw new IllegalArgumentException("Invalid player bounds for " + id);
        }
        if (teamSize < 1 || teamSize > maxPlayers) {
            throw new IllegalArgumentException("Invalid teamSize for " + id);
        }
        aliases = aliases == null ? List.of() : aliases.stream()
                .map(GameMode::normalizeAlias)
                .distinct()
                .toList();
    }

    public boolean matches(String value) {
        String normalized = normalizeAlias(value);
        return normalizeAlias(id).equals(normalized) || aliases.contains(normalized);
    }

    public static String normalizeId(String value) {
        return requireText(value, "id")
                .trim()
                .toUpperCase(Locale.ROOT)
                .replace('-', '_')
                .replace(' ', '_');
    }

    public static String normalizeAlias(String value) {
        return requireText(value, "alias").trim().toLowerCase(Locale.ROOT);
    }

    private static String normalizePathId(String value, String name) {
        return requireText(value, name).trim().toLowerCase(Locale.ROOT);
    }

    private static String requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
