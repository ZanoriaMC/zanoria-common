package net.zanoria.common.game;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

/**
 * Der ausgelieferte Kanon — die Fassung, die in JEDEM Jar steckt, das zanoria-common schattet.
 *
 * <p>⚠️ Der Schaden, gegen den das steht: bis 2026-08-21 lag der Kanon nur in
 * {@code Nexus/src/main/resources}. Die Steuerungsebene (NexusService) band dieselben Typen, aber
 * <b>nicht</b> die Datei — ihr Jar trug 0 von 3344 Eintraegen mit dem Namen {@code games}. Sie las
 * ihren Kanon deshalb aus einer handgepflegten Datei auf dem Wirt, die kein Bau und keine
 * Auslieferung je erreichte.</p>
 */
public final class KanonRessource {

    /** Der Name der Ressource im Jar UND der Betriebsdatei auf der Platte. */
    public static final String DATEINAME = "games.yml";

    private KanonRessource() {
    }

    /**
     * Ein <b>frischer</b> Strom auf die Jar-Ressource, oder {@code null}, wenn sie fehlt.
     *
     * <p>Diese Methode ist die Form, die {@code GamesKanonAbgleich} erwartet
     * ({@code Supplier<InputStream>}) — sie darf deshalb bei jedem Aufruf neu oeffnen und nie
     * einen verbrauchten Strom zurueckgeben.</p>
     */
    public static InputStream oeffnen() {
        return KanonRessource.class.getClassLoader().getResourceAsStream(DATEINAME);
    }

    /** Derselbe Inhalt als Text — fuer Faelle, die den Rohtext brauchen statt eines Stroms. */
    public static String lesen() {
        try (InputStream strom = oeffnen()) {
            if (strom == null) {
                throw new IllegalStateException(
                        "⚠️ " + DATEINAME + " fehlt im Bau. Ein Jar ohne Kanon liefert nichts aus,"
                                + " meldet dabei aber Erfolg.");
            }
            return new String(strom.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException fehler) {
            throw new UncheckedIOException(fehler);
        }
    }
}
