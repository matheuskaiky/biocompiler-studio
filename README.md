# BioCompiler Studio

Ferramenta educacional offline para execução, inspeção passo a passo, exportação e comparação das quatro atividades de bioinformática (AT1–AT4) e do fluxo integrado (`all`).

- **Núcleo, CLI e API Python:** utilizam apenas a biblioteca padrão do Python (sem dependências externas).
- **Interface web (opcional):** requer apenas `Jinja2` para renderização dos templates HTML e consome os mesmos serviços Python que a CLI.

## Instalação

- **Requisito mínimo:** Python ≥ 3.10.
- **Núcleo e CLI (sem dependências externas):** basta clonar/extrair o repositório e executar `python3 main.py` ou `python3 -S -m biocompiler`.

```bash
python3 main.py --help
python3 -S -m biocompiler --help
```

- **Interface web opcional:** instale `Jinja2` localmente com:

```text
python3 -m pip install -r requirements-web.txt
```

Se a camada web ou `Jinja2` não estiver disponível, todos os comandos de núcleo e CLI (`at1`, `at2`, `at3`, `at4`, `all`, `examples`, `test`) continuam funcionando normalmente; apenas `serve` informa a ausência com código de saída `1`.

## Uso rápido

Cada atividade funciona de forma isolada, ou em conjunto com `all`:

```bash
python3 main.py at1 --seq ATGGCTAAACCGTAA --no-save
python3 main.py at2 --seq CCCGUCCCCACCCCCCCCCCAGCCC --no-save
python3 main.py at3 --seq m7GpppCCAUGGCUAAACCGUAAGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA --no-save
python3 main.py at4 --seq1 ACGTAC --seq2 ACGTTC --method both --no-save
python3 main.py all --input exemplos/integrado.txt --no-save
```

Exemplos de lote e alinhamento a partir dos arquivos em `exemplos/`:

```bash
python3 main.py at1 --input exemplos/at1_casos.txt --no-save   # saída 2
python3 main.py at2 --input exemplos/at2_casos.txt --no-save   # saída 2
python3 main.py at3 --input exemplos/at3_casos.txt --no-save   # saída 2
python3 main.py at4 --input exemplos/at4_par.fasta --no-save
python3 main.py examples
python3 -m biocompiler at4 --seq1 ACGTAC --seq2 ACGTTC --method local --no-save
python3 main.py at1 --seq ATGGCTXAACCGTAA --no-save   # saída 2
```

## Comandos

Subcomandos disponíveis em `python3 main.py <comando>` (ou `python3 -m biocompiler <comando>`):

- `at1`: transcrição de DNA para pré-mRNA e validação de ORF (ATG até STOP em fase).
- `at2`: splicing (remoção de íntrons `GU...AG` com branch point `A` a 10–30 nt do `AG`), adição de quepe `m7Gppp` e cauda poli-A (`100` adeninas).
- `at3`: tradução de mRNA maduro (validação de `m7Gppp`, cauda com exatamente `100` `A`, `AUG` até STOP em fase) para proteína em código de 3 letras.
- `at4`: alinhamento de exatamente duas sequências de DNA via Smith–Waterman (`local`), Needleman–Wunsch (`global`) ou ambos (`both`).
- `all`: pipeline integrado `AT1 → AT2 → AT3` em duas amostras independentes + alinhamento `AT4` dos dois DNAs originais.
- `examples`: lista os casos didáticos dos enunciados (`--write` grava os arquivos em pasta).
- `serve`: inicia o servidor HTTP local da interface web opcional (`--host`, `--port`).
- `test`: executa a suíte de testes unitários do pacote.

Principais opções da CLI (decisões **D015–D017**):

| Opção | Uso |
|---|---|
| `--input <arquivo>` | Lê lote (AT1–AT3) ou par de sequências (AT4 / `all`) em UTF-8. |
| `--seq <sequencia>` | Sequência única direta para AT1, AT2 ou AT3. |
| `--seq1` / `--seq2` | Par de sequências diretas para AT4 e `all`. |
| `--format` | Formato de saída no terminal (`text`, `json`, `csv`). |
| `--out-dir <pasta>` | Diretório de saída para artefatos gerados (D015). |
| `--output <arquivo>` | Arquivo de saída único (AT1–AT3). |
| `--no-save` | Não grava arquivos em disco; imprime apenas no terminal. |
| `--force` | Sobrescreve arquivos já existentes (D015). |
| `--quiet` | Reduz saída textual no terminal. |
| `--step` | Execução passo a passo no terminal (pausa interativa entre eventos). |
| `--interactive` | Modo guiado interativo no terminal (D016). |
| `--explain` | Exibe explicação didática dos eventos e desempates. |
| `--method` | Método de AT4/`all`: `local`, `global` ou `both` (padrão). |
| `--match`, `--mismatch`, `--gap` | Pontuações inteiras para AT4/`all` (padrão `2`, `-1`, `-2`). |
| `--delimiter` | Delimitador CSV (`semicolon` para `;` ou `comma` para `,`, D015). |

Códigos de saída da CLI (D015): `0` (sucesso em todas as entradas), `1` (erro de uso, argumentos do `argparse`, arquivo ou destino), `2` (ao menos um resultado com `ok=False`, inclusive `BUG - ...` ou `ERRO - parâmetro não numérico` como `--match x`) e `3` (erro interno).

## Formatos

- **AT1, AT2 e AT3 (`.txt`):** uma sequência por linha física (linhas vazias são preservadas na numeração de erros quando aplicável; leitura em UTF-8 com ou sem BOM).
- **AT4 e `all`:**
  - `.txt` com **exatamente 2 linhas não vazias** (Seq1 e Seq2);
  - `.fasta` com **exatamente 2 registros** (`>cabeçalho` seguido da sequência, com suporte a múltiplas linhas por registro).

## Exportações

Ao executar sem `--no-save`, os artefatos são gravados em UTF-8 na pasta de saída (`saidas/` por padrão, ou `--out-dir`):

- **AT1:** `at1_resultados.txt` (`linha;status;resultado;pre_mRNA`)
- **AT2:** `at2_resultados.txt` (`linha;status;resultado;mRNA_maduro`)
- **AT3:** `at3_resultados.txt` (`linha;status;resultado;proteina`)
- **AT4:** `alinhamento_local.txt`, `alinhamento_global.txt`, `matriz_pontuacao_local.csv`, `matriz_pontuacao_global.csv`, `matriz_traceback_local.csv`, `matriz_traceback_global.csv`, `alinhamento_local.csv`, `alinhamento_global.csv` e `comparacao.txt` (usando `--delimiter semicolon` por padrão ou `comma`, D015).
- **`all`:** `relatorio_mestre.txt`, `at1_resultados.txt`, `at2_resultados.txt`, `at3_resultados.txt` e os artefatos AT4 de cada método OK (D017).

## Interface web

A interface web é **opcional** e utiliza os mesmos serviços Python da CLI (`biocompiler/servicos.py`), sem reimplementar regras biológicas no navegador (decisão **D021** e plano diretor em [`docs/FRONTEND_DESIGN_PLAN.md`](docs/FRONTEND_DESIGN_PLAN.md)).

```text
python3 main.py serve --port 8765
```

Acesse `http://127.0.0.1:8765/`. Navegação principal e rotas disponíveis:

- `/` — **Laboratório Completo** (`all`: Mapa da expressão gênica com expansão contextual via **Detalhar**, **Comparador molecular** em `/?aba=comparador`, Laboratório de mutações e Relatório final)
- `/at1` — **BioCompiler 1.0** (Transcrição: cursor científico deslizante, trincas a partir do START, pré-mRNA nascendo da fita de DNA com `T → U` e diagnóstico só em posições determinadas pela API)
- `/at2` — **BioCompiler 2.0** (Splicing e maturação: remoção do íntron na mesma fita com aproximação dos éxons, régua D009, quepe `m7Gppp` no 5′, cauda `A×100` expansível no 3′ e legenda removido/preservado/adicionado)
- `/at3` — **Ribossomo** (Tradução: ribossomo avançando de 3 em 3 bases, cadeia polipeptídica e seleção sincronizada códon ↔ aminoácido)
- `/at4` — **Alinhamento** (Smith–Waterman e Needleman–Wunsch: preenchimento com dependências SVG, inspetor de célula, traceback diferenciado, zoom/arraste e comparação **lado a lado** entre Local e Global)
- `/casos` — **Casos de Teste** dos enunciados
- `/historico` — **Histórico** local da sessão
- `/sobre` — **Sobre** / Metodologia

Recursos da interface (D021):

- **Liquid Glass seletivo e fallbacks:** material translúcido restrito à barra superior, barra do player e diálogos (`[data-superficie="vidro"]`), mantendo dados (fitas, matrizes e tabelas) em superfícies opacas. Em navegadores sem `backdrop-filter` ou com **transparência reduzida** (`prefers-reduced-transparency: reduce`), aplica fundo opaco equivalente.
- **Player, linha do tempo e modos:** barra flutuante com **linha do tempo** arrastável e acessível (`role="slider"` com marcos por tipo de evento), controle de velocidade (`0,5×`–`4×`), botão **Pular para o resultado** com cancelamento imediato e controle segmentado de **Modo** (`Rápido`, `Guiado`, `Animado`). Com **movimento reduzido** (`prefers-reduced-motion: reduce`), as transições apresentam diretamente o estado final.
- **Fluxo entre etapas e apresentação:** botões **Enviar para BioCompiler 2.0** (AT1 → AT2) e **Enviar para o Ribossomo** (AT2 → AT3) transferem o produto gerado para a etapa seguinte; o modo **Apresentação** oculta a barra lateral e amplia a tipografia.

## Testes

- **Suíte principal (núcleo, arquitetura, propriedades, CLI, README, sem dependências web):**

```bash
python3 -m unittest discover -s tests -v
```

- **Mesma suíte com Python isolado (`-S`, sem `site-packages`):**

```bash
python3 -S -m unittest discover -s tests -v
```

- **Suíte da interface web e servidor HTTP (requer `Jinja2` e Chrome/Chromium para CDP):**

```bash
python3 -m unittest discover -s tests_web -v
```

## Estrutura

```text
biocompiler/
  __init__.py, __main__.py   # Despacho preguiçoso (serve x CLI)
  modelos.py                 # Dataclasses imutáveis de resultados e eventos
  exemplos.py                # Casos oficiais dos enunciados (AT1–AT4, §11.1)
  servicos.py                # Fachada compartilhada por CLI e servidor web
  io_formats.py              # Leitura e validação de .txt, .fasta e stdin (UTF-8)
  exports.py                 # Exportação TXT e CSV (UTF-8) e relatórios CLI/API
  cli.py                     # Interface de linha de comando
  webserver.py               # Servidor HTTP opcional (stdlib + Jinja2)
  core/
    at1.py, at2.py, at3.py, at4.py  # Núcleo puro (sem I/O, sem dependência cruzada)
    pipeline.py                     # Composição do modo `all`
  web/
    templates/               # Templates Jinja2
    static/                  # CSS e módulos ES6
exemplos/                    # Arquivos .txt e .fasta derivados de exemplos.py
tests/                       # Testes obrigatórios (stdlib pura)
tests_web/                   # Testes de servidor e navegador via CDP
```

**Grafo de dependências:** `core/at1.py`..`at4.py` são independentes entre si e puros; apenas `core/pipeline.py` os encadeia no modo `all`. `servicos.py` importa sob demanda somente a atividade solicitada. `cli.py` e `webserver.py` consomem `servicos.py`, nunca um ao outro.

## Demonstração

Consulte o roteiro completo de apresentação (5–8 minutos, com links profundos na interface web e Plano B via CLI) em [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md).

A matriz completa entre as 9 condições de conclusão da SPEC §12 e suas evidências reais encontra-se em [`docs/RASTREABILIDADE.md`](docs/RASTREABILIDADE.md).

## Critérios dos enunciados

| Atividade | Regra / Exigência | Comprovação |
|---|---|---|
| AT1 | 6 casos do enunciado, precedência de erro, T→U na sequência inteira, ORF em fase | `tests/test_at1.py`, `tests/test_propriedades.py` |
| AT2 | 4 casos do enunciado, `GU...AG`, branch point `A` em 10–30 nt (**D009**), `m7Gppp` + 100 `A` | `tests/test_at2.py`, `tests/test_propriedades.py` |
| AT3 | 6 casos do enunciado, 64 códons manuais, `m7Gppp`, cauda exata de `100` `A`, proteína em 3 letras | `tests/test_at3.py`, `tests/test_propriedades.py` |
| AT4 | Exatamente 2 DNAs, Smith–Waterman e Needleman–Wunsch manuais, matriz, traceback, desempate | `tests/test_at4.py`, `tests/test_at4_inspecao.py`, `tests/test_propriedades.py` |
| `all` | Cadeias Seq1/Seq2 independentes + alinhamento dos DNAs originais | `tests/test_pipeline.py`, `tests/test_cli_all.py` |
| CLI / Web | Paridade CLI/API/Web, exportações UTF-8, acessibilidade, movimento reduzido | `tests/test_cli.py`, `tests_web/test_webserver.py`, `tests_web/test_laboratorio.py` |

## Limites

- **AT1 — `frameshift` × `STOP ausente` (D007):** sem STOP em fase, classifica `BUG - frameshift` se `(len - inicio_ATG) % 3 != 0` e `BUG - STOP ausente` caso contrário.
- **AT2 — distância do branch point (D009):** intervalo inclusivo de **10 a 30 nt** entre `A` e `AG` (`10 <= ag - branch - 1 <= 30`); 9 e 31 retornam `BUG - branch point`.
- **AT3 — quadro de leitura e cauda poli-A (D012 / D013):** sem STOP em fase, `BUG - quadro de leitura` ocorre se houver STOP na fase `+1` (`(p - inicio_AUG) % 3 == 1`); a cauda poli-A deve ter **exatamente 100 `A`** (99 ou 101 retornam `BUG - cauda poli-A`).
- **AT4 — tamanho máximo de entrada (D014):** máximo de **2000 bases** por sequência; entradas maiores são recusadas antes de alocar a matriz (`ERRO - sequência muito longa`).
- **Política de saída, delimitador e códigos da CLI (D015):** não sobrescreve destinos explícitos sem `--force`, usa `;` (`semicolon`) como padrão em CSV e retorna código `2` para qualquer `ok=False`.
- **Modo interativo / passo a passo (D016):** exige terminal interativo (`--interactive` / `--step`); em pipes sem TTY usa execução direta.
- **Modo `all` (D017):** encadeia `AT1 → AT2 → AT3` por amostra e executa `AT4` sobre os DNAs originais; `--step`, `--explain` e modo interativo ficam nas atividades individuais.
- **Interface visual e teto de exibição na web (D019 / D020):** sem diagnóstico clínico no JS (D019); acima de **1 000 000 de células** na matriz AT4 a web exibe aviso honesto sem desenho célula a célula, e fitas/comparadores usam janelamento > 600 bases e teto < 8000 nós em `main` (**D020**).
