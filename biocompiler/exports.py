"""Formatadores puros de relatórios de terminal e exportações CSV/TXT."""

import csv
import io

_SEP_IGUAL = "=" * 40
_SEP_TRACO = "-" * 40

_TITULOS_LOTE = {
    "at1": "BIOCOMPILER 1.0 - DNA TRANSCRIBER",
    "at2": "BIOCOMPILER 2.0 - RNA PROCESSOR",
    "at3": "RIBOSSOMO - PROTEIN TRANSLATOR",
}

_COLUNAS_CSV = {
    "at1": ("pre_mRNA", "pre_mrna", "NÃO GERADO"),
    "at2": ("mRNA_maduro", "mrna_maduro", "NÃO GERADO"),
    "at3": ("proteina", "proteina", "NÃO GERADA"),
}

_TITULOS_AT4 = {
    "local": "ALINHAMENTO LOCAL (SMITH-WATERMAN)",
    "global": "ALINHAMENTO GLOBAL (NEEDLEMAN-WUNSCH)",
}


def _eh_int(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _linha_parametros_at4(match: int, mismatch: int, gap: int) -> str:
    return f"Match: {match:+d}   Mismatch: {mismatch:+d}   Gap: {gap:+d}"


def csv_lote(atividade: str, resultados) -> str:
    """Gera o CSV canônico com delimitador ';' para lotes AT1–AT3."""
    if atividade not in _COLUNAS_CSV:
        raise ValueError(f"atividade inválida para CSV de lote: {atividade!r}")
    coluna, atributo, texto_falha = _COLUNAS_CSV[atividade]
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=";", lineterminator="\n")
    escritor.writerow(["linha", "status", "resultado", coluna])
    for idx, res in enumerate(resultados, start=1):
        produto = getattr(res, atributo) if res.ok else texto_falha
        escritor.writerow([idx, res.status, res.resultado, produto])
    return buf.getvalue()


def relatorio_lote(atividade: str, resultados) -> str:
    """Gera o relatório textual de lote AT1–AT3 fiel aos enunciados."""
    if atividade not in _TITULOS_LOTE:
        raise ValueError(f"atividade inválida para relatório de lote: {atividade!r}")

    linhas: list[str] = [_SEP_IGUAL, _TITULOS_LOTE[atividade], _SEP_IGUAL]
    for idx, res in enumerate(resultados, start=1):
        linhas.append(f"ENTRADA: {idx}")
        linhas.append(f"STATUS: {'CORRETO' if res.ok else 'ERRO'}")
        if atividade == "at1":
            if res.ok:
                linhas.extend([
                    "Bases: OK",
                    "START: ATG - OK",
                    "Quadro de leitura: OK",
                    f"STOP: {res.codon_stop} - OK",
                    "Transcrição: OK",
                    f"pré-mRNA: {res.pre_mrna}",
                ])
            else:
                linhas.extend([
                    f"TIPO: {res.resultado}",
                    "pré-mRNA: NÃO GERADO",
                ])
        elif atividade == "at2":
            if res.ok:
                linhas.extend([
                    "Sítio 5': OK",
                    "Branch point: OK",
                    "Sítio 3': OK",
                    "Splicing: OK",
                    "CAP 5': ADICIONADA",
                    f"Cauda poli-A: {len(res.cauda_adicionada)} A",
                    f"mRNA MADURO: {res.mrna_maduro}",
                ])
            else:
                linhas.extend([
                    f"TIPO: {res.resultado}",
                    "mRNA MADURO: NÃO GERADO",
                ])
        else:
            if res.ok:
                linhas.extend([
                    "CAP 5': OK",
                    "START: AUG - OK",
                    "Quadro de leitura: OK",
                    f"STOP: {res.codon_stop} - OK",
                    f"Cauda poli-A: {res.tamanho_cauda} A - OK",
                    "Tradução: OK",
                    f"PROTEÍNA: {res.proteina}",
                ])
            else:
                linhas.extend([
                    f"TIPO: {res.resultado}",
                    "PROTEÍNA: NÃO GERADA",
                ])
        linhas.append(_SEP_TRACO)
    return "\n".join(linhas) + "\n"


def _csv_grade(seq1: str, seq2: str, linhas_matriz, delimitador: str) -> str:
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=delimitador, lineterminator="\n")
    escritor.writerow(["", "-", *seq2])
    rotulos = ["-", *seq1]
    for idx, linha in enumerate(linhas_matriz):
        escritor.writerow([rotulos[idx], *linha])
    return buf.getvalue()


def csv_matriz_pontuacao(r, delimitador: str = ";") -> str:
    """Exporta a matriz de pontuação completa da AT4 em CSV."""
    return _csv_grade(r.seq1, r.seq2, r.matriz, delimitador)


def csv_matriz_traceback(r, delimitador: str = ";") -> str:
    """Exporta a matriz de direções de traceback da AT4 em CSV."""
    return _csv_grade(r.seq1, r.seq2, r.direcoes, delimitador)


def csv_alinhamento(r, delimitador: str = ";") -> str:
    """Exporta as colunas alinhadas e contribuições de score da AT4 em CSV."""
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=delimitador, lineterminator="\n")
    escritor.writerow(["posicao", "seq1", "marcador", "seq2", "contribuicao_score"])
    for pos, (b1, marc, b2) in enumerate(
        zip(r.alinhado1, r.marcadores, r.alinhado2), start=1
    ):
        if marc == "|":
            contrib = r.match
        elif marc == ".":
            contrib = r.mismatch
        else:
            contrib = r.gap
        escritor.writerow([pos, b1, marc, b2, contrib])
    return buf.getvalue()


def _grade_texto(seq1: str, seq2: str, linhas_matriz) -> list[str]:
    linhas = [" ".join(["", "-", *seq2])]
    rotulos = ["-", *seq1]
    for idx, linha in enumerate(linhas_matriz):
        linhas.append(" ".join([rotulos[idx], *(str(v) for v in linha)]))
    return linhas


def relatorio_at4(r) -> str:
    """Gera o relatório textual completo da AT4."""
    titulo = _TITULOS_AT4.get(r.metodo, "ALINHAMENTO")
    linhas: list[str] = [
        _SEP_IGUAL,
        titulo,
        _SEP_IGUAL,
        f"Seq1 original: {r.seq1}",
        f"Seq2 original: {r.seq2}",
    ]
    if _eh_int(r.match) and _eh_int(r.mismatch) and _eh_int(r.gap):
        linhas.append(_linha_parametros_at4(r.match, r.mismatch, r.gap))

    if not r.ok:
        linhas.append("STATUS: ERRO")
        linhas.append(f"TIPO: {r.resultado}")
        for item in r.erros:
            linhas.append(f"- {item}")
        linhas.append(_SEP_TRACO)
        return "\n".join(linhas) + "\n"

    linhas.extend([
        "STATUS: CORRETO",
        "",
        "MATRIZ DE PONTUAÇÃO",
        *_grade_texto(r.seq1, r.seq2, r.matriz),
        "",
        "MATRIZ DE TRACEBACK",
        *_grade_texto(r.seq1, r.seq2, r.direcoes),
        "",
    ])

    if r.inicio_traceback is None:
        linhas.append(
            "Início do traceback: nenhum (sem região de similaridade positiva)"
        )
    else:
        ini_i, ini_j = r.inicio_traceback
        caminho_str = " ".join(f"({ci},{cj})" for ci, cj in r.caminho)
        linhas.extend([
            f"Início do traceback: ({ini_i},{ini_j})",
            f"Caminho: {caminho_str}",
            "",
            "Seq1: " + " ".join(r.alinhado1),
            ("      " + " ".join(r.marcadores)).rstrip(),
            "Seq2: " + " ".join(r.alinhado2),
        ])

    linhas.extend([
        f"Score: {r.score}",
        f"Matches: {r.matches}   Mismatches: {r.mismatches}   Gaps: {r.gaps}   Tamanho: {r.tamanho}",
        _SEP_TRACO,
    ])
    return "\n".join(linhas) + "\n"


def texto_comparacao(local, global_) -> str:
    """Gera o resumo comparativo entre alinhamento local e global (AT4 both)."""
    linhas = [
        "COMPARAÇÃO LOCAL × GLOBAL",
        f"Seq1 original: {local.seq1}",
        f"Seq2 original: {local.seq2}",
        _linha_parametros_at4(local.match, local.mismatch, local.gap),
        (
            f"LOCAL: score={local.score} tamanho={local.tamanho} "
            f"matches={local.matches} mismatches={local.mismatches} gaps={local.gaps}"
        ),
        (
            f"GLOBAL: score={global_.score} tamanho={global_.tamanho} "
            f"matches={global_.matches} mismatches={global_.mismatches} gaps={global_.gaps}"
        ),
    ]
    return "\n".join(linhas) + "\n"
