"""AT2 — BioCompiler 2.0: splicing e maturação de pré-mRNA em mRNA maduro (função pura)."""

from biocompiler.modelos import Evento, Intron, ResultadoAT2

_BASES_VALIDAS = frozenset(("A", "U", "C", "G"))
_CAP = "m7Gppp"
_TAMANHO_CAUDA = 100


def _resultado_erro(
    sequencia: str,
    resultado: str,
    bases_invalidas: tuple[tuple[int, str], ...],
    sitios_gu: tuple[int, ...],
    sitios_ag: tuple[int, ...],
    eventos: tuple[Evento, ...],
) -> ResultadoAT2:
    return ResultadoAT2(
        sequencia=sequencia,
        ok=False,
        status="ERRO",
        resultado=resultado,
        mrna_maduro=None,
        rna_processado=None,
        cap=None,
        cauda_adicionada=None,
        bases_invalidas=bases_invalidas,
        sitios_gu=sitios_gu,
        sitios_ag=sitios_ag,
        introns=(),
        eventos=eventos,
    )


def _classificar_sem_intron(gus: tuple[int, ...], ags: tuple[int, ...]) -> str:
    if gus and ags and ags[-1] >= gus[0] + 2:
        return "BUG - branch point"
    if ags:
        return "BUG - sítio 5' ausente"
    if gus:
        return "BUG - sítio 3' ausente"
    return "BUG - íntron ausente"


def maturar_pre_mrna(sequencia: str) -> ResultadoAT2:
    """Valida pré-mRNA, remove íntrons não sobrepostos e adiciona CAP e cauda poli-A."""
    if sequencia == "":
        rotulo = "BUG - entrada vazia"
        return _resultado_erro(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=(),
            sitios_gu=(),
            sitios_ag=(),
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
        return _resultado_erro(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=invalidas,
            sitios_gu=(),
            sitios_ag=(),
            eventos=eventos,
        )

    eventos: list[Evento] = [Evento("BASES_VALIDADAS", None, "")]

    n = len(sequencia)
    gus = tuple(i for i in range(n - 1) if sequencia[i : i + 2] == "GU")
    ags = tuple(i for i in range(n - 1) if sequencia[i : i + 2] == "AG")

    for g in gus:
        eventos.append(Evento("GU_CANDIDATO", g, "GU"))
    for j in ags:
        eventos.append(Evento("AG_CANDIDATO", j, "AG"))

    # Para cada AG em j, o maior k elegível (10 <= j - k - 1 <= 30) depende só de j.
    ags_com_branch: list[tuple[int, int]] = []
    for j in ags:
        if j >= 11:
            k = sequencia.rfind("A", max(0, j - 31), j - 10)
            if k != -1:
                ags_com_branch.append((j, k))

    introns: list[Intron] = []
    g_idx = 0
    ag_start_idx = 0
    num_gus = len(gus)
    num_ags_branch = len(ags_com_branch)

    while g_idx < num_gus:
        g = gus[g_idx]
        while ag_start_idx < num_ags_branch and ags_com_branch[ag_start_idx][0] < g + 2:
            ag_start_idx += 1

        escolhido: Intron | None = None
        for idx in range(ag_start_idx, num_ags_branch):
            j, k = ags_com_branch[idx]
            if k >= g + 2:
                escolhido = Intron(g, k, j)
                break

        if escolhido is not None:
            introns.append(escolhido)
            eventos.append(
                Evento(
                    "INTRON_SELECIONADO",
                    g,
                    sequencia[g : escolhido.posicao_ag + 2],
                )
            )
            eventos.append(Evento("BRANCH_POINT", escolhido.posicao_branch, "A"))
            cursor = escolhido.posicao_ag + 2
            while g_idx < num_gus and gus[g_idx] < cursor:
                g_idx += 1
        else:
            g_idx += 1

    if not introns:
        rotulo = _classificar_sem_intron(gus, ags)
        eventos.append(Evento("RESULTADO", None, rotulo))
        return _resultado_erro(
            sequencia=sequencia,
            resultado=rotulo,
            bases_invalidas=(),
            sitios_gu=gus,
            sitios_ag=ags,
            eventos=tuple(eventos),
        )

    partes: list[str] = []
    pos = 0
    for intr in introns:
        partes.append(sequencia[pos : intr.posicao_gu])
        pos = intr.posicao_ag + 2
    partes.append(sequencia[pos:])
    rna_processado = "".join(partes)

    cauda = "A" * _TAMANHO_CAUDA
    mrna_maduro = _CAP + rna_processado + cauda

    eventos.append(Evento("EXONS_UNIDOS", None, rna_processado))
    eventos.append(Evento("CAP_ADICIONADA", None, _CAP))
    eventos.append(Evento("POLIA_ADICIONADA", None, str(_TAMANHO_CAUDA)))
    eventos.append(Evento("RESULTADO", None, "CORRETO"))

    return ResultadoAT2(
        sequencia=sequencia,
        ok=True,
        status="OK",
        resultado="CORRETO",
        mrna_maduro=mrna_maduro,
        rna_processado=rna_processado,
        cap=_CAP,
        cauda_adicionada=cauda,
        bases_invalidas=(),
        sitios_gu=gus,
        sitios_ag=ags,
        introns=tuple(introns),
        eventos=tuple(eventos),
    )
