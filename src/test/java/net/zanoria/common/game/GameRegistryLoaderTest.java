package net.zanoria.common.game;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class GameRegistryLoaderTest {

    private static final String KANON = """
            revision: 4
            modes:
              - id: RELICWARS_1V1
                displayName: RelicWars 1v1
                template: relicwars
                mode: relicwars1v1
                neededPlayers: 2
                maxPlayers: 2
                teamSize: 1
                enabled: true
                aliases: [1v1]
            """;

    @Test
    @DisplayName("Liest Revision und Modi aus einem Reader")
    void liestRevisionUndModi() {
        GameRegistry registry = new GameRegistryLoader().load(new StringReader(KANON));

        assertEquals(4, registry.revision());
        assertEquals(1, registry.modes().size());
        assertEquals("RELICWARS_1V1", registry.require("1v1").id());
    }

    /**
     * ⚠️ Eine fehlende Revision darf NICHT als 0 durchgehen. Der bisherige Lader der
     * Steuerungsebene tat genau das - eine Datei ohne revision: haette dort still als revision 0
     * gegolten und jede Sperrklinke ausgehebelt.
     */
    @Test
    @DisplayName("Ein Kanon ohne revision: ist kein Kanon")
    void ohneRevisionWirdAbgewiesen() {
        String ohneRevision = KANON.substring(KANON.indexOf("modes:"));

        assertThrows(IllegalArgumentException.class,
                () -> new GameRegistryLoader().load(new StringReader(ohneRevision)));
    }

    @Test
    @DisplayName("Ein Modus ohne Pflichtfeld wird abgewiesen")
    void unvollstaendigerModusWirdAbgewiesen() {
        String ohneVorlage = KANON.replace("    template: relicwars\n", "");

        assertThrows(IllegalArgumentException.class,
                () -> new GameRegistryLoader().load(new StringReader(ohneVorlage)));
    }
}
