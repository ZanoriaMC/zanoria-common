#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gegenprobe zum Befehlswaechter - beide Richtungen, je Pruefung einzeln.

WARUM DAS EIN EIGENES WERKZEUG IST
==================================
Standing Rule 13: eine Reparatur zaehlt erst mit bestandener Gegenprobe. Standing Rule 21: eine
Zusicherung ueber ein Nicht-Ereignis braucht einen Nachbarn, der belegt, dass ueberhaupt etwas
lief - und die Gegenprobe muss je Haelfte EINZELN laufen, weil eine gemeinsame genau den Fall
verdeckt, in dem nur eine der beiden Haelften traegt.

Fuer jede der fuenf Pruefungen macht dieses Werkzeug drei Schritte:

  1  GIFT    ein Wegwerfbaum, der genau diese Pruefung ausloesen MUSS   -> erwartet Rueckgabe 1
  2  MUTANT  eine Kopie des Waechters, in der genau diese Pruefung entfernt ist,
             gegen denselben Baum                                       -> erwartet die Kennung WEG
  3  ZEUGE   das Original ist byteweise unveraendert (sha256 vorher/nachher)

⚠️ Schritt 2 ist der eigentliche Punkt. Ein Waechter, dessen Mutation nichts bricht, prueft
nichts - dann kam der Fund von woanders her, und die Pruefung war Deko. Standing Rule 28: ein
Mutationslauf, bei dem KEINE einzige Mutation gefangen wird, meldet nicht "alles ueberlebt",
sondern "es lief nichts".

⚠️ Und die Mutation muss etwas entfernen, das der Lauf wirklich benutzt (Standing Rule 30). Ein
Kommentar taugt nicht. Entfernt wird deshalb der Rumpf der Pruefung selbst, und der Mutant wird
vor dem Lauf gegen das Original byteweise verglichen: sind sie gleich, wurde nicht mutiert, und
der Fall gilt als NICHT GELAUFEN statt als bestanden.

Rueckgabe: 0 alle Faelle bestanden · 1 mindestens einer gefallen · 2 es lief nichts

WER RUFT DIESES SKRIPT (seit 2026-08-22)
========================================
``zanoria-common/gradle/waechter-gegenprobe.gradle`` haengt es an den ``check`` von
zanoria-common. Dort steht auch, warum ZENTRAL und nicht je Verbraucher - und was diese
Gegenprobe NICHT deckt.
⚠️ Bis dahin rief es NICHTS. Ein Werkzeug, das niemand ruft, belegt nichts, egal was es koennte.

⚠️ WAS SIE NICHT DECKT - am 2026-08-22 mit 22 Einzelmutationen gemessen: 12 rot, ZEHN still.
Still bleiben unter anderem: jede Ueber-Meldung (es gibt hier KEINEN Fall der Gegenrichtung -
Kommentarabtrennung aus, ``deklarierte_befehle`` leer, ``aliases`` nicht gezaehlt: alles gruen),
halbe Toetungen (D ohne die onTabComplete-Haelfte, E ohne CommandExecutor/TabExecutor/
TabCompleter, E ohne ``record``), die Ausnahmedatei - und die Stillegarantie des Waechters
selbst: wird sein ``return 2`` ("NICHTS GEPRUEFT") zu ``return 0``, bleiben diese Gegenprobe UND
``befehlswaechter.py --selbsttest`` gruen, waehrend alle acht Verbraucher einen bestandenen Lauf
ueber null gesehene Deskriptoren melden.
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
WAECHTER = os.path.join(HIER, "befehlswaechter.py")

PAPER_KOPF = """name: Probe
version: '1.0'
main: net.probe.Probe
api-version: '1.21'

permissions:
  probe.admin:
    default: op
"""

BUKKIT_KOPF = """name: Probe
version: '1.0'
main: net.probe.Probe
api-version: '1.21'

commands:
  ping:
    description: Probe
"""

SAUBERER_BEFEHL = """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;
public final class Pingbefehl implements BasicCommand {
    @Override public void execute(CommandSourceStack q, String[] a) { }
}
"""


# Je Fall: (Kennung, Deskriptorname, Deskriptorinhalt, Java-Dateien, Mutation)
# Die Mutation ist ein (suchen, ersetzen)-Paar auf dem Quelltext des Waechters. Sie entfernt den
# WIRKSAMEN Teil der Pruefung, nicht ihren Kommentar.
FAELLE = [
    (
        "A_PAPER_COMMANDS_BLOCK", "paper-plugin.yml",
        PAPER_KOPF + "\ncommands:\n  ping:\n    description: erfunden\n",
        {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { registerCommand("ping", "x", new Pingbefehl()); }
}
""", "Pingbefehl.java": SAUBERER_BEFEHL},
        ('    for nr, zeile in enumerate(zeilen, 1):\n        if zeile.startswith("commands:"):\n            return nr\n    return None',
         '    return None'),
    ),
    (
        "B_PAPER_GETCOMMAND", "paper-plugin.yml", PAPER_KOPF,
        {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("ping").setExecutor(null); }
}
"""},
        ('            if m.ist_paper and RE_GETCOMMAND_BLIND.search(nackt):',
         '            if False:'),
    ),
    (
        "C_BUKKIT_GETCOMMAND_UNDEKLARIERT", "plugin.yml", BUKKIT_KOPF,
        {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("fly").setExecutor(null); }
}
"""},
        ('            if (not m.ist_paper) and RE_GETCOMMAND_BLIND.search(nackt):',
         '            if False:'),
    ),
    (
        "D_PAPER_ONCOMMAND_TOT", "paper-plugin.yml", PAPER_KOPF,
        {"Probe.java": """package net.probe;
import org.bukkit.command.Command; import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public boolean onCommand(CommandSender s, Command c, String l, String[] a) { return true; }
}
"""},
        ('                if RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt):',
         '                if False:'),
    ),
    (
        "E_BEFEHL_NIE_ERZEUGT", "paper-plugin.yml", PAPER_KOPF,
        {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts"); }
}
""", "Pingbefehl.java": SAUBERER_BEFEHL},
        ('            if not any(erzeugung.search(t) for t in alle_texte.values()):',
         '            if False:'),
    ),
]


def sha(pfad: str) -> str:
    with io.open(pfad, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def schreibe(pfad: str, inhalt: str):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with io.open(pfad, "wb") as f:
        f.write(inhalt.encode("utf-8"))


def baum(basis: str, dname: str, dinhalt: str, dateien: dict) -> str:
    wurzel = os.path.join(basis, "probe")
    schreibe(os.path.join(wurzel, "src", "main", "resources", dname), dinhalt)
    for name, inhalt in dateien.items():
        schreibe(os.path.join(wurzel, "src", "main", "java", "net", "probe", name), inhalt)
    return wurzel


def lauf(waechter: str, wurzel: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, waechter, wurzel],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    if not os.path.isfile(WAECHTER):
        print(f"GEGENPROBE: {WAECHTER} fehlt - es lief nichts.", file=sys.stderr)
        return 2

    with io.open(WAECHTER, "rb") as f:
        original_bytes = f.read()
    sha_vorher = sha(WAECHTER)
    original_text = original_bytes.decode("utf-8")

    bestanden = 0
    gefallen = 0
    gelaufen = 0

    print(f"GEGENPROBE gegen {os.path.relpath(WAECHTER)}  (sha256/16 {sha_vorher})\n")

    with tempfile.TemporaryDirectory() as tmp:
        for nr, (kennung, dname, dinhalt, dateien, (suchen, ersetzen)) in enumerate(FAELLE, 1):
            # ⚠️ NEUTRALER Ordnername, nicht die Kennung. Beim ersten Anlauf hiess der
            # Wegwerfbaum wie der gesuchte Fund - und der Waechter druckt seinen Pfad in die
            # Zeile "geprueft ... in <pfad>". Damit stand die Kennung in JEDER Ausgabe, auch in
            # der des Mutanten, und alle fuenf Faelle meldeten "Kennung DA" bei Rueckgabe 0.
            # Standing Rule 22: der Prueftreffer war eine Zeichenkette, kein Fund.
            wurzel = baum(os.path.join(tmp, f"fall{nr}"), dname, dinhalt, dateien)

            # ── 1 GIFT ────────────────────────────────────────────────────
            rc_gift, aus_gift = lauf(WAECHTER, wurzel)
            gift_ok = rc_gift == 1 and kennung in aus_gift

            # ── 2 MUTANT ──────────────────────────────────────────────────
            if suchen not in original_text:
                print(f"  NICHT GELAUFEN  {kennung}: der Mutationsanker steht nicht mehr im"
                      f" Waechter. Kein Urteil, nicht 'bestanden'.")
                gefallen += 1
                continue
            mutant_text = original_text.replace(suchen, ersetzen, 1)
            mutant = os.path.join(tmp, f"mutant_{kennung}.py")
            with io.open(mutant, "wb") as f:
                f.write(mutant_text.encode("utf-8"))

            # ⚠️ Belegen, dass wirklich mutiert wurde. Ein Mutant, der dem Original gleicht,
            # gibt eine Gegenprobe zurueck, die nichts geprueft hat (Standing Rule 28).
            if sha(mutant) == sha_vorher:
                print(f"  NICHT GELAUFEN  {kennung}: Mutant ist byteweise das Original.")
                gefallen += 1
                continue

            rc_mut, aus_mut = lauf(mutant, wurzel)
            mutant_ok = kennung not in aus_mut
            gelaufen += 1

            ok = gift_ok and mutant_ok
            bestanden += 1 if ok else 0
            gefallen += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FEHL'} {kennung}")
            print(f"         GIFT    Rueckgabe {rc_gift}, Kennung {'da' if kennung in aus_gift else 'FEHLT'}"
                  f"   (erwartet: 1 / da)")
            print(f"         MUTANT  Rueckgabe {rc_mut}, Kennung {'DA' if kennung in aus_mut else 'weg'}"
                  f"   (erwartet: Kennung weg - sonst prueft die Zeile nichts)")

    # ── 3 ZEUGE ──────────────────────────────────────────────────────────
    sha_nachher = sha(WAECHTER)
    unberuehrt = sha_nachher == sha_vorher
    print(f"\n  ZEUGE   Original nach dem Lauf: sha256/16 {sha_nachher}"
          f"  -> {'unberuehrt' if unberuehrt else '⚠️ VERAENDERT'}")
    if not unberuehrt:
        gefallen += 1

    if gelaufen == 0:
        print("\nGEGENPROBE: keine einzige Mutation gelaufen - es lief nichts.", file=sys.stderr)
        return 2

    print(f"\nGEGENPROBE: {bestanden} von {bestanden + gefallen} Faellen bestanden,"
          f" {gelaufen} Mutationen wirklich ausgefuehrt.")
    return 0 if gefallen == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
