package net.zanoria.common.game;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class GameRegistryTest {

    @Test
    void resolvesConfiguredIdsAndAliases() {
        GameMode mode = new GameMode(
                "sky_clash_duos", "Sky Clash Duos", "skyclash", "duos",
                2, 8, 2, true, List.of("sc", "duos")
        );
        GameRegistry registry = new GameRegistry(7, List.of(mode));

        assertSame(mode, registry.require("sky_clash_duos"));
        assertSame(mode, registry.require("SC"));
        assertSame(mode, registry.require("duos"));
    }

    @Test
    void rejectsDuplicateAliasesAcrossModes() {
        GameMode first = new GameMode(
                "first", "First", "first", "default",
                2, 4, 2, true, List.of("play")
        );
        GameMode second = new GameMode(
                "second", "Second", "second", "default",
                2, 4, 2, true, List.of("PLAY")
        );

        assertThrows(IllegalArgumentException.class,
                () -> new GameRegistry(1, List.of(first, second)));
    }

    @Test
    void snapshotRoundTripPreservesRevisionAndDefinitions() {
        GameRegistry original = GameRegistry.defaults();

        String json = GameRegistrySnapshot.encode(original);
        GameRegistry restored = GameRegistrySnapshot.decode(json);

        assertEquals(original.revision(), restored.revision());
        assertEquals(original.modes(), restored.modes());
        assertEquals("RELICWARS_2V2", restored.require("2v2").id());
    }

    @Test
    void registryRejectsInvalidPlayerBounds() {
        assertThrows(IllegalArgumentException.class, () -> new GameMode(
                "broken", "Broken", "broken", "default",
                5, 4, 2, true, List.of()
        ));
    }
}
