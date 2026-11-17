"""Interface de linha de comando (CLI) do BioCompiler Studio."""

import argparse
import sys

_SUBCOMANDOS = (
    ("at1", "AT1 — DNA → pré-mRNA (transcrição)"),
    ("at2", "AT2 — pré-mRNA → mRNA maduro (splicing e maturação)"),
    ("at3", "AT3 — mRNA maduro → proteína (tradução)"),
    ("at4", "AT4 — alinhamento local (Smith–Waterman) e global (Needleman–Wunsch)"),
    ("all", "Laboratório completo: AT1→AT2→AT3 em dois DNAs e AT4 entre eles"),
    ("serve", "Interface web local opcional (requer requirements-web.txt)"),
    ("examples", "Lista exemplos didáticos"),
    ("test", "Executa a suíte unittest do projeto"),
)


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m biocompiler",
        description="BioCompiler Studio — AT1–AT4 de bioinformática (CLI)",
    )
    subparsers = parser.add_subparsers(dest="comando")
    for nome, ajuda in _SUBCOMANDOS:
        sub = subparsers.add_parser(nome, help=ajuda, description=ajuda)
        if nome == "serve":
            sub.add_argument("--host", default="127.0.0.1", help="Endereço de escuta (padrão: 127.0.0.1)")
            sub.add_argument("--port", type=int, default=8765, help="Porta HTTP (padrão: 8765)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI para comandos não web e ajuda de subcomandos."""
    parser = _criar_parser()
    args = parser.parse_args(argv)

    if args.comando is None:
        parser.print_help(sys.stdout)
        return 1

    if args.comando == "serve":
        sys.stderr.write("biocompiler: use python -m biocompiler serve\n")
        return 1

    sys.stderr.write(
        f"biocompiler: comando '{args.comando}' ainda não implementado neste marco\n"
    )
    return 3
