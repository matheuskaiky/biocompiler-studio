"""AT3 — Ribossomo: tradução de mRNA maduro em proteína (função pura)."""

from biocompiler.core.genetic_code import CODIGO_GENETICO, CODONS_STOP
from biocompiler.modelos import Evento, ResultadoAT3

_BASES_VALIDAS = frozenset(("A", "U", "C", "G"))
_CAP = "m7Gppp"
_TAMANHO_CAP = len(_CAP)
_TAMANHO_CAUDA_ESPERADA = 100


def _resultado_inicial_erro(
    sequencia: str,
    resultado: str,
    cap_ok: bool,
    tamanho_cauda: int | None,
    regiao_transcrita: str | None,
    bases_invalidas: tuple[tuple[int, str], ...],
    eventos: tuple[Evento, ...],
) -> ResultadoAT3:
    return ResultadoAT3(
        sequencia=sequencia,
        ok=False,
        status="ERRO",
        resultado=resultado,
        proteina=None,
        aminoacidos=(),
        cap_ok=cap_ok,
        tamanho_cauda=tamanho_cauda,
        regiao_transcrita=regiao_transcrita,
        bases_invalidas=bases_invalidas,
        posicao_start=None,
        posicao_stop=None,
        codon_stop=None,
        stops_fora_de_fase=(),
        codons=(),
        utr5="",
        utr3="",
        eventos=eventos,
    )


def traduzir_mrna(sequencia: str) -> ResultadoAT3:
    """Valida CAP 5', cauda poli-A, bases e traduz o mRNA maduro a partir do 1º AUG."""
    if sequencia == "":
        rotulo = "BUG - entrada vazia"
        return _resultado_inicial_erro(
            sequencia=sequencia,
            resultado=rotulo,
            cap_ok=False,
            tamanho_cauda=None,
            regiao_transcrita=None,
            bases_invalidas=(),
            eventos=(Evento("RESULTADO", None, rotulo),),
        )

    cap_ok = sequencia.startswith(_CAP)
    if not cap_ok:
        rotulo = "BUG - CAP 5'"
        return _resultado_inicial_erro(
            sequencia=sequencia,
            resultado=rotulo,
            cap_ok=False,
            tamanho_cauda=None,
            regiao_transcrita=None,
            bases_invalidas=(),
            eventos=(Evento("RESULTADO", None, rotulo),),
        )

    corpo = sequencia[_TAMANHO_CAP:]
    tamanho_cauda = len(corpo) - len(corpo.rstrip("A"))
    if tamanho_cauda != _TAMANHO_CAUDA_ESPERADA:
        rotulo = "BUG - cauda poli-A"
        return _resultado_inicial_erro(
            sequencia=sequencia,
            resultado=rotulo,
            cap_ok=True,
            tamanho_cauda=tamanho_cauda,
            regiao_transcrita=None,
            bases_invalidas=(),
            eventos=(
                Evento("CAP_VALIDADA", None, _CAP),
                Evento("RESULTADO", None, rotulo),
            ),
        )

    regiao = corpo[:-_TAMANHO_CAUDA_ESPERADA]
    invalidas = tuple(
        (i, base) for i, base in enumerate(regiao) if base not in _BASES_VALIDAS
    )
    if invalidas:
        rotulo = "BUG - base inválida"
        eventos = (
            Evento("CAP_VALIDADA", None, _CAP),
            Evento("POLIA_VALIDADA", None, str(_TAMANHO_CAUDA_ESPERADA)),
            *(Evento("BASE_INVALIDA", pos, base) for pos, base in invalidas),
            Evento("RESULTADO", None, rotulo),
        )
        return _resultado_inicial_erro(
            sequencia=sequencia,
            resultado=rotulo,
            cap_ok=True,
            tamanho_cauda=tamanho_cauda,
            regiao_transcrita=regiao,
            bases_invalidas=invalidas,
            eventos=eventos,
        )

    eventos: list[Evento] = [
        Evento("CAP_VALIDADA", None, _CAP),
        Evento("POLIA_VALIDADA", None, str(_TAMANHO_CAUDA_ESPERADA)),
        Evento("BASES_VALIDADAS", None, ""),
    ]

    start = regiao.find("AUG")
    if start == -1:
        rotulo = "BUG - START ausente"
        eventos.append(Evento("RESULTADO", None, rotulo))
        return _resultado_inicial_erro(
            sequencia=sequencia,
            resultado=rotulo,
            cap_ok=True,
            tamanho_cauda=tamanho_cauda,
            regiao_transcrita=regiao,
            bases_invalidas=(),
            eventos=tuple(eventos),
        )

    eventos.append(Evento("AUG_ENCONTRADO", start, "AUG"))

    n = len(regiao)
    codons: list[str] = []
    aminoacidos: list[str] = []
    posicao_stop: int | None = None
    codon_stop: str | None = None

    for i in range(start, n - 2, 3):
        trinca = regiao[i : i + 3]
        codons.append(trinca)
        if trinca in CODONS_STOP:
            posicao_stop = i
            codon_stop = trinca
            eventos.append(Evento("STOP_ENCONTRADO", i, trinca))
            break
        aa = CODIGO_GENETICO[trinca]
        aminoacidos.append(aa)
        eventos.append(Evento("CODON_TRADUZIDO", i, f"{trinca}:{aa}"))

    stops_fora_de_fase: list[int] = []
    for p in range(start + 1, n - 2):
        if (p - start) % 3 != 0:
            trinca = regiao[p : p + 3]
            if trinca in CODONS_STOP:
                stops_fora_de_fase.append(p)
                eventos.append(Evento("STOP_FORA_DE_FASE", p, trinca))

    utr5 = regiao[:start]
    if posicao_stop is not None:
        rotulo = "CORRETO"
        proteina = "-".join(aminoacidos)
        utr3 = regiao[posicao_stop + 3 :]
        eventos.append(Evento("PROTEINA_GERADA", None, proteina))
        eventos.append(Evento("RESULTADO", None, rotulo))
        return ResultadoAT3(
            sequencia=sequencia,
            ok=True,
            status="OK",
            resultado=rotulo,
            proteina=proteina,
            aminoacidos=tuple(aminoacidos),
            cap_ok=True,
            tamanho_cauda=tamanho_cauda,
            regiao_transcrita=regiao,
            bases_invalidas=(),
            posicao_start=start,
            posicao_stop=posicao_stop,
            codon_stop=codon_stop,
            stops_fora_de_fase=tuple(stops_fora_de_fase),
            codons=tuple(codons),
            utr5=utr5,
            utr3=utr3,
            eventos=tuple(eventos),
        )

    rotulo = (
        "BUG - quadro de leitura"
        if any((p - start) % 3 == 1 for p in stops_fora_de_fase)
        else "BUG - STOP ausente"
    )
    eventos.append(Evento("RESULTADO", None, rotulo))
    return ResultadoAT3(
        sequencia=sequencia,
        ok=False,
        status="ERRO",
        resultado=rotulo,
        proteina=None,
        aminoacidos=(),
        cap_ok=True,
        tamanho_cauda=tamanho_cauda,
        regiao_transcrita=regiao,
        bases_invalidas=(),
        posicao_start=start,
        posicao_stop=None,
        codon_stop=None,
        stops_fora_de_fase=tuple(stops_fora_de_fase),
        codons=tuple(codons),
        utr5=utr5,
        utr3="",
        eventos=tuple(eventos),
    )
