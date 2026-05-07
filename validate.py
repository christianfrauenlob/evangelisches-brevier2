#!/usr/bin/env python3
"""
Evangelisches Brevier — JSON-Validator
Ausführen: python3 validate.py data/rogate.json
Oder alle auf einmal: python3 validate.py data/*.json
"""

import json
import sys
from pathlib import Path

VALID_TYPEN = {
    "leitwort", "leitwort_lobgesang", "psalm", "lied",
    "lesung", "gebet", "vaeterstimme", "spruch",
    "antwort", "rubrik"
}

VALID_KIRCHENZEITEN = {"advent", "weihnachten", "epiphanias", "passionszeit",
                       "karwoche", "ostern", "pfingsten", "trinitatis"}

errors = []
warnings = []

def err(path, msg):
    errors.append(f"  FEHLER  [{path}] {msg}")

def warn(path, msg):
    warnings.append(f"  WARNUNG [{path}] {msg}")

def check_block(block, path):
    if not isinstance(block, dict):
        err(path, f"Block ist kein Objekt: {type(block)}")
        return

    typ = block.get("typ")
    if not typ:
        err(path, "Kein 'typ'-Feld")
        return
    if typ not in VALID_TYPEN:
        err(path, f"Unbekannter Typ: '{typ}'")

    p = f"{path}/{typ}"

    # ── psalm ────────────────────────────────────────────────────────────
    if typ == "psalm":
        nummern = block.get("nummern")
        if not isinstance(nummern, list) or len(nummern) == 0:
            err(p, "'nummern' fehlt oder ist leer")
        else:
            for i, n in enumerate(nummern):
                if not isinstance(n, str):
                    err(p, f"nummern[{i}] ist kein String: {repr(n)} ({type(n).__name__})"
                        " — muss String sein, z.B. \"66\" nicht 66")

    # ── leitwort / leitwort_lobgesang / spruch ───────────────────────────
    elif typ in ("leitwort", "leitwort_lobgesang", "spruch"):
        zeilen = block.get("zeilen")
        if not isinstance(zeilen, list) or len(zeilen) == 0:
            err(p, "'zeilen' fehlt oder ist leer")
        else:
            for i, z in enumerate(zeilen):
                if not isinstance(z, str):
                    err(p, f"zeilen[{i}] ist kein String: {repr(z)}")

    # ── lesung ───────────────────────────────────────────────────────────
    elif typ == "lesung":
        if not block.get("ref"):
            err(p, "'ref' fehlt")
        if not block.get("text"):
            err(p, "'text' fehlt")

    # ── gebet ────────────────────────────────────────────────────────────
    elif typ == "gebet":
        if not block.get("text"):
            err(p, "'text' fehlt")
        if "amen" not in block:
            warn(p, "'amen' fehlt (sollte true oder false sein)")

    # ── vaeterstimme ─────────────────────────────────────────────────────
    elif typ == "vaeterstimme":
        if not block.get("quelle"):
            err(p, "'quelle' fehlt")
        if not block.get("text"):
            err(p, "'text' fehlt")

    # ── rubrik ───────────────────────────────────────────────────────────
    elif typ == "rubrik":
        if not block.get("inhalt"):
            err(p, "'inhalt' fehlt")

    # ── lied ─────────────────────────────────────────────────────────────
    elif typ == "lied":
        if not block.get("titel"):
            err(p, "'titel' fehlt")
        strophen = block.get("strophen")
        if not isinstance(strophen, list) or len(strophen) == 0:
            err(p, "'strophen' fehlt oder ist leer")
        else:
            for si, st in enumerate(strophen):
                sp = f"{p}/strophe[{si}]"
                if not isinstance(st, dict):
                    err(sp, "Strophe ist kein Objekt")
                    continue
                links = st.get("links")
                rechts = st.get("rechts")
                if not isinstance(links, list) or len(links) == 0:
                    err(sp, "'links' fehlt oder ist leer")
                if rechts is None:
                    err(sp, "'rechts' ist null — muss [] sein, nicht null")
                elif not isinstance(rechts, list):
                    err(sp, f"'rechts' ist kein Array: {type(rechts)}")

    # ── antwort ──────────────────────────────────────────────────────────
    elif typ == "antwort":
        absaetze = block.get("absätze")
        if not isinstance(absaetze, list) or len(absaetze) == 0:
            err(p, "'absätze' fehlt oder ist leer")
        else:
            for ai, ab in enumerate(absaetze):
                ap = f"{p}/absätze[{ai}]"
                if not isinstance(ab, dict):
                    err(ap, "Absatz ist kein Objekt")
                    continue
                if not ab.get("art"):
                    err(ap, "'art' fehlt")
                if not ab.get("inhalt"):
                    err(ap, "'inhalt' fehlt")


def check_stunde(blocks, path):
    if not isinstance(blocks, list):
        err(path, "Stunde ist keine Liste")
        return
    for i, block in enumerate(blocks):
        check_block(block, f"{path}[{i}]")


def check_tag(tag, path):
    for field in ("id", "titel", "wochentag", "seiten"):
        if not tag.get(field):
            err(path, f"Pflichtfeld '{field}' fehlt")

    seiten = tag.get("seiten")
    if isinstance(seiten, list):
        for s in seiten:
            if not isinstance(s, int):
                err(path, f"seiten-Eintrag ist kein Integer: {repr(s)}")

    stunden = tag.get("stunden", {})
    for stunde_name in ("morgen", "mittag", "abend"):
        stunde = stunden.get(stunde_name)
        if stunde is None:
            warn(f"{path}/{stunde_name}", "Stunde fehlt komplett")
        else:
            check_stunde(stunde, f"{path}/{stunde_name}")


def check_file(path: Path):
    print(f"\n{'─'*60}")
    print(f"Prüfe: {path.name}")
    print(f"{'─'*60}")

    global errors, warnings
    errors = []
    warnings = []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  FATAL: Kein valides JSON — {e}")
        return False

    # Pflichtfelder auf Wochenebene
    for field in ("id", "titel", "kirchenzeit", "reihe", "band", "tage"):
        if field not in data:
            err("root", f"Pflichtfeld '{field}' fehlt")

    if data.get("kirchenzeit") not in VALID_KIRCHENZEITEN:
        warn("root", f"Unbekannte kirchenzeit: '{data.get('kirchenzeit')}'")

    tage = data.get("tage", [])
    if not isinstance(tage, list) or len(tage) == 0:
        err("root", "'tage' fehlt oder ist leer")
    else:
        for i, tag in enumerate(tage):
            check_tag(tag, f"tage[{i}]/{tag.get('id','?')}")

    # Ausgabe
    if warnings:
        for w in warnings:
            print(w)
    if errors:
        for e in errors:
            print(e)
        print(f"\n  → {len(errors)} Fehler, {len(warnings)} Warnungen")
        return False
    else:
        print(f"  ✓ Alles in Ordnung ({len(warnings)} Warnungen)")
        return True


def check_index(path: Path):
    print(f"\n{'─'*60}")
    print(f"Prüfe index: {path.name}")
    print(f"{'─'*60}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  FATAL: Kein valides JSON — {e}")
        return False

    wochen = data.get("wochen", [])
    ok = True
    for i, w in enumerate(wochen):
        for field in ("id", "titel", "datei"):
            if not w.get(field):
                print(f"  FEHLER  [wochen[{i}]] Pflichtfeld '{field}' fehlt")
                ok = False
    if ok:
        print(f"  ✓ {len(wochen)} Einträge, alle Pflichtfelder vorhanden")
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Verwendung: python3 validate.py data/rogate.json [data/cantate.json ...]")
        print("            python3 validate.py data/index.json")
        sys.exit(1)

    all_ok = True
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"Datei nicht gefunden: {p}")
            all_ok = False
            continue
        if p.name == "index.json":
            result = check_index(p)
        else:
            result = check_file(p)
        all_ok = all_ok and result

    print(f"\n{'═'*60}")
    if all_ok:
        print("GESAMT: ✓ Alle Dateien valide")
    else:
        print("GESAMT: ✗ Fehler gefunden — bitte korrigieren")
        sys.exit(1)
