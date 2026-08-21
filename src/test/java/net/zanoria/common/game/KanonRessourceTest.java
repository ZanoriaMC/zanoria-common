package net.zanoria.common.game;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

class KanonRessourceTest {

    @Test
    @DisplayName("Die Ressource liegt im Bau und ist ladbar")
    void ressourceIstDaUndLadbar() throws Exception {
        try (InputStream strom = KanonRessource.oeffnen()) {
            assertNotNull(strom, "⚠️ games.yml fehlt im Bau von zanoria-common. Genau dieser"
                    + " Zustand - ein Jar ohne Kanon - war bei NexusService der Grund, dass ein"
                    + " Revisionsabgleich dort nichts bewirken konnte.");
        }

        GameRegistry registry = new GameRegistryLoader()
                .load(new StringReader(KanonRessource.lesen()));
        assertTrue(registry.revision() > 0, "Der ausgelieferte Kanon traegt keine Revision");
        assertFalse(registry.enabledModes().isEmpty(),
                "Der ausgelieferte Kanon traegt keinen scharfen Modus");
    }

    /**
     * ⚠️ Jeder Aufruf muss einen FRISCHEN Strom liefern. {@code GamesKanonAbgleich} liest die
     * Ressource unter Umstaenden zweimal; ein zwischengespeicherter, schon verbrauchter Strom
     * liefert beim zweiten Mal einen leeren Kanon - und der Abgleich haelt das Jar fuer
     * unbrauchbar und laesst die Betriebsdatei unangetastet, ohne dass etwas rot wird.
     *
     * <p>⚠️ Der Vergleich {@code lesen()} gegen {@code lesen()} allein belegt das <b>nicht</b>
     * scharf genug — er faellt zwar auf einen verbrauchten Strom herein (zweiter Aufruf laese
     * leer), aber nicht auf einen zwischengespeicherten <em>Text</em>. Deshalb steht darunter der
     * Nachweis, dass zwei Aufrufe zwei <b>verschiedene Stromobjekte</b> liefern.</p>
     */
    @Test
    @DisplayName("Jeder Aufruf liefert einen frischen Strom")
    void jederAufrufLiefertFrischenStrom() throws Exception {
        assertEquals(KanonRessource.lesen(), KanonRessource.lesen());

        try (InputStream erster = KanonRessource.oeffnen();
             InputStream zweiter = KanonRessource.oeffnen()) {
            assertNotNull(erster);
            assertNotNull(zweiter);
            assertNotSame(erster, zweiter,
                    "⚠️ Zwei Aufrufe liefern dasselbe Stromobjekt. Wer den ersten verbraucht,"
                            + " bekommt beim zweiten einen leeren Kanon - und GamesKanonAbgleich"
                            + " haelt das Jar dann fuer unbrauchbar.");

            // Den ersten leerlesen; der zweite muss davon unberuehrt bleiben.
            erster.readAllBytes();
            assertTrue(zweiter.readAllBytes().length > 0,
                    "⚠️ Der zweite Strom ist leer, nachdem der erste gelesen wurde - die beiden"
                            + " teilen sich eine Leseposition.");
        }
    }

    @Test
    @DisplayName("Der Dateiname ist der, den beide Konsumenten auf Platte erwarten")
    void dateinameIstGamesYml() {
        assertEquals("games.yml", KanonRessource.DATEINAME);
    }
}
