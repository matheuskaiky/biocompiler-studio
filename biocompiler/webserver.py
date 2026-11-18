"""Servidor web local opcional do BioCompiler Studio (carregado apenas por `serve`)."""

import argparse
import collections
import http.server
import io
import json
import sys
import threading
import urllib.parse
import zipfile
from pathlib import Path

import jinja2

from biocompiler import exemplos, exports, io_formats, servicos
from biocompiler.core.genetic_code import CODIGO_GENETICO, CODONS_STOP

_LIMITE_CORPO_BYTES = 2 * 1024 * 1024  # 2 097 152 bytes
_LIMITE_LOTE = 1000
_LIMITE_CACHE_CELULA = 8
_LIMITE_CELULAS_CACHE = 250_000
_CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; "
    "script-src 'self'; connect-src 'self'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)
_HOSTS_LOCAIS = frozenset(("127.0.0.1", "localhost", "::1"))

_WEB_DIR = Path(__file__).resolve().parent / "web"
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"

_PAGINAS = {
    "/": ("Laboratório Completo", "Fluxo integrado AT1 → AT2 → AT3 + AT4."),
    "/at1": ("AT1 · Transcrição", "Transcrição de DNA em pré-mRNA."),
    "/at2": ("AT2 · Maturação", "Splicing e maturação de pré-mRNA."),
    "/at3": ("AT3 · Tradução", "Tradução de mRNA maduro em proteína."),
    "/at4": ("AT4 · Alinhamento", "Alinhamento local (Smith–Waterman) e global (Needleman–Wunsch)."),
    "/casos": ("Casos de Teste", "Exemplos didáticos das atividades."),
    "/historico": ("Histórico local", "Histórico de execuções na sessão."),
    "/sobre": ("Sobre/Metodologia", "Convenções didáticas e arquitetura do BioCompiler Studio."),
}

_TIPOS_ESTATICOS = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}

_ROTAS_API_GET = frozenset(("/api/saude", "/api/exemplos", "/api/codigo-genetico"))
_ROTAS_API_POST = frozenset(
    ("/api/at1", "/api/at2", "/api/at3", "/api/at4", "/api/all", "/api/at4/celula", "/api/exportar")
)

_SEMAFORO_CALCULO = threading.BoundedSemaphore(2)
_CACHE_LOCK = threading.Lock()
_CACHE_AT4: collections.OrderedDict[tuple, object] = collections.OrderedDict()


class _ErroHttp(Exception):
    def __init__(self, status: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class _ServeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _eh_int_puro(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _normalizar_parametro(valor: object):
    if isinstance(valor, str):
        try:
            return int(valor)
        except ValueError:
            return valor
    return valor


def _extrair_lote(payload: dict) -> list[str]:
    tem_seqs = "sequencias" in payload
    tem_texto = "texto" in payload
    if tem_seqs == tem_texto:
        raise _ErroHttp(400, "informe 'sequencias' ou 'texto'")

    if tem_seqs:
        seqs = payload["sequencias"]
        if not isinstance(seqs, list) or not all(isinstance(s, str) for s in seqs):
            raise _ErroHttp(400, "'sequencias' deve ser uma lista de textos")
    else:
        texto = payload["texto"]
        if not isinstance(texto, str):
            raise _ErroHttp(400, "'texto' deve ser um texto")
        seqs = io_formats.separar_registros(texto)

    if not seqs:
        raise _ErroHttp(400, "nenhuma sequência na entrada")
    if len(seqs) > _LIMITE_LOTE:
        raise _ErroHttp(400, f"lote acima do limite de {_LIMITE_LOTE} sequências")
    return seqs


def _extrair_par(payload: dict) -> tuple[str, str]:
    tem_seq1 = "seq1" in payload
    tem_seq2 = "seq2" in payload
    tem_texto = "texto" in payload
    if tem_texto:
        if tem_seq1 or tem_seq2:
            raise _ErroHttp(400, "informe 'seq1' e 'seq2' ou 'texto'")
        texto = payload["texto"]
        if not isinstance(texto, str):
            raise _ErroHttp(400, "'texto' deve ser um texto")
        try:
            return io_formats.ler_par(texto)
        except io_formats.ErroEntrada as exc:
            raise _ErroHttp(400, str(exc)) from exc

    if not (tem_seq1 and tem_seq2):
        raise _ErroHttp(400, "informe 'seq1' e 'seq2' ou 'texto'")
    s1, s2 = payload["seq1"], payload["seq2"]
    if not isinstance(s1, str) or not isinstance(s2, str):
        raise _ErroHttp(400, "'seq1' e 'seq2' devem ser textos")
    return s1, s2


def _extrair_parametros_at4(payload: dict, metodo_obrigatorio: str | None = None):
    if metodo_obrigatorio is not None:
        metodo = metodo_obrigatorio
    else:
        metodo = payload.get("metodo", "both")
        if not isinstance(metodo, str) or metodo not in ("local", "global", "both"):
            raise _ErroHttp(
                400, f"método inválido: {metodo!r} (use local, global ou both)"
            )
    match = _normalizar_parametro(payload.get("match", 2))
    mismatch = _normalizar_parametro(payload.get("mismatch", -1))
    gap = _normalizar_parametro(payload.get("gap", -2))
    return metodo, match, mismatch, gap


def _obter_alinhamento_com_cache(
    seq1: str,
    seq2: str,
    alinhamento: str,
    match,
    mismatch,
    gap,
):
    usavel = all(isinstance(v, (int, str)) for v in (match, mismatch, gap))
    chave = None
    if usavel:
        chave = (
            seq1,
            seq2,
            alinhamento,
            (type(match), match),
            (type(mismatch), mismatch),
            (type(gap), gap),
        )
        with _CACHE_LOCK:
            if chave in _CACHE_AT4:
                _CACHE_AT4.move_to_end(chave)
                return _CACHE_AT4[chave]

    res = servicos.alinhar_par(seq1, seq2, alinhamento, match, mismatch, gap)[0]

    if chave is not None and res.ok and res.matriz is not None:
        celulas = (len(res.seq1) + 1) * (len(res.seq2) + 1)
        if celulas <= _LIMITE_CELULAS_CACHE:
            with _CACHE_LOCK:
                _CACHE_AT4[chave] = res
                _CACHE_AT4.move_to_end(chave)
                while len(_CACHE_AT4) > _LIMITE_CACHE_CELULA:
                    _CACHE_AT4.popitem(last=False)

    return res


def _gerar_zip_bytes(artefatos: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in artefatos.items():
            zf.writestr(nome, conteudo.encode("utf-8"))
    return buf.getvalue()


def criar_servidor(
    host: str = "127.0.0.1",
    porta: int = 8765,
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor HTTP da aplicação web usando Jinja2 para templates."""
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    static_root = _STATIC_DIR.resolve()

    class _Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args) -> None:
            return

        def _enviar_resposta(self, status: int, content_type: str, corpo: bytes, extra_headers=None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Content-Security-Policy", _CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if extra_headers:
                for nome, valor in extra_headers.items():
                    self.send_header(nome, valor)
            self.end_headers()
            self.wfile.write(corpo)

        def _enviar_json(self, status: int, dados: object) -> None:
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self._enviar_resposta(status, "application/json; charset=utf-8", corpo)

        def _enviar_html(self, status: int, titulo: str, descricao: str) -> None:
            template = jinja_env.get_template("pagina.html")
            html = template.render(titulo=titulo, descricao=descricao)
            self._enviar_resposta(status, "text/html; charset=utf-8", html.encode("utf-8"))

        def _ler_json_post(self) -> dict:
            cl_raw = self.headers.get("Content-Length")
            if cl_raw is None:
                raise _ErroHttp(411, "Content-Length obrigatório")
            try:
                tamanho = int(cl_raw)
            except ValueError as exc:
                raise _ErroHttp(400, "Content-Length inválido") from exc
            if tamanho < 0:
                raise _ErroHttp(400, "Content-Length inválido")
            if tamanho > _LIMITE_CORPO_BYTES:
                raise _ErroHttp(413, "requisição acima de 2 MB")

            bruto = self.rfile.read(tamanho)
            try:
                texto = bruto.decode("utf-8")
                dados = json.loads(texto)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _ErroHttp(400, "JSON inválido") from exc
            if not isinstance(dados, dict):
                raise _ErroHttp(400, "corpo deve ser um objeto JSON")
            return dados

        def _servir_estatico(self, caminho: str) -> None:
            sub = urllib.parse.unquote(caminho[len("/static/"):])
            if not sub or sub.startswith(("/", "\\")) or "\x00" in sub:
                self._enviar_html(404, "Não encontrado", "Recurso estático não encontrado.")
                return
            alvo = (static_root / sub).resolve()
            if not alvo.is_relative_to(static_root) or not alvo.is_file():
                self._enviar_html(404, "Não encontrado", "Recurso estático não encontrado.")
                return
            tipo = _TIPOS_ESTATICOS.get(alvo.suffix.lower())
            if tipo is None:
                self._enviar_html(404, "Não encontrado", "Tipo de arquivo não suportado.")
                return
            self._enviar_resposta(200, tipo, alvo.read_bytes())

        def do_GET(self) -> None:
            caminho = urllib.parse.urlsplit(self.path).path
            if caminho in _PAGINAS:
                titulo, desc = _PAGINAS[caminho]
                self._enviar_html(200, titulo, desc)
                return

            if caminho.startswith("/static/"):
                self._servir_estatico(caminho)
                return

            if caminho == "/api/saude":
                self._enviar_json(200, {"ok": True, "nome": "BioCompiler Studio"})
                return

            if caminho == "/api/exemplos":
                self._enviar_json(
                    200,
                    {
                        "at1": list(exemplos.AT1_EXEMPLOS),
                        "at2": list(exemplos.AT2_EXEMPLOS),
                        "at3": list(exemplos.AT3_EXEMPLOS),
                        "at4": {
                            "seq1": exemplos.AT4_EXEMPLO[0],
                            "seq2": exemplos.AT4_EXEMPLO[1],
                        },
                        "all": {
                            "seq1": exemplos.ALL_EXEMPLO[0],
                            "seq2": exemplos.ALL_EXEMPLO[1],
                        },
                    },
                )
                return

            if caminho == "/api/codigo-genetico":
                self._enviar_json(
                    200,
                    {
                        "codigos": CODIGO_GENETICO,
                        "stops": sorted(CODONS_STOP),
                    },
                )
                return

            if caminho in _ROTAS_API_POST:
                self._enviar_json(405, {"erro": "método não permitido"})
                return

            if caminho.startswith("/api/"):
                self._enviar_json(404, {"erro": "rota inexistente"})
                return

            self._enviar_html(404, "Página não encontrada", "A rota solicitada não existe.")

        def do_POST(self) -> None:
            caminho = urllib.parse.urlsplit(self.path).path
            if caminho in _PAGINAS:
                self._enviar_html(405, "Método não permitido", "Use GET para acessar páginas.")
                return

            if caminho in _ROTAS_API_GET:
                self._enviar_json(405, {"erro": "método não permitido"})
                return

            if caminho not in _ROTAS_API_POST:
                self._enviar_json(404, {"erro": "rota inexistente"})
                return

            try:
                payload = self._ler_json_post()
                with _SEMAFORO_CALCULO:
                    if caminho in ("/api/at1", "/api/at2", "/api/at3"):
                        at = caminho.rsplit("/", 1)[-1]
                        seqs = _extrair_lote(payload)
                        res = servicos.processar_lote(at, seqs)
                        corpo = exports.json_lote(at, seqs, res, []).encode("utf-8")
                        self._enviar_resposta(200, "application/json; charset=utf-8", corpo)
                        return

                    if caminho == "/api/at4":
                        s1, s2 = _extrair_par(payload)
                        metodo, ma, mi, g = _extrair_parametros_at4(payload)
                        res = servicos.alinhar_par(s1, s2, metodo, ma, mi, g)
                        corpo = exports.json_at4(s1, s2, ma, mi, g, res, []).encode("utf-8")
                        self._enviar_resposta(200, "application/json; charset=utf-8", corpo)
                        return

                    if caminho == "/api/all":
                        s1, s2 = _extrair_par(payload)
                        metodo, ma, mi, g = _extrair_parametros_at4(payload)
                        rf = servicos.fluxo_completo(s1, s2, metodo, ma, mi, g)
                        corpo = exports.json_fluxo(s1, s2, metodo, ma, mi, g, rf, []).encode("utf-8")
                        self._enviar_resposta(200, "application/json; charset=utf-8", corpo)
                        return

                    if caminho == "/api/at4/celula":
                        s1, s2 = _extrair_par(payload)
                        alinhamento = payload.get("alinhamento")
                        if alinhamento not in ("local", "global"):
                            raise _ErroHttp(400, "'alinhamento' deve ser 'local' ou 'global'")
                        i = payload.get("i")
                        j = payload.get("j")
                        if not _eh_int_puro(i) or not _eh_int_puro(j):
                            raise _ErroHttp(400, "'i' e 'j' devem ser inteiros")
                        _, ma, mi, g = _extrair_parametros_at4(payload, metodo_obrigatorio=alinhamento)
                        r = _obter_alinhamento_com_cache(s1, s2, alinhamento, ma, mi, g)
                        if not r.ok:
                            raise _ErroHttp(400, f"alinhamento com erro: {r.resultado}")
                        try:
                            cands = servicos.inspecionar_celula(r, i, j)
                        except ValueError as exc:
                            raise _ErroHttp(400, f"célula fora da matriz: ({i},{j})") from exc
                        self._enviar_json(
                            200,
                            {
                                "metodo": r.metodo,
                                "i": i,
                                "j": j,
                                "valor": r.matriz[i][j],
                                "direcao": r.direcoes[i][j],
                                "candidatos": [{"nome": n, "valor": v} for n, v in cands],
                            },
                        )
                        return

                    # /api/exportar
                    atividade = payload.get("atividade")
                    if atividade not in ("at1", "at2", "at3", "at4", "all"):
                        raise _ErroHttp(400, f"atividade inválida: {atividade!r}")
                    delim_nome = payload.get("delimitador", "semicolon")
                    if delim_nome not in ("semicolon", "comma"):
                        raise _ErroHttp(400, "'delimitador' deve ser 'semicolon' ou 'comma'")
                    delimitador = "," if delim_nome == "comma" else ";"

                    if atividade in ("at1", "at2", "at3"):
                        seqs = _extrair_lote(payload)
                        res = servicos.processar_lote(atividade, seqs)
                        artefatos = exports.artefatos_lote(atividade, res)
                    elif atividade == "at4":
                        s1, s2 = _extrair_par(payload)
                        metodo, ma, mi, g = _extrair_parametros_at4(payload)
                        res = servicos.alinhar_par(s1, s2, metodo, ma, mi, g)
                        primeiro_erro = next((r for r in res if not r.ok), None)
                        if primeiro_erro is not None:
                            raise _ErroHttp(422, f"nada a exportar: {primeiro_erro.resultado}")
                        artefatos = exports.artefatos_at4(res, delimitador)
                    else:
                        s1, s2 = _extrair_par(payload)
                        metodo, ma, mi, g = _extrair_parametros_at4(payload)
                        rf = servicos.fluxo_completo(s1, s2, metodo, ma, mi, g)
                        artefatos = exports.artefatos_fluxo(rf, delimitador)

                    zip_bytes = _gerar_zip_bytes(artefatos)
                    self._enviar_resposta(
                        200,
                        "application/zip",
                        zip_bytes,
                        {"Content-Disposition": f'attachment; filename="biocompiler_{atividade}.zip"'},
                    )
            except _ErroHttp as exc:
                self._enviar_json(exc.status, {"erro": exc.mensagem})
            except Exception as exc:
                self._enviar_json(500, {"erro": f"erro interno: {type(exc).__name__}: {exc}"})

    return http.server.ThreadingHTTPServer((host, porta), _Handler)


def main(argv: list[str]) -> int:
    """Ponto de entrada do servidor web local (`python -m biocompiler serve`)."""
    parser = _ServeParser(
        prog="python -m biocompiler serve",
        description="Interface web local opcional do BioCompiler Studio",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Endereço de escuta (padrão: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Porta HTTP (padrão: 8765)",
    )
    parser.add_argument(
        "--permitir-rede",
        action="store_true",
        help="Permite expor o servidor em endereços não locais",
    )
    args = parser.parse_args(argv)

    if args.host not in _HOSTS_LOCAIS:
        if not args.permitir_rede:
            sys.stderr.write(
                f"biocompiler: host {args.host} não é local; "
                "use --permitir-rede para expor o servidor na rede\n"
            )
            return 1
        sys.stderr.write(
            f"biocompiler: aviso: servidor exposto em {args.host} sem autenticação\n"
        )

    try:
        srv = criar_servidor(args.host, args.port)
    except OSError as exc:
        sys.stderr.write(f"biocompiler: porta {args.port} indisponível: {exc}\n")
        return 1

    porta_real = srv.server_address[1]
    sys.stdout.write(
        f"BioCompiler Studio em http://{args.host}:{porta_real}/ (Ctrl+C para encerrar)\n"
    )
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
