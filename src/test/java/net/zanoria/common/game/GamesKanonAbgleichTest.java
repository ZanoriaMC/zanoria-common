package net.zanoria.common.game;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.function.Supplier;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * ⚠️ Der Waechter gegen die Erstinstallations-Falle.
 *
 * <p>Der Schaden, gegen den er steht: mit {@code saveResource("games.yml", false)} erreichte ein
 * neues Jar einen Server, der die Datei schon hatte, NIE. Gemessen am 2026-08-16 im laufenden
 * Netz: {@code 9c0b593d-.../plugins/Nexus/games.yml} auf revision 5 (sieben Modi), das Nexus-Jar
 * desselben Servers auf revision 7 (vier Modi) - und Repo, Bau und Auslieferung meldeten gruen.
 * Das betrifft JEDE kuenftige Kanon-Aenderung, nicht nur eine.</p>
 *
 * <p>Die Positivkontrolle steht in {@link #jarLoestAeltereBetriebsdateiAb()}: dieser Fall MUSS
 * uebernehmen. Ein Waechter, der nur "bleibt" belegen kann, wuerde auch dann gruen laufen, wenn
 * der Abgleich gar nichts tut - das alte Verhalten also unveraendert weiterliefe.</p>
 */
class GamesKanonAbgleichTest {
    @TempDir
    Path temp;

    private final Clock feste = Clock.fixed(Instant.parse("2026-08-16T10:00:00Z"), ZoneOffset.UTC);

    private GamesKanonAbgleich abgleich() {
        return new GamesKanonAbgleich(new GameRegistryLoader(), feste);
    }

    private static String kanon(long revision, String... modusKennungen) {
        StringBuilder text = new StringBuilder("revision: " + revision + "\nmodes:\n");
        for (String kennung : modusKennungen) {
            text.append("  - id: ").append(kennung).append('\n')
                    .append("    displayName: ").append(kennung).append('\n')
                    .append("    template: relicwars\n")
                    .append("    mode: ").append(kennung.toLowerCase()).append('\n')
                    .append("    neededPlayers: 2\n")
                    .append("    maxPlayers: 2\n")
                    .append("    teamSize: 1\n")
                    .append("    enabled: true\n")
                    .append("    aliases: [").append(kennung.toLowerCase()).append("]\n");
        }
        return text.toString();
    }

    private static Supplier<InputStream> imJar(String inhalt) {
        // Bei JEDEM Aufruf ein frischer Strom - genau wie Bukkits plugin.getResource().
        return () -> inhalt == null
                ? null
                : new ByteArrayInputStream(inhalt.getBytes(StandardCharsets.UTF_8));
    }

    private List<Path> sicherungen() throws Exception {
        try (Stream<Path> eintraege = Files.list(temp)) {
            return eintraege.filter(p -> p.getFileName().toString().endsWith(".abgeloest")).toList();
        }
    }

    // ---- POSITIVKONTROLLE: der Fall, der das alte Verhalten entlarvt -------------------------

    /**
     * ⚠️ POSITIVKONTROLLE. Genau der Betriebsfall vom 2026-08-16: Datei revision 5, Jar
     * revision 7. Mit {@code saveResource(..., false)} passierte hier NICHTS. Faellt dieser Fall
     * weg oder wird er weich formuliert, ist der ganze Waechter wertlos.
     */
    @Test
    void jarLoestAeltereBetriebsdateiAb() throws Exception {
        Path platte = temp.resolve("games.yml");
        Files.writeString(platte, kanon(5, "RELICWARS_1V1", "SHOWDOWN_SOLO"));

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar(kanon(7, "RELICWARS_1V1", "CORECLASH_2X4")));

        assertEquals(GamesKanonAbgleich.Ausgang.JAR_UEBERNOMMEN, ergebnis.ausgang());
        assertTrue(ergebnis.uebernommen());
        assertEquals(7, ergebnis.jarRevision());
        assertEquals(5, ergebnis.platteRevision());

        assertEquals(7, new GameRegistryLoader().load(platte).revision(),
                "Die Datei auf der Platte muss danach die Jar-Revision tragen");
        assertNotNull(new GameRegistryLoader().load(platte).find("CORECLASH_2X4").orElse(null),
                "Der neue Modus aus dem Jar muss auf der Platte angekommen sein");

        assertNotNull(ergebnis.sicherung());
        assertEquals(5, new GameRegistryLoader().load(ergebnis.sicherung()).revision(),
                "Die verdraengte Fassung darf nicht verlorengehen");
    }

    // ---- Der Fall, den blindes Ueberschreiben kaputtmachen wuerde ----------------------------

    /**
     * ⚠️ Der Schaden, gegen den das steht: eine von Hand am laufenden Netz gepflegte Datei mit
     * HOEHERER Revision. {@code saveResource(..., true)} wuerde sie stillschweigend wegwerfen.
     */
    @Test
    void hoehereBetriebsdateiUeberlebtEinAeltererJarKanon() throws Exception {
        Path platte = temp.resolve("games.yml");
        String vonHand = kanon(9, "RELICWARS_1V1", "NEXUSSTRIKE_2X4");
        Files.writeString(platte, vonHand);

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar(kanon(7, "RELICWARS_1V1")));

        assertEquals(GamesKanonAbgleich.Ausgang.PLATTE_BEHALTEN, ergebnis.ausgang());
        assertFalse(ergebnis.uebernommen());
        assertEquals(vonHand, Files.readString(platte), "Die Datei darf nicht angefasst werden");
        assertNull(ergebnis.sicherung());
        assertTrue(sicherungen().isEmpty(), "Ohne Verdraengung darf keine Sicherung entstehen");
    }

    /** Gleichstand ist kein Grund zu schreiben - sonst wuerde jeder Start die Datei anfassen. */
    @Test
    void gleicheRevisionLaesstDieDateiUnangetastet() throws Exception {
        Path platte = temp.resolve("games.yml");
        String vorher = kanon(7, "RELICWARS_1V1");
        Files.writeString(platte, vorher);

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar(kanon(7, "RELICWARS_1V1", "CORECLASH_2X4")));

        assertEquals(GamesKanonAbgleich.Ausgang.PLATTE_BEHALTEN, ergebnis.ausgang());
        assertEquals(vorher, Files.readString(platte));
        assertTrue(sicherungen().isEmpty());
    }

    // ---- Erstinstallation: das alte Verhalten bleibt erhalten --------------------------------

    @Test
    void fehlendeDateiWirdErstmalsGeschrieben() throws Exception {
        Path platte = temp.resolve("unterordner").resolve("games.yml");

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar(kanon(7, "RELICWARS_1V1")));

        assertEquals(GamesKanonAbgleich.Ausgang.ERSTMALS_GESCHRIEBEN, ergebnis.ausgang());
        assertEquals(-1, ergebnis.platteRevision());
        assertEquals(7, new GameRegistryLoader().load(platte).revision());
        assertNull(ergebnis.sicherung());
    }

    // ---- Beide Richtungen von Schrott --------------------------------------------------------

    /**
     * Eine Datei ohne ladbare Revision kann keinen Vorrang beanspruchen - sie wird ersetzt,
     * aber gesichert, nie geloescht.
     */
    @Test
    void unlesbareBetriebsdateiWirdGesichertUndErsetzt() throws Exception {
        Path platte = temp.resolve("games.yml");
        Files.writeString(platte, "das hier ist kein games.yml: [[[\n");

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar(kanon(7, "RELICWARS_1V1")));

        assertEquals(GamesKanonAbgleich.Ausgang.UNLESBARE_PLATTE_ERSETZT, ergebnis.ausgang());
        assertEquals(7, new GameRegistryLoader().load(platte).revision());
        assertNotNull(ergebnis.sicherung());
        assertTrue(Files.readString(ergebnis.sicherung()).contains("kein games.yml"),
                "Auch eine kaputte Betriebsdatei darf nicht spurlos verschwinden");
    }

    /**
     * ⚠️ Die Gegenrichtung, und die wiegt schwerer: ein Jar mit kaputtem Kanon darf eine
     * funktionierende Betriebsdatei NICHT ersetzen. Sonst startet der Knoten auf
     * {@code GameRegistry.defaults()} - drei RelicWars-Modi statt des Kanons, ohne rotes Signal.
     */
    @Test
    void kaputterJarKanonLaesstDieBetriebsdateiInRuhe() throws Exception {
        Path platte = temp.resolve("games.yml");
        String gut = kanon(5, "RELICWARS_1V1");
        Files.writeString(platte, gut);

        GamesKanonAbgleich.Ergebnis ergebnis =
                abgleich().abgleichen(platte, imJar("revision: siebzehn\nmodes: nein\n"));

        assertEquals(GamesKanonAbgleich.Ausgang.JAR_UNBRAUCHBAR, ergebnis.ausgang());
        assertFalse(ergebnis.uebernommen());
        assertEquals(gut, Files.readString(platte));
        assertEquals(5, ergebnis.platteRevision());
    }

    /** Fehlt die Ressource im Jar ganz, gilt dasselbe. */
    @Test
    void fehlendeJarRessourceLaesstDieBetriebsdateiInRuhe() throws Exception {
        Path platte = temp.resolve("games.yml");
        String gut = kanon(5, "RELICWARS_1V1");
        Files.writeString(platte, gut);

        GamesKanonAbgleich.Ergebnis ergebnis = abgleich().abgleichen(platte, imJar(null));

        assertEquals(GamesKanonAbgleich.Ausgang.JAR_UNBRAUCHBAR, ergebnis.ausgang());
        assertEquals(gut, Files.readString(platte));
    }

    /** Zwei Abgleiche hintereinander: der zweite darf nicht noch einmal schreiben. */
    @Test
    void zweiterStartSchreibtNichtNochEinmal() throws Exception {
        Path platte = temp.resolve("games.yml");
        Files.writeString(platte, kanon(5, "RELICWARS_1V1"));
        String jar = kanon(7, "RELICWARS_1V1", "CORECLASH_2X4");

        assertEquals(GamesKanonAbgleich.Ausgang.JAR_UEBERNOMMEN,
                abgleich().abgleichen(platte, imJar(jar)).ausgang());
        assertEquals(GamesKanonAbgleich.Ausgang.PLATTE_BEHALTEN,
                abgleich().abgleichen(platte, imJar(jar)).ausgang());
        assertEquals(1, sicherungen().size(),
                "Nur die eine echte Verdraengung darf eine Sicherung hinterlassen");
    }
}
