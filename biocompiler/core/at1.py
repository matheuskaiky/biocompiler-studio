"""AT1 — BioCompiler 1.0: transcrição de DNA em pré-mRNA (função pura)."""

from biocompiler.modelos import Evento, ResultadoAT1

_BASES_VALIDAS = frozenset(("A", "T", "C", "G"))
_STOPS = frozenset(("TAA", "TAG", "TGA"))


def _resultado_sem_leitura(
    sequencia: str,
    resultado: str,
    bases_invalidas: tuple[tuple[int, str], ...],
    eventos: tuple[Evento, ...],
) -> ResultadoAT1:
    return ResultadoAT1(
        sequencia=sequencia,
        ok=False,
        status="ERRO",
        resultado=resultado,
        pre_mrna=None,
        bases_invalidas=bases_invalidas,
        posicao_start=None,
        posicao_stop=None,
        codon_stop=None,
        stops_em_fase=(),
        stops_fora_de_fase=(),
        codons=(),
        utr5="",
        utr3="",
        resto_quadro=None,
        eventos=eventos,
    )


def transcrever_dna(sequencia: str) -> ResultadoAT1:
    """Valida uma fita codificante de DNA e transcreve para pré-mRNA conforme SPEC §4.1/§5.1."""
    if sequencia == "":
        rotulo = "BUG - entrada vazia"
        return _resultado_sem_leitura(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=(),
            eventos=(Evento("RESULTADO", None, rotulo),),
        )

    invalidas = tuple(
        (i, base) for i, base in enumerate(sequencia) if base not in _BASES_VALIDAS
    )
    if invalidas:
        rotulo = "BUG - base inválida"
        eventos = tuple(Evento("BASE_INVALIDA", pos, base) for pos, base in invalidas) + (
            Evento("RESULTADO", None, rotulo),
        )
        return _resultado_sem_leitura(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=invalidas,
            eventos=eventos,
        )

    eventos: list[Evento] = [Evento("BASES_VALIDADAS", None, "")]

    start = sequencia.find("ATG")
    if start == -1:
        rotulo = "BUG - START ausente"
        eventos.append(Evento("RESULTADO", None, rotulo))
        return _resultado_sem_leitura(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=(),
            eventos=tuple(eventos),
        )

    eventos.append(Evento("START_ENCONTRADO", start, "ATG"))

    n = len(sequencia)
    stops_em_fase: list[int] = []
    codons_ate_stop: list[str] = []
    encontrou_primeiro_stop = False

    for i in range(start, n - 2, 3):
        trinca = sequencia[i : i + 3]
        eventos.append(Evento("CODON_LIDO", i, trinca))
        if not encontrou_primeiro_stop:
            codons_ate_stop.append(trinca)
        if trinca in _STOPS:
            stops_em_fase.append(i)
            eventos.append(Evento("STOP_EM_FASE", i, trinca))
            encontrou_primeiro_stop = True

    stops_fora_de_fase: list[int] = []
    for j in range(start + 1, n - 2):
        if (j - start) % 3 != 0:
            trinca = sequencia[j : j + 3]
            if trinca in _STOPS:
                stops_fora_de_fase.append(j)
                eventos.append(Evento("STOP_FORA_DE_FASE", j, trinca))

    resto_quadro = (n - start) % 3

    if len(stops_em_fase) >= 2:
        ok = False
        status = "ERRO"
        resultado = "BUG - nonsense / STOP prematuro"
        pre_mrna = None
    elif len(stops_em_fase) == 1:
        ok = True
        status = "OK"
        resultado = "CORRETO"
        pre_mrna = sequencia.replace("T", "U")
        eventos.append(Evento("T_PARA_U", None, pre_mrna))
    elif resto_quadro != 0:
        ok = False
        status = "ERRO"
        resultado = "BUG - frameshift"
        pre_mrna = None
    else:
        ok = False
        status = "ERRO"
        resultado = "BUG - STOP ausente"
        pre_mrna = None

    eventos.append(Evento("RESULTADO", None, resultado))

    posicao_stop = stops_em_fase[0] if stops_em_fase else None
    codon_stop = sequencia[posicao_stop : posicao_stop + 3] if posicao_stop is not None else None
    utr5 = sequencia[:start]
    utr3 = sequencia[posicao_stop + 3 :] if posicao_stop is not None else ""

    return ResultadoAT1(
        sequencia=sequencia,
        ok=ok,
        status=status,
        resultado=resultado,
        pre_mrna=pre_mrna,
        bases_invalidas=(),
        posicao_start=start,
        posicao_stop=posicao_stop,
        codon_stop=codon_stop,
        stops_em_fase=tuple(stops_em_fase),
        stops_fora_de_fase=tuple(stops_fora_de_fase),
        codons=tuple(codons_ate_stop),
        utr5=utr5,
        utr3=utr3,
        resto_quadro=resto_quadro,
        eventos=tuple(eventos),
    )
