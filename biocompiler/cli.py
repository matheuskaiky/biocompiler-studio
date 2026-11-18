"""Interface de linha de comando (CLI) do BioCompiler Studio."""

import argparse
import sys
import unittest
from pathlib import Path

from biocompiler import exemplos, exports, io_formats, servicos

_SUBCOMANDOS = (
    ("at1", "AT1 — DNA → pré-mRNA (transcrição)"),
    ("at2", "AT2 — pré-mRNA → mRNA maduro (splicing e maturação)"),
    ("at3", "AT3 — mRNA maduro → proteína (tradução)"),
    ("at4", "AT4 — alinhamento local (Smith–Waterman) e global (Needleman–Wunsch)"),
    ("all", "Laboratório completo: AT1→AT2→AT3 em dois DNAs e AT4 entre eles"),
    ("serve", "Interface web local opcional (requer requirements-web.txt)"),
    ("examples", "Lista exemplos didáticos"),
    ("test", "Executa a suíte unittest do projeto"),
)

_EPILOGO_PADRAO = (
    "Códigos de saída: 0=OK, 1=erro de entrada/argumentos/arquivo, "
    "2=erro biológico/didático, 3=erro interno."
)

_PROMPT_STEP = "[Enter] próximo, p pula, q sai: "
_PROMPT_LOTE = (
    "Cole as sequências (uma por linha) ou informe o caminho de um arquivo .txt; "
    "linha vazia encerra:\n"
)
_PROMPT_MENU = "Escolha a atividade: 1) AT1  2) AT2  3) AT3  4) AT4  (q para sair): "


class _CliParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _erro(mensagem: str) -> int:
    sys.stderr.write(f"biocompiler: {mensagem}\n")
    return 1


def _forcar_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def _parse_int_ou_raw(valor: str):
    try:
        return int(valor)
    except ValueError:
        return valor


def _ler_linha() -> str | None:
    linha = sys.stdin.readline()
    if linha == "":
        return None
    return linha.rstrip("\r\n")


def _perguntar(texto: str) -> str | None:
    sys.stdout.write(texto)
    sys.stdout.flush()
    return _ler_linha()


def _emitir(texto: str, ascii_mode: bool) -> None:
    sys.stdout.write(exports.para_ascii(texto) if ascii_mode else texto)


def _ler_comando_step() -> str:
    resp = _perguntar(_PROMPT_STEP)
    if resp is None:
        return "q"
    return resp


def _gravar_arquivos(arquivos: list[tuple[Path, str]], quiet: bool) -> list[str]:
    gravados: list[str] = []
    for destino, conteudo in arquivos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo.encode("utf-8"))
        gravados.append(str(destino))
        if not quiet:
            sys.stderr.write(f"biocompiler: arquivo gravado: {destino}\n")
    return gravados


def _resolver_destino_lote(
    atividade: str,
    output: str | None,
    out_dir: str | None,
    force: bool,
) -> Path:
    nome_padrao = f"{atividade}_resultados.txt"
    if output is not None:
        destino = Path(output)
        if destino.exists() and not force:
            raise io_formats.ErroEntrada(
                f"arquivo já existe: {output} (use --force para sobrescrever)"
            )
        return destino

    if out_dir is not None:
        destino = Path(out_dir) / nome_padrao
        if destino.exists() and not force:
            raise io_formats.ErroEntrada(
                f"arquivo já existe: {destino} (use --force para sobrescrever)"
            )
        return destino

    pasta_padrao = Path("saidas")
    candidato = pasta_padrao / nome_padrao
    if force or not candidato.exists():
        return candidato
    indice = 2
    while True:
        candidato = pasta_padrao / f"{atividade}_resultados_{indice}.txt"
        if not candidato.exists():
            return candidato
        indice += 1


def _nomes_artefatos_at4(metodo: str) -> list[str]:
    metodos = ["local", "global"] if metodo == "both" else [metodo]
    nomes: list[str] = []
    for m in metodos:
        nomes.extend([
            f"alinhamento_{m}.txt",
            f"matriz_pontuacao_{m}.csv",
            f"matriz_traceback_{m}.csv",
            f"alinhamento_{m}.csv",
        ])
    if metodo == "both":
        nomes.append("comparacao.txt")
    return nomes


def _resolver_pasta_at4(
    metodo: str,
    out_dir: str | None,
    force: bool,
) -> Path:
    nomes = _nomes_artefatos_at4(metodo)
    if out_dir is not None:
        pasta = Path(out_dir)
        for nome in nomes:
            alvo = pasta / nome
            if alvo.exists() and not force:
                raise io_formats.ErroEntrada(
                    f"arquivo já existe: {alvo} (use --force para sobrescrever)"
                )
        return pasta

    base = Path("saidas")
    pasta = base / "at4"
    if force or not any((pasta / nome).exists() for nome in nomes):
        return pasta
    indice = 2
    while True:
        pasta = base / f"at4_{indice}"
        if not any((pasta / nome).exists() for nome in nomes):
            return pasta
        indice += 1


def _validar_flags_apresentacao(args: argparse.Namespace, eh_at4: bool) -> str | None:
    if eh_at4 and args.granularidade is not None and not args.step and not args.explain:
        return "--granularidade exige --step ou --explain"
    if args.step:
        if not sys.stdin.isatty():
            return "--step requer um terminal interativo"
        if args.quiet:
            return "opções incompatíveis: --step e --quiet"
        if args.fast:
            return "opções incompatíveis: --step e --fast"
        if args.explain:
            return "opções incompatíveis: --step e --explain"
        if args.format != "text":
            return f"opções incompatíveis: --step e --format {args.format}"
        if args.input == "-":
            return "--step não pode ser usado com entrada por stdin (--input -)"
    if args.explain and args.format != "text":
        return f"opções incompatíveis: --explain e --format {args.format}"
    if args.ascii and args.format != "text":
        return f"opções incompatíveis: --ascii e --format {args.format}"
    return None


def _ler_lote_interativo() -> list[str]:
    sys.stdout.write(_PROMPT_LOTE)
    sys.stdout.flush()
    linhas: list[str] = []
    while True:
        linha = _ler_linha()
        if linha is None or linha == "":
            break
        linhas.append(linha)

    if not linhas:
        raise io_formats.ErroEntrada("nenhuma sequência na entrada")

    if len(linhas) == 1 and Path(linhas[0]).is_file():
        texto = io_formats.ler_texto(linhas[0])
        registros = io_formats.separar_registros(texto)
        if not registros:
            raise io_formats.ErroEntrada("nenhuma sequência na entrada")
        return registros

    return linhas


def _executar_lote(args: argparse.Namespace) -> int:
    atividade = args.comando
    tem_entrada = args.input is not None or args.seq is not None

    if args.interactive and tem_entrada:
        return _erro("opções incompatíveis: --interactive e entrada informada")
    if args.input is not None and args.seq is not None:
        return _erro("use apenas um entre --input e --seq")

    eh_tty = sys.stdin.isatty()
    if args.interactive and not eh_tty:
        return _erro("--interactive requer um terminal interativo")
    modo_interativo = args.interactive or (not tem_entrada and eh_tty)
    if not tem_entrada and not modo_interativo:
        return _erro("informe --input ou --seq")

    msg_apresentacao = _validar_flags_apresentacao(args, eh_at4=False)
    if msg_apresentacao is not None:
        return _erro(msg_apresentacao)

    if args.output is not None and args.no_save:
        return _erro("opções incompatíveis: --output e --no-save")
    if args.output is not None and args.out_dir is not None:
        return _erro("opções incompatíveis: --output e --out-dir")
    if args.out_dir is not None and args.no_save:
        return _erro("opções incompatíveis: --out-dir e --no-save")

    try:
        if modo_interativo:
            sequencias = _ler_lote_interativo()
        elif args.seq is not None:
            sequencias = [args.seq]
        else:
            texto = io_formats.ler_texto(args.input)
            sequencias = io_formats.separar_registros(texto)
            if not sequencias:
                return _erro("nenhuma sequência na entrada")

        destino = None
        if not args.no_save:
            destino = _resolver_destino_lote(
                atividade, args.output, args.out_dir, args.force
            )
    except io_formats.ErroEntrada as exc:
        return _erro(str(exc))

    resultados = servicos.processar_lote(atividade, sequencias)

    saidas_gravadas: list[str] = []
    if destino is not None:
        conteudo_csv = exports.csv_lote(atividade, resultados)
        try:
            saidas_gravadas = _gravar_arquivos([(destino, conteudo_csv)], args.quiet)
        except OSError as exc:
            return _erro(f"falha ao gravar {destino}: {exc}")

    if args.quiet:
        for idx, res in enumerate(resultados, start=1):
            if not res.ok:
                sys.stderr.write(f"biocompiler: linha {idx}: {res.resultado}\n")
    elif args.format == "json":
        sys.stdout.write(
            exports.json_lote(atividade, sequencias, resultados, saidas_gravadas)
        )
    elif args.format == "csv":
        sys.stdout.write(exports.csv_lote(atividade, resultados))
    elif args.step:
        _emitir(exports.cabecalho_lote(atividade), args.ascii)
        sair_step = False
        for idx, res in enumerate(resultados, start=1):
            _emitir(f"PASSO A PASSO — ENTRADA {idx}\n", args.ascii)
            pular_registro = False
            for linha_p in exports.passos(res):
                _emitir(linha_p + "\n", args.ascii)
                if not sair_step and not pular_registro:
                    cmd_step = _ler_comando_step()
                    if cmd_step == "p":
                        pular_registro = True
                    elif cmd_step == "q":
                        sair_step = True
            _emitir(exports.bloco_lote(atividade, idx, res), args.ascii)
    elif args.explain:
        _emitir(exports.cabecalho_lote(atividade), args.ascii)
        for idx, res in enumerate(resultados, start=1):
            _emitir(exports.bloco_lote(atividade, idx, res), args.ascii)
            _emitir(f"PASSOS — ENTRADA {idx}\n", args.ascii)
            _emitir(
                "\n".join(exports.passos(res)) + "\n" + "-" * 40 + "\n",
                args.ascii,
            )
    else:
        _emitir(exports.relatorio_lote(atividade, resultados), args.ascii)

    return 0 if all(r.ok for r in resultados) else 2


def _ler_at4_interativo(
    metodo_atual: str,
    match_atual: str,
    mismatch_atual: str,
    gap_atual: str,
) -> tuple[str, str, str, str, str, str]:
    resp1 = _perguntar("Seq1 (ou caminho de arquivo .txt/.fasta): ")
    if resp1 is None:
        raise io_formats.ErroEntrada("entrada interrompida")

    if resp1 != "" and Path(resp1).is_file():
        texto = io_formats.ler_texto(resp1)
        seq1, seq2 = io_formats.ler_par(texto)
    else:
        seq1 = resp1
        resp2 = _perguntar("Seq2: ")
        if resp2 is None:
            raise io_formats.ErroEntrada("entrada interrompida")
        seq2 = resp2

    metodo = metodo_atual
    while True:
        resp_m = _perguntar(f"Método (local/global/both) [{metodo}]: ")
        if resp_m is None:
            raise io_formats.ErroEntrada("entrada interrompida")
        if resp_m == "":
            break
        if resp_m in ("local", "global", "both"):
            metodo = resp_m
            break

    valores = [match_atual, mismatch_atual, gap_atual]
    rotulos = ("Match", "Mismatch", "Gap")
    for idx, (rotulo, atual) in enumerate(zip(rotulos, valores)):
        resp_p = _perguntar(f"{rotulo} [{atual}]: ")
        if resp_p is None:
            raise io_formats.ErroEntrada("entrada interrompida")
        if resp_p != "":
            valores[idx] = resp_p

    return seq1, seq2, metodo, valores[0], valores[1], valores[2]


def _executar_at4(args: argparse.Namespace) -> int:
    has_input = args.input is not None
    has_pair = args.seq1 is not None or args.seq2 is not None
    tem_entrada = has_input or has_pair

    if args.interactive and tem_entrada:
        return _erro("opções incompatíveis: --interactive e entrada informada")
    if has_input and has_pair:
        return _erro("use apenas um entre --input e --seq1/--seq2")
    if (args.seq1 is None) != (args.seq2 is None):
        return _erro("--seq1 e --seq2 devem ser informados juntos")

    eh_tty = sys.stdin.isatty()
    if args.interactive and not eh_tty:
        return _erro("--interactive requer um terminal interativo")
    modo_interativo = args.interactive or (not tem_entrada and eh_tty)
    if not tem_entrada and not modo_interativo:
        return _erro("informe --input ou --seq1 e --seq2")

    msg_apresentacao = _validar_flags_apresentacao(args, eh_at4=True)
    if msg_apresentacao is not None:
        return _erro(msg_apresentacao)

    if args.out_dir is not None and args.no_save:
        return _erro("opções incompatíveis: --out-dir e --no-save")

    metodo = args.method
    match_raw = args.match
    mismatch_raw = args.mismatch
    gap_raw = args.gap

    try:
        if modo_interativo:
            seq1, seq2, metodo, match_raw, mismatch_raw, gap_raw = (
                _ler_at4_interativo(metodo, match_raw, mismatch_raw, gap_raw)
            )
        elif args.seq1 is not None:
            seq1, seq2 = args.seq1, args.seq2
        else:
            texto = io_formats.ler_texto(args.input)
            seq1, seq2 = io_formats.ler_par(texto)

        pasta_destino = None
        if not args.no_save:
            pasta_destino = _resolver_pasta_at4(metodo, args.out_dir, args.force)
    except io_formats.ErroEntrada as exc:
        return _erro(str(exc))

    match = _parse_int_ou_raw(match_raw)
    mismatch = _parse_int_ou_raw(mismatch_raw)
    gap = _parse_int_ou_raw(gap_raw)

    resultados = servicos.alinhar_par(seq1, seq2, metodo, match, mismatch, gap)
    todos_ok = all(r.ok for r in resultados)

    saidas_gravadas: list[str] = []
    if pasta_destino is not None and todos_ok:
        delimitador = "," if args.delimiter == "comma" else ";"
        arquivos: list[tuple[Path, str]] = []
        for r in resultados:
            m = r.metodo
            arquivos.extend([
                (pasta_destino / f"alinhamento_{m}.txt", exports.relatorio_at4(r)),
                (
                    pasta_destino / f"matriz_pontuacao_{m}.csv",
                    exports.csv_matriz_pontuacao(r, delimitador),
                ),
                (
                    pasta_destino / f"matriz_traceback_{m}.csv",
                    exports.csv_matriz_traceback(r, delimitador),
                ),
                (
                    pasta_destino / f"alinhamento_{m}.csv",
                    exports.csv_alinhamento(r, delimitador),
                ),
            ])
        if metodo == "both":
            arquivos.append(
                (
                    pasta_destino / "comparacao.txt",
                    exports.texto_comparacao(resultados[0], resultados[1]),
                )
            )
        try:
            saidas_gravadas = _gravar_arquivos(arquivos, args.quiet)
        except OSError as exc:
            return _erro(f"falha ao gravar em {pasta_destino}: {exc}")

    granularidade = args.granularidade or "fase"

    if args.quiet:
        for r in resultados:
            if not r.ok:
                sys.stderr.write(f"biocompiler: {r.metodo}: {r.resultado}\n")
    elif args.format == "json":
        sys.stdout.write(
            exports.json_at4(
                seq1, seq2, match, mismatch, gap, resultados, saidas_gravadas
            )
        )
    elif args.step:
        sair_step = False
        for r in resultados:
            _emitir(f"PASSO A PASSO — {r.metodo.upper()}\n", args.ascii)
            pular_metodo = False
            for linha_p in exports.passos(r, granularidade):
                _emitir(linha_p + "\n", args.ascii)
                if not sair_step and not pular_metodo:
                    cmd_step = _ler_comando_step()
                    if cmd_step == "p":
                        pular_metodo = True
                    elif cmd_step == "q":
                        sair_step = True
            _emitir(exports.relatorio_at4(r), args.ascii)
        if metodo == "both" and todos_ok:
            _emitir(
                exports.texto_comparacao(resultados[0], resultados[1]), args.ascii
            )
    elif args.explain:
        for r in resultados:
            _emitir(exports.relatorio_at4(r), args.ascii)
            _emitir(f"PASSOS — {r.metodo.upper()}\n", args.ascii)
            _emitir(
                "\n".join(exports.passos(r, granularidade))
                + "\n"
                + "-" * 40
                + "\n",
                args.ascii,
            )
        if metodo == "both" and todos_ok:
            _emitir(
                exports.texto_comparacao(resultados[0], resultados[1]), args.ascii
            )
    else:
        partes = [exports.relatorio_at4(r) for r in resultados]
        if metodo == "both" and todos_ok:
            partes.append(exports.texto_comparacao(resultados[0], resultados[1]))
        _emitir("".join(partes), args.ascii)

    return 0 if todos_ok else 2


def _artefatos_at4_para_gravar(
    pasta_destino: Path,
    resultados,
    metodo: str,
    delimitador: str,
    incluir_comparacao: bool,
) -> list[tuple[Path, str]]:
    arquivos: list[tuple[Path, str]] = []
    for r in resultados:
        if not r.ok:
            continue
        m = r.metodo
        arquivos.extend([
            (pasta_destino / f"alinhamento_{m}.txt", exports.relatorio_at4(r)),
            (
                pasta_destino / f"matriz_pontuacao_{m}.csv",
                exports.csv_matriz_pontuacao(r, delimitador),
            ),
            (
                pasta_destino / f"matriz_traceback_{m}.csv",
                exports.csv_matriz_traceback(r, delimitador),
            ),
            (
                pasta_destino / f"alinhamento_{m}.csv",
                exports.csv_alinhamento(r, delimitador),
            ),
        ])
    if incluir_comparacao and metodo == "both" and len(resultados) == 2 and all(
        r.ok for r in resultados
    ):
        arquivos.append(
            (
                pasta_destino / "comparacao.txt",
                exports.texto_comparacao(resultados[0], resultados[1]),
            )
        )
    return arquivos


def _resolver_pasta_all(
    metodo: str,
    out_dir: str | None,
    force: bool,
) -> Path:
    nomes = [
        "relatorio_mestre.txt",
        "at1_resultados.txt",
        "at2_resultados.txt",
        "at3_resultados.txt",
        *_nomes_artefatos_at4(metodo),
    ]
    if out_dir is not None:
        pasta = Path(out_dir)
        for nome in nomes:
            alvo = pasta / nome
            if alvo.exists() and not force:
                raise io_formats.ErroEntrada(
                    f"arquivo já existe: {alvo} (use --force para sobrescrever)"
                )
        return pasta

    base = Path("saidas")
    pasta = base / "all"
    if force or not any((pasta / nome).exists() for nome in nomes):
        return pasta
    indice = 2
    while True:
        pasta = base / f"all_{indice}"
        if not any((pasta / nome).exists() for nome in nomes):
            return pasta
        indice += 1


def _executar_all(args: argparse.Namespace) -> int:
    has_input = args.input is not None
    has_pair = args.seq1 is not None or args.seq2 is not None
    if has_input and has_pair:
        return _erro("use apenas um entre --input e --seq1/--seq2")
    if not has_input and not has_pair:
        return _erro("informe --input ou --seq1 e --seq2")
    if (args.seq1 is None) != (args.seq2 is None):
        return _erro("--seq1 e --seq2 devem ser informados juntos")
    if args.out_dir is not None and args.no_save:
        return _erro("opções incompatíveis: --out-dir e --no-save")
    if args.ascii and args.format != "text":
        return _erro(f"opções incompatíveis: --ascii e --format {args.format}")

    try:
        if args.seq1 is not None:
            seq1, seq2 = args.seq1, args.seq2
        else:
            texto = io_formats.ler_texto(args.input)
            seq1, seq2 = io_formats.ler_par(texto)

        pasta_destino = None
        if not args.no_save:
            pasta_destino = _resolver_pasta_all(args.method, args.out_dir, args.force)
    except io_formats.ErroEntrada as exc:
        return _erro(str(exc))

    match = _parse_int_ou_raw(args.match)
    mismatch = _parse_int_ou_raw(args.mismatch)
    gap = _parse_int_ou_raw(args.gap)

    rf = servicos.fluxo_completo(seq1, seq2, args.method, match, mismatch, gap)

    saidas_gravadas: list[str] = []
    if pasta_destino is not None:
        delimitador = "," if args.delimiter == "comma" else ";"
        arquivos: list[tuple[Path, str]] = [
            (pasta_destino / "relatorio_mestre.txt", exports.relatorio_fluxo(rf)),
            (
                pasta_destino / "at1_resultados.txt",
                exports.csv_lote("at1", [rf.seq1.at1, rf.seq2.at1]),
            ),
            (
                pasta_destino / "at2_resultados.txt",
                exports.csv_lote("at2", [rf.seq1.at2, rf.seq2.at2]),
            ),
            (
                pasta_destino / "at3_resultados.txt",
                exports.csv_lote("at3", [rf.seq1.at3, rf.seq2.at3]),
            ),
            *_artefatos_at4_para_gravar(
                pasta_destino, rf.alinhamentos, args.method, delimitador, True
            ),
        ]
        try:
            saidas_gravadas = _gravar_arquivos(arquivos, args.quiet)
        except OSError as exc:
            return _erro(f"falha ao gravar em {pasta_destino}: {exc}")

    if args.quiet:
        for cadeia in (rf.seq1, rf.seq2):
            if not cadeia.ok:
                etapa = cadeia.etapa_falha
                res_etapa = getattr(cadeia, etapa.lower())
                sys.stderr.write(
                    f"biocompiler: {cadeia.origem}: {etapa}: {res_etapa.resultado}\n"
                )
        for r in rf.alinhamentos:
            if not r.ok:
                sys.stderr.write(f"biocompiler: {r.metodo}: {r.resultado}\n")
    elif args.format == "json":
        sys.stdout.write(
            exports.json_fluxo(
                seq1, seq2, args.method, match, mismatch, gap, rf, saidas_gravadas
            )
        )
    else:
        _emitir(exports.relatorio_fluxo(rf), args.ascii)

    return 0 if rf.ok else 2


def _executar_examples(args: argparse.Namespace) -> int:
    if args.write is None:
        sys.stdout.write(exemplos.texto_exemplos())
        return 0

    pasta = Path(args.write)
    arquivos = [
        (pasta / "at1_exemplos.txt", "\n".join(exemplos.AT1_EXEMPLOS) + "\n"),
        (pasta / "at2_exemplos.txt", "\n".join(exemplos.AT2_EXEMPLOS) + "\n"),
        (pasta / "at3_exemplos.txt", "\n".join(exemplos.AT3_EXEMPLOS) + "\n"),
        (
            pasta / "at4_exemplo.fasta",
            f">Seq1\n{exemplos.AT4_EXEMPLO[0]}\n>Seq2\n{exemplos.AT4_EXEMPLO[1]}\n",
        ),
    ]
    for destino, _ in arquivos:
        if destino.exists() and not args.force:
            return _erro(
                f"arquivo já existe: {destino} (use --force para sobrescrever)"
            )

    try:
        _gravar_arquivos(arquivos, args.quiet)
    except OSError as exc:
        return _erro(f"falha ao gravar exemplos em {pasta}: {exc}")
    return 0


def _executar_test(args: argparse.Namespace) -> int:
    raiz = Path(__file__).resolve().parent.parent
    tests_dir = raiz / "tests"
    raiz_str = str(raiz)
    adicionou_path = False
    if raiz_str not in sys.path:
        sys.path.insert(0, raiz_str)
        adicionou_path = True
    try:
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(tests_dir),
            pattern=args.pattern,
            top_level_dir=str(tests_dir),
        )
        runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1)
        resultado = runner.run(suite)
    finally:
        if adicionou_path and raiz_str in sys.path:
            sys.path.remove(raiz_str)

    if resultado.testsRun == 0 or not resultado.wasSuccessful():
        return 1
    return 0


def _executar_menu() -> int:
    while True:
        resp = _perguntar(_PROMPT_MENU)
        if resp is None or resp == "q":
            return 0
        if resp in ("1", "2", "3", "4"):
            return main([f"at{resp}"])


def _criar_parser() -> _CliParser:
    parser = _CliParser(
        prog="python -m biocompiler",
        description="BioCompiler Studio — AT1–AT4 de bioinformática (CLI)",
    )
    subparsers = parser.add_subparsers(dest="comando", parser_class=_CliParser)
    ajudas = dict(_SUBCOMANDOS)

    for cmd in ("at1", "at2", "at3"):
        sub = subparsers.add_parser(
            cmd,
            help=ajudas[cmd],
            description=ajudas[cmd],
            epilog=f"{_EPILOGO_PADRAO}\nExemplo: python -m biocompiler {cmd} --input entrada.txt",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub.add_argument("-i", "--input", help="Arquivo de entrada ('-' lê stdin)")
        sub.add_argument("--seq", help="Sequência única informada diretamente")
        sub.add_argument("-o", "--output", help="Caminho explícito do arquivo de saída")
        sub.add_argument("--out-dir", help="Pasta explícita de saída")
        sub.add_argument(
            "--format",
            choices=("text", "csv", "json"),
            default="text",
            help="Formato da saída no terminal (padrão: text)",
        )
        sub.add_argument(
            "--step",
            action="store_true",
            help="Exibe passo a passo interativo dos eventos",
        )
        sub.add_argument(
            "--explain",
            action="store_true",
            help="Lista os passos após cada bloco do relatório",
        )
        sub.add_argument(
            "--ascii",
            action="store_true",
            help="Converte símbolos Unicode de setas/marcadores para ASCII no terminal",
        )
        sub.add_argument(
            "--interactive",
            action="store_true",
            help="Força entrada interativa via terminal",
        )
        sub.add_argument(
            "--fast",
            action="store_true",
            help="Exibe resultado final sem pausar (comportamento padrão)",
        )
        sub.add_argument(
            "--quiet",
            action="store_true",
            help="Suprime saída padrão e avisos de gravação (mantém erros)",
        )
        sub.add_argument(
            "--no-save",
            action="store_true",
            help="Não grava arquivos de exportação",
        )
        sub.add_argument(
            "--force",
            action="store_true",
            help="Permite sobrescrever arquivo de destino existente",
        )

    sub_at4 = subparsers.add_parser(
        "at4",
        help=ajudas["at4"],
        description=ajudas["at4"],
        epilog=(
            f"{_EPILOGO_PADRAO}\n"
            "Exemplo: python -m biocompiler at4 --seq1 ACGTAC --seq2 ACGTTC --method both"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub_at4.add_argument("-i", "--input", help="Arquivo TXT/FASTA com 2 sequências ('-' lê stdin)")
    sub_at4.add_argument("--seq1", help="Primeira sequência de DNA")
    sub_at4.add_argument("--seq2", help="Segunda sequência de DNA")
    sub_at4.add_argument(
        "--method",
        choices=("local", "global", "both"),
        default="both",
        help="Método de alinhamento (padrão: both)",
    )
    sub_at4.add_argument("--match", default="2", help="Pontuação de match (padrão: 2)")
    sub_at4.add_argument("--mismatch", default="-1", help="Pontuação de mismatch (padrão: -1)")
    sub_at4.add_argument("--gap", default="-2", help="Penalidade de gap (padrão: -2)")
    sub_at4.add_argument(
        "--delimiter",
        choices=("semicolon", "comma"),
        default="semicolon",
        help="Delimitador dos arquivos CSV da AT4 (padrão: semicolon)",
    )
    sub_at4.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Formato da saída no terminal (padrão: text)",
    )
    sub_at4.add_argument(
        "--step",
        action="store_true",
        help="Exibe passo a passo interativo do algoritmo",
    )
    sub_at4.add_argument(
        "--granularidade",
        choices=("fase", "linha", "celula"),
        default=None,
        help="Granularidade do --step/--explain na AT4 (padrão: fase)",
    )
    sub_at4.add_argument(
        "--explain",
        action="store_true",
        help="Lista os passos após cada relatório",
    )
    sub_at4.add_argument(
        "--ascii",
        action="store_true",
        help="Converte símbolos Unicode para ASCII no terminal",
    )
    sub_at4.add_argument(
        "--interactive",
        action="store_true",
        help="Força entrada interativa via terminal",
    )
    sub_at4.add_argument("--out-dir", help="Pasta explícita para os artefatos")
    sub_at4.add_argument("--fast", action="store_true", help="Execução direta sem pausas")
    sub_at4.add_argument("--quiet", action="store_true", help="Suprime saída padrão e avisos")
    sub_at4.add_argument("--no-save", action="store_true", help="Não grava arquivos")
    sub_at4.add_argument("--force", action="store_true", help="Sobrescreve destinos existentes")

    sub_all = subparsers.add_parser(
        "all",
        help=ajudas["all"],
        description=ajudas["all"],
        epilog=(
            f"{_EPILOGO_PADRAO}\n"
            "Exemplo: python -m biocompiler all --seq1 ACGTAC --seq2 ACGTTC --method both"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub_all.add_argument("-i", "--input", help="Arquivo TXT/FASTA com 2 sequências ('-' lê stdin)")
    sub_all.add_argument("--seq1", help="Primeira sequência de DNA")
    sub_all.add_argument("--seq2", help="Segunda sequência de DNA")
    sub_all.add_argument(
        "--method",
        choices=("local", "global", "both"),
        default="both",
        help="Método de alinhamento da AT4 (padrão: both)",
    )
    sub_all.add_argument("--match", default="2", help="Pontuação de match (padrão: 2)")
    sub_all.add_argument("--mismatch", default="-1", help="Pontuação de mismatch (padrão: -1)")
    sub_all.add_argument("--gap", default="-2", help="Penalidade de gap (padrão: -2)")
    sub_all.add_argument(
        "--delimiter",
        choices=("semicolon", "comma"),
        default="semicolon",
        help="Delimitador dos arquivos CSV da AT4 (padrão: semicolon)",
    )
    sub_all.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Formato da saída no terminal (padrão: text)",
    )
    sub_all.add_argument("--out-dir", help="Pasta explícita para os artefatos")
    sub_all.add_argument("--fast", action="store_true", help="Execução direta sem pausas")
    sub_all.add_argument("--quiet", action="store_true", help="Suprime saída padrão e avisos")
    sub_all.add_argument("--no-save", action="store_true", help="Não grava arquivos")
    sub_all.add_argument("--force", action="store_true", help="Sobrescreve destinos existentes")
    sub_all.add_argument(
        "--ascii",
        action="store_true",
        help="Converte símbolos Unicode para ASCII no terminal",
    )

    sub_serve = subparsers.add_parser(
        "serve", help=ajudas["serve"], description=ajudas["serve"]
    )
    sub_serve.add_argument(
        "--host", default="127.0.0.1", help="Endereço de escuta (padrão: 127.0.0.1)"
    )
    sub_serve.add_argument(
        "--port", type=int, default=8765, help="Porta HTTP (padrão: 8765)"
    )

    sub_ex = subparsers.add_parser(
        "examples", help=ajudas["examples"], description=ajudas["examples"]
    )
    sub_ex.add_argument("--write", metavar="PASTA", help="Grava os arquivos de exemplo na pasta")
    sub_ex.add_argument("--force", action="store_true", help="Sobrescreve exemplos existentes")
    sub_ex.add_argument("--quiet", action="store_true", help="Suprime avisos de gravação")

    sub_test = subparsers.add_parser(
        "test", help=ajudas["test"], description=ajudas["test"]
    )
    sub_test.add_argument(
        "--pattern",
        default="test*.py",
        help="Padrão de arquivos de teste (padrão: test*.py)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI para comandos não web."""
    _forcar_utf8()
    parser = _criar_parser()
    args = parser.parse_args(argv)

    if args.comando is None:
        if sys.stdin.isatty():
            return _executar_menu()
        parser.print_help(sys.stdout)
        return 1

    if args.comando == "serve":
        return _erro("use python -m biocompiler serve")

    try:
        if args.comando in ("at1", "at2", "at3"):
            return _executar_lote(args)
        if args.comando == "at4":
            return _executar_at4(args)
        if args.comando == "all":
            return _executar_all(args)
        if args.comando == "examples":
            return _executar_examples(args)
        if args.comando == "test":
            return _executar_test(args)
    except Exception as exc:
        sys.stderr.write(
            f"biocompiler: erro interno: {type(exc).__name__}: {exc}\n"
        )
        return 3

    return 1
