"""AT4 — Alinhamento de duas sequências de DNA: Smith–Waterman (local) e Needleman–Wunsch (global)."""

from biocompiler.modelos import Evento, ResultadoAT4

_NORM = str.maketrans("acgt", "ACGT")
_BASES_VALIDAS = frozenset(("A", "C", "G", "T"))
_LIMITE_TAMANHO = 2000


def _eh_int(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _resultado_erro(
    seq1: str,
    seq2: str,
    metodo: str,
    match: int | None,
    mismatch: int | None,
    gap: int | None,
    rotulo: str,
    erros: tuple[str, ...],
) -> ResultadoAT4:
    return ResultadoAT4(
        seq1=seq1,
        seq2=seq2,
        metodo=metodo,
        match=match,
        mismatch=mismatch,
        gap=gap,
        ok=False,
        status="ERRO",
        resultado=rotulo,
        erros=erros,
        matriz=None,
        direcoes=None,
        inicio_traceback=None,
        caminho=(),
        alinhado1="",
        marcadores="",
        alinhado2="",
        score=None,
        matches=0,
        mismatches=0,
        gaps=0,
        tamanho=0,
        observacao="",
        eventos=(Evento("RESULTADO", None, rotulo),),
    )


def alinhar_dna(
    seq1: str,
    seq2: str,
    metodo: str,
    match: int,
    mismatch: int,
    gap: int,
) -> ResultadoAT4:
    """Executa alinhamento local (Smith–Waterman) ou global (Needleman–Wunsch) em dois DNAs."""
    s1 = seq1.translate(_NORM)
    s2 = seq2.translate(_NORM)

    match_val = match if _eh_int(match) else None
    mismatch_val = mismatch if _eh_int(mismatch) else None
    gap_val = gap if _eh_int(gap) else None

    if metodo not in ("local", "global"):
        return _resultado_erro(
            s1, s2, metodo, match_val, mismatch_val, gap_val,
            "ERRO - método inválido",
            (f"método inválido: {metodo!r} (use 'local' ou 'global')",),
        )

    erros_num: list[str] = []
    for nome, valor in (("match", match), ("mismatch", mismatch), ("gap", gap)):
        if not _eh_int(valor):
            erros_num.append(f"{nome} não numérico: {valor!r}")
    if erros_num:
        return _resultado_erro(
            s1, s2, metodo, match_val, mismatch_val, gap_val,
            "ERRO - parâmetro não numérico",
            tuple(erros_num),
        )

    erros_vazias: list[str] = []
    if s1 == "":
        erros_vazias.append("Seq1 vazia")
    if s2 == "":
        erros_vazias.append("Seq2 vazia")
    if erros_vazias:
        return _resultado_erro(
            s1, s2, metodo, match_val, mismatch_val, gap_val,
            "ERRO - sequência vazia",
            tuple(erros_vazias),
        )

    erros_bases: list[str] = []
    for idx, ch in enumerate(s1, start=1):
        if ch not in _BASES_VALIDAS:
            erros_bases.append(f"Seq1, posição {idx}: {ch}")
    for idx, ch in enumerate(s2, start=1):
        if ch not in _BASES_VALIDAS:
            erros_bases.append(f"Seq2, posição {idx}: {ch}")
    if erros_bases:
        return _resultado_erro(
            s1, s2, metodo, match_val, mismatch_val, gap_val,
            "ERRO - base inválida",
            tuple(erros_bases),
        )

    erros_longas: list[str] = []
    if len(s1) > _LIMITE_TAMANHO:
        erros_longas.append(f"Seq1 com {len(s1)} bases (limite {_LIMITE_TAMANHO})")
    if len(s2) > _LIMITE_TAMANHO:
        erros_longas.append(f"Seq2 com {len(s2)} bases (limite {_LIMITE_TAMANHO})")
    if erros_longas:
        return _resultado_erro(
            s1, s2, metodo, match_val, mismatch_val, gap_val,
            "ERRO - sequência muito longa",
            tuple(erros_longas),
        )

    m, n = len(s1), len(s2)
    is_local = metodo == "local"

    F = [[0] * (n + 1) for _ in range(m + 1)]
    D = [["·"] * (n + 1) for _ in range(m + 1)]

    if not is_local:
        for i in range(1, m + 1):
            F[i][0] = i * gap
            D[i][0] = "↑"
        for j in range(1, n + 1):
            F[0][j] = j * gap
            D[0][j] = "←"

    max_val = 0
    max_pos: tuple[int, int] | None = None

    for i in range(1, m + 1):
        c1 = s1[i - 1]
        f_prev = F[i - 1]
        f_curr = F[i]
        d_curr = D[i]
        for j in range(1, n + 1):
            diag = f_prev[j - 1] + (match if c1 == s2[j - 1] else mismatch)
            cima = f_prev[j] + gap
            esq = f_curr[j - 1] + gap

            if diag >= cima and diag >= esq:
                melhor = diag
                direcao = "↖"
            elif cima >= esq:
                melhor = cima
                direcao = "↑"
            else:
                melhor = esq
                direcao = "←"

            if is_local and melhor <= 0:
                f_curr[j] = 0
                d_curr[j] = "·"
            else:
                f_curr[j] = melhor
                d_curr[j] = direcao
                if is_local and melhor > max_val:
                    max_val = melhor
                    max_pos = (i, j)

    eventos: list[Evento] = [
        Evento("BORDA_INICIALIZADA", None, metodo),
        Evento("MATRIZ_PREENCHIDA", None, f"{m + 1}x{n + 1}"),
    ]

    if is_local:
        score = max_val
        inicio = max_pos
    else:
        score = F[m][n]
        inicio = (m, n)

    if inicio is None:
        caminho_tuple: tuple[tuple[int, int], ...] = ()
        alinhado1 = ""
        marcadores = ""
        alinhado2 = ""
        matches = 0
        mismatches = 0
        gaps = 0
        tamanho = 0
        observacao = "sem região de similaridade positiva"
    else:
        eventos.append(Evento("INICIO_TRACEBACK", None, f"{inicio[0]},{inicio[1]}"))
        caminho: list[tuple[int, int]] = []
        a1_rev: list[str] = []
        a2_rev: list[str] = []
        marc_rev: list[str] = []
        matches = 0
        mismatches = 0
        gaps = 0

        i, j = inicio
        while True:
            caminho.append((i, j))
            direcao = D[i][j]
            eventos.append(Evento("TRACEBACK_PASSO", None, f"{i},{j},{direcao}"))
            if direcao == "·":
                break
            if direcao == "↖":
                b1 = s1[i - 1]
                b2 = s2[j - 1]
                a1_rev.append(b1)
                a2_rev.append(b2)
                if b1 == b2:
                    marc_rev.append("|")
                    matches += 1
                else:
                    marc_rev.append(".")
                    mismatches += 1
                i -= 1
                j -= 1
            elif direcao == "↑":
                a1_rev.append(s1[i - 1])
                a2_rev.append("-")
                marc_rev.append(" ")
                gaps += 1
                i -= 1
            else:
                a1_rev.append("-")
                a2_rev.append(s2[j - 1])
                marc_rev.append(" ")
                gaps += 1
                j -= 1

        caminho_tuple = tuple(caminho)
        alinhado1 = "".join(reversed(a1_rev))
        alinhado2 = "".join(reversed(a2_rev))
        marcadores = "".join(reversed(marc_rev))
        tamanho = len(alinhado1)
        observacao = ""

    eventos.append(Evento("ALINHAMENTO_FINAL", None, str(score)))
    eventos.append(Evento("RESULTADO", None, "CORRETO"))

    return ResultadoAT4(
        seq1=s1,
        seq2=s2,
        metodo=metodo,
        match=match,
        mismatch=mismatch,
        gap=gap,
        ok=True,
        status="OK",
        resultado="CORRETO",
        erros=(),
        matriz=tuple(tuple(linha) for linha in F),
        direcoes=tuple(tuple(linha) for linha in D),
        inicio_traceback=inicio,
        caminho=caminho_tuple,
        alinhado1=alinhado1,
        marcadores=marcadores,
        alinhado2=alinhado2,
        score=score,
        matches=matches,
        mismatches=mismatches,
        gaps=gaps,
        tamanho=tamanho,
        observacao=observacao,
        eventos=tuple(eventos),
    )


def candidatos_celula(
    r: ResultadoAT4,
    i: int,
    j: int,
) -> tuple[tuple[str, int], ...]:
    """Devolve os candidatos da recorrência da célula (i, j) a partir de r.matriz."""
    if not r.ok or r.matriz is None:
        raise ValueError("resultado sem matriz válida")
    m = len(r.seq1)
    n = len(r.seq2)
    if i < 0 or i > m or j < 0 or j > n:
        raise ValueError(f"célula fora da matriz: ({i}, {j})")
    if i == 0 or j == 0:
        return ()

    s = r.match if r.seq1[i - 1] == r.seq2[j - 1] else r.mismatch
    diag = r.matriz[i - 1][j - 1] + s
    cima = r.matriz[i - 1][j] + r.gap
    esq = r.matriz[i][j - 1] + r.gap
    cands: tuple[tuple[str, int], ...] = (
        ("diagonal", diag),
        ("vertical", cima),
        ("horizontal", esq),
    )
    if r.metodo == "local":
        cands = cands + (("zero", 0),)
    return cands
