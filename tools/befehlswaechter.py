#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Befehlswaechter - faengt Befehle, die deklariert oder implementiert sind und niemand anmeldet.

WOGEGEN DIESER WAECHTER STEHT
=============================
Ein ``commands:``-Block in einer ``paper-plugin.yml`` ist WIRKUNGSLOS. PaperPluginMeta hat kein
Feld fuer Befehle, und Configurate laesst unbekannte Schluessel stehen, ohne zu klagen. Die Datei
sieht vollstaendig aus, der Server startet, das Plugin laedt - und der Befehl existiert nicht.
Im Log steht kein Wort. Zweimal in diesem Stack passiert, beide Male durch Zufall gefunden:

  ZanUI        Block + getCommand() in onEnable -> UnsupportedOperationException, Plugin AUS
  HeavyCrown   Block ohne getCommand()          -> Plugin laedt, /heavycrown fehlt STILL
  NexusStrike  Block ohne getCommand()          -> derselbe Zustand, Modus unerreichbar

Paper sagt es woertlich in JavaPlugin.java (Zinth/paper-api):
  "You are trying to call JavaPlugin#getCommand on a Paper plugin during startup: you are
   probably trying to get a command you tried to define in paper-plugin.yml.
   Paper plugins do not support YAML-based command declarations!"

WAS ER PRUEFT (fuenf Proben, je mit Kennung)
============================================
  A  PAPER_COMMANDS_BLOCK     paper-plugin.yml fuehrt einen top-level ``commands:``-Block.
                              Immer ein Fehler. Exakt, keine Heuristik.
  B  PAPER_GETCOMMAND         Ein Paper-Plugin ruft ``getCommand(...)``. Das WIRFT im onEnable
                              und deaktiviert das ganze Plugin. Exakt.
  C  BUKKIT_GETCOMMAND_UNDEKLARIERT
                              Ein Bukkit-Plugin (plugin.yml) ruft ``getCommand("x")``, aber
                              ``x`` steht nicht unter ``commands:``. getCommand gibt dann null
                              zurueck -> NullPointerException im onEnable. Exakt.
  D  PAPER_ONCOMMAND_TOT      Eine JavaPlugin-Unterklasse eines Paper-Plugins ueberschreibt
                              ``onCommand``/``onTabComplete``. Diese Methoden ruft nur ein
                              PluginCommand aus einer plugin.yml. In einem Paper-Plugin gibt es
                              keines - der Rumpf ist tot durch Bauart. Exakt.
  E  BEFEHL_NIE_ERZEUGT       Eine Klasse implementiert CommandExecutor / BasicCommand /
                              TabExecutor / TabCompleter und wird nirgends im Projekt mit
                              ``new <Name>(`` erzeugt. Dann kann sie niemand anmelden.

SEINE REICHWEITE - das DESKRIPTOR-MODUL, ausdruecklich NICHT "das ganze Repo"
=============================================================================
Der Aufrufer uebergibt eine Projektwurzel (der Gradle-Anschluss uebergibt ``project.rootDir``).
Dieser Pfad dient AUSSCHLIESSLICH dem FINDEN der Deskriptoren. Welche Java-Dateien gelesen
werden, entscheidet ``module_finden()`` weiter unten: es sammelt je Deskriptor nur unter
``Modul.wurzel`` - dem Verzeichnis, in dem die ``paper-plugin.yml``/``plugin.yml`` liegt.

⚠️ Ein Nachbarmodul OHNE eigenen Deskriptor wird nie zu einem ``Modul`` und liefert keine
einzige Quelle. Befehlscode dort bleibt UNGESEHEN - kein Fund, Rueckgabe 0, kein Log, kein
Unterschied ausser der Zahl in der Zeile "geprueft N Deskriptor(en), M Java-Datei(en)". Wer die
Zeile nicht gegen den Bestand haelt, liest ein gruenes Urteil ueber einen Ausschnitt.

Am 2026-08-22 ueber die sieben angebundenen Plugin-Repos (Nexus, NexusStrike, RelicWars,
Showdown, ZanUI, ZanoriaCommands, ZanoriaLobby) plus CoreClash gemessen, beide Richtungen mit
derselben Klasse
(``implements BasicCommand``, nirgends ``new``) im Deskriptor-Modul und im Nachbarmodul:
im Deskriptor-Modul ``E_BEFEHL_NIE_ERZEUGT`` und Rueckgabe 1, im Nachbarmodul "keine Funde" und
Rueckgabe 0. Betroffen sind die zwei mehrmoduligen Repos:
  NexusStrike  101 Java-Dateien im Repo, gemeldet 54 (``:core`` 46 + Sonde 1 blind)
  ZanUI         49 Java-Dateien im Repo, gemeldet  9 (``:core`` 40 blind)
Beide ``:core`` sind heute bukkitfrei und koennen keine Befehlsschnittstelle tragen - das steht
dort aber nur als KOMMENTAR, keine Maschine haelt es.

WAS ER NICHT PRUEFT - ausdruecklich, damit niemand mehr hineinliest als drinsteht
=================================================================================
  * Er sieht ZEICHEN, nicht das laufende Programm. Probe E belegt eine ERZEUGUNG, nicht eine
    ANMELDUNG: wer ``new Meinbefehl(...)`` schreibt und das Ergebnis wegwirft, kommt durch.
    (Standing Rule 25: "hat einen Aufrufer" ist nicht "ist verdrahtet".)
  * Er prueft nicht, ob ein angemeldeter Name zu dem passt, den Doku oder GDD nennen.
  * Er prueft keine Brigadier-Baeume (``Commands.literal``) auf Erreichbarkeit - er sieht nur,
    ob die Klasse ueberhaupt erzeugt wird.
  * Er prueft keine Velocity-Plugins (dort ist ``CommandManager.register`` der Weg und es gibt
    keine YAML-Befehle).
  * Reflexion, Aufrufe ueber Fabriken oder ueber Zeichenketten sieht er nicht.

WIE ER GEGEN SEINE EIGENE STILLE GESICHERT IST (Standing Rules 16, 22, 29)
==========================================================================
  * Er nennt IMMER, wieviel er gesehen hat ("geprueft: N Deskriptoren, M Java-Dateien").
  * Hat er NICHTS in der Hand gehabt, ist das NICHT gruen, sondern Rueckgabe 2 (NICHTS
    GEPRUEFT). Ein Werkzeug, das nichts findet, hat nicht bewiesen, dass nichts da ist.
    ⚠️ Das sind VIER Wege, nicht einer - bis zum 2026-08-22 war nur der erste abgedeckt, die
    anderen drei druckten "keine Funde" und gaben 0 zurueck. Die Liste steht bei
    ``blindstellen()`` samt Begruendung, warum die Grenze bei NULL liegt und nicht bei "wenig":
      KEIN DESKRIPTOR         gar keine paper-plugin.yml/plugin.yml gefunden
      WURZEL OHNE DESKRIPTOR  eine von mehreren uebergebenen Wurzeln traegt nichts bei
      KEINE JAVA-DATEI        Deskriptoren da, aber keine einzige Quelle - B bis E liefen nie
      MODUL OHNE QUELLEN      ein Modul liefert nichts, ein anderes laesst den Lauf gruen
                              aussehen
  * Er entfernt Kommentare und Zeichenketten-Literale VOR jeder Suche. Ohne das schlaegt er auf
    genau den Kommentaren an, die den Fehler erklaeren - ZanUI und HeavyCrown fuehren beide das
    Wort ``getCommand`` in ihrem Javadoc, und HeavyCrowns Test-Javadoc nennt ``commands:``.
  * Er sucht mehrzeilig (Umbruch zwischen Name und Punkt ist in Java erlaubt).

RUECKGABEWERTE
==============
  0  nichts gefunden, und es wurde etwas geprueft
  1  Funde vorhanden (der Bau soll rot werden)
  2  nichts geprueft - Werkzeug oder Aufruf kaputt, NICHT gruen (vier Lagen, siehe
     ``blindstellen()``). ⚠️ 2 wird VOR allem anderen entschieden: ein Lauf, der nichts gesehen
     hat, darf weder "keine Funde" noch "Funde" melden, denn beides waere eine Aussage ueber
     Code, den er nie gelesen hat.
  3  Aufruf falsch
  4  keine offenen Funde, aber mindestens eine VERALTETE Ausnahme (der Bau soll rot werden)
     ⚠️ 1 schlaegt 4: liegen echte Funde vor, ist das der Rueckgabewert, und die veralteten
     Ausnahmen stehen trotzdem in der Ausgabe.

AUSNAHMEN
=========
Bekannte Altlasten stehen in ``<repo>/.befehlswaechter-ausnahmen``, eine Zeile je Fund:
``KENNUNG:relativer/pfad:Begruendung``. Ohne Begruendung gilt die Zeile nicht. Neue Schuld wird
rot, bekannte Schuld steht benannt - das ist der Unterschied zu einem abgeschalteten Waechter.

⚠️ JEDE ANGEWANDTE AUSNAHME STEHT IN DER AUSGABE - namentlich, mit ihrer Begruendung.
Bis zum 2026-08-22 verwarf ``melde()`` einen ausgenommenen Fund LAUTLOS, und der Lauf druckte
danach "keine Funde". Ein gruener Lauf und einer mit unterdruecktem Fund waren damit
ununterscheidbar - genau die Bauart Stille, gegen die dieser Waechter sonst steht. Seitdem
druckt der Lauf je angewandter Ausnahme eine Zeile UNTERDRUECKT samt Begruendung, und die
Schlusszeile heisst nicht mehr "keine Funde", sondern nennt die Zahl der unterdrueckten Funde.

⚠️ VERALTETE AUSNAHMEN FALLEN AUF (dieselbe Aenderung)
Die Ausnahmedatei behauptet selbst eine Pflicht: "Wer einen Eintrag aufloest, loescht die
Zeile" und "Liste offener Entscheidungen, kein Freibrief". Bis zum 2026-08-22 fuehrte diese
Pflicht NICHTS aus - eine Zeile fuer eine geloeschte Datei blieb ewig stehen und log den Leser
an, hier stuende noch eine offene Entscheidung. Jetzt wird jede Ausnahme, die NICHTS
unterdrueckt hat, in eine von drei Lagen einsortiert:

  WEG             Der Pfad existiert nicht mehr.                            -> ROT (Rueckgabe 4)
  GEGENSTANDSLOS  Der Pfad existiert und WURDE in diesem Lauf gelesen,
                  der Fund kam trotzdem nicht.                              -> ROT (Rueckgabe 4)
  UNGEPRUEFT      Der Pfad existiert, lag aber ausserhalb der Quellenmenge
                  (Nachbarmodul ohne eigenen Deskriptor, siehe oben).       -> nur LAUTE WARNUNG

⚠️ DIE ABWAEGUNG, ausdruecklich benannt. Eine veraltete Ausnahme, die den Bau rot macht, kann
jemanden zwingen, sie BLIND zu loeschen; eine, die nur warnt, wird ueberlesen. Der Schnitt
laeuft deshalb nicht zwischen "streng" und "milde", sondern zwischen BEWIESEN und UNBEKANNT:
  * Bei WEG und GEGENSTANDSLOS hat der Waechter den Beweis in der Hand - er hat die Datei
    gesucht bzw. gelesen und der Fund kam nicht. Die einzige richtige Handlung IST das Loeschen
    der Zeile, genau wie die Datei es selbst verlangt. Wer hier "blind" loescht, tut das
    Richtige; ein Schaden durch Blindheit ist gar nicht moeglich.
  * Bei UNGEPRUEFT hat er den Beweis NICHT - er ist auf diesem Pfad blind (Nachbarmodule ohne
    Deskriptor liefern keine einzige Quelle). Rot waere hier die Aufforderung, eine Ausnahme zu
    loeschen, die moeglicherweise weiter echte Schuld deckt, und das Loeschen wuerde am Urteil
    NICHTS aendern - der Fund erscheint so oder so nicht. Das ist reines Blindloeschen, und
    genau davor steht die Warnung statt der roten Ampel.

SELBSTTEST
==========
``python3 befehlswaechter.py --selbsttest`` baut Wegwerfbaeume fuer jede der fuenf Proben und
fuer die Gegenrichtung (ein sauberes Plugin muss gruen sein) und meldet jede einzeln. Danach
laeuft der Ausnahmeteil: derselbe Baum mit und ohne Ausnahmedatei (die Zeile muss erscheinen
bzw. fehlen) und je ein Baum fuer WEG, GEGENSTANDSLOS und UNGEPRUEFT. Zuletzt die
Stillegarantie: je ein Baum fuer die vier Blindstellen plus ein gesunder, der KEINE haben darf.
⚠️ Dieser letzte Teil ruft ``main()`` und prueft dessen RUECKGABEWERT, nicht ein internes Feld -
die Mutation, gegen die er steht, aendert nicht die Erkennung, sondern das Urteil.

WER PRUEFT DIESEN WAECHTER
==========================
  ``tools/waechter-gegenprobe.py``  Giftbaeume je Alternative + ein anspruchsvoller SAUBERER
                                    Baum gegen Ueber-Meldung + zu strenge Mutanten.
  ``--selbsttest`` (hier)           Gegenrichtung, Kommentarfall, Ausnahmen, Stillegarantie.
  ``tools/mutationskatalog.py``     misst, wieviel die beiden oben wirklich fangen. Am
                                    2026-08-22 vor der Reparatur: 11 von 22 still. Danach: 0.
Alle drei haengen an ``check`` von zanoria-common - bis auf den Katalog, der von Hand laeuft.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import tempfile
import textwrap

def _stroeme_auf_utf8():
    """Setzt stdout/stderr auf UTF-8.

    ⚠️ SCHADEN ohne das, unter Windows am 2026-08-22 gemessen: die Vorgabe ist ``cp1252``. Auf
    stdout steht sie auf ``strict`` - ein ``⚠️`` in einer gedruckten Zeile wirft dann
    UnicodeEncodeError, das Skript stirbt mitten in der Ausgabe und verlaesst sich mit
    Rueckgabe 1. Das sieht in Gradle aus wie "Funde vorhanden", ist aber ein abgestuerztes
    Werkzeug - der teuerste Verwechslungsfall, den dieser Waechter kennt. Auf stderr steht
    ``backslashreplace``; dort stand bisher woertlich ``\\u26a0\\ufe0f`` im Bericht statt des
    Zeichens. Der Gradle-Anschluss liest den Strom ohnehin als UTF-8
    (``ausgabe.toString("UTF-8")``), also ist UTF-8 hier die einzige Fassung, die auf beiden
    Seiten dasselbe bedeutet.
    """
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


AUSGESCHLOSSEN = {".git", "build", ".gradle", ".idea", "out", "run", "deploy",
                  ".claude", "node_modules", "logs", ".kotlin"}

BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand", "TabExecutor", "TabCompleter")

AUSNAHMEDATEI = ".befehlswaechter-ausnahmen"


# ─────────────────────────────────────────────────────────────────────────────
# Kommentare und Zeichenketten entfernen
# ─────────────────────────────────────────────────────────────────────────────

def java_ohne_kommentare(text: str) -> str:
    """Ersetzt Java-Kommentare und String-/Char-Literale durch Leerzeichen.

    ⚠️ Das ist keine Bequemlichkeit, sondern der Kern der Brauchbarkeit. ZanUIs
    TestDialogCommand.java und HeavyCrowns Heavybefehl.java fuehren das Wort ``getCommand``
    in ihrem Javadoc - genau in der Erklaerung, warum sie es NICHT rufen. Ein Waechter, der
    Kommentare mitliest, meldet die Erklaerung als den Fehler.

    Zeichen bleiben positionsgleich (Ersatz durch Leerzeichen), damit Zeilennummern stimmen.
    """
    ergebnis = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        z = text[i + 1] if i + 1 < n else ""
        if c == "/" and z == "/":
            while i < n and text[i] != "\n":
                ergebnis.append(" ")
                i += 1
            continue
        if c == "/" and z == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                ergebnis.append("\n" if text[i] == "\n" else " ")
                i += 1
            for _ in range(min(2, n - i)):
                ergebnis.append(" ")
                i += 1
            continue
        if c == '"':
            # Text-Block """ ... """
            if text[i:i + 3] == '"""':
                ergebnis.append(" ")
                ergebnis.append(" ")
                ergebnis.append(" ")
                i += 3
                while i < n and text[i:i + 3] != '"""':
                    ergebnis.append("\n" if text[i] == "\n" else " ")
                    i += 1
                for _ in range(min(3, n - i)):
                    ergebnis.append(" ")
                    i += 1
                continue
            ergebnis.append(" ")
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    ergebnis.append(" ")
                    i += 1
                    if i < n:
                        ergebnis.append(" ")
                        i += 1
                    continue
                ergebnis.append("\n" if text[i] == "\n" else " ")
                i += 1
            if i < n:
                ergebnis.append(" ")
                i += 1
            continue
        if c == "'":
            ergebnis.append(" ")
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    ergebnis.append(" ")
                    i += 1
                    if i < n:
                        ergebnis.append(" ")
                        i += 1
                    continue
                ergebnis.append(" ")
                i += 1
            if i < n:
                ergebnis.append(" ")
                i += 1
            continue
        ergebnis.append(c)
        i += 1
    return "".join(ergebnis)


def java_literale_behalten(text: str) -> str:
    """Wie oben, aber String-Literale bleiben stehen.

    Gebraucht fuer Probe B und C, wo der Befehlsname IM Literal steht: ``getCommand("tp")``.
    Kommentare fallen trotzdem weg.
    """
    ergebnis = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        z = text[i + 1] if i + 1 < n else ""
        if c == "/" and z == "/":
            while i < n and text[i] != "\n":
                ergebnis.append(" ")
                i += 1
            continue
        if c == "/" and z == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                ergebnis.append("\n" if text[i] == "\n" else " ")
                i += 1
            for _ in range(min(2, n - i)):
                ergebnis.append(" ")
                i += 1
            continue
        if c == '"':
            ergebnis.append(c)
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    ergebnis.append(text[i])
                    i += 1
                    if i < n:
                        ergebnis.append(text[i])
                        i += 1
                    continue
                ergebnis.append(text[i])
                i += 1
            if i < n:
                ergebnis.append(text[i])
                i += 1
            continue
        ergebnis.append(c)
        i += 1
    return "".join(ergebnis)


def yaml_ohne_kommentare(text: str) -> list[str]:
    """Gibt die Zeilen zurueck, Kommentarzeilen als Leerzeile.

    ⚠️ Nur ganze Kommentarzeilen. Ein ``#`` mitten in einer Zeile hinter einem Wert wird nicht
    angetastet - fuer die einzige Frage hier (steht ``commands:`` in Spalte 0?) reicht das, und
    ein halber YAML-Parser waere eine zweite Wahrheit neben Configurate.
    """
    raus = []
    for zeile in text.split("\n"):
        raus.append("" if zeile.lstrip().startswith("#") else zeile)
    return raus


# ─────────────────────────────────────────────────────────────────────────────
# Einsammeln
# ─────────────────────────────────────────────────────────────────────────────

def lies(pfad: str) -> str:
    with io.open(pfad, "rb") as f:
        rohdaten = f.read()
    return rohdaten.decode("utf-8", errors="replace")


def gehe(wurzel: str):
    for ordner, unter, dateien in os.walk(wurzel):
        unter[:] = [u for u in unter if u not in AUSGESCHLOSSEN]
        for d in dateien:
            yield os.path.join(ordner, d)


class Modul:
    """Ein Deskriptor plus die Java-Quellen, die dazugehoeren."""

    def __init__(self, deskriptor: str, ist_paper: bool, herkunft: str = ""):
        self.deskriptor = deskriptor
        self.ist_paper = ist_paper
        # ⚠️ Die WURZEL, unter der dieser Deskriptor gefunden wurde. Ohne sie laesst sich nicht
        # sagen, ob eine uebergebene Wurzel ueberhaupt etwas beigetragen hat - siehe
        # blindstellen(), Lage WURZEL OHNE DESKRIPTOR.
        self.herkunft = herkunft
        # .../<modul>/src/<menge>/resources/<datei>  ->  .../<modul>
        res = os.path.dirname(deskriptor)
        menge = os.path.dirname(res)
        src = os.path.dirname(menge)
        self.wurzel = os.path.dirname(src)
        self.quellen: list[str] = []

    def __repr__(self):
        return f"Modul({self.deskriptor})"


def module_finden(wurzeln: list[str]) -> list[Modul]:
    module = []
    for w in wurzeln:
        for pfad in gehe(w):
            name = os.path.basename(pfad)
            if name == "paper-plugin.yml":
                module.append(Modul(pfad, True, w))
            elif name == "plugin.yml":
                # ⚠️ Nur echte Plugin-Deskriptoren. Eine plugin.yml irgendwo in einer Vorlage
                # oder in einem Serververzeichnis ist nicht unser Gegenstand.
                if f"{os.sep}resources{os.sep}" in pfad or pfad.endswith(f"resources{os.sep}plugin.yml"):
                    module.append(Modul(pfad, False, w))
    for m in module:
        if os.path.isdir(m.wurzel):
            for pfad in gehe(m.wurzel):
                if pfad.endswith(".java"):
                    m.quellen.append(pfad)
    return module


class Ausnahme:
    """Eine gueltige Zeile aus ``.befehlswaechter-ausnahmen``.

    ⚠️ ``angewandt`` ist der ganze Punkt dieser Klasse. Vorher war eine Ausnahme ein blosses
    Paar in einem ``set`` - ob sie je gegriffen hat, wusste hinterher niemand, und der Lauf
    druckte "keine Funde". Wer zaehlt, kann sowohl die Unterdrueckung NENNEN als auch die
    Ausnahme erkennen, die gar nichts mehr unterdrueckt.
    """

    __slots__ = ("kennung", "pfad", "begruendung", "wurzel", "datei", "zeilennummer", "angewandt")

    def __init__(self, kennung: str, pfad: str, begruendung: str,
                 wurzel: str, datei: str, zeilennummer: int):
        self.kennung = kennung
        self.pfad = pfad
        self.begruendung = begruendung
        self.wurzel = wurzel
        self.datei = datei
        self.zeilennummer = zeilennummer
        self.angewandt = 0

    @property
    def schluessel(self) -> tuple[str, str]:
        return (self.kennung, self.pfad)

    @property
    def absolut(self) -> str:
        return os.path.join(self.wurzel, self.pfad.replace("/", os.sep))

    @property
    def herkunft(self) -> str:
        return f"{os.path.basename(self.datei)}:{self.zeilennummer}"

    def __repr__(self):
        return f"Ausnahme({self.kennung}, {self.pfad}, angewandt={self.angewandt})"


def ausnahmen_lesen(wurzeln: list[str]) -> tuple[list[Ausnahme], list[str]]:
    """Liest ``.befehlswaechter-ausnahmen`` aus jeder Wurzel.

    Gibt (gueltige Ausnahmen, Beanstandungen) zurueck. Ohne Begruendung gilt die Zeile nicht.

    ⚠️ Verworfene Zeilen werden nicht mehr still uebergangen. Eine Zeile ohne Begruendung und
    eine Dublette sehen im Repo aus wie eine wirksame Ausnahme; wer nicht erfaehrt, dass sie
    nicht gilt, sucht den roten Fund an der falschen Stelle - oder haelt eine Schuld fuer
    gedeckt, die es nicht ist.
    """
    raus: list[Ausnahme] = []
    beanstandungen: list[str] = []
    gesehen: dict[tuple[str, str], Ausnahme] = {}
    for w in wurzeln:
        p = os.path.join(w, AUSNAHMEDATEI)
        if not os.path.isfile(p):
            continue
        for nr, rohzeile in enumerate(lies(p).split("\n"), 1):
            zeile = rohzeile.strip()
            if not zeile or zeile.startswith("#"):
                continue
            teile = zeile.split(":", 2)
            if len(teile) < 3 or not teile[2].strip():
                beanstandungen.append(
                    f"{os.path.basename(p)}:{nr}: Zeile OHNE Begruendung - sie gilt NICHT,"
                    f" der Fund bleibt rot. Form: KENNUNG:relativer/pfad:Begruendung."
                    f"\n      Zeile: {zeile[:160]}")
                continue
            a = Ausnahme(teile[0].strip(), teile[1].strip().replace("\\", "/"),
                         teile[2].strip(), w, p, nr)
            vorher = gesehen.get(a.schluessel)
            if vorher is not None:
                beanstandungen.append(
                    f"{os.path.basename(p)}:{nr}: DUBLETTE zu {vorher.herkunft} fuer"
                    f" {a.kennung} {a.pfad} - nur die erste Zeile gilt. Die zweite waere sonst"
                    f" gleich als veraltet gemeldet worden, obwohl sie es nicht ist.")
                continue
            gesehen[a.schluessel] = a
            raus.append(a)
    return raus, beanstandungen


# ⚠️ Die drei Lagen einer Ausnahme, die NICHTS unterdrueckt hat. Warum zwei davon rot machen und
# die dritte nur warnt, steht ausfuehrlich im Kopf der Datei unter AUSNAHMEN.
VERALTET_WEG = "WEG"
VERALTET_GEGENSTANDSLOS = "GEGENSTANDSLOS"
VERALTET_UNGEPRUEFT = "UNGEPRUEFT"

VERALTET_ROT = (VERALTET_WEG, VERALTET_GEGENSTANDSLOS)

VERALTET_SATZ = {
    VERALTET_WEG:
        "der Pfad existiert nicht mehr. Die Ausnahme deckt nichts und behauptet trotzdem eine"
        " offene Entscheidung. Die Datei verlangt es selbst: wer einen Eintrag aufloest,"
        " loescht die Zeile.",
    VERALTET_GEGENSTANDSLOS:
        "der Pfad wurde in diesem Lauf GELESEN und der Fund kam nicht. Die Altlast ist weg, die"
        " Zeile nicht. Sie deckt ab jetzt nur noch kuenftige Schuld an derselben Stelle - genau"
        " das soll eine Ausnahme nicht.",
    VERALTET_UNGEPRUEFT:
        "der Pfad existiert, lag aber AUSSERHALB der gelesenen Quellenmenge (Nachbarmodul ohne"
        " eigenen Deskriptor). Ob die Altlast weg ist, weiss dieser Lauf NICHT - er war dort"
        " blind. Deshalb nur diese Warnung und kein rotes Urteil: ein Loeschen aufgrund einer"
        " Blindstelle waere blindes Loeschen.",
}


class Ergebnis:
    """Was ein Lauf gesehen hat - Funde UND was ihm die Ausnahmen weggenommen haben."""

    __slots__ = ("funde", "deskriptoren", "java_dateien", "ausnahmen", "veraltet",
                 "beanstandungen", "module", "wurzeln")

    def __init__(self, funde, deskriptoren, java_dateien, ausnahmen, veraltet, beanstandungen,
                 module=(), wurzeln=()):
        self.funde: list[str] = funde
        self.deskriptoren: int = deskriptoren
        self.java_dateien: int = java_dateien
        self.ausnahmen: list[Ausnahme] = ausnahmen
        self.veraltet: list[tuple[Ausnahme, str]] = veraltet
        self.beanstandungen: list[str] = beanstandungen
        # ⚠️ Nur mit diesen beiden laesst sich "nichts gefunden" von "nichts gesehen"
        # unterscheiden. Siehe blindstellen().
        self.module: list = list(module)
        self.wurzeln: list[str] = list(wurzeln)

    @property
    def angewandt(self) -> list[Ausnahme]:
        return [a for a in self.ausnahmen if a.angewandt]

    @property
    def unterdrueckt(self) -> int:
        return sum(a.angewandt for a in self.ausnahmen)

    @property
    def veraltet_rot(self) -> list[tuple[Ausnahme, str]]:
        return [(a, art) for a, art in self.veraltet if art in VERALTET_ROT]


# ─────────────────────────────────────────────────────────────────────────────
# Die fuenf Proben
# ─────────────────────────────────────────────────────────────────────────────

RE_GETCOMMAND = re.compile(r'\bgetCommand\s*\(\s*"([^"]*)"\s*\)', re.S)
RE_GETCOMMAND_BLIND = re.compile(r'\bgetCommand\s*\(', re.S)
RE_KLASSE = re.compile(
    r'\b(?:final\s+|public\s+|abstract\s+|static\s+)*(?:class|record)\s+(\w+)'
    r'[^{;]*?\bimplements\b([^{]*)\{', re.S)
RE_EXTENDS_JAVAPLUGIN = re.compile(r'\bclass\s+(\w+)[^{;]*?\bextends\s+JavaPlugin\b', re.S)
RE_ONCOMMAND = re.compile(r'\bboolean\s+onCommand\s*\(', re.S)
RE_ONTABCOMPLETE = re.compile(r'\bonTabComplete\s*\(', re.S)


def deklarierte_befehle(zeilen: list[str]) -> set[str]:
    """Sammelt die Namen unter einem top-level ``commands:``-Block, inklusive ``aliases``."""
    namen = set()
    drin = False
    for zeile in zeilen:
        if zeile.startswith("commands:"):
            drin = True
            continue
        if drin:
            if zeile.strip() == "":
                continue
            if not zeile.startswith((" ", "\t")):
                drin = False
                continue
            m = re.match(r'^\s{1,4}([A-Za-z0-9_\-]+)\s*:\s*$', zeile)
            if m:
                namen.add(m.group(1).lower())
            m = re.match(r'^\s+aliases\s*:\s*\[(.*)\]\s*$', zeile)
            if m:
                for a in m.group(1).split(","):
                    a = a.strip().strip("'\"")
                    if a:
                        namen.add(a.lower())
            m = re.match(r'^\s+-\s*([A-Za-z0-9_\-]+)\s*$', zeile)
            if m:
                namen.add(m.group(1).lower())
    return namen


def hat_commands_block(zeilen: list[str]) -> int | None:
    for nr, zeile in enumerate(zeilen, 1):
        if zeile.startswith("commands:"):
            return nr
    return None


def pruefe(wurzeln: list[str]) -> Ergebnis:
    """Prueft und gibt ein ``Ergebnis`` zurueck - Funde UND das, was Ausnahmen weggenommen haben."""
    module = module_finden(wurzeln)
    ausnahmen, beanstandungen = ausnahmen_lesen(wurzeln)
    nach_schluessel = {a.schluessel: a for a in ausnahmen}
    funde: list[str] = []
    java_gesehen = 0
    # ⚠️ Alles, was dieser Lauf wirklich in der Hand hatte. Nur damit laesst sich spaeter
    # "der Fund ist weg" von "ich war dort blind" unterscheiden - siehe VERALTET_UNGEPRUEFT.
    gelesen: set[str] = set()

    def rel(p: str) -> str:
        for w in wurzeln:
            try:
                r = os.path.relpath(p, w)
                if not r.startswith(".."):
                    return r.replace("\\", "/")
            except ValueError:
                pass
        return p.replace("\\", "/")

    def melde(kennung: str, pfad: str, satz: str):
        # ⚠️ Hier wird nichts mehr lautlos weggeworfen. Die getroffene Ausnahme wird GEZAEHLT,
        # und main() druckt sie namentlich mit Begruendung. Ein Lauf mit Ausnahme darf nicht
        # aussehen wie einer ohne - vor dem 2026-08-22 tat er genau das.
        treffer = nach_schluessel.get((kennung, rel(pfad)))
        if treffer is not None:
            treffer.angewandt += 1
            return
        funde.append(f"{kennung}  {rel(pfad)}\n      {satz}")

    for m in module:
        gelesen.add(rel(m.deskriptor))
        for q in m.quellen:
            gelesen.add(rel(q))
        zeilen = yaml_ohne_kommentare(lies(m.deskriptor))

        # ── A ──────────────────────────────────────────────────────────────
        if m.ist_paper:
            nr = hat_commands_block(zeilen)
            if nr is not None:
                melde("A_PAPER_COMMANDS_BLOCK", m.deskriptor,
                      f"Zeile {nr}: top-level commands:-Block in einer paper-plugin.yml. Paper"
                      f" liest das Feld NICHT (PaperPluginMeta hat es nicht, Configurate laesst"
                      f" unbekannte Schluessel stehen). Der Block sieht aus wie eine Anmeldung"
                      f" und ist keine - der Befehl existiert nicht, und im Log steht nichts."
                      f" Befehle gehoeren in registerCommand(...) bzw."
                      f" LifecycleEvents.COMMANDS.")

        deklariert = deklarierte_befehle(zeilen) if not m.ist_paper else set()

        klassen_mit_befehlsschnittstelle: list[tuple[str, str]] = []
        alle_texte: dict[str, str] = {}

        for q in m.quellen:
            java_gesehen += 1
            roh = lies(q)
            nackt = java_ohne_kommentare(roh)
            mit_literalen = java_literale_behalten(roh)
            alle_texte[q] = nackt

            # ── B ──────────────────────────────────────────────────────────
            # ⚠️ B und C stehen als ZWEI eigenstaendige if-Bloecke da, nicht als if/else. Der
            # Grund ist die Gegenprobe: bei einem if/else laesst sich B nicht abschalten, ohne
            # dass C an seine Stelle springt - der Mutant meldete dann einen ANDEREN Fund und
            # sah aus wie ein Waechter, der noch greift. Zwei Bloecke lassen sich einzeln
            # abschalten, und genau das verlangt Standing Rule 21.
            if m.ist_paper and RE_GETCOMMAND_BLIND.search(nackt):
                melde("B_PAPER_GETCOMMAND", q,
                      "ruft getCommand(...) in einem Paper-Plugin. Das WIRFT"
                      " (UnsupportedOperationException), wenn es im onEnable steht, und"
                      " nimmt das ganze Plugin mit - kein Dienst, kein Hoerer, kein Befehl."
                      " Genau das ist ZanUI am 2026-08-20 passiert.")

            # ── C ──────────────────────────────────────────────────────────
            if (not m.ist_paper) and RE_GETCOMMAND_BLIND.search(nackt):
                for treffer in RE_GETCOMMAND.finditer(mit_literalen):
                    name = treffer.group(1).lower()
                    if name and name not in deklariert:
                        melde("C_BUKKIT_GETCOMMAND_UNDEKLARIERT", q,
                              f'getCommand("{treffer.group(1)}") - der Name steht NICHT unter'
                              f' commands: in {rel(m.deskriptor)}. getCommand gibt dann null'
                              f' zurueck; ein .setExecutor(...) darauf ist eine'
                              f' NullPointerException im onEnable und deaktiviert das Plugin.')

            # ── D ──────────────────────────────────────────────────────────
            if m.ist_paper and RE_EXTENDS_JAVAPLUGIN.search(nackt):
                if RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt):
                    melde("D_PAPER_ONCOMMAND_TOT", q,
                          "ueberschreibt onCommand/onTabComplete in einem Paper-Plugin. Diese"
                          " Methoden ruft ausschliesslich ein PluginCommand aus einer"
                          " plugin.yml. Ein Paper-Plugin hat keines - der Rumpf ist tot durch"
                          " Bauart, nicht durch Zufall. Der Weg ist eine BasicCommand-Klasse"
                          " plus registerCommand(...).")

            # ── E: sammeln ────────────────────────────────────────────────
            for treffer in RE_KLASSE.finditer(nackt):
                name, schnittstellen = treffer.group(1), treffer.group(2)
                if any(s in schnittstellen for s in BEFEHLSSCHNITTSTELLEN):
                    klassen_mit_befehlsschnittstelle.append((name, q))

        # ── E: urteilen ────────────────────────────────────────────────────
        for name, q in klassen_mit_befehlsschnittstelle:
            erzeugung = re.compile(r'\bnew\s+(?:[\w.]+\.)?' + re.escape(name) + r'\s*[(<]')
            if not any(erzeugung.search(t) for t in alle_texte.values()):
                melde("E_BEFEHL_NIE_ERZEUGT", q,
                      f"{name} implementiert eine Befehlsschnittstelle, wird aber im ganzen"
                      f" Modul nirgends mit 'new {name}(' erzeugt. Was nie entsteht, kann"
                      f" niemand anmelden - der Befehl ist unerreichbar, ohne dass irgendwo"
                      f" etwas im Log steht. ⚠️ Diese Probe belegt eine ERZEUGUNG, nicht eine"
                      f" ANMELDUNG.")

    # ── Die Pflicht, die die Ausnahmedatei ueber sich selbst behauptet, ausfuehren ──────────
    # "Wer einen Eintrag aufloest, loescht die Zeile." Bis zum 2026-08-22 fuehrte das NICHTS
    # aus. Eine Ausnahme, die nichts unterdrueckt hat, ist entweder erledigt (dann muss die
    # Zeile weg) oder sie liegt in einer Blindstelle (dann weiss dieser Lauf es nicht).
    veraltet: list[tuple[Ausnahme, str]] = []
    for a in ausnahmen:
        if a.angewandt:
            continue
        if not os.path.exists(a.absolut):
            veraltet.append((a, VERALTET_WEG))
        elif a.pfad in gelesen:
            veraltet.append((a, VERALTET_GEGENSTANDSLOS))
        else:
            veraltet.append((a, VERALTET_UNGEPRUEFT))

    return Ergebnis(funde, len(module), java_gesehen, ausnahmen, veraltet, beanstandungen,
                    module, wurzeln)


# ─────────────────────────────────────────────────────────────────────────────
#  DIE STILLEGARANTIE - jeder Weg, "bestanden" zu melden, ohne etwas gesehen zu haben
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ Bis zum 2026-08-22 stand hier EIN Fall, und zwar als nackte Zeile ``return 2`` mitten in
# ``main()``: null Deskriptoren. Zwei Dinge waren daran falsch.
#
#   1  Er war nicht der einzige Weg. Ein Deskriptor OHNE eine einzige Java-Datei daneben, ein
#      zweites Modul, das keine Quelle liefert, eine uebergebene Wurzel, die gar nichts
#      beitraegt - jeder dieser Laeufe druckte "keine Funde" und gab 0 zurueck. Der Waechter
#      hatte in all diesen Faellen NICHTS in der Hand und meldete trotzdem einen bestandenen
#      Lauf. Es ist derselbe Fall wie null Deskriptoren, nur eine Ebene tiefer.
#   2  Er war UNGEPRUEFT. Wer ``return 2`` zu ``return 0`` machte, bekam von Gegenprobe und
#      Selbsttest gruen - am 2026-08-22 als Mutation M21 gemessen. Die Stillegarantie war
#      damit selbst die Stille, gegen die sie steht.
#
# Deshalb steht die Frage jetzt an EINER Stelle, gibt GRUENDE statt eines Wahrheitswerts zurueck
# (jeder Grund ist eine eigene Zeile in der Ausgabe und damit einzeln pruefbar), und beide
# Absicherungen fahren sie an: ``waechter-gegenprobe.py`` (Fall NICHTS_GEPRUEFT und Geschwister)
# und ``--selbsttest`` (Abschnitt "Stillegarantie").
#
# ⚠️ WO DIE GRENZE LIEGT UND WARUM GENAU DORT: bei NULL, nicht bei "wenig".
# ZanoriaLobby hat FUENF Java-Dateien, ZanoriaCommands SECHS - beide vollstaendig und richtig
# gesehen. Eine Mindestzahl waere geraten und wuerde diese zwei Repos dauerhaft rot faerben,
# ohne dass dort irgendetwas fehlt; sie muesste dann per Ausnahme abgeschaltet werden, und eine
# abgeschaltete Grenze ist keine. Null dagegen ist kein Schaetzwert, sondern eine Aussage ueber
# das Werkzeug selbst: der Waechter kann ueber eine Datei, die er nie gelesen hat, nichts
# behaupten - und ueber null gelesene Dateien behauptet er genau nichts. Der Satz "ich habe
# nichts gefunden" setzt voraus, dass gesucht wurde; bei null ist diese Voraussetzung falsch,
# bei fuenf ist sie wahr. Die Grenze trennt also nicht viel von wenig, sondern GESUCHT von
# NICHT GESUCHT, und dazwischen liegt nichts Ermessbares.

BLIND_KEIN_DESKRIPTOR = "KEIN DESKRIPTOR"
BLIND_WURZEL_LEER = "WURZEL OHNE DESKRIPTOR"
BLIND_KEINE_QUELLE = "KEINE JAVA-DATEI"
BLIND_MODUL_OHNE_QUELLEN = "MODUL OHNE QUELLEN"


def blindstellen(e: Ergebnis) -> list[tuple[str, str]]:
    """Gibt (Lage, Satz) je Weg zurueck, auf dem dieser Lauf NICHTS in der Hand hatte.

    Leere Liste heisst: es wurde wirklich etwas gesehen. Nur dann darf ein Urteil fallen.
    """
    gruende: list[tuple[str, str]] = []

    if e.deskriptoren == 0:
        gruende.append((
            BLIND_KEIN_DESKRIPTOR,
            "keine paper-plugin.yml und keine plugin.yml gefunden. Ohne Deskriptor gibt es kein"
            " Modul, ohne Modul keine gelesene Quelle - dieser Lauf hat NICHTS geprueft."
            " Falscher Pfad, oder der Deskriptor liegt nicht unter src/*/resources/."))
    else:
        # ⚠️ Nur sinnvoll, wenn mehr als eine Wurzel uebergeben wurde; bei einer sagt es der
        # Fall darueber schon. Mehrere Wurzeln sind der gefaehrlichere Aufruf: EINE davon kann
        # ins Leere zeigen, waehrend die anderen den Lauf gruen aussehen lassen.
        if len(e.wurzeln) > 1:
            beigetragen = {m.herkunft for m in e.module}
            for w in e.wurzeln:
                if w not in beigetragen:
                    gruende.append((
                        BLIND_WURZEL_LEER,
                        f"{w} hat keinen einzigen Deskriptor beigetragen. Die anderen Wurzeln"
                        f" haben welche - der Lauf saehe also gruen aus, waehrend dieser Pfad"
                        f" komplett ungesehen bleibt."))

    if e.deskriptoren > 0 and e.java_dateien == 0:
        gruende.append((
            BLIND_KEINE_QUELLE,
            "es gibt Deskriptoren, aber unter keinem von ihnen liegt eine einzige .java-Datei."
            " Die Proben B bis E lesen ausschliesslich Java-Quellen; sie sind in diesem Lauf"
            " allesamt nicht zum Zuge gekommen. 'Keine Funde' heisst hier 'nicht gesucht'."))

    for m in e.module:
        if not m.quellen:
            gruende.append((
                BLIND_MODUL_OHNE_QUELLEN,
                f"{m.deskriptor} meldet ein Plugin an, aber unter {m.wurzel} liegt keine einzige"
                f" .java-Datei. Fuer dieses Modul sind B bis E nicht gelaufen. Ein anderes Modul"
                f" kann den Lauf trotzdem gruen aussehen lassen - genau diese Mischung ist"
                f" gefaehrlich."))

    return gruende


def zeilen_blindstellen(gruende: list[tuple[str, str]]) -> list[str]:
    zeilen = [
        f"BEFEHLSWAECHTER: NICHTS GEPRUEFT - {len(gruende)} Blindstelle(n). Das ist KEIN"
        f" bestandener Lauf. Ein Werkzeug, das nichts gesehen hat, hat nicht bewiesen, dass"
        f" nichts da ist.",
    ]
    for lage, satz in gruende:
        zeilen.append(f"  BLIND  {lage}")
        zeilen.extend(_umbruch(satz, "      "))
    return zeilen


# ─────────────────────────────────────────────────────────────────────────────
# Ausgabe - eigene Funktionen, damit der Selbsttest den TEXT pruefen kann
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ Diese drei Funktionen geben Zeilen zurueck, statt zu drucken. Nur so kann der Selbsttest
# belegen, dass die Zeile WIRKLICH ERSCHEINT - eine Zusicherung auf ein internes Feld belegt das
# nicht, und genau das war der Fehler: ``melde()`` verwarf sauber, nur sah es niemand.

def _umbruch(text: str, einzug: str, breite: int = 100) -> list[str]:
    # ⚠️ Der Folgeeinzug ist LEERRAUM in Breite des ersten, nicht der erste noch einmal. Sonst
    # steht "Begruendung:" vor jeder Zeile und eine lange Begruendung liest sich wie ein Dutzend
    # Ausnahmen statt wie eine.
    return textwrap.wrap(text, width=breite, initial_indent=einzug,
                         subsequent_indent=" " * len(einzug)) or [einzug.rstrip()]


def zeilen_ausnahmen(e: Ergebnis) -> list[str]:
    """Je angewandter Ausnahme eine sichtbare Zeile - mit Pfad, Zahl und Begruendung."""
    angewandt = e.angewandt
    if not angewandt:
        return []
    zeilen = [
        f"BEFEHLSWAECHTER: {len(angewandt)} Ausnahme(n) angewandt,"
        f" {e.unterdrueckt} Fund(e) dadurch unterdrueckt."
        f" ⚠️ Das ist KEIN Lauf ohne Funde.",
    ]
    for a in sorted(angewandt, key=lambda x: (x.kennung, x.pfad)):
        zeilen.append(f"  UNTERDRUECKT  {a.kennung}  {a.pfad}"
                      f"   ({a.angewandt} Fund(e), {a.herkunft})")
        zeilen.extend(_umbruch(a.begruendung, "      Begruendung: "))
    return zeilen


def zeilen_veraltet(e: Ergebnis) -> list[str]:
    """Je Ausnahme, die nichts mehr unterdrueckt, eine Zeile - rot oder als laute Warnung."""
    if not e.veraltet:
        return []
    rot = e.veraltet_rot
    zeilen = [
        f"BEFEHLSWAECHTER: {len(e.veraltet)} Ausnahme(n) haben in diesem Lauf NICHTS"
        f" unterdrueckt - davon {len(rot)} nachweislich veraltet.",
    ]
    for a, art in sorted(e.veraltet, key=lambda x: (x[1], x[0].kennung, x[0].pfad)):
        marke = "VERALTET  " if art in VERALTET_ROT else "UNBELEGT  "
        zeilen.append(f"  {marke}{art}  {a.kennung}  {a.pfad}   ({a.herkunft})")
        zeilen.extend(_umbruch(VERALTET_SATZ[art], "      "))
    if rot:
        zeilen.append("  ⚠️ Loeschen ist hier die richtige Handlung, nicht das Umgehen: der"
                      " Waechter hat die Stelle gesucht bzw. gelesen und den Fund NICHT mehr"
                      " bekommen.")
    return zeilen


def zeilen_beanstandungen(e: Ergebnis) -> list[str]:
    if not e.beanstandungen:
        return []
    zeilen = [f"BEFEHLSWAECHTER: {len(e.beanstandungen)} Zeile(n) in {AUSNAHMEDATEI} gelten"
              f" NICHT:"]
    for b in e.beanstandungen:
        zeilen.append(f"  UNGUELTIG  {b}")
    return zeilen


# ─────────────────────────────────────────────────────────────────────────────
# Selbsttest - jede Probe einzeln, plus die Gegenrichtung
# ─────────────────────────────────────────────────────────────────────────────

PAPER_SAUBER = """name: Probe
version: '1.0'
main: net.probe.Probe
api-version: '1.21'

permissions:
  probe.admin:
    default: op
"""

BUKKIT_MIT_BEFEHL = """name: Probe
version: '1.0'
main: net.probe.Probe
api-version: '1.21'

commands:
  ping:
    description: Probe
    aliases: [p]
"""

HAUPT_SAUBER = """package net.probe;

import org.bukkit.plugin.java.JavaPlugin;

public final class Probe extends JavaPlugin {
    @Override
    public void onEnable() {
        registerCommand("ping", "Probe", new Pingbefehl());
    }
}
"""

BEFEHL_SAUBER = """package net.probe;

import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;

public final class Pingbefehl implements BasicCommand {
    @Override
    public void execute(CommandSourceStack quelle, String[] argumente) { }
}
"""


def _schreibe(pfad: str, inhalt: str):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with io.open(pfad, "wb") as f:
        f.write(inhalt.encode("utf-8"))


def _baum(basis: str, deskriptorname: str, deskriptor: str, dateien: dict[str, str]) -> str:
    wurzel = os.path.join(basis, "probe")
    _schreibe(os.path.join(wurzel, "src", "main", "resources", deskriptorname), deskriptor)
    for name, inhalt in dateien.items():
        _schreibe(os.path.join(wurzel, "src", "main", "java", "net", "probe", name), inhalt)
    return wurzel


# ⚠️ Der Ausnahmeteil baut MEHRMODULIG (plugin/ + core/), nicht wie die Faelle oben einmodulig.
# Das ist Absicht und der einzige Weg zu Fall 5: ``Modul.wurzel`` ist das Verzeichnis mit dem
# Deskriptor, hier ``plugin/``. Alles unter ``core/`` liegt AUSSERHALB der Quellenmenge und ist
# damit die Blindstelle, die VERALTET_UNGEPRUEFT beschreibt. In einem einmoduligen Baum liegt
# jeder Unterordner INNERHALB von Modul.wurzel - dort laesst sich der Fall nicht herstellen.
E_MODUL = "plugin"
E_PFAD = f"{E_MODUL}/src/main/java/net/probe/Pingbefehl.java"
E_BLINDPFAD = "core/src/main/java/net/probe/Fremdbefehl.java"

FREMDER_BEFEHL = """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;
public final class Fremdbefehl implements BasicCommand {
    @Override public void execute(CommandSourceStack q, String[] a) { }
}
"""

E_BAUM = {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts angemeldet"); }
}
""", "Pingbefehl.java": BEFEHL_SAUBER}


def selbsttest_ausnahmen() -> tuple[int, int]:
    """Positivkontrolle fuer die Ausnahmen. Gibt (bestanden, gefallen) zurueck.

    ⚠️ Jeder Fall prueft den AUSGEDRUCKTEN TEXT, nicht ein internes Feld. Der reparierte Fehler
    war nicht, dass die Ausnahme falsch gegriffen haette - sie griff richtig und SCHWIEG. Eine
    Zusicherung auf ``a.angewandt == 1`` haette den Fehler nicht gefangen.
    """
    faelle: list[tuple[str, dict, str | None, object]] = []

    BEGR = "Altlast vom 2026-08-21, Corwis entscheidet ueber Loeschen oder Anmelden."
    ZEILE = f"E_BEFEHL_NIE_ERZEUGT:{E_PFAD}:{BEGR}"

    def hat_zeile(e: Ergebnis, text: str) -> bool:
        return "UNTERDRUECKT" in text and E_PFAD in text and BEGR.split(",")[0] in text

    # 1  MIT Ausnahme: kein offener Fund, aber die Zeile MUSS erscheinen.
    faelle.append((
        "MIT Ausnahme: Fund unterdrueckt UND namentlich in der Ausgabe", E_BAUM, ZEILE,
        lambda e, t: not e.funde and e.unterdrueckt == 1 and hat_zeile(e, t) and not e.veraltet))

    # 2  Gegenrichtung - ohne Ausnahmedatei darf die Zeile NICHT erscheinen. Ohne diesen Fall
    #    koennte die Zeile immer stehen und Fall 1 waere trotzdem "bestanden".
    faelle.append((
        "OHNE Ausnahme: Fund ist rot und KEINE UNTERDRUECKT-Zeile", E_BAUM, None,
        lambda e, t: len(e.funde) == 1 and e.unterdrueckt == 0 and "UNTERDRUECKT" not in t))

    # 3  VERALTET WEG - der Pfad existiert nicht mehr.
    faelle.append((
        "VERALTET WEG: Ausnahme zeigt auf eine geloeschte Datei", E_BAUM,
        f"E_BEFEHL_NIE_ERZEUGT:{E_MODUL}/src/main/java/net/probe/Weg.java:{BEGR}",
        lambda e, t: [art for _, art in e.veraltet] == [VERALTET_WEG]
        and e.veraltet_rot and "VERALTET" in t))

    # 4  VERALTET GEGENSTANDSLOS - die Datei wurde gelesen, der Fund kam nicht.
    faelle.append((
        "VERALTET GEGENSTANDSLOS: Datei gelesen, Fund weg",
        {"Probe.java": HAUPT_SAUBER, "Pingbefehl.java": BEFEHL_SAUBER}, ZEILE,
        lambda e, t: [art for _, art in e.veraltet] == [VERALTET_GEGENSTANDSLOS]
        and e.veraltet_rot and "VERALTET" in t))

    # 5  UNGEPRUEFT - der Pfad existiert, lag aber ausserhalb der Quellenmenge. Nur Warnung.
    #    ⚠️ Das ist die Abwaegung als Maschine: hier war der Waechter blind, also kein rotes
    #    Urteil. Faellt dieser Fall, macht der Waechter jemanden zum Blindloescher.
    faelle.append((
        "UNGEPRUEFT: Pfad ausserhalb der Quellenmenge - warnt, faellt aber nicht", E_BAUM,
        f"E_BEFEHL_NIE_ERZEUGT:{E_BLINDPFAD}:{BEGR}",
        lambda e, t: [art for _, art in e.veraltet] == [VERALTET_UNGEPRUEFT]
        and not e.veraltet_rot and "UNBELEGT" in t and VERALTET_UNGEPRUEFT in t))

    # 6  Zeile ohne Begruendung: gilt nicht - der Fund bleibt rot UND die Zeile wird genannt.
    faelle.append((
        "OHNE BEGRUENDUNG: gilt nicht, Fund bleibt rot, Zeile wird genannt", E_BAUM,
        f"E_BEFEHL_NIE_ERZEUGT:{E_PFAD}:",
        lambda e, t: len(e.funde) == 1 and e.unterdrueckt == 0
        and len(e.beanstandungen) == 1 and "UNGUELTIG" in t))

    bestanden = 0
    gefallen = 0
    with tempfile.TemporaryDirectory() as tmp:
        for nr, (bezeichnung, dateien, ausnahmezeile, pruefung) in enumerate(faelle, 1):
            wurzel = os.path.join(tmp, f"ausnahme{nr}")
            _schreibe(os.path.join(wurzel, E_MODUL, "src", "main", "resources",
                                   "paper-plugin.yml"), PAPER_SAUBER)
            for name, inhalt in dateien.items():
                _schreibe(os.path.join(wurzel, E_MODUL, "src", "main", "java", "net", "probe",
                                       name), inhalt)
            # Ein Nachbarmodul OHNE Deskriptor - Fall 5 braucht einen Pfad, den es GIBT und
            # den der Waechter trotzdem nicht liest.
            _schreibe(os.path.join(wurzel, *E_BLINDPFAD.split("/")), FREMDER_BEFEHL)
            if ausnahmezeile is not None:
                _schreibe(os.path.join(wurzel, AUSNAHMEDATEI),
                          "# Kopf\n" + ausnahmezeile + "\n")
            e = pruefe([wurzel])
            text = "\n".join(zeilen_ausnahmen(e) + zeilen_veraltet(e) + zeilen_beanstandungen(e))
            ok = bool(pruefung(e, text))
            if e.deskriptoren == 0:
                ok = False
                bezeichnung += "  [KEIN DESKRIPTOR GEFUNDEN]"
            print(f"  {'OK  ' if ok else 'FEHL'} {bezeichnung}")
            if not ok:
                gefallen += 1
                print(f"         Funde {len(e.funde)}, unterdrueckt {e.unterdrueckt},"
                      f" veraltet {[art for _, art in e.veraltet]},"
                      f" Beanstandungen {len(e.beanstandungen)}")
                for z in text.splitlines():
                    print(f"         | {z}")
            else:
                bestanden += 1
    return bestanden, gefallen


def selbsttest_stille() -> tuple[int, int]:
    """Positivkontrolle fuer die Stillegarantie. Gibt (bestanden, gefallen) zurueck.

    ⚠️ Diese Faelle rufen ``main()`` und pruefen SEINEN Rueckgabewert, nicht ``blindstellen()``.
    Das ist der Unterschied, der zaehlt: die Mutation, gegen die dieser Abschnitt steht, aendert
    nicht die Erkennung, sondern das Urteil - ``return 2`` zu ``return 0``. Eine Zusicherung auf
    ``blindstellen(e) != []`` waere davon voellig unberuehrt geblieben und haette gruen
    gemeldet, waehrend acht Repos einen bestandenen Lauf ueber null Deskriptoren drucken.
    """
    import contextlib

    def fahre(wurzeln: list[str]) -> tuple[int, str]:
        aus, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(aus), contextlib.redirect_stderr(err):
            rc = main(list(wurzeln))
        return rc, aus.getvalue() + err.getvalue()

    faelle: list[tuple[str, object, object]] = []

    # 1  Gar kein Deskriptor.
    def bau_leer(w):
        _schreibe(os.path.join(w, "liesmich.txt"), "hier ist kein Plugin\n")
        return [w]

    faelle.append(("KEIN DESKRIPTOR: leerer Baum -> Rueckgabe 2", bau_leer,
                   lambda rc, t: rc == 2 and BLIND_KEIN_DESKRIPTOR in t))

    # 2  Deskriptor da, aber keine einzige Java-Datei. Die Proben B-E sind nicht gelaufen.
    def bau_ohne_java(w):
        _schreibe(os.path.join(w, "src", "main", "resources", "paper-plugin.yml"), PAPER_SAUBER)
        return [w]

    faelle.append(("KEINE JAVA-DATEI: Deskriptor ohne Quellen -> Rueckgabe 2", bau_ohne_java,
                   lambda rc, t: rc == 2 and BLIND_KEINE_QUELLE in t))

    # 3  Zwei Module, eines ohne Quellen. ⚠️ Der gefaehrlichste Fall: das andere Modul laesst
    #    den Lauf gruen aussehen.
    def bau_modul_ohne_quellen(w):
        _schreibe(os.path.join(w, "plugin", "src", "main", "resources", "paper-plugin.yml"),
                  PAPER_SAUBER)
        _schreibe(os.path.join(w, "plugin", "src", "main", "java", "net", "probe", "Probe.java"),
                  HAUPT_SAUBER)
        _schreibe(os.path.join(w, "plugin", "src", "main", "java", "net", "probe",
                               "Pingbefehl.java"), BEFEHL_SAUBER)
        _schreibe(os.path.join(w, "zweit", "src", "main", "resources", "paper-plugin.yml"),
                  PAPER_SAUBER)
        return [w]

    faelle.append(("MODUL OHNE QUELLEN: zweites Modul liefert nichts -> Rueckgabe 2",
                   bau_modul_ohne_quellen,
                   lambda rc, t: rc == 2 and BLIND_MODUL_OHNE_QUELLEN in t))

    # 4  Zwei Wurzeln, eine traegt nichts bei.
    def bau_zwei_wurzeln(w):
        eins = os.path.join(w, "eins")
        zwei = os.path.join(w, "zwei")
        _schreibe(os.path.join(eins, "src", "main", "resources", "paper-plugin.yml"),
                  PAPER_SAUBER)
        _schreibe(os.path.join(eins, "src", "main", "java", "net", "probe", "Probe.java"),
                  HAUPT_SAUBER)
        _schreibe(os.path.join(eins, "src", "main", "java", "net", "probe", "Pingbefehl.java"),
                  BEFEHL_SAUBER)
        _schreibe(os.path.join(zwei, "liesmich.txt"), "diese Wurzel traegt nichts bei\n")
        return [eins, zwei]

    faelle.append(("WURZEL OHNE DESKRIPTOR: zweite Wurzel zeigt ins Leere -> Rueckgabe 2",
                   bau_zwei_wurzeln,
                   lambda rc, t: rc == 2 and BLIND_WURZEL_LEER in t))

    # 5  ⚠️ Die Gegenrichtung, und sie ist nicht optional. Ohne sie duerfte blindstellen()
    #    einfach IMMER etwas zurueckgeben - alle vier Faelle oben blieben "bestanden", und der
    #    Waechter waere in allen acht Repos dauerhaft rot, ohne dass irgendetwas fehlt.
    def bau_gesund(w):
        _schreibe(os.path.join(w, "src", "main", "resources", "paper-plugin.yml"), PAPER_SAUBER)
        _schreibe(os.path.join(w, "src", "main", "java", "net", "probe", "Probe.java"),
                  HAUPT_SAUBER)
        _schreibe(os.path.join(w, "src", "main", "java", "net", "probe", "Pingbefehl.java"),
                  BEFEHL_SAUBER)
        return [w]

    faelle.append(("GRUEN gesunder Baum: keine Blindstelle, Rueckgabe 0", bau_gesund,
                   lambda rc, t: rc == 0 and "NICHTS GEPRUEFT" not in t))

    bestanden = 0
    gefallen = 0
    with tempfile.TemporaryDirectory() as tmp:
        for nr, (bezeichnung, bauen, pruefung) in enumerate(faelle, 1):
            w = os.path.join(tmp, f"stille{nr}")
            os.makedirs(w, exist_ok=True)
            wurzeln = bauen(w)
            rc, text = fahre(wurzeln)
            ok = bool(pruefung(rc, text))
            print(f"  {'OK  ' if ok else 'FEHL'} {bezeichnung}   (Rueckgabe {rc})")
            if not ok:
                gefallen += 1
                for z in text.splitlines():
                    print(f"         | {z}")
            else:
                bestanden += 1
    return bestanden, gefallen


def selbsttest() -> int:
    faelle = []

    # Gegenrichtung zuerst: ein sauberes Paper-Plugin MUSS gruen sein. Ohne diesen Fall koennte
    # der Waechter alles anschwaerzen und die anderen Faelle waeren trotzdem "bestanden".
    faelle.append(("GRUEN sauberes Paper-Plugin", "paper-plugin.yml", PAPER_SAUBER,
                   {"Probe.java": HAUPT_SAUBER, "Pingbefehl.java": BEFEHL_SAUBER}, None))

    faelle.append(("GRUEN sauberes Bukkit-Plugin", "plugin.yml", BUKKIT_MIT_BEFEHL,
                   {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("ping").setExecutor(new Pingbefehl()); }
}
""", "Pingbefehl.java": """package net.probe;
import org.bukkit.command.CommandExecutor; import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
public final class Pingbefehl implements CommandExecutor {
    @Override public boolean onCommand(CommandSender s, Command c, String l, String[] a) { return true; }
}
"""}, None))

    faelle.append(("A commands:-Block in paper-plugin.yml", "paper-plugin.yml",
                   PAPER_SAUBER + "\ncommands:\n  ping:\n    description: erfunden\n",
                   {"Probe.java": HAUPT_SAUBER, "Pingbefehl.java": BEFEHL_SAUBER},
                   "A_PAPER_COMMANDS_BLOCK"))

    faelle.append(("B getCommand in einem Paper-Plugin", "paper-plugin.yml", PAPER_SAUBER,
                   {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("ping").setExecutor(null); }
}
"""}, "B_PAPER_GETCOMMAND"))

    faelle.append(("C getCommand auf einen undeklarierten Namen", "plugin.yml", BUKKIT_MIT_BEFEHL,
                   {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("fly").setExecutor(null); }
}
"""}, "C_BUKKIT_GETCOMMAND_UNDEKLARIERT"))

    faelle.append(("D onCommand in einem Paper-Plugin", "paper-plugin.yml", PAPER_SAUBER,
                   {"Probe.java": """package net.probe;
import org.bukkit.command.Command; import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public boolean onCommand(CommandSender s, Command c, String l, String[] a) { return true; }
}
"""}, "D_PAPER_ONCOMMAND_TOT"))

    faelle.append(("E Befehlsklasse wird nie erzeugt", "paper-plugin.yml", PAPER_SAUBER,
                   {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts angemeldet"); }
}
""", "Pingbefehl.java": BEFEHL_SAUBER}, "E_BEFEHL_NIE_ERZEUGT"))

    # ⚠️ Der Kommentarfall. Ohne ihn ist der Waechter im Bestand unbrauchbar: ZanUI und
    # HeavyCrown fuehren 'getCommand' und 'commands:' in ihrem Javadoc, ausgerechnet in der
    # Erklaerung, warum sie es nicht tun.
    faelle.append(("GRUEN dieselben Woerter, aber nur im Kommentar", "paper-plugin.yml",
                   PAPER_SAUBER + "\n# commands:\n#   ping: nur ein Kommentar\n",
                   {"Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
/**
 * ⚠️ Hier steht KEIN commands:-Block und dieses Plugin ruft getCommand() nirgends.
 * Wer getCommand("ping") in einem Paper-Plugin ruft, bekommt eine Ausnahme.
 */
public final class Probe extends JavaPlugin {
    @Override
    public void onEnable() {
        // getCommand("ping").setExecutor(...) waere hier falsch
        String hinweis = "getCommand(\\"ping\\") gehoert nicht hierher";
        registerCommand("ping", hinweis, new Pingbefehl());
    }
}
""", "Pingbefehl.java": BEFEHL_SAUBER}, None))

    bestanden = 0
    gefallen = 0
    with tempfile.TemporaryDirectory() as tmp:
        for nr, (bezeichnung, dname, dinhalt, dateien, erwartet) in enumerate(faelle, 1):
            basis = os.path.join(tmp, f"fall{nr}")
            wurzel = _baum(basis, dname, dinhalt, dateien)
            e = pruefe([wurzel])
            funde, deskriptoren, javas = e.funde, e.deskriptoren, e.java_dateien
            kennungen = {f.split()[0] for f in funde}
            if erwartet is None:
                ok = len(funde) == 0
            else:
                ok = erwartet in kennungen
            # ⚠️ Auch der Selbsttest braucht seinen Erreichbarkeitsnachweis: ein Fall, in dem
            # kein Deskriptor gefunden wurde, ist nicht bestanden, sondern nicht gelaufen.
            if deskriptoren == 0:
                ok = False
                bezeichnung += "  [KEIN DESKRIPTOR GEFUNDEN]"
            print(f"  {'OK  ' if ok else 'FEHL'} {bezeichnung}"
                  f"   (Deskriptoren {deskriptoren}, Java {javas}, Funde {sorted(kennungen) or '-'})")
            if not ok:
                gefallen += 1
                for f in funde:
                    print(f"         {f.splitlines()[0]}")
            else:
                bestanden += 1

    print("")
    a_bestanden, a_gefallen = selbsttest_ausnahmen()
    bestanden += a_bestanden
    gefallen += a_gefallen

    print("")
    s_bestanden, s_gefallen = selbsttest_stille()
    bestanden += s_bestanden
    gefallen += s_gefallen

    print(f"\nSelbsttest: {bestanden} von {bestanden + gefallen} bestanden.")
    return 0 if gefallen == 0 else 1


# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    _stroeme_auf_utf8()
    p = argparse.ArgumentParser(
        description="Befehlswaechter - faengt deklarierte oder implementierte Befehle, die"
                    " niemand anmeldet.")
    p.add_argument("wurzel", nargs="*", default=["."],
                   help="Projektwurzeln (Vorgabe: aktuelles Verzeichnis)")
    p.add_argument("--selbsttest", action="store_true",
                   help="prueft den Waechter selbst gegen Wegwerfbaeume, beide Richtungen")
    a = p.parse_args(argv)

    if a.selbsttest:
        return selbsttest()

    wurzeln = [os.path.abspath(w) for w in a.wurzel]
    for w in wurzeln:
        if not os.path.isdir(w):
            print(f"BEFEHLSWAECHTER: '{w}' ist kein Verzeichnis.", file=sys.stderr)
            return 3

    e = pruefe(wurzeln)

    # ⚠️ Standing Rule 22/29: ein Werkzeug, das nichts findet, muss das von "nichts geprueft"
    # unterscheiden koennen. Die vollstaendige Liste dieser Wege steht in blindstellen().
    print(f"BEFEHLSWAECHTER: geprueft {e.deskriptoren} Plugin-Deskriptor(en),"
          f" {e.java_dateien} Java-Datei(en) in {', '.join(wurzeln)}")

    blind = blindstellen(e)
    if blind:
        for z in zeilen_blindstellen(blind):
            print(z, file=sys.stderr)
        return 2

    # ⚠️ Diese drei Bloecke stehen VOR dem Urteil und laufen bei JEDEM Ausgang - auch bei
    # Rueckgabe 0. Genau darin liegt die Reparatur: ein gruener Lauf mit unterdruecktem Fund
    # sah bis zum 2026-08-22 aus wie ein gruener Lauf ohne.
    for block in (zeilen_ausnahmen(e), zeilen_veraltet(e), zeilen_beanstandungen(e)):
        if block:
            print("")
            for z in block:
                print(z)

    # ⚠️ stdout ist gepuffert, stderr nicht. Ohne dieses flush() steht das Schlussurteil im
    # Gradle-Log VOR den Zeilen, die es begruendet - und wer nur die ersten Zeilen liest, sieht
    # ein Urteil ohne seinen Beleg.
    sys.stdout.flush()

    if e.funde:
        print(f"\nBEFEHLSWAECHTER: {len(e.funde)} Fund(e) - der Bau ist rot.\n", file=sys.stderr)
        for f in e.funde:
            print(f"  {f}\n", file=sys.stderr)
        print("Bekannte Altlast? Zeile in .befehlswaechter-ausnahmen aufnehmen, Form"
              " KENNUNG:pfad:Begruendung. Ohne Begruendung gilt sie nicht.", file=sys.stderr)
        # ⚠️ 1 schlaegt 4. Ein offener Fund ist der schwerere Befund; die veralteten Ausnahmen
        # stehen oben und gehen nicht verloren.
        return 1

    if e.veraltet_rot:
        print(f"\nBEFEHLSWAECHTER: keine offenen Funde, aber {len(e.veraltet_rot)} VERALTETE"
              f" Ausnahme(n) - der Bau ist rot. Die Ausnahmedatei nennt sich selbst eine 'Liste"
              f" offener Entscheidungen, kein Freibrief'; eine Zeile, die nichts mehr deckt,"
              f" behauptet eine offene Entscheidung, die keine ist. Zeile loeschen.",
              file=sys.stderr)
        return 4

    if e.unterdrueckt:
        print(f"\nBEFEHLSWAECHTER: keine OFFENEN Funde - aber {e.unterdrueckt} Fund(e) durch"
              f" {len(e.angewandt)} benannte Ausnahme(n) unterdrueckt (siehe oben).")
        return 0

    print("BEFEHLSWAECHTER: keine Funde, keine Ausnahme angewandt.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
