package net.zanoria.common.game;

import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class GameRegistryLoader {
    private final Yaml yaml = new Yaml();

    public GameRegistry load(Path file) throws IOException {
        if (file == null || !Files.isRegularFile(file)) {
            throw new IOException("Game registry file missing: " + file);
        }
        try (Reader reader = Files.newBufferedReader(file)) {
            return load(reader);
        }
    }

    /**
     * Dieselbe Pruefung fuer eine Quelle, die keine Datei ist - etwa die Ressource im Jar.
     *
     * <p>⚠️ Der Kanon im Jar wird damit VOR dem Ausliefern vollstaendig geparst, nicht nur
     * auf {@code revision:} abgeklopft. Der Schaden, gegen den das steht: ein fehlerhaftes
     * games.yml im Jar wuerde sonst eine funktionierende Betriebsdatei ueberschreiben, und der
     * Knoten faellt beim naechsten Start auf {@code GameRegistry.defaults()} zurueck - er laeuft
     * dann mit drei RelicWars-Modi statt mit dem Kanon, ohne dass etwas rot wird.</p>
     */
    public GameRegistry load(Reader reader) {
        Object raw = yaml.load(reader);
        if (!(raw instanceof Map<?, ?> root)) {
            throw new IllegalArgumentException("games.yml root must be a mapping");
        }
        long revision = number(root, "revision").longValue();
        Object rawModes = root.get("modes");
        if (!(rawModes instanceof List<?> entries)) {
            throw new IllegalArgumentException("games.yml modes must be a list");
        }
        List<GameMode> modes = new ArrayList<>();
        for (Object entry : entries) {
            if (!(entry instanceof Map<?, ?> mode)) {
                throw new IllegalArgumentException("Each game mode must be a mapping");
            }
            modes.add(new GameMode(
                    text(mode, "id"),
                    text(mode, "displayName"),
                    text(mode, "template"),
                    text(mode, "mode"),
                    number(mode, "neededPlayers").intValue(),
                    number(mode, "maxPlayers").intValue(),
                    number(mode, "teamSize").intValue(),
                    booleanValue(mode, "enabled", true),
                    strings(mode.get("aliases"))
            ));
        }
        return new GameRegistry(revision, modes);
    }

    private static String text(Map<?, ?> source, String key) {
        Object value = source.get(key);
        if (!(value instanceof String text) || text.isBlank()) {
            throw new IllegalArgumentException("Missing text field " + key);
        }
        return text;
    }

    private static Number number(Map<?, ?> source, String key) {
        Object value = source.get(key);
        if (!(value instanceof Number number)) {
            throw new IllegalArgumentException("Missing numeric field " + key);
        }
        return number;
    }

    private static boolean booleanValue(Map<?, ?> source, String key, boolean fallback) {
        Object value = source.get(key);
        return value instanceof Boolean flag ? flag : fallback;
    }

    private static List<String> strings(Object value) {
        if (value == null) {
            return List.of();
        }
        if (!(value instanceof List<?> list)) {
            throw new IllegalArgumentException("aliases must be a list");
        }
        return list.stream().map(String::valueOf).toList();
    }
}
