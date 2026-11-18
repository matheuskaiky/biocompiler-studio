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


def _gravar_arquivos(arquivos: list[tuple[Path, str]], quiet: bool) -> None:
    for destino, conteudo in arquivos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo.encode("utf-8"))
        if not quiet:
            sys.stderr.write(f"biocompiler: arquivo gravado: {destino}\n")


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


def _executar_lote(args: argparse.Namespace) -> int:
    atividade = args.comando
    if args.input is not None and args.seq is not None:
        return _erro("use apenas um entre --input e --seq")
    if args.input is None and args.seq is None:
        return _erro("informe --input ou --seq")
    if args.output is not None and args.no_save:
        return _erro("opções incompatíveis: --output e --no-save")
    if args.output is not None and args.out_dir is not None:
        return _erro("opções incompatíveis: --output e --out-dir")
    if args.out_dir is not None and args.no_save:
        return _erro("opções incompatíveis: --out-dir e --no-save")

    try:
        if args.seq is not None:
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

    if destino is not None:
        conteudo_csv = exports.csv_lote(atividade, resultados)
        try:
            _gravar_arquivos([(destino, conteudo_csv)], args.quiet)
        except OSError as exc:
            return _erro(f"falha ao gravar {destino}: {exc}")

    if args.quiet:
        for idx, res in enumerate(resultados, start=1):
            if not res.ok:
                sys.stderr.write(f"biocompiler: linha {idx}: {res.resultado}\n")
    else:
        saida = (
            exports.csv_lote(atividade, resultados)
            if args.format == "csv"
            else exports.relatorio_lote(atividade, resultados)
        )
        sys.stdout.write(saida)

    return 0 if all(r.ok for r in resultados) else 2


def _executar_at4(args: argparse.Namespace) -> int:
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

    try:
        if args.seq1 is not None:
            seq1, seq2 = args.seq1, args.seq2
        else:
            texto = io_formats.ler_texto(args.input)
            seq1, seq2 = io_formats.ler_par(texto)

        pasta_destino = None
        if not args.no_save:
            pasta_destino = _resolver_pasta_at4(args.method, args.out_dir, args.force)
    except io_formats.ErroEntrada as exc:
        return _erro(str(exc))

    match = _parse_int_ou_raw(args.match)
    mismatch = _parse_int_ou_raw(args.mismatch)
    gap = _parse_int_ou_raw(args.gap)

    resultados = servicos.alinhar_par(seq1, seq2, args.method, match, mismatch, gap)
    todos_ok = all(r.ok for r in resultados)

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
        if args.method == "both":
            arquivos.append(
                (
                    pasta_destino / "comparacao.txt",
                    exports.texto_comparacao(resultados[0], resultados[1]),
                )
            )
        try:
            _gravar_arquivos(arquivos, args.quiet)
        except OSError as exc:
            return _erro(f"falha ao gravar em {pasta_destino}: {exc}")

    if args.quiet:
        for r in resultados:
            if not r.ok:
                sys.stderr.write(f"biocompiler: {r.metodo}: {r.resultado}\n")
    else:
        partes = [exports.relatorio_at4(r) for r in resultados]
        if args.method == "both" and todos_ok:
            partes.append(exports.texto_comparacao(resultados[0], resultados[1]))
        sys.stdout.write("".join(partes))

    return 0 if todos_ok else 2


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
            choices=("text", "csv"),
            default="text",
            help="Formato da saída no terminal (padrão: text)",
        )
        sub.add_argument(
            "--fast",
            action="store_true",
            help="Exibe resultado final sem pausar (comportamento padrão)",
        )
        sub.add_argument(
            "--quiet",
            action="store_true",
            help="Suprime saída padrão e avisos de gravação",
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
    sub_at4.add_argument("--out-dir", help="Pasta explícita para os artefatos")
    sub_at4.add_argument("--fast", action="store_true", help="Execução direta sem pausas")
    sub_at4.add_argument("--quiet", action="store_true", help="Suprime saída padrão e avisos")
    sub_at4.add_argument("--no-save", action="store_true", help="Não grava arquivos")
    sub_at4.add_argument("--force", action="store_true", help="Sobrescreve destinos existentes")

    subparsers.add_parser("all", help=ajudas["all"], description=ajudas["all"])

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
        parser.print_help(sys.stdout)
        return 1

    if args.comando == "serve":
        return _erro("use python -m biocompiler serve")

    if args.comando == "all":
        sys.stderr.write(
            "biocompiler: comando 'all' ainda não implementado neste marco\n"
        )
        return 3

    try:
        if args.comando in ("at1", "at2", "at3"):
            return _executar_lote(args)
        if args.comando == "at4":
            return _executar_at4(args)
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
