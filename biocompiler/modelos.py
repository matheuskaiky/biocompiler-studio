"""Modelos estruturados e imutáveis compartilhados entre núcleo, serviços e interfaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Evento:
    """Evento estruturado emitido durante a execução passo a passo de um algoritmo."""

    tipo: str
    posicao: int | None
    detalhe: str


@dataclass(frozen=True)
class ResultadoAT1:
    """Resultado estruturado da transcrição DNA → pré-mRNA (AT1)."""

    sequencia: str
    ok: bool
    status: str
    resultado: str
    pre_mrna: str | None
    bases_invalidas: tuple[tuple[int, str], ...]
    posicao_start: int | None
    posicao_stop: int | None
    codon_stop: str | None
    stops_em_fase: tuple[int, ...]
    stops_fora_de_fase: tuple[int, ...]
    codons: tuple[str, ...]
    utr5: str
    utr3: str
    resto_quadro: int | None
    eventos: tuple[Evento, ...]
