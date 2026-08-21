package net.zanoria.common.game;


import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Clock;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.function.Supplier;

/**
 * Bringt den Kanon aus dem Jar und die Datei {@code plugins/Nexus/games.yml} auf der Platte
 * zusammen - nach der Revision, nicht nach dem blossen Vorhandensein.
 *
 * <p>⚠️ WOGEGEN DAS STEHT. Bis 2026-08-16 lautete der Weg
 * {@code plugin.saveResource("games.yml", false)}: die Datei wird NUR bei der Erstinstallation
 * geschrieben und danach nie wieder angefasst. Ein neues Jar aendert an einem Server, der die
 * Datei schon hat, damit NICHTS. Der Fall ist im Betrieb eingetreten und gemessen:
 * {@code pelican-daemon/9c0b593d-.../plugins/Nexus/games.yml} trug am 2026-08-16 die
 * {@code revision: 5} mit sieben Modi (Datei vom 2026-08-15 18:10), waehrend das Nexus-Jar
 * DESSELBEN Servers (2026-08-15 21:37) die {@code revision: 7} mit vier Modi enthielt. Drei
 * Stunden juengeres Jar, alter Kanon - und Repo, Bau und Auslieferung meldeten Erfolg.</p>
 *
 * <p>⚠️ WARUM NICHT BLIND UEBERSCHREIBEN. Eine von Hand gepflegte Betriebsdatei kann eine
 * HOEHERE Revision tragen als das Jar (Notfallschalter am laufenden Netz, Erprobung eines
 * Modus vor dem Bau). {@code saveResource("games.yml", true)} wuerde die stillschweigend
 * wegwerfen. Deshalb entscheidet hier dieselbe Regel wie in
 * {@code ProxyGameRegistry.apply}: eine Fassung setzt sich nur durch, wenn ihre Revision
 * ECHT hoeher ist. Dieselbe Sperrklinke, zweiter Ort.</p>
 *
 * <p>Ersetzt wird nie loeschend: die verdraengte Fassung liegt danach als
 * {@code games.yml.<revision>-<zeitstempel>.abgeloest} daneben.</p>
 */
public final class GamesKanonAbgleich {
    /** Der Name der Ressource im Jar und der Datei im Datenverzeichnis. */
    public static final String DATEINAME = "games.yml";

    private static final DateTimeFormatter STEMPEL =
            DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss").withZone(ZoneOffset.UTC);

    private final GameRegistryLoader loader;
    private final Clock clock;

    public GamesKanonAbgleich() {
        this(new GameRegistryLoader(), Clock.systemUTC());
    }

    public GamesKanonAbgleich(GameRegistryLoader loader, Clock clock) {
        this.loader = loader;
        this.clock = clock;
    }

    /** Was der Abgleich getan hat. Jeder Zweig hat genau einen Wert - kein Sammelposten. */
    public enum Ausgang {
        /** Auf der Platte lag nichts; die Jar-Fassung wurde erstmals geschrieben. */
        ERSTMALS_GESCHRIEBEN,
        /** Das Jar trug eine hoehere Revision; die alte Datei wurde gesichert und ersetzt. */
        JAR_UEBERNOMMEN,
        /** Die Platte war unlesbar; sie wurde gesichert und durch die Jar-Fassung ersetzt. */
        UNLESBARE_PLATTE_ERSETZT,
        /** Die Platte trug dieselbe oder eine hoehere Revision; sie bleibt unangetastet. */
        PLATTE_BEHALTEN,
        /**
         * Das Jar trug keinen brauchbaren Kanon. Die Platte bleibt unangetastet - lieber ein
         * alter Kanon als gar keiner.
         */
        JAR_UNBRAUCHBAR
    }

    /**
     * @param ausgang         welcher Zweig gegriffen hat
     * @param jarRevision     Revision im Jar, oder -1 wenn dort keine brauchbare zu finden war
     * @param platteRevision  Revision auf der Platte VOR dem Abgleich, oder -1 wenn keine
     * @param sicherung       wohin die verdraengte Fassung gelegt wurde, oder null
     * @param meldung         eine Zeile fuers Startprotokoll
     */
    public record Ergebnis(
            Ausgang ausgang,
            long jarRevision,
            long platteRevision,
            Path sicherung,
            String meldung
    ) {
        public boolean uebernommen() {
            return ausgang == Ausgang.ERSTMALS_GESCHRIEBEN
                    || ausgang == Ausgang.JAR_UEBERNOMMEN
                    || ausgang == Ausgang.UNLESBARE_PLATTE_ERSETZT;
        }
    }

    /**
     * Gleicht ab und schreibt gegebenenfalls.
     *
     * @param platte       Zieldatei, ueblicherweise {@code plugins/Nexus/games.yml}
     * @param jarRessource liefert bei JEDEM Aufruf einen frischen Strom auf die Jar-Ressource
     *                     (in Bukkit: {@code plugin::getResource}); darf {@code null} liefern
     */
    public Ergebnis abgleichen(Path platte, Supplier<InputStream> jarRessource) throws IOException {
        // ⚠️ Zuerst das Jar pruefen, nicht die Platte. Wer die Platte zuerst wegnimmt und dann
        // merkt, dass das Jar nichts Brauchbares hat, hat den Knoten kanonlos gemacht.
        long jarRevision;
        String jarInhalt;
        try {
            jarInhalt = lesen(jarRessource);
            if (jarInhalt == null) {
                return neuesErgebnis(Ausgang.JAR_UNBRAUCHBAR, -1, revisionDerPlatte(platte), null,
                        "Keine Ressource " + DATEINAME + " im Jar - Platte bleibt unangetastet.");
            }
            jarRevision = loader.load(new java.io.StringReader(jarInhalt)).revision();
        } catch (RuntimeException fehler) {
            return neuesErgebnis(Ausgang.JAR_UNBRAUCHBAR, -1, revisionDerPlatte(platte), null,
                    DATEINAME + " im Jar ist nicht ladbar (" + fehler.getMessage()
                            + ") - Platte bleibt unangetastet.");
        }

        if (!Files.isRegularFile(platte)) {
            schreiben(platte, jarInhalt);
            return neuesErgebnis(Ausgang.ERSTMALS_GESCHRIEBEN, jarRevision, -1, null,
                    "Kanon erstmals geschrieben, revision " + jarRevision + ".");
        }

        long platteRevision = revisionDerPlatte(platte);
        if (platteRevision < 0) {
            Path sicherung = sichern(platte, "unlesbar");
            schreiben(platte, jarInhalt);
            return neuesErgebnis(Ausgang.UNLESBARE_PLATTE_ERSETZT, jarRevision, -1, sicherung,
                    "Betriebsdatei war nicht ladbar; gesichert nach " + sicherung.getFileName()
                            + " und durch Jar-Kanon revision " + jarRevision + " ersetzt.");
        }

        if (jarRevision <= platteRevision) {
            return neuesErgebnis(Ausgang.PLATTE_BEHALTEN, jarRevision, platteRevision, null,
                    "Betriebsdatei revision " + platteRevision + " bleibt; Jar traegt revision "
                            + jarRevision + " und ist nicht hoeher.");
        }

        Path sicherung = sichern(platte, "rev" + platteRevision);
        schreiben(platte, jarInhalt);
        return neuesErgebnis(Ausgang.JAR_UEBERNOMMEN, jarRevision, platteRevision, sicherung,
                "Jar-Kanon revision " + jarRevision + " loest Betriebsdatei revision "
                        + platteRevision + " ab; alte Fassung liegt als "
                        + sicherung.getFileName() + ".");
    }

    private long revisionDerPlatte(Path platte) {
        if (platte == null || !Files.isRegularFile(platte)) {
            return -1;
        }
        try {
            GameRegistry vorhanden = loader.load(platte);
            return vorhanden.revision();
        } catch (IOException | RuntimeException ignoriert) {
            return -1;
        }
    }

    private static String lesen(Supplier<InputStream> jarRessource) throws IOException {
        if (jarRessource == null) {
            return null;
        }
        InputStream strom = jarRessource.get();
        if (strom == null) {
            return null;
        }
        try (Reader reader = new InputStreamReader(strom, StandardCharsets.UTF_8)) {
            StringBuilder inhalt = new StringBuilder();
            char[] puffer = new char[8192];
            int gelesen;
            while ((gelesen = reader.read(puffer)) >= 0) {
                inhalt.append(puffer, 0, gelesen);
            }
            return inhalt.toString();
        }
    }

    private Path sichern(Path platte, String kennzeichen) throws IOException {
        Path ziel = platte.resolveSibling(
                platte.getFileName() + "." + kennzeichen + "-" + STEMPEL.format(clock.instant())
                        + ".abgeloest");
        Files.copy(platte, ziel, StandardCopyOption.REPLACE_EXISTING);
        return ziel;
    }

    private static void schreiben(Path platte, String inhalt) throws IOException {
        Path ordner = platte.getParent();
        if (ordner != null) {
            Files.createDirectories(ordner);
        }
        // ⚠️ Ueber eine Nebendatei und ATOMIC_MOVE. Ein Abbruch mitten im Schreiben wuerde sonst
        // eine halbe games.yml hinterlassen, und der Knoten startet auf GameRegistry.defaults().
        Path neben = platte.resolveSibling(platte.getFileName() + ".neu");
        Files.writeString(neben, inhalt, StandardCharsets.UTF_8);
        try {
            Files.move(neben, platte,
                    StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (java.nio.file.AtomicMoveNotSupportedException ohneAtom) {
            Files.move(neben, platte, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private static Ergebnis neuesErgebnis(
            Ausgang ausgang, long jarRevision, long platteRevision, Path sicherung, String meldung) {
        return new Ergebnis(ausgang, jarRevision, platteRevision, sicherung, meldung);
    }
}
