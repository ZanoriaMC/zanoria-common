package net.zanoria.common.game;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * Bindet den Inhalt von {@code games.yml} an seine {@code revision:}.
 *
 * <p><b>Warum das ein Test sein muss und kein Kommentar.</b> Der Proxy nimmt einen Schnappschuss
 * nur an, wenn dessen Revision <em>groesser</em> ist als die, die er schon haelt
 * ({@code ProxyGameRegistry.apply}: {@code if (candidate.revision() <= current().revision())
 * return false;}) — und er schreibt den angenommenen Stand nach
 * {@code games-snapshot.json}. Aendert sich der Inhalt, ohne dass die Zahl steigt, weist der
 * Proxy den korrigierten Stand ab und laeuft <b>dauerhaft</b> auf dem alten. Kein Fehler, keine
 * Logzeile, kein roter Bau.</p>
 *
 * <p>⚠️ <b>Das ist kein gedachter Fall.</b> Am 2026-08-14 gemessen: {@code games-snapshot.json}
 * stand auf Revision 5 mit acht Modi (darunter {@code RELICWARS_4X3}), {@code games.yml} auf
 * Revision 5 mit sieben und anderen Spielerzahlen. Gleiche Revision, anderer Inhalt — der Proxy
 * fuhr ein veraltetes Modusregister und nahm keine Korrektur mehr an.</p>
 *
 * <p><b>Hochzaehlen behebt den Fall, dieser Test die Moeglichkeit.</b> Solange {@code revision:}
 * eine handgepflegte Zahl <em>neben</em> dem Inhalt ist, kann die naechste Aenderung sie wieder
 * vergessen. Hier ist sie an den Inhalt gekoppelt.</p>
 *
 * <p><b>Der Abdruck ist bewusst semantisch, nicht wortwoertlich.</b> Er laeuft ueber die
 * <em>geladenen</em> Modi, nicht ueber den Dateitext. Ein Kommentar oder eine Leerzeile aendert
 * ihn nicht — sonst waere jede Kommentarpflege ein Revisions-Hub, und die Zahl wuerde gedankenlos
 * hochgezaehlt statt gelesen.</p>
 */
class GamesRevisionFolgtDemInhaltTest {

    private static final Path GAMES_YML = Path.of("src/main/resources/games.yml");

    /**
     * Der zuletzt festgehaltene Stand. ⚠️ <b>Beide Zeilen wandern zusammen oder gar nicht.</b>
     * Wer den Abdruck nachzieht, ohne die Revision zu heben, hat den Test entwertet, nicht
     * bestanden — die Zusicherung unten faengt genau das.
     */
    private static final long GEPINNTE_REVISION = 9L;
    private static final String GEPINNTER_ABDRUCK =
            "e04771d0c45174f4249e8524dcaf936a7ea93b4850bedf8179150ce0420b1969";

    @Test
    @DisplayName("Aendert sich der modes:-Block, muss revision: gestiegen sein")
    void inhaltUndRevisionWandernZusammen() throws Exception {
        GameRegistry registry = new GameRegistryLoader().load(GAMES_YML);
        long revision = registry.revision();
        String abdruck = abdruckVon(registry);

        if (abdruck.equals(GEPINNTER_ABDRUCK)) {
            assertEquals(GEPINNTE_REVISION, revision,
                    "⚠️ Der Inhalt ist unveraendert, aber revision: hat sich bewegt. Ein Hub ohne"
                            + " Aenderung macht die Zahl bedeutungslos — sie ist dann keine"
                            + " Aussage ueber den Inhalt mehr, sondern nur noch ein Zaehler.");
            return;
        }

        assertTrue(revision > GEPINNTE_REVISION,
                "⚠️ Der modes:-Block hat sich geaendert, aber revision: steht weiter auf "
                        + revision + " (festgehalten war " + GEPINNTE_REVISION + ")."
                        + " Der Proxy weist den neuen Stand damit ab (ProxyGameRegistry.apply"
                        + " vergleicht mit <=) und laeuft dauerhaft auf dem alten Register."
                        + " revision: erhoehen.");

        fail("Inhalt UND revision: sind gewandert — jetzt den Pin nachziehen, damit der naechste"
                + " Lauf wieder etwas bewacht:\n"
                + "    GEPINNTE_REVISION = " + revision + "L;\n"
                + "    GEPINNTER_ABDRUCK = \"" + abdruck + "\";");
    }

    /**
     * Semantischer Abdruck ueber alle Modi, nach Id sortiert, damit die Reihenfolge in der Datei
     * ihn nicht bewegt. Jedes Feld, das der Proxy auswertet, geht ein — Aliasse eingeschlossen,
     * denn ueber sie loest {@code QueueType.valueOf} auf.
     */
    private static String abdruckVon(GameRegistry registry) throws Exception {
        List<GameMode> sortiert = new ArrayList<>(registry.modes());
        sortiert.sort(Comparator.comparing(GameMode::id));

        StringBuilder sb = new StringBuilder();
        for (GameMode mode : sortiert) {
            List<String> aliasse = new ArrayList<>(mode.aliases());
            aliasse.sort(Comparator.naturalOrder());
            sb.append(mode.id()).append('|')
                    .append(mode.displayName()).append('|')
                    .append(mode.templateId()).append('|')
                    .append(mode.modeId()).append('|')
                    .append(mode.neededPlayers()).append('|')
                    .append(mode.maxPlayers()).append('|')
                    .append(mode.teamSize()).append('|')
                    .append(mode.enabled()).append('|')
                    .append(String.join(",", aliasse)).append('\n');
        }

        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return HexFormat.of().formatHex(digest.digest(sb.toString().getBytes("UTF-8")));
    }
}
