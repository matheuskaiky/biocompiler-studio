"""Orquestrador do laboratório completo: AT1→AT2→AT3 em dois DNAs + AT4 nos originais."""

from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.at4 import alinhar_dna
from biocompiler.modelos import CadeiaFluxo, ResultadoFluxo


def _executar_cadeia(origem: str, dna: str) -> CadeiaFluxo:
    r1 = transcrever_dna(dna)
    r2 = maturar_pre_mrna(r1.pre_mrna) if r1.ok else None
    r3 = traduzir_mrna(r2.mrna_maduro) if r2 is not None and r2.ok else None

    if not r1.ok:
        falha = "AT1"
    elif not r2.ok:
        falha = "AT2"
    elif not r3.ok:
        falha = "AT3"
    else:
        falha = None

    return CadeiaFluxo(
        origem=origem,
        dna=dna,
        at1=r1,
        at2=r2,
        at3=r3,
        ok=falha is None,
        etapa_falha=falha,
    )


def executar_fluxo(
    seq1: str,
    seq2: str,
    metodo: str = "both",
    match: int = 2,
    mismatch: int = -1,
    gap: int = -2,
) -> ResultadoFluxo:
    """Executa o fluxo integrado AT1→AT2→AT3 nas duas amostras e AT4 nos DNAs originais."""
    metodos = ("local", "global") if metodo == "both" else (metodo,)
    alinhamentos = tuple(
        alinhar_dna(seq1, seq2, m, match, mismatch, gap) for m in metodos
    )
    cadeia1 = _executar_cadeia("Seq1", seq1)
    cadeia2 = _executar_cadeia("Seq2", seq2)
    ok = cadeia1.ok and cadeia2.ok and all(r.ok for r in alinhamentos)
    return ResultadoFluxo(
        seq1=cadeia1,
        seq2=cadeia2,
        alinhamentos=alinhamentos,
        ok=ok,
    )
