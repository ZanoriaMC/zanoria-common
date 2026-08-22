#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mutationskatalog - misst, WELCHE Beschaedigung des Befehlswaechters auffliegt und welche still bleibt.

WOFUER DAS DA IST
=================
``waechter-gegenprobe.py`` und ``befehlswaechter.py --selbsttest`` behaupten, den Waechter
abzusichern. Diese Behauptung ist selbst eine Behauptung. Dieses Werkzeug misst sie: es setzt
22 EINZELNE Beschaedigungen in den Waechter und laesst danach BEIDE Absicherungen gegen den
beschaedigten Waechter laufen. Wird der Lauf rot, ist die Beschaedigung GEFANGEN. Bleibt er
gruen, ist sie STILL - und dann deckt genau diese Stelle des Waechters niemand ab.

⚠️ SCHADEN einer stillen Mutation, konkret: der Waechter haengt in neun Repos. Verrutscht dort
eine Regex oder kippt eine Bedingung, meldet er in allen neun "keine Funde" und Rueckgabe 0 -
neun gruene Baeume ueber ungesehenem Befehlscode, kein Log, keine Warnung. Eine stille Mutation
ist also nicht "ein Testloch", sondern die exakte Bauart Fehler, gegen die der Waechter steht.

⚠️ DER KATALOG IST EINE REKONSTRUKTION. Am 2026-08-22 wurden schon einmal 22 Mutationen von Hand
gemessen (12 rot, 10 still), aber NICHT als Datei festgehalten - nur als Prosa in zwei
Kommentarkoepfen. Eine Zahl aus einer Messung, die niemand wiederholen kann, ist keine Messung,
sondern eine Erinnerung. Dieser Katalog ist aus dieser Prosa rekonstruiert und weicht in der
Auswahl ab; die Zahlen hier sind mit DIESEM Katalog gemessen und nur mit ihm vergleichbar.
Ab jetzt ist er eine Datei, und der naechste Lauf misst dasselbe wie dieser.

⚠️ NICHT AN ``check`` GEHAENGT, ausdruecklich. Ein Lauf startet 22 mal die ganze Gegenprobe plus
22 mal den Selbsttest, das sind einige hundert Unterprozesse. Er gehoert vor eine Aenderung am
Waechter und danach, von Hand - nicht in jeden Bau.

AUFRUF
======
    python3 mutationskatalog.py            alle 22, Zusammenfassung
    python3 mutationskatalog.py M21        nur eine (auch mehrere Kennungen moeglich)
    python3 mutationskatalog.py --laut     zeigt die Ausgabe der gefallenen Laeufe

RUECKGABE
=========
  0  keine einzige Mutation blieb still
  1  mindestens eine blieb still  (die Zahl steht in der Schlusszeile)
  2  es lief nichts - ein Anker fehlt oder ein Werkzeug ist weg. NICHT gruen.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
WAECHTER = os.path.join(HIER, "befehlswaechter.py")
GEGENPROBE = os.path.join(HIER, "waechter-gegenprobe.py")


def _stroeme_auf_utf8():
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  DIE 22 MUTATIONEN
#
#  Je Eintrag: (Kennung, Beschreibung, suchen, ersetzen)
#  ⚠️ ``suchen`` MUSS woertlich im Waechter stehen. Steht es nicht mehr da, meldet der Lauf
#  ANKER WEG und faellt - nicht "bestanden". Ein Katalog, der ins Leere greift, misst nichts.
# ─────────────────────────────────────────────────────────────────────────────

KATALOG: list[tuple[str, str, str, str]] = [
    # ── Ganze Toetungen der fuenf Proben ──────────────────────────────────────
    ("M01", "A: hat_commands_block findet nie einen Block",
     '    for nr, zeile in enumerate(zeilen, 1):\n'
     '        if zeile.startswith("commands:"):\n'
     '            return nr\n'
     '    return None',
     '    return None'),
    ("M02", "B: Probe abgeschaltet",
     '            if m.ist_paper and RE_GETCOMMAND_BLIND.search(nackt):',
     '            if False:'),
    ("M03", "C: Probe abgeschaltet",
     '            if (not m.ist_paper) and RE_GETCOMMAND_BLIND.search(nackt):',
     '            if False:'),
    ("M04", "D: Probe abgeschaltet",
     '                if RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt):',
     '                if False:'),
    ("M05", "E: Probe abgeschaltet",
     '            if not any(erzeugung.search(t) for t in alle_texte.values()):',
     '            if False:'),

    # ── Halbe Toetungen: je EINE Alternative einer Probe faellt weg ───────────
    ("M06", "D halb: die onTabComplete-Haelfte faellt weg",
     'RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt)',
     'RE_ONCOMMAND.search(nackt)'),
    ("M07", "D halb: die onCommand-Haelfte faellt weg",
     'RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt)',
     'RE_ONTABCOMPLETE.search(nackt)'),
    ("M08", "E halb: CommandExecutor zaehlt nicht mehr als Befehlsschnittstelle",
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor", "TabCompleter")',
     'BEFEHLSSCHNITTSTELLEN = ("BasicCommand", "TabExecutor", "TabCompleter")'),
    ("M09", "E halb: BasicCommand zaehlt nicht mehr",
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor", "TabCompleter")',
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "TabExecutor", "TabCompleter")'),
    ("M10", "E halb: TabExecutor zaehlt nicht mehr",
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor", "TabCompleter")',
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabCompleter")'),
    ("M12", "E halb: TabCompleter zaehlt nicht mehr",
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor", "TabCompleter")',
     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor")'),
    ("M13", "E halb: ein record traegt keine Befehlsschnittstelle mehr",
     r"r'\b(?:final\s+|public\s+|abstract\s+|static\s+)*(?:class|record)\s+(\w+)'",
     r"r'\b(?:final\s+|public\s+|abstract\s+|static\s+)*(?:class)\s+(\w+)'"),
    ("M18", "B/C halb: getCommand nur ohne Leerraum vor der Klammer",
     "RE_GETCOMMAND_BLIND = re.compile(r'\\bgetCommand\\s*\\(', re.S)",
     "RE_GETCOMMAND_BLIND = re.compile(r'\\bgetCommand\\(', re.S)"),

    # ── Ueber-Meldung: der Waechter wird ZU STRENG und schwaerzt Sauberes an ──
    ("M11", "E: die Erzeugungsregex sieht weder qualifiziert noch generisch",
     "erzeugung = re.compile(r'\\bnew\\s+(?:[\\w.]+\\.)?' + re.escape(name) + r'\\s*[(<]')",
     "erzeugung = re.compile(r'\\bnew\\s+' + re.escape(name) + r'\\s*\\(')"),
    ("M14", "YAML-Kommentarabtrennung aus",
     '        raus.append("" if zeile.lstrip().startswith("#") else zeile)',
     '        raus.append(zeile)'),
    ("M15", "deklarierte_befehle liefert nie einen Namen",
     '    namen = set()\n    drin = False',
     '    return set()\n    namen = set()\n    drin = False'),
    ("M16", "aliases werden nicht mehr gezaehlt",
     "            m = re.match(r'^\\s+aliases\\s*:\\s*\\[(.*)\\]\\s*$', zeile)",
     "            m = None if True else re.match(r'^\\s+aliases\\s*:\\s*\\[(.*)\\]\\s*$', zeile)"),
    ("M22", "die Listenform '- name' unter aliases wird nicht mehr gezaehlt",
     "            m = re.match(r'^\\s+-\\s*([A-Za-z0-9_\\-]+)\\s*$', zeile)",
     "            m = None if True else re.match(r'^\\s+-\\s*([A-Za-z0-9_\\-]+)\\s*$', zeile)"),
    ("M17", "Java-Kommentarabtrennung aus",
     '    ergebnis = []\n    i = 0\n    n = len(text)\n    while i < n:\n        c = text[i]\n'
     '        z = text[i + 1] if i + 1 < n else ""\n        if c == "/" and z == "/":',
     '    return text\n'
     '    ergebnis = []\n    i = 0\n    n = len(text)\n    while i < n:\n        c = text[i]\n'
     '        z = text[i + 1] if i + 1 < n else ""\n        if c == "/" and z == "/":'),

    # ── Die Maschinerie um die Proben ────────────────────────────────────────
    ("M19", "eine Ausnahme OHNE Begruendung gilt trotzdem",
     '            if len(teile) < 3 or not teile[2].strip():',
     '            if len(teile) < 3:'),
    ("M20", "eine DUBLETTE in der Ausnahmedatei wird nicht mehr beanstandet",
     '            if vorher is not None:',
     '            if False:'),

    # ── Die Stillegarantie des Waechters selbst ──────────────────────────────
    # ⚠️ Der Kern. Wird hier 2 zu 0, meldet der Waechter einen BESTANDENEN Lauf ueber NULL
    # gesehene Deskriptoren - in allen neun Repos zugleich.
    ("M21", "Stillegarantie: NICHTS GEPRUEFT meldet bestanden",
     '            print(z, file=sys.stderr)\n        return 2',
     '            print(z, file=sys.stderr)\n        return 0'),
]


def lauf(befehl: list[str]) -> tuple[int, str]:
    p = subprocess.run(befehl, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main(argv: list[str]) -> int:
    _stroeme_auf_utf8()
    laut = "--laut" in argv
    gewaehlt = {a for a in argv if not a.startswith("--")}

    for pfad in (WAECHTER, GEGENPROBE):
        if not os.path.isfile(pfad):
            print(f"MUTATIONSKATALOG: {pfad} fehlt - es lief nichts.", file=sys.stderr)
            return 2

    # ⚠️ ``\r\n`` zu ``\n``. ``core.autocrlf`` steht hier auf ``true``, ein frischer Klon legt
    # den Waechter mit CRLF ab - und die mehrzeiligen Anker unten stehen als ``\n``-Folgen im
    # Quelltext dieser Datei. Ohne die Normalisierung fande kein einziger seine Stelle, und der
    # Katalog meldete 22 mal ANKER WEG ueber einen Waechter, an dem nichts fehlt.
    with io.open(WAECHTER, "rb") as f:
        original = f.read().decode("utf-8").replace("\r\n", "\n")

    faelle = [k for k in KATALOG if not gewaehlt or k[0] in gewaehlt]
    if not faelle:
        print(f"MUTATIONSKATALOG: keine Kennung passt auf {sorted(gewaehlt)} - es lief nichts.",
              file=sys.stderr)
        return 2

    print(f"MUTATIONSKATALOG: {len(faelle)} Mutation(en) einzeln in den Waechter gesetzt,"
          f" danach je Gegenprobe UND Selbsttest.\n")

    still: list[tuple[str, str]] = []
    gefangen: list[str] = []
    kaputt: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        for kennung, was, suchen, ersetzen in faelle:
            if suchen not in original:
                print(f"  ANKER WEG  {kennung}  {was}")
                print(f"             Der Suchtext steht nicht mehr im Waechter. Kein Urteil -"
                      f" und kein Urteil ist NICHT 'bestanden'.")
                kaputt.append(kennung)
                continue

            arbeit = os.path.join(tmp, kennung)
            os.makedirs(arbeit, exist_ok=True)
            zielwaechter = os.path.join(arbeit, "befehlswaechter.py")
            with io.open(zielwaechter, "wb") as f:
                f.write(original.replace(suchen, ersetzen, 1).encode("utf-8"))
            shutil.copyfile(GEGENPROBE, os.path.join(arbeit, "waechter-gegenprobe.py"))

            rc_g, aus_g = lauf([sys.executable,
                                os.path.join(arbeit, "waechter-gegenprobe.py")])
            rc_s, aus_s = lauf([sys.executable, zielwaechter, "--selbsttest"])

            von = []
            if rc_g != 0:
                von.append(f"Gegenprobe rc={rc_g}")
            if rc_s != 0:
                von.append(f"Selbsttest rc={rc_s}")

            if von:
                print(f"  GEFANGEN   {kennung}  {was}")
                print(f"             von: {', '.join(von)}")
                gefangen.append(kennung)
            else:
                print(f"  ⚠️ STILL   {kennung}  {was}")
                print(f"             Gegenprobe rc=0, Selbsttest rc=0 - der beschaedigte"
                      f" Waechter meldet in neun Repos weiter gruen.")
                still.append((kennung, was))
                if laut:
                    for z in (aus_g + aus_s).splitlines():
                        print(f"             | {z}")

    print("")
    if kaputt:
        print(f"MUTATIONSKATALOG: {len(kaputt)} Anker fehlen ({', '.join(kaputt)}) - der Katalog"
              f" misst diese Stellen NICHT mehr. Anker nachziehen.", file=sys.stderr)
    print(f"MUTATIONSKATALOG: {len(gefangen)} gefangen, {len(still)} STILL,"
          f" {len(kaputt)} ohne Anker  (von {len(faelle)}).")
    for kennung, was in still:
        print(f"  STILL  {kennung}  {was}")

    if kaputt:
        return 2
    return 0 if not still else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
