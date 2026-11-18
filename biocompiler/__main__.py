"""Ponto de entrada `python -m biocompiler` com despacho preguiçoso."""

import importlib.util
import sys


def main(argv: list[str] | None = None) -> int:
    """Despacha `serve` para o servidor web e demais comandos para a CLI."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "serve" and "-h" not in args[1:] and "--help" not in args[1:]:
        if importlib.util.find_spec("biocompiler.webserver") is None:
            sys.stderr.write(
                "biocompiler: a interface web não está disponível nesta instalação "
                "(módulo biocompiler.webserver ausente).\n"
            )
            return 1
        try:
            from biocompiler import webserver
        except ModuleNotFoundError as exc:
            if exc.name == "jinja2":
                sys.stderr.write(
                    "biocompiler: o comando serve requer Jinja2. "
                    "Instale com: python -m pip install -r requirements-web.txt\n"
                )
                return 1
            raise
        return webserver.main(args[1:])

    from biocompiler import cli

    return cli.main(args)


if __name__ == "__main__":
    sys.exit(main())
