"""Serviços de aplicação compartilhados entre CLI e interface web."""

import importlib

_ATIVIDADES = {
    "at1": ("biocompiler.core.at1", "transcrever_dna"),
    "at2": ("biocompiler.core.at2", "maturar_pre_mrna"),
    "at3": ("biocompiler.core.at3", "traduzir_mrna"),
    "at4": ("biocompiler.core.at4", "alinhar_dna"),
    "all": ("biocompiler.core.pipeline", "executar_fluxo"),
}


def carregar_atividade(nome: str):
    """Importa sob demanda apenas o módulo da atividade solicitada e retorna sua função pública."""
    if nome not in _ATIVIDADES:
        raise ValueError(f"atividade desconhecida: {nome!r}")
    modulo_nome, funcao_nome = _ATIVIDADES[nome]
    modulo = importlib.import_module(modulo_nome)
    return getattr(modulo, funcao_nome)


def processar_lote(atividade: str, sequencias):
    """Executa AT1, AT2 ou AT3 sobre uma coleção de sequências, preservando a ordem."""
    if atividade not in ("at1", "at2", "at3"):
        raise ValueError(f"atividade inválida para lote: {atividade!r}")
    fn = carregar_atividade(atividade)
    return tuple(fn(seq) for seq in sequencias)


def alinhar_par(
    seq1: str,
    seq2: str,
    metodo: str,
    match: int,
    mismatch: int,
    gap: int,
):
    """Executa AT4 para um par de sequências ('both' retorna (local, global))."""
    fn = carregar_atividade("at4")
    if metodo == "both":
        return (
            fn(seq1, seq2, "local", match, mismatch, gap),
            fn(seq1, seq2, "global", match, mismatch, gap),
        )
    return (fn(seq1, seq2, metodo, match, mismatch, gap),)
