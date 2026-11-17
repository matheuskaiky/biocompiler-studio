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
