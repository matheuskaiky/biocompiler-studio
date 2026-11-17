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


@dataclass(frozen=True)
class Intron:
    """Íntron removido durante a maturação de pré-mRNA (AT2)."""

    posicao_gu: int
    posicao_branch: int
    posicao_ag: int


@dataclass(frozen=True)
class ResultadoAT2:
    """Resultado estruturado da maturação pré-mRNA → mRNA maduro (AT2)."""

    sequencia: str
    ok: bool
    status: str
    resultado: str
    mrna_maduro: str | None
    rna_processado: str | None
    cap: str | None
    cauda_adicionada: str | None
    bases_invalidas: tuple[tuple[int, str], ...]
    sitios_gu: tuple[int, ...]
    sitios_ag: tuple[int, ...]
    introns: tuple[Intron, ...]
    eventos: tuple[Evento, ...]


@dataclass(frozen=True)
class ResultadoAT3:
    """Resultado estruturado da tradução mRNA maduro → proteína (AT3)."""

    sequencia: str
    ok: bool
    status: str
    resultado: str
    proteina: str | None
    aminoacidos: tuple[str, ...]
    cap_ok: bool
    tamanho_cauda: int | None
    regiao_transcrita: str | None
    bases_invalidas: tuple[tuple[int, str], ...]
    posicao_start: int | None
    posicao_stop: int | None
    codon_stop: str | None
    stops_fora_de_fase: tuple[int, ...]
    codons: tuple[str, ...]
    utr5: str
    utr3: str
    eventos: tuple[Evento, ...]


@dataclass(frozen=True)
class ResultadoAT4:
    """Resultado estruturado do alinhamento de DNA local/global (AT4)."""

    seq1: str
    seq2: str
    metodo: str
    match: int | None
    mismatch: int | None
    gap: int | None
    ok: bool
    status: str
    resultado: str
    erros: tuple[str, ...]
    matriz: tuple[tuple[int, ...], ...] | None
    direcoes: tuple[tuple[str, ...], ...] | None
    inicio_traceback: tuple[int, int] | None
    caminho: tuple[tuple[int, int], ...]
    alinhado1: str
    marcadores: str
    alinhado2: str
    score: int | None
    matches: int
    mismatches: int
    gaps: int
    tamanho: int
    observacao: str
    eventos: tuple[Evento, ...]
