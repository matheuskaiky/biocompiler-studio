"""Leitura de entradas TXT, FASTA e stdin em UTF-8 para a CLI."""

import sys


class ErroEntrada(Exception):
    """Erro controlado de leitura ou formato de arquivo/entrada."""


def ler_texto(caminho: str) -> str:
    """Lê bytes de arquivo (ou stdin se '-') e decodifica como UTF-8 com ou sem BOM."""
    if caminho == "-":
        dados = sys.stdin.buffer.read()
    else:
        try:
            with open(caminho, "rb") as arquivo:
                dados = arquivo.read()
        except FileNotFoundError as exc:
            raise ErroEntrada(f"arquivo não encontrado: {caminho}") from exc
        except OSError as exc:
            raise ErroEntrada(f"arquivo ilegível: {caminho}") from exc

    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ErroEntrada(f"arquivo ilegível: {caminho}") from exc


def separar_registros(texto: str) -> list[str]:
    """Separa linhas físicas por '\\n', removendo apenas um '\\r' final de cada linha."""
    if texto == "":
        return []
    linhas = texto.split("\n")
    if linhas[-1] == "":
        linhas.pop()
    return [linha[:-1] if linha.endswith("\r") else linha for linha in linhas]


def ler_par(texto: str) -> tuple[str, str]:
    """Lê exatamente duas sequências a partir de FASTA (se iniciar com '>') ou TXT."""
    linhas = separar_registros(texto)
    primeira = next((linha.strip() for linha in linhas if linha.strip()), "")

    if primeira.startswith(">"):
        registros: list[str] = []
        atual: list[str] | None = None
        for linha in linhas:
            limpa = linha.strip()
            if not limpa:
                continue
            if limpa.startswith(">"):
                if atual is not None:
                    registros.append("".join(atual))
                atual = []
            elif atual is not None:
                atual.append(limpa)
        if atual is not None:
            registros.append("".join(atual))
    else:
        registros = linhas

    if len(registros) != 2:
        raise ErroEntrada(
            f"esperadas exatamente 2 sequências, encontradas {len(registros)}"
        )
    return (registros[0], registros[1])
