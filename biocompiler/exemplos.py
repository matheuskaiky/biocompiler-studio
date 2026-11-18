"""Dados dos exemplos didáticos dos enunciados AT1–AT4."""

_CAP = "m7Gppp"
_A100 = "A" * 100

AT1_EXEMPLOS: tuple[str, ...] = (
    "ATGGCTAAACCGTAA",
    "ATGGCTXAACCGTAA",
    "CCCGCTAAACCGTAA",
    "ATGGCTAAACCGGGC",
    "ATGGCTAAAACCGTAA",
    "ATGGCTTAACCGGGCTAA",
)

AT2_EXEMPLOS: tuple[str, ...] = (
    "CCCGUCCCCACCCCCCCCCCAGCCC",
    "CCCCCCCCACCCCCCCCCCAGCCC",
    "CCCGUCCCCACCCCCCCCCCCCCCC",
    "CCCGU" + "C" * 16 + "AAGCCC",
)

AT3_EXEMPLOS: tuple[str, ...] = (
    _CAP + "CCAUGGCUAAACCGUAAGG" + _A100,
    "CCAUGGCUAAACCGUAAGG" + _A100,
    _CAP + "CCGCCGCUAAACCGUAAGG" + _A100,
    _CAP + "CCAUGGCUAAACCGGGCGG" + _A100,
    _CAP + "CCAUGGCUAAAACCGUAAGG" + _A100,
    _CAP + "CCAUGGCUAAACCGUAAGG" + "A" * 80,
)

AT4_EXEMPLO: tuple[str, str] = ("ACGTAC", "ACGTTC")


def texto_exemplos() -> str:
    """Formata os exemplos didáticos para exibição no terminal."""
    linhas = [
        "Exemplos didáticos — BioCompiler Studio",
        "",
        "[AT1 — DNA → pré-mRNA]",
        *AT1_EXEMPLOS,
        "",
        "[AT2 — pré-mRNA → mRNA maduro]",
        *AT2_EXEMPLOS,
        "",
        "[AT3 — mRNA maduro → proteína]",
        *AT3_EXEMPLOS,
        "",
        "[AT4 — alinhamento de DNA]",
        f"Seq1: {AT4_EXEMPLO[0]}",
        f"Seq2: {AT4_EXEMPLO[1]}",
    ]
    return "\n".join(linhas) + "\n"
