"""Servidor web local opcional do BioCompiler Studio (carregado apenas por `serve`)."""

import sys

import jinja2  # noqa: F401 — dependência opcional exigida exclusivamente na camada web


def main(argv: list[str]) -> int:
    """Ponto de entrada do servidor web local."""
    sys.stderr.write("biocompiler: servidor web ainda não implementado (marco M7)\n")
    return 1
