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
  * Findet er KEINEN Deskriptor, ist das NICHT gruen, sondern Rueckgabe 2 (NICHTS GEPRUEFT).
    Ein Werkzeug, das nichts findet, hat nicht bewiesen, dass nichts da ist.
  * Er entfernt Kommentare und Zeichenketten-Literale VOR jeder Suche. Ohne das schlaegt er auf
    genau den Kommentaren an, die den Fehler erklaeren - ZanUI und HeavyCrown fuehren beide das
    Wort ``getCommand`` in ihrem Javadoc, und HeavyCrowns Test-Javadoc nennt ``commands:``.
  * Er sucht mehrzeilig (Umbruch zwischen Name und Punkt ist in Java erlaubt).

RUECKGABEWERTE
==============
  0  nichts gefunden, und es wurde etwas geprueft
  1  Funde vorhanden (der Bau soll rot werden)
  2  nichts geprueft - Werkzeug oder Aufruf kaputt, NICHT gruen
  3  Aufruf falsch

AUSNAHMEN
=========
Bekannte Altlasten stehen in ``<repo>/.befehlswaechter-ausnahmen``, eine Zeile je Fund:
``KENNUNG:relativer/pfad:Begruendung``. Ohne Begruendung gilt die Zeile nicht. Neue Schuld wird
rot, bekannte Schuld steht benannt - das ist der Unterschied zu einem abgeschalteten Waechter.

SELBSTTEST
==========
``python3 befehlswaechter.py --selbsttest`` baut Wegwerfbaeume fuer jede der fuenf Proben und
fuer die Gegenrichtung (ein sauberes Plugin muss gruen sein) und meldet jede einzeln.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import tempfile

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

    def __init__(self, deskriptor: str, ist_paper: bool):
        self.deskriptor = deskriptor
        self.ist_paper = ist_paper
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
                module.append(Modul(pfad, True))
            elif name == "plugin.yml":
                # ⚠️ Nur echte Plugin-Deskriptoren. Eine plugin.yml irgendwo in einer Vorlage
                # oder in einem Serververzeichnis ist nicht unser Gegenstand.
                if f"{os.sep}resources{os.sep}" in pfad or pfad.endswith(f"resources{os.sep}plugin.yml"):
                    module.append(Modul(pfad, False))
    for m in module:
        if os.path.isdir(m.wurzel):
            for pfad in gehe(m.wurzel):
                if pfad.endswith(".java"):
                    m.quellen.append(pfad)
    return module


def ausnahmen_lesen(wurzeln: list[str]) -> set[tuple[str, str]]:
    """Liest ``.befehlswaechter-ausnahmen`` aus jeder Wurzel. Ohne Begruendung gilt die Zeile nicht."""
    raus = set()
    for w in wurzeln:
        p = os.path.join(w, AUSNAHMEDATEI)
        if not os.path.isfile(p):
            continue
        for zeile in lies(p).split("\n"):
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#"):
                continue
            teile = zeile.split(":", 2)
            if len(teile) < 3 or not teile[2].strip():
                # ⚠️ Absichtlich still uebergangen statt geduldet: eine Ausnahme ohne Begruendung
                # ist keine Ausnahme. Der Fund bleibt damit rot.
                continue
            raus.add((teile[0].strip(), teile[1].strip().replace("\\", "/")))
    return raus


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


def pruefe(wurzeln: list[str]) -> tuple[list[str], int, int]:
    """Gibt (Funde, Zahl der Deskriptoren, Zahl der Java-Dateien) zurueck."""
    module = module_finden(wurzeln)
    ausnahmen = ausnahmen_lesen(wurzeln)
    funde: list[str] = []
    java_gesehen = 0

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
        if (kennung, rel(pfad)) in ausnahmen:
            return
        funde.append(f"{kennung}  {rel(pfad)}\n      {satz}")

    for m in module:
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

    return funde, len(module), java_gesehen


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
            funde, deskriptoren, javas = pruefe([wurzel])
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
    print(f"\nSelbsttest: {bestanden} von {bestanden + gefallen} bestanden.")
    return 0 if gefallen == 0 else 1


# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
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

    funde, deskriptoren, javas = pruefe(wurzeln)

    # ⚠️ Standing Rule 22/29: ein Werkzeug, das nichts findet, muss das von "nichts geprueft"
    # unterscheiden koennen. Null Deskriptoren ist NICHT gruen.
    print(f"BEFEHLSWAECHTER: geprueft {deskriptoren} Plugin-Deskriptor(en),"
          f" {javas} Java-Datei(en) in {', '.join(wurzeln)}")
    if deskriptoren == 0:
        print("BEFEHLSWAECHTER: NICHTS GEPRUEFT - keine paper-plugin.yml und keine plugin.yml"
              " gefunden. Das ist kein bestandener Lauf. Falscher Pfad, oder der Deskriptor"
              " liegt nicht unter src/*/resources/.", file=sys.stderr)
        return 2

    if not funde:
        print("BEFEHLSWAECHTER: keine Funde.")
        return 0

    print(f"\nBEFEHLSWAECHTER: {len(funde)} Fund(e) - der Bau ist rot.\n", file=sys.stderr)
    for f in funde:
        print(f"  {f}\n", file=sys.stderr)
    print("Bekannte Altlast? Zeile in .befehlswaechter-ausnahmen aufnehmen, Form"
          " KENNUNG:pfad:Begruendung. Ohne Begruendung gilt sie nicht.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
