#!/usr/bin/env python3
"""Copia a base comum para o projeto de uma ponte, ou confere se as cópias estão em dia.

Rodar na pasta do projeto (a que tem firmware/ e tools/):

    python3 ../amp-link/firmware-base/copiar.py                # copia o que mudou
    python3 ../amp-link/firmware-base/copiar.py --conferir     # só confere; sai com erro se algo difere
    python3 ../amp-link/firmware-base/copiar.py --sem firmware/main.py    # deixa esse arquivo como está

Os arquivos vão iguais, byte a byte. Uma cópia diferente da base quer dizer que alguém a mudou no projeto: leve a
mudança para a base antes de copiar, porque a cópia a apaga.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDERS = ("firmware", "tools")


def base_files():
    """Os arquivos da base, como "firmware/wifi.py"."""
    out = []
    for folder in FOLDERS:
        for name in sorted(os.listdir(os.path.join(HERE, folder))):
            if name.endswith(".py"):
                out.append(folder + "/" + name)
    return out


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", nargs="?", default=".", help="a pasta do projeto (padrão: a atual)")
    ap.add_argument("--conferir", action="store_true", help="não copia: só diz o que difere")
    ap.add_argument("--sem", action="append", default=[], metavar="ARQUIVO",
                    help="arquivo que este projeto mantém por conta própria (pode repetir)")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(os.path.join(project, "firmware")):
        sys.exit("%s não tem a pasta firmware/: rode na pasta do projeto da ponte." % project)
    if os.path.samefile(project, HERE):
        sys.exit("Esta é a própria base. Rode na pasta do projeto da ponte.")
    for skipped in args.sem:
        if skipped not in base_files():
            sys.exit("--sem %s: a base não tem esse arquivo." % skipped)

    differs = 0
    for rel in base_files():
        if rel in args.sem:
            print("  %-28s por conta do projeto" % rel)
            continue
        want = read(os.path.join(HERE, rel))
        target = os.path.join(project, rel)
        have = read(target)
        if have == want:
            continue
        differs += 1
        what = "falta" if have is None else "difere da base"
        if args.conferir:
            print("  %-28s %s" % (rel, what))
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(want)
        print("  %-28s copiado (%s)" % (rel, "novo" if have is None else "estava diferente"))

    if not differs:
        print("Tudo em dia com a base.")
    elif args.conferir:
        sys.exit("%d arquivo(s) fora de dia com a base." % differs)


if __name__ == "__main__":
    main()
