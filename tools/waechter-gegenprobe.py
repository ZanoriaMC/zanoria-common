#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gegenprobe zum Befehlswaechter - beide Richtungen, je Alternative einzeln.

WARUM DAS EIN EIGENES WERKZEUG IST
==================================
Standing Rule 13: eine Reparatur zaehlt erst mit bestandener Gegenprobe. Standing Rule 21: eine
Zusicherung ueber ein Nicht-Ereignis braucht einen Nachbarn, der belegt, dass ueberhaupt etwas
lief - und die Gegenprobe muss je Haelfte EINZELN laufen, weil eine gemeinsame genau den Fall
verdeckt, in dem nur eine der beiden Haelften traegt.

DREI ABSCHNITTE, ZWEI RICHTUNGEN
================================
  1  GIFTBAEUME (Unter-Meldung).  Je Baum drei Schritte:
       GIFT    ein Wegwerfbaum, der genau diese Alternative ausloesen MUSS  -> erwartete
               Rueckgabe, erwartete KENNUNGSMENGE, erwartete Fundzahl
       MUTANT  eine Kopie des Waechters, in der genau diese Alternative entfernt ist, gegen
               denselben Baum                                               -> Marke MUSS weg
       ZEUGE   das Original ist byteweise unveraendert (sha256 vorher/nachher)

  2  DER SAUBERE BAUM (Ueber-Meldung).  Ein einziger, vollstaendig korrekter Baum. Der Waechter
     MUSS darauf null Funde und Rueckgabe 0 melden. Jeder Fund darauf ist ein FALSCHFUND.

  3  ZU STRENGE MUTANTEN.  Dieselben Mutationen, aber gegen den SAUBEREN Baum: jede Verengung
     des Waechters MUSS ihn roeten. Ohne diesen Abschnitt ist Abschnitt 2 ein Baum, den nichts
     bedroht.

⚠️ Schritt 2 im Giftteil ist der eigentliche Punkt. Ein Waechter, dessen Mutation nichts bricht,
prueft nichts - dann kam der Fund von woanders her, und die Pruefung war Deko. Standing Rule 28:
ein Mutationslauf, bei dem KEINE einzige Mutation gefangen wird, meldet nicht "alles ueberlebt",
sondern "es lief nichts".

⚠️ Und die Mutation muss etwas entfernen, das der Lauf wirklich benutzt (Standing Rule 30). Ein
Kommentar taugt nicht. Entfernt wird deshalb der Rumpf der Pruefung selbst, und der Mutant wird
vor dem Lauf gegen das Original byteweise verglichen: sind sie gleich, wurde nicht mutiert, und
der Fall gilt als NICHT GELAUFEN statt als bestanden.

WAS AM 2026-08-22 DAZUKAM UND WARUM
===================================
Bis dahin hatte diese Gegenprobe fuenf Giftbaeume und KEINEN sauberen. Gemessen (22
Einzelmutationen, Katalog in ``mutationskatalog.py``): 11 rot, ELF still. Drei Bauarten Loch:

  * ⚠️ KEINE GEGENRICHTUNG. ``gift_ok`` verlangte nur ``rc==1`` und dass die Kennung irgendwo in
    der Ausgabe steht. Ein Waechter, der ZUSAETZLICH drei Falschfunde meldet, kam damit als
    "bestanden" durch. Ueber-Meldung war voellig unsichtbar: Erzeugungsregex zu streng,
    ``deklarierte_befehle`` leer, ``aliases`` nicht gezaehlt, YAML-Kommentare nicht abgetrennt -
    alles gruen. SCHADEN: ein zu strenger Waechter faerbt acht Repos rot ueber Code, der
    richtig ist; wer das ein paarmal erlebt, schaltet ihn ab oder deckt ihn mit Ausnahmen zu,
    und dann faengt er auch die echten Faelle nicht mehr.
    Deshalb jetzt: EIN sauberer Baum - und er ist ausdruecklich ANSPRUCHSVOLL. Ein Baum, der nur
    den einfachsten Fall zeigt, laesst genau die vier Mutationen oben weiter durch. Er fuehrt
    deshalb ``record``-Befehle, Aliase in Klammer- UND Listenform, einen Kommentar in Spalte 0
    MITTEN im ``commands:``-Block, vier verschiedene Befehlsschnittstellen, Erzeugung ueber eine
    Fabrik, ueber eine Variable, qualifiziert (``new net.probe.X()``) und mit Typargument
    (``new X<>()``), und einen ``getCommand``-Aufruf mit Umbruch vor der Klammer.
    ⚠️ Jede dieser Formen steht hier, weil eine benannte Mutation sie braucht - keine ist
    Zierde. Welche zu welcher, steht bei UEBERSTRENG.

  * ⚠️ NUR GANZE TOETUNGEN. Gepruefte Alternative war je Probe genau eine: D nur ueber
    ``onCommand`` (nicht ``onTabComplete``), E nur ueber ``BasicCommand`` (nicht
    ``CommandExecutor``/``TabExecutor``/``TabCompleter``), E nur ueber ``class`` (nicht
    ``record``), B/C nur ohne Leerraum vor der Klammer. Jetzt hat JEDE Alternative ihren
    eigenen Giftbaum und ihre eigene Mutation.

  * ⚠️ DIE MASCHINERIE UM DIE PROBEN war Prosa. "Ohne Begruendung gilt die Zeile nicht" und die
    Dublettenerkennung standen als Satz im Kopf des Waechters und wurden von nichts ausgefuehrt.
    Ebenso die Stillegarantie selbst - ``return 2`` zu ``return 0`` blieb still, und das ist der
    teuerste Fall ueberhaupt: acht Repos melden einen BESTANDENEN Lauf ueber NULL gesehene
    Deskriptoren.

WER RUFT DIESES SKRIPT
======================
``zanoria-common/gradle/waechter-gegenprobe.gradle`` haengt es an den ``check`` von
zanoria-common. Dort steht auch, warum ZENTRAL und nicht je Verbraucher.
⚠️ Bis zum 2026-08-22 rief es NICHTS. Ein Werkzeug, das niemand ruft, belegt nichts, egal was es
koennte.

⚠️ WAS SIE WEITERHIN NICHT DECKT
Die Lage ``UNGEPRUEFT`` einer veralteten Ausnahme (Pfad existiert, lag aber ausserhalb der
gelesenen Quellenmenge -> nur Warnung, kein rotes Urteil) braucht einen mehrmoduligen Baum mit
einem Modul OHNE Deskriptor; sie ist von ``befehlswaechter.py --selbsttest`` gedeckt, nicht von
hier. Und diese Gegenprobe misst den Waechter gegen WEGWERFBAEUME, nicht gegen den Bestand -
dass er in Nexus 571 und in ZanUI nur 9 Java-Dateien sieht, sagt sie nicht.

Rueckgabe: 0 alle Faelle bestanden · 1 mindestens einer gefallen · 2 es lief nichts
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
WAECHTER = os.path.join(HIER, "befehlswaechter.py")

# ⚠️ Die Kennungen, nach denen die Ausgabe abgesucht wird. Steht eine davon am Anfang einer
# Fundzeile, gilt sie als gemeldet. Nur mit dieser Menge laesst sich "genau diese Funde und
# keine weiteren" pruefen - die alte Fassung fragte "kommt die Kennung irgendwo vor" und war
# gegen Falschfunde blind.
ALLE_KENNUNGEN = (
    "A_PAPER_COMMANDS_BLOCK",
    "B_PAPER_GETCOMMAND",
    "C_BUKKIT_GETCOMMAND_UNDEKLARIERT",
    "D_PAPER_ONCOMMAND_TOT",
    "E_BEFEHL_NIE_ERZEUGT",
)

RE_FUNDZAHL = re.compile(r"BEFEHLSWAECHTER: (\d+) Fund\(e\) - der Bau ist rot")


# ═════════════════════════════════════════════════════════════════════════════
#  Bausteine
# ═════════════════════════════════════════════════════════════════════════════

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

# Ein Paper-Hauptklasse, die nichts Verbotenes tut und Pingbefehl anmeldet.
PAPER_HAUPT_ANGEMELDET = """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { registerCommand("ping", "x", new Pingbefehl()); }
}
"""

# Eine Paper-Hauptklasse, die gar nichts anmeldet.
PAPER_HAUPT_STUMM = """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts"); }
}
"""

AUSNAHME_PFAD = "src/main/java/net/probe/Pingbefehl.java"
AUSNAHME_BEGRUENDUNG = "Altlast vom 2026-08-21, Corwis entscheidet."


def _befehlsklasse(name: str, schnittstelle: str, importzeile: str, rumpf: str) -> str:
    return (f"package net.probe;\n{importzeile}\n"
            f"public final class {name} implements {schnittstelle} {{\n{rumpf}}}\n")


IMPORT_EXECUTOR = ("import org.bukkit.command.Command;\n"
                   "import org.bukkit.command.CommandExecutor;\n"
                   "import org.bukkit.command.CommandSender;")
IMPORT_TABEXECUTOR = ("import java.util.List;\n"
                      "import org.bukkit.command.Command;\n"
                      "import org.bukkit.command.CommandSender;\n"
                      "import org.bukkit.command.TabExecutor;")
IMPORT_TABCOMPLETER = ("import java.util.List;\n"
                       "import org.bukkit.command.Command;\n"
                       "import org.bukkit.command.CommandSender;\n"
                       "import org.bukkit.command.TabCompleter;")

RUMPF_EXECUTOR = ("    @Override public boolean onCommand(CommandSender s, Command c,"
                  " String l, String[] a) { return true; }\n")
RUMPF_TABEXECUTOR = (
    "    @Override public boolean onCommand(CommandSender s, Command c, String l,"
    " String[] a) { return true; }\n"
    "    @Override public List<String> onTabComplete(CommandSender s, Command c, String l,"
    " String[] a) { return List.of(); }\n")
RUMPF_TABCOMPLETER = (
    "    @Override public List<String> onTabComplete(CommandSender s, Command c, String l,"
    " String[] a) { return List.of(); }\n")


# ═════════════════════════════════════════════════════════════════════════════
#  ABSCHNITT 1 - DIE GIFTBAEUME
#
#  Je Fall ein dict. Pflicht:
#    name        Anzeigename (⚠️ NIE eine Kennung: der Waechter druckt seinen Pfad, und ein
#                Ordner- oder Fallname mit Kennung stuende dann in JEDER Ausgabe, auch in der
#                des Mutanten. Beim ersten Anlauf 2026-08-21 genau so passiert.)
#    dateien     {relativer Pfad im Baum: Inhalt}
#    rc          erwarteter Rueckgabewert des Waechters
#    kennungen   die GENAUE Menge gemeldeter Kennungen - nicht "mindestens"
#    funde       die GENAUE Zahl offener Funde
#    weg         die Marke, die im Mutanten VERSCHWINDEN muss
#    mutation    (suchen, ersetzen) auf dem Quelltext des Waechters
#  Freiwillig:
#    text        weitere Zeichenketten, die in der Gift-Ausgabe stehen muessen
#    ausnahmen   Inhalt einer .befehlswaechter-ausnahmen im Baum
#    wurzeln     Unterpfade, die als Wurzeln uebergeben werden (Vorgabe: der Baum selbst)
# ═════════════════════════════════════════════════════════════════════════════

GIFTBAEUME: list[dict] = [

    # ── Probe A ──────────────────────────────────────────────────────────────
    {
        "name": "A ueber einen commands:-Block in der paper-plugin.yml",
        "dateien": {
            "src/main/resources/paper-plugin.yml":
                PAPER_KOPF + "\ncommands:\n  ping:\n    description: erfunden\n",
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_ANGEMELDET,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "rc": 1, "kennungen": {"A_PAPER_COMMANDS_BLOCK"}, "funde": 1,
        "weg": "A_PAPER_COMMANDS_BLOCK",
        "mutation": ('    for nr, zeile in enumerate(zeilen, 1):\n'
                     '        if zeile.startswith("commands:"):\n'
                     '            return nr\n    return None',
                     '    return None'),
    },

    # ── Probe B ──────────────────────────────────────────────────────────────
    {
        "name": "B ueber getCommand in einem Paper-Plugin",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("ping").setExecutor(null); }
}
""",
        },
        "rc": 1, "kennungen": {"B_PAPER_GETCOMMAND"}, "funde": 1,
        "weg": "B_PAPER_GETCOMMAND",
        "mutation": ('            if m.ist_paper and RE_GETCOMMAND_BLIND.search(nackt):',
                     '            if False:'),
    },

    # ── Probe C ──────────────────────────────────────────────────────────────
    {
        "name": "C ueber einen undeklarierten Namen",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getCommand("fly").setExecutor(null); }
}
""",
        },
        "rc": 1, "kennungen": {"C_BUKKIT_GETCOMMAND_UNDEKLARIERT"}, "funde": 1,
        "weg": "C_BUKKIT_GETCOMMAND_UNDEKLARIERT",
        "mutation": ('            if (not m.ist_paper) and RE_GETCOMMAND_BLIND.search(nackt):',
                     '            if False:'),
    },
    # ⚠️ Zwei Baeume fuer denselben Fund, und das ist kein Zufall: der Aufruf steht mit UMBRUCH
    # vor der Klammer. Java erlaubt das, und zwei getrennte Regexe muessen es beide sehen -
    # RE_GETCOMMAND_BLIND oeffnet die Probe, RE_GETCOMMAND holt den Namen. Faellt der Leerraum
    # aus EINER von beiden, meldet der Waechter still nichts mehr.
    {
        "name": "C ueber einen Aufruf mit Umbruch vor der Klammer (Tuersteher-Regex)",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() {
        getCommand
                ("fly").setExecutor(null);
    }
}
""",
        },
        "rc": 1, "kennungen": {"C_BUKKIT_GETCOMMAND_UNDEKLARIERT"}, "funde": 1,
        "weg": "C_BUKKIT_GETCOMMAND_UNDEKLARIERT",
        "mutation": ("RE_GETCOMMAND_BLIND = re.compile(r'\\bgetCommand\\s*\\(', re.S)",
                     "RE_GETCOMMAND_BLIND = re.compile(r'\\bgetCommand\\(', re.S)"),
    },
    {
        "name": "C ueber einen Aufruf mit Umbruch vor der Klammer (Namens-Regex)",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() {
        getCommand
                ("fly").setExecutor(null);
    }
}
""",
        },
        "rc": 1, "kennungen": {"C_BUKKIT_GETCOMMAND_UNDEKLARIERT"}, "funde": 1,
        "weg": "C_BUKKIT_GETCOMMAND_UNDEKLARIERT",
        "mutation": ("RE_GETCOMMAND = re.compile(r'\\bgetCommand\\s*\\(\\s*\"([^\"]*)\"\\s*\\)',"
                     " re.S)",
                     "RE_GETCOMMAND = re.compile(r'\\bgetCommand\\(\"([^\"]*)\"\\)', re.S)"),
    },

    # ── Probe D: BEIDE Haelften ──────────────────────────────────────────────
    {
        "name": "D ueber die onCommand-Haelfte",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.command.Command; import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public boolean onCommand(CommandSender s, Command c, String l, String[] a) { return true; }
}
""",
        },
        "rc": 1, "kennungen": {"D_PAPER_ONCOMMAND_TOT"}, "funde": 1,
        "weg": "D_PAPER_ONCOMMAND_TOT",
        # ⚠️ Nur die onCommand-Haelfte faellt weg. Die andere bleibt stehen - genau deshalb
        # faengt der ANDERE Baum sie nicht, und genau deshalb braucht es zwei.
        "mutation": ('RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt)',
                     'RE_ONTABCOMPLETE.search(nackt)'),
    },
    {
        "name": "D ueber die onTabComplete-Haelfte",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import java.util.List;
import org.bukkit.command.Command; import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public List<String> onTabComplete(CommandSender s, Command c, String l, String[] a) {
        return List.of();
    }
}
""",
        },
        "rc": 1, "kennungen": {"D_PAPER_ONCOMMAND_TOT"}, "funde": 1,
        "weg": "D_PAPER_ONCOMMAND_TOT",
        "mutation": ('RE_ONCOMMAND.search(nackt) or RE_ONTABCOMPLETE.search(nackt)',
                     'RE_ONCOMMAND.search(nackt)'),
    },

    # ── Probe E: ALLE VIER Schnittstellen und BEIDE Typarten ─────────────────
    {
        "name": "E ueber BasicCommand",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_STUMM,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "weg": "E_BEFEHL_NIE_ERZEUGT",
        "mutation": ('BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabExecutor", "TabCompleter")',
                     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "TabExecutor",'
                     ' "TabCompleter")'),
    },
    {
        "name": "E ueber CommandExecutor",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts"); }
}
""",
            "src/main/java/net/probe/Pingbefehl.java":
                _befehlsklasse("Pingbefehl", "CommandExecutor", IMPORT_EXECUTOR, RUMPF_EXECUTOR),
        },
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "weg": "E_BEFEHL_NIE_ERZEUGT",
        "mutation": ('BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabExecutor", "TabCompleter")',
                     'BEFEHLSSCHNITTSTELLEN = ("BasicCommand", "TabExecutor", "TabCompleter")'),
    },
    {
        "name": "E ueber TabExecutor",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts"); }
}
""",
            "src/main/java/net/probe/Flugbefehl.java":
                _befehlsklasse("Flugbefehl", "TabExecutor", IMPORT_TABEXECUTOR,
                               RUMPF_TABEXECUTOR),
        },
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "weg": "E_BEFEHL_NIE_ERZEUGT",
        "mutation": ('BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabExecutor", "TabCompleter")',
                     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabCompleter")'),
    },
    {
        "name": "E ueber TabCompleter",
        "dateien": {
            "src/main/resources/plugin.yml": BUKKIT_KOPF,
            "src/main/java/net/probe/Probe.java": """package net.probe;
import org.bukkit.plugin.java.JavaPlugin;
public final class Probe extends JavaPlugin {
    @Override public void onEnable() { getLogger().info("nichts"); }
}
""",
            "src/main/java/net/probe/Tippbefehl.java":
                _befehlsklasse("Tippbefehl", "TabCompleter", IMPORT_TABCOMPLETER,
                               RUMPF_TABCOMPLETER),
        },
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "weg": "E_BEFEHL_NIE_ERZEUGT",
        "mutation": ('BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabExecutor", "TabCompleter")',
                     'BEFEHLSSCHNITTSTELLEN = ("CommandExecutor", "BasicCommand",'
                     ' "TabExecutor")'),
    },
    {
        # ⚠️ Ein record traegt Befehlsschnittstellen genauso wie eine class. Sah die
        # Klassenregex nur ``class``, war jeder record-Befehl unsichtbar - kein Fund, keine
        # Meldung, und die Probe E hatte im ganzen Repo ein Loch nach Sprachmittel.
        "name": "E ueber einen record statt einer class",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_STUMM,
            "src/main/java/net/probe/Pongbefehl.java": """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;
public record Pongbefehl(String antwort) implements BasicCommand {
    @Override public void execute(CommandSourceStack q, String[] a) { }
}
""",
        },
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "weg": "E_BEFEHL_NIE_ERZEUGT",
        "mutation": (r"(?:class|record)\s+(\w+)'", r"(?:class)\s+(\w+)'"),
    },

    # ── Die Maschinerie: Ausnahmen ───────────────────────────────────────────
    # ⚠️ Diese Faelle decken die Reparatur vom 2026-08-22 ab. Vorher verwarf ``melde()``
    # einen ausgenommenen Fund lautlos, und der Lauf druckte danach "keine Funde" - ein gruener
    # Lauf und einer mit unterdruecktem Fund waren ununterscheidbar.
    {
        "name": "eine angewandte Ausnahme steht namentlich in der Ausgabe",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_STUMM,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "ausnahmen": f"E_BEFEHL_NIE_ERZEUGT:{AUSNAHME_PFAD}:{AUSNAHME_BEGRUENDUNG}\n",
        "rc": 0, "kennungen": set(), "funde": 0,
        "text": ["UNTERDRUECKT"], "weg": "UNTERDRUECKT",
        # ⚠️ Die Mutation nimmt die MELDUNG weg, nicht die Unterdrueckung. Genau darum geht es:
        # unterdrueckt wurde vorher auch schon richtig - es sagte nur niemand.
        "mutation": ('    angewandt = e.angewandt\n    if not angewandt:\n        return []',
                     '    angewandt = []\n    if not angewandt:\n        return []'),
    },
    {
        "name": "eine Ausnahme, die nichts mehr unterdrueckt, faellt auf",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_ANGEMELDET,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "ausnahmen": f"E_BEFEHL_NIE_ERZEUGT:{AUSNAHME_PFAD}:{AUSNAHME_BEGRUENDUNG}\n",
        "rc": 4, "kennungen": set(), "funde": 0,
        "text": ["VERALTET"], "weg": "VERALTET",
        "mutation": ('    for a in ausnahmen:\n        if a.angewandt:\n            continue',
                     '    for a in []:\n        if a.angewandt:\n            continue'),
    },
    {
        # ⚠️ "Ohne Begruendung gilt die Zeile nicht" stand bis zum 2026-08-22 als Satz im Kopf
        # des Waechters und wurde von KEINER Maschine gehalten. SCHADEN: wer eine Ausnahme ohne
        # Begruendung schreibt, deckt damit echte Schuld zu und niemand merkt es.
        "name": "eine Ausnahme OHNE Begruendung gilt nicht - der Fund bleibt rot",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_STUMM,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "ausnahmen": f"E_BEFEHL_NIE_ERZEUGT:{AUSNAHME_PFAD}:\n",
        "rc": 1, "kennungen": {"E_BEFEHL_NIE_ERZEUGT"}, "funde": 1,
        "text": ["UNGUELTIG"], "weg": "UNGUELTIG",
        "mutation": ('            if len(teile) < 3 or not teile[2].strip():',
                     '            if len(teile) < 3:'),
    },
    {
        # ⚠️ Eine Dublette sieht im Repo aus wie eine wirksame Ausnahme. Ohne Beanstandung
        # wuerde die zweite Zeile die erste verdraengen und die erste danach als VERALTET
        # gemeldet - eine Zeile, die gerade greift, waere als erledigt ausgewiesen.
        "name": "eine doppelte Ausnahmezeile wird beanstandet",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "src/main/java/net/probe/Probe.java": PAPER_HAUPT_STUMM,
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
        },
        "ausnahmen": (f"E_BEFEHL_NIE_ERZEUGT:{AUSNAHME_PFAD}:{AUSNAHME_BEGRUENDUNG}\n"
                      f"E_BEFEHL_NIE_ERZEUGT:{AUSNAHME_PFAD}:noch einmal dasselbe, aus Versehen\n"),
        "rc": 0, "kennungen": set(), "funde": 0,
        "text": ["DUBLETTE"], "weg": "DUBLETTE",
        "mutation": ('            if vorher is not None:', '            if False:'),
    },

    # ── Die Stillegarantie ───────────────────────────────────────────────────
    # ⚠️ DER TEUERSTE FALL. Meldet der Waechter hier gruen, melden acht Repos einen bestandenen
    # Lauf ueber NULL gesehene Deskriptoren - und niemand erfaehrt es, weil nichts rot wird.
    {
        "name": "ein Baum ganz ohne Deskriptor ist NICHT bestanden",
        "dateien": {
            "src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
            "liesmich.txt": "hier liegt kein Plugin-Deskriptor\n",
        },
        "rc": 2, "kennungen": set(), "funde": 0,
        "text": ["NICHTS GEPRUEFT", "KEIN DESKRIPTOR"], "weg": "NICHTS GEPRUEFT",
        "mutant_rc": 0,
        "mutation": ('            print(z, file=sys.stderr)\n        return 2',
                     '            print(z, file=sys.stderr)\n        return 0'),
    },
    {
        "name": "ein Deskriptor ohne eine einzige Java-Datei ist NICHT bestanden",
        "dateien": {
            "src/main/resources/paper-plugin.yml": PAPER_KOPF,
        },
        "rc": 2, "kennungen": set(), "funde": 0,
        "text": ["KEINE JAVA-DATEI"], "weg": "KEINE JAVA-DATEI",
        "mutation": ('    if e.deskriptoren > 0 and e.java_dateien == 0:',
                     '    if False:'),
    },
    {
        # ⚠️ Die gefaehrlichste Mischung: EIN Modul liefert Quellen und laesst den Lauf gruen
        # aussehen, das zweite liefert keine einzige und wird trotzdem als geprueft gezaehlt.
        "name": "ein zweites Modul ohne Quellen ist NICHT bestanden",
        "dateien": {
            "plugin/src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "plugin/src/main/java/net/probe/Probe.java": PAPER_HAUPT_ANGEMELDET,
            "plugin/src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
            "zweit/src/main/resources/paper-plugin.yml": PAPER_KOPF,
        },
        "rc": 2, "kennungen": set(), "funde": 0,
        "text": ["MODUL OHNE QUELLEN"], "weg": "MODUL OHNE QUELLEN",
        "mutation": ('    for m in e.module:\n        if not m.quellen:',
                     '    for m in []:\n        if not m.quellen:'),
    },
    {
        "name": "eine zweite Wurzel, die nichts beitraegt, ist NICHT bestanden",
        "dateien": {
            "eins/src/main/resources/paper-plugin.yml": PAPER_KOPF,
            "eins/src/main/java/net/probe/Probe.java": PAPER_HAUPT_ANGEMELDET,
            "eins/src/main/java/net/probe/Pingbefehl.java": SAUBERER_BEFEHL,
            "zwei/liesmich.txt": "diese Wurzel traegt nichts bei\n",
        },
        "wurzeln": ["eins", "zwei"],
        "rc": 2, "kennungen": set(), "funde": 0,
        "text": ["WURZEL OHNE DESKRIPTOR"], "weg": "WURZEL OHNE DESKRIPTOR",
        "mutation": ('        if len(e.wurzeln) > 1:', '        if False:'),
    },
]


# ═════════════════════════════════════════════════════════════════════════════
#  ABSCHNITT 2 - DER SAUBERE BAUM
#
#  ⚠️ Er ist mit Absicht anspruchsvoll. Jede Form darin steht fuer eine benannte Mutation aus
#  UEBERSTRENG weiter unten; ein Baum, der nur den einfachsten Fall zeigt, laesst genau die
#  Ueber-Meldungen durch, gegen die dieser Abschnitt gebaut ist.
#
#  ZWEI MODULE, weil beide Deskriptorarten vorkommen muessen:
#    plugin/  Paper (paper-plugin.yml)  -> BasicCommand, record, Fabrik, qualifiziert, generisch
#    alt/     Bukkit (plugin.yml)       -> commands:-Block mit Aliassen, CommandExecutor,
#                                          TabExecutor, TabCompleter, getCommand mit Umbruch
# ═════════════════════════════════════════════════════════════════════════════

SAUBER_PAPER_YML = """name: ProbeNeu
version: '1.0'
main: net.probe.Probe
api-version: '1.21'

# ⚠️ Hier steht KEIN commands:-Block. Das Wort commands: kommt in dieser Datei nur in diesem
# Kommentar vor - ein Waechter ohne Kommentarabtrennung meldet die Erklaerung als den Fehler.
permissions:
  probe.admin:
    default: op
"""

SAUBER_PAPER_HAUPT = """package net.probe;

import org.bukkit.plugin.java.JavaPlugin;

/**
 * ⚠️ Dieses Plugin ruft getCommand("ping") NIRGENDS - Paper wirft darauf
 * (UnsupportedOperationException) und nimmt das ganze Plugin mit. Genau dieser erklaerende
 * Javadoc steht in ZanUI und HeavyCrown, und genau daran schlug ein Waechter ohne
 * Kommentarabtrennung an: er meldete die Erklaerung als den Fehler.
 */
public final class Probe extends JavaPlugin {

    @Override
    public void onEnable() {
        // Erzeugung ueber eine FABRIK - der Waechter muss die Erzeugung im ganzen Modul suchen,
        // nicht nur in der Datei der Klasse.
        registerCommand("ping", "Probe", Befehlsfabrik.ping());

        // Erzeugung ueber eine VARIABLE und QUALIFIZIERT geschrieben.
        Tpbefehl tp = new net.probe.Tpbefehl();
        registerCommand("tp", "Probe", tp);

        // Erzeugung mit TYPARGUMENT.
        registerCommand("liste", "Probe", new Listenbefehl<>());

        // Ein RECORD als Befehl.
        registerCommand("pong", "Probe", new Pongbefehl("Probe"));

        String hinweis = "getCommand(\\"ping\\") gehoert nicht in ein Paper-Plugin";
        getLogger().info(hinweis);
    }
}
"""

SAUBER_FABRIK = """package net.probe;

/** Erzeugt Befehle. ⚠️ Absichtlich in einer ANDEREN Datei als die Befehlsklassen. */
public final class Befehlsfabrik {
    private Befehlsfabrik() { }

    public static Pingbefehl ping() {
        return new Pingbefehl();
    }
}
"""

SAUBER_BASIC = """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;
public final class %s implements BasicCommand {
    @Override public void execute(CommandSourceStack quelle, String[] argumente) { }
}
"""

SAUBER_GENERISCH = """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;
public final class Listenbefehl<T> implements BasicCommand {
    @Override public void execute(CommandSourceStack quelle, String[] argumente) { }
}
"""

SAUBER_RECORD = """package net.probe;
import io.papermc.paper.command.brigadier.BasicCommand;
import io.papermc.paper.command.brigadier.CommandSourceStack;

/** ⚠️ Ein record traegt eine Befehlsschnittstelle genauso wie eine class. */
public record Pongbefehl(String antwort) implements BasicCommand {
    @Override public void execute(CommandSourceStack quelle, String[] argumente) { }
}
"""

# ⚠️ Der Kommentar in SPALTE 0 mitten im commands:-Block ist der Kern dieses Deskriptors. Ohne
# yaml_ohne_kommentare endet der Block fuer den Waechter an dieser Zeile (sie beginnt nicht mit
# Leerraum), und alles darunter - fly, tp, teleport - gilt als UNDEKLARIERT. Der Waechter meldet
# dann drei Falschfunde ueber vollkommen richtigen Code.
SAUBER_BUKKIT_YML = """name: ProbeAlt
version: '1.0'
main: net.probe.alt.ProbeAlt
api-version: '1.21'

commands:
  ping:
    description: Probe
    aliases: [p, pong]
# ⚠️ Kommentar in Spalte 0 MITTEN im Block - trennt ihn ohne Kommentarabtrennung ab.
  fly:
    description: Probe
  tp:
    description: Probe
    aliases:
      - teleport
"""

SAUBER_BUKKIT_HAUPT = """package net.probe.alt;

import org.bukkit.plugin.java.JavaPlugin;

public final class ProbeAlt extends JavaPlugin {

    @Override
    public void onEnable() {
        // Der deklarierte Name selbst.
        getCommand("ping").setExecutor(new Pingbefehl());
        // Ein Alias in KLAMMERFORM (aliases: [p, pong]).
        getCommand("pong").setExecutor(new Pingbefehl());
        // Ein Name UNTERHALB des Kommentars in Spalte 0.
        getCommand("fly").setExecutor(new Flugbefehl());
        // Ein Alias in LISTENFORM (aliases:\\n      - teleport).
        getCommand("teleport").setTabCompleter(new Tippbefehl());
        // Ein Aufruf mit UMBRUCH vor der Klammer - in Java erlaubt.
        getCommand
                ("tp").setTabCompleter(new Tippbefehl());
    }
}
"""


def _sauberer_baum() -> dict[str, str]:
    return {
        # ── Paper-Modul ──────────────────────────────────────────────────────
        "plugin/src/main/resources/paper-plugin.yml": SAUBER_PAPER_YML,
        "plugin/src/main/java/net/probe/Probe.java": SAUBER_PAPER_HAUPT,
        "plugin/src/main/java/net/probe/Befehlsfabrik.java": SAUBER_FABRIK,
        "plugin/src/main/java/net/probe/Pingbefehl.java": SAUBER_BASIC % "Pingbefehl",
        "plugin/src/main/java/net/probe/Tpbefehl.java": SAUBER_BASIC % "Tpbefehl",
        "plugin/src/main/java/net/probe/Listenbefehl.java": SAUBER_GENERISCH,
        "plugin/src/main/java/net/probe/Pongbefehl.java": SAUBER_RECORD,
        # ── Bukkit-Modul ─────────────────────────────────────────────────────
        "alt/src/main/resources/plugin.yml": SAUBER_BUKKIT_YML,
        "alt/src/main/java/net/probe/alt/ProbeAlt.java": SAUBER_BUKKIT_HAUPT,
        "alt/src/main/java/net/probe/alt/Pingbefehl.java":
            _befehlsklasse("Pingbefehl", "CommandExecutor", IMPORT_EXECUTOR, RUMPF_EXECUTOR)
            .replace("package net.probe;", "package net.probe.alt;"),
        "alt/src/main/java/net/probe/alt/Flugbefehl.java":
            _befehlsklasse("Flugbefehl", "TabExecutor", IMPORT_TABEXECUTOR, RUMPF_TABEXECUTOR)
            .replace("package net.probe;", "package net.probe.alt;"),
        "alt/src/main/java/net/probe/alt/Tippbefehl.java":
            _befehlsklasse("Tippbefehl", "TabCompleter", IMPORT_TABCOMPLETER, RUMPF_TABCOMPLETER)
            .replace("package net.probe;", "package net.probe.alt;"),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  ABSCHNITT 3 - ZU STRENGE MUTANTEN
#
#  Je Eintrag: (Was verengt wird, (suchen, ersetzen), welche Form im sauberen Baum sie faellt)
#  Jede MUSS den sauberen Baum roeten. Tut sie es nicht, fehlt dem sauberen Baum die
#  entsprechende Form - dann ist nicht der Waechter in Ordnung, sondern der Baum zu leicht.
# ═════════════════════════════════════════════════════════════════════════════

UEBERSTRENG: list[tuple[str, tuple[str, str], str]] = [
    ("Java-Kommentare werden nicht mehr abgetrennt",
     ('    ergebnis = []\n    i = 0\n    n = len(text)\n    while i < n:\n'
      '        c = text[i]\n        z = text[i + 1] if i + 1 < n else ""\n'
      '        if c == "/" and z == "/":',
      '    return text\n'
      '    ergebnis = []\n    i = 0\n    n = len(text)\n    while i < n:\n'
      '        c = text[i]\n        z = text[i + 1] if i + 1 < n else ""\n'
      '        if c == "/" and z == "/":'),
     "der erklaerende Javadoc in plugin/.../Probe.java nennt getCommand"),

    ("YAML-Kommentare werden nicht mehr abgetrennt",
     ('        raus.append("" if zeile.lstrip().startswith("#") else zeile)',
      '        raus.append(zeile)'),
     "der Kommentar in Spalte 0 mitten im commands:-Block von alt/.../plugin.yml"),

    ("deklarierte_befehle liefert nie einen Namen",
     ('    namen = set()\n    drin = False',
      '    return set()\n    namen = set()\n    drin = False'),
     "jeder getCommand-Aufruf in alt/.../ProbeAlt.java"),

    ("aliases in Klammerform zaehlen nicht mehr",
     ("            m = re.match(r'^\\s+aliases\\s*:\\s*\\[(.*)\\]\\s*$', zeile)",
      "            m = None if True else"
      " re.match(r'^\\s+aliases\\s*:\\s*\\[(.*)\\]\\s*$', zeile)"),
     'getCommand("pong") - Alias aus aliases: [p, pong]'),

    ("aliases in Listenform zaehlen nicht mehr",
     ("            m = re.match(r'^\\s+-\\s*([A-Za-z0-9_\\-]+)\\s*$', zeile)",
      "            m = None if True else"
      " re.match(r'^\\s+-\\s*([A-Za-z0-9_\\-]+)\\s*$', zeile)"),
     'getCommand("teleport") - Alias aus der Listenform'),

    ("die Erzeugungsregex sieht weder qualifiziert noch generisch",
     ("erzeugung = re.compile(r'\\bnew\\s+(?:[\\w.]+\\.)?' + re.escape(name) + r'\\s*[(<]')",
      "erzeugung = re.compile(r'\\bnew\\s+' + re.escape(name) + r'\\s*\\(')"),
     "new net.probe.Tpbefehl() und new Listenbefehl<>()"),

    ("die Erzeugung wird nur in der eigenen Datei gesucht",
     ('            if not any(erzeugung.search(t) for t in alle_texte.values()):',
      '            if not erzeugung.search(alle_texte[q]):'),
     "Pingbefehl entsteht in Befehlsfabrik.java, nicht in seiner eigenen"),
]


# ═════════════════════════════════════════════════════════════════════════════
#  Maschinerie
# ═════════════════════════════════════════════════════════════════════════════

def sha(pfad: str) -> str:
    with io.open(pfad, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def schreibe(pfad: str, inhalt: str):
    ordner = os.path.dirname(pfad)
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    with io.open(pfad, "wb") as f:
        f.write(inhalt.encode("utf-8"))


def baum(basis: str, dateien: dict[str, str], ausnahmen: str | None = None) -> str:
    # ⚠️ NEUTRALER Ordnername, nie eine Kennung. Der Waechter druckt seinen Pfad in die Zeile
    # "geprueft ... in <pfad>"; hiesse der Baum wie der gesuchte Fund, stuende die Kennung in
    # JEDER Ausgabe - auch in der des Mutanten. Beim ersten Anlauf am 2026-08-21 genau so
    # passiert, und alle fuenf Faelle meldeten "Kennung DA" bei Rueckgabe 0.
    wurzel = os.path.join(basis, "probe")
    for relpfad, inhalt in dateien.items():
        schreibe(os.path.join(wurzel, *relpfad.split("/")), inhalt)
    if ausnahmen is not None:
        schreibe(os.path.join(wurzel, ".befehlswaechter-ausnahmen"), "# Kopf\n" + ausnahmen)
    return wurzel


def lauf(waechter: str, wurzeln: list[str]) -> tuple[int, str]:
    p = subprocess.run([sys.executable, waechter] + wurzeln,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def gemeldet(text: str) -> tuple[set[str], int]:
    """Welche Kennungen hat der Lauf gemeldet, und wieviele offene Funde?

    ⚠️ Die GENAUE Menge, nicht "kommt vor". Der alte Test fragte ``kennung in ausgabe`` und
    liess damit jeden ZUSAETZLICHEN Falschfund durch - ein Waechter, der neben dem richtigen
    Fund noch drei falsche meldet, galt als bestanden. Gelesen wird nur das erste Wort einer
    Zeile: Fundzeilen beginnen mit der Kennung, die Zeilen UNTERDRUECKT/VERALTET/UNGUELTIG
    nennen sie erst danach und duerfen hier nicht mitzaehlen.
    """
    kennungen = set()
    for zeile in text.splitlines():
        teile = zeile.strip().split()
        if teile and teile[0] in ALLE_KENNUNGEN:
            kennungen.add(teile[0])
    m = RE_FUNDZAHL.search(text)
    return kennungen, int(m.group(1)) if m else 0


def _mutant_schreiben(tmp: str, original_text: str, sha_vorher: str, nr: int,
                      suchen: str, ersetzen: str) -> tuple[str | None, str]:
    """Gibt (Pfad, "") oder (None, Grund) zurueck."""
    if suchen not in original_text:
        return None, ("der Mutationsanker steht nicht mehr im Waechter. Kein Urteil, nicht"
                      " 'bestanden'.")
    pfad = os.path.join(tmp, f"mutant{nr}.py")
    with io.open(pfad, "wb") as f:
        f.write(original_text.replace(suchen, ersetzen, 1).encode("utf-8"))
    # ⚠️ Belegen, dass wirklich mutiert wurde. Ein Mutant, der dem Original gleicht, gibt eine
    # Gegenprobe zurueck, die nichts geprueft hat (Standing Rule 28).
    if sha(pfad) == sha_vorher:
        return None, "Mutant ist byteweise das Original."
    return pfad, ""


def main() -> int:
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if not os.path.isfile(WAECHTER):
        print(f"GEGENPROBE: {WAECHTER} fehlt - es lief nichts.", file=sys.stderr)
        return 2

    with io.open(WAECHTER, "rb") as f:
        original_text = f.read().decode("utf-8")
    sha_vorher = sha(WAECHTER)

    bestanden = 0
    gefallen = 0
    gelaufen = 0

    print(f"GEGENPROBE gegen {os.path.relpath(WAECHTER)}  (sha256/16 {sha_vorher})\n")

    with tempfile.TemporaryDirectory() as tmp:

        # ── ABSCHNITT 1: Giftbaeume ──────────────────────────────────────────
        print(f"  ── {len(GIFTBAEUME)} GIFTBAEUME  (Unter-Meldung: die Probe MUSS anschlagen,"
              f" und ihre Entfernung MUSS das aendern)")
        for nr, fall in enumerate(GIFTBAEUME, 1):
            wurzel = baum(os.path.join(tmp, f"fall{nr}"), fall["dateien"],
                          fall.get("ausnahmen"))
            wurzeln = ([os.path.join(wurzel, u) for u in fall["wurzeln"]]
                       if fall.get("wurzeln") else [wurzel])
            marke = fall["weg"]

            # 1 GIFT
            rc_gift, aus_gift = lauf(WAECHTER, wurzeln)
            k_gift, z_gift = gemeldet(aus_gift)
            maengel = []
            if rc_gift != fall["rc"]:
                maengel.append(f"Rueckgabe {rc_gift}, erwartet {fall['rc']}")
            if k_gift != fall["kennungen"]:
                maengel.append(f"Kennungen {sorted(k_gift) or '-'},"
                               f" erwartet {sorted(fall['kennungen']) or '-'}")
            if z_gift != fall["funde"]:
                maengel.append(f"{z_gift} Fund(e), erwartet {fall['funde']}")
            for t in [marke] + list(fall.get("text", [])):
                if t not in aus_gift:
                    maengel.append(f"'{t}' fehlt in der Ausgabe")

            # 2 MUTANT
            mutant, grund = _mutant_schreiben(tmp, original_text, sha_vorher, nr,
                                              *fall["mutation"])
            if mutant is None:
                print(f"  NICHT GELAUFEN  {fall['name']}: {grund}")
                gefallen += 1
                continue
            rc_mut, aus_mut = lauf(mutant, wurzeln)
            gelaufen += 1
            # ⚠️ Woran man sieht, dass die Mutation wirklich etwas genommen hat. Vorgabe ist die
            # Marke: sie muss verschwinden. Bei EINEM Fall geht das nicht, und der Grund ist der
            # Fall selbst - mutiert man ``return 2`` zu ``return 0``, druckt der Waechter seine
            # Blindstellen WEITER und aendert nur das Urteil. Genau das ist der Schaden: die
            # Ausgabe sieht aus wie vorher, Gradle liest aber die Rueckgabe, und acht Repos
            # bauen gruen. Ein Marken-Test haette diese Mutation fuer gefangen erklaert, obwohl
            # sie durchgeht - deshalb prueft dieser Fall die RUECKGABE.
            if "mutant_rc" in fall:
                if rc_mut != fall["mutant_rc"]:
                    maengel.append(f"MUTANT gibt {rc_mut} zurueck, erwartet"
                                   f" {fall['mutant_rc']} - die entfernte Zeile hat das Urteil"
                                   f" also gar nicht gefaellt")
                elif rc_mut == fall["rc"]:
                    maengel.append(f"MUTANT gibt dasselbe Urteil wie das Original ({rc_mut}) -"
                                   f" die Mutation aendert nichts")
            elif marke in aus_mut:
                maengel.append(f"MUTANT meldet '{marke}' weiterhin (Rueckgabe {rc_mut}) - die"
                               f" entfernte Zeile hat den Fund also gar nicht gemacht")

            ok = not maengel
            bestanden += 1 if ok else 0
            gefallen += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FEHL'} {fall['name']}")
            if not ok:
                for m in maengel:
                    print(f"         ⚠️ {m}")

        # ── ABSCHNITT 2: der saubere Baum ────────────────────────────────────
        print(f"\n  ── DER SAUBERE BAUM  (Ueber-Meldung: jeder Fund hier ist ein FALSCHFUND)")
        sauber = baum(os.path.join(tmp, "sauber"), _sauberer_baum())
        rc_s, aus_s = lauf(WAECHTER, [sauber])
        k_s, z_s = gemeldet(aus_s)
        maengel = []
        if rc_s != 0:
            maengel.append(f"Rueckgabe {rc_s}, erwartet 0")
        if k_s:
            maengel.append(f"FALSCHFUNDE: {sorted(k_s)}")
        if z_s != 0:
            maengel.append(f"{z_s} Fund(e), erwartet 0")
        # ⚠️ Erreichbarkeitsnachweis: ein sauberer Baum, den der Waechter gar nicht gelesen hat,
        # ist trivial gruen. Beide Module muessen gesehen worden sein.
        if "geprueft 2 Plugin-Deskriptor(en)" not in aus_s:
            maengel.append("der Waechter hat NICHT beide Module gesehen - ein gruenes Urteil"
                           " ueber einen ungelesenen Baum ist keins")
        ok = not maengel
        bestanden += 1 if ok else 0
        gefallen += 0 if ok else 1
        print(f"  {'OK  ' if ok else 'FEHL'} sauberer Baum: null Funde, Rueckgabe 0")
        if not ok:
            for m in maengel:
                print(f"         ⚠️ {m}")
            for z in aus_s.splitlines():
                print(f"         | {z}")

        # ── ABSCHNITT 3: zu strenge Mutanten ─────────────────────────────────
        print(f"\n  ── {len(UEBERSTRENG)} ZU STRENGE MUTANTEN  (jede MUSS den sauberen Baum"
              f" roeten)")
        for nr, (was, (suchen, ersetzen), form) in enumerate(UEBERSTRENG, 1):
            mutant, grund = _mutant_schreiben(tmp, original_text, sha_vorher, 1000 + nr,
                                              suchen, ersetzen)
            if mutant is None:
                print(f"  NICHT GELAUFEN  {was}: {grund}")
                gefallen += 1
                continue
            rc_u, aus_u = lauf(mutant, [sauber])
            k_u, _ = gemeldet(aus_u)
            gelaufen += 1
            ok = rc_u != 0 and bool(k_u)
            bestanden += 1 if ok else 0
            gefallen += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FEHL'} {was}"
                  f"   -> Rueckgabe {rc_u}, Falschfunde {sorted(k_u) or '-'}")
            if not ok:
                print(f"         ⚠️ Der saubere Baum bleibt gruen. Ihm fehlt die Form, die diese"
                      f" Verengung faellen wuerde: {form}")

    # ── ZEUGE ────────────────────────────────────────────────────────────────
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
