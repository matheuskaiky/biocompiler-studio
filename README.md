# BioCompiler Studio

**Laboratório computacional de Bioinformática — AT1, AT2, AT3 e AT4**

O **BioCompiler Studio** é uma aplicação educacional para o estudo de etapas simplificadas da expressão gênica e de algoritmos de alinhamento de sequências de DNA. O projeto reúne quatro atividades acadêmicas, executáveis **individualmente** ou por meio de um **laboratório integrado**, com apresentação dos resultados no terminal e em uma interface web local opcional.

O foco do trabalho é a implementação explícita dos algoritmos: as operações de análise de sequências, transcrição, processamento de RNA, tradução e programação dinâmica são realizadas em Python, sem bibliotecas que forneçam essas soluções prontas. As convenções biológicas adotadas são **didáticas** e não pretendem reproduzir integralmente os processos celulares reais.

## Atividades implementadas

| Atividade | Entrada | Processamento | Resultado |
| --- | --- | --- | --- |
| **AT1 — BioCompiler 1.0** | Sequência de DNA | Identificação de `ATG`, análise dos códons e de STOP em fase; transcrição de `T` para `U` | Pré-mRNA ou diagnóstico |
| **AT2 — BioCompiler 2.0** | Pré-mRNA | Identificação de íntrons `GU ... A ... AG`, splicing, adição de CAP 5′ e cauda poli-A | mRNA maduro ou diagnóstico |
| **AT3 — Ribossomo** | mRNA maduro | Validação da CAP e da cauda, leitura de códons e tradução pelo código genético | Proteína em códigos de três letras ou diagnóstico |
| **AT4 — Alinhamento** | Exatamente dois DNAs | Smith–Waterman (local) e Needleman–Wunsch (global), com programação dinâmica e traceback | Matrizes, alinhamentos e pontuações |

No **modo integrado (`all`)**, duas sequências de DNA são processadas separadamente por AT1 → AT2 → AT3. A AT4 compara os **dois DNAs originais**; ela é uma análise complementar, não uma etapa da tradução. Erros em uma cadeia não impedem que a outra seja analisada.

## Instalação

### 1. Pré-requisitos

- **Python 3.10 ou superior**.
- Um terminal (PowerShell, Prompt de Comando, Terminal do macOS ou terminal Linux).
- **Somente para a interface web:** acesso ao pacote `Jinja2` na instalação inicial, conforme `requirements-web.txt`.

O núcleo algorítmico, a CLI e os testes principais usam apenas a **biblioteca padrão do Python**. Não é necessário instalar dependências de terceiros para executar as atividades pelo terminal.

### 2. Obter o projeto

Faça o download do repositório como ZIP e extraia os arquivos ou clone-o com Git:

```bash
git clone https://github.com/matheuskaiky/biocompiler-studio.git
cd biocompiler-studio
```

Execute os comandos a seguir **na raiz do projeto**, onde estão `main.py` e `requirements-web.txt`.

### 3. Verificar a instalação para uso sem frontend

```bash
python3 main.py --help
python3 -S -m biocompiler --help
```

A opção `-S` desabilita o carregamento automático de `site-packages`, sendo uma forma adicional de verificar a independência das bibliotecas opcionais. Em Windows, caso `python3` não seja reconhecido, utilize `py -3` ou `python`:

```powershell
py -3 --version
py -3 main.py --help
py -3 -S -m biocompiler --help
```

## Uso rápido

O programa pode ser iniciado por `python3 main.py` ou `python3 -m biocompiler`. Ambos acessam os mesmos comandos. A opção `--no-save` apresenta o resultado sem criar arquivos de saída.

```bash
# AT1: sequência de DNA informada diretamente
python3 main.py at1 --seq ATGGCTAAACCGTAA --no-save

# AT2: exemplo de processamento de pré-mRNA
python3 main.py at2 --seq CCCGUCCCCACCCCCCCCCCAGCCC --no-save

# AT3: exemplo de tradução de mRNA maduro
python3 main.py at3 --seq m7GpppCCAUGGCUAAACCGUAAGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA --no-save

# AT4: comparação pelos dois métodos
python3 main.py at4 --seq1 ACGTAC --seq2 ACGTTC --method both --no-save

# Laboratório integrado: duas sequências em arquivo
python3 main.py all --input exemplos/integrado.txt --no-save
```

**Nota:** no caso da AT3, `m7Gppp` é a representação textual da CAP 5′; a extremidade final contém **100 adeninas**, conforme a convenção do exercício.

### Arquivos de exemplos e casos diagnósticos

O diretório `exemplos/` reúne entradas de referência. Alguns arquivos contêm casos deliberadamente incorretos, portanto o programa pode terminar com código de saída `2`; isso representa um diagnóstico esperado, não uma falha de instalação.

```bash
python3 main.py examples
python3 main.py at1 --input exemplos/at1_casos.txt --no-save  # saída 2
python3 main.py at2 --input exemplos/at2_casos.txt --no-save  # saída 2
python3 main.py at3 --input exemplos/at3_casos.txt --no-save  # saída 2
python3 main.py at4 --input exemplos/at4_par.fasta --no-save
python3 -m biocompiler at4 --seq1 ACGTAC --seq2 ACGTTC --method local --no-save
```

## Comandos

### Comandos disponíveis

| Comando | Descrição |
| --- | --- |
| `at1` | Valida e transcreve DNA em pré-mRNA. |
| `at2` | Identifica e remove íntrons; adiciona CAP 5′ e cauda poli-A. |
| `at3` | Traduz mRNA maduro em uma sequência de aminoácidos. |
| `at4` | Alinha exatamente duas sequências por método local, global ou ambos. |
| `all` | Executa as três etapas de expressão gênica em duas amostras e o alinhamento complementar. |
| `examples` | Lista os casos didáticos; com `--write PASTA`, grava arquivos de exemplo. |
| `serve` | Inicia o servidor da interface web local, opcional. |
| `test` | Executa a suíte de testes unitários do núcleo e da CLI. |

Para consultar todos os argumentos aceitos por um comando, execute `python3 main.py at1 --help`, substituindo `at1` pela atividade desejada.

### Opções mais utilizadas

| Opção | Aplicação | Significado |
| --- | --- | --- |
| `--input ARQUIVO` | AT1–AT4 e `all` | Carrega entradas `.txt` ou, no caso de AT4/`all`, também `.fasta`. Use `--input -` para ler da entrada padrão (*stdin*). |
| `--seq SEQUENCIA` | AT1–AT3 | Informa uma sequência diretamente na linha de comando. |
| `--seq1` e `--seq2` | AT4 e `all` | Informam as duas sequências de DNA diretamente. |
| `--method local\|global\|both` | AT4 e `all` | Escolhe Smith–Waterman, Needleman–Wunsch ou ambos. Padrão: `both`. |
| `--match`, `--mismatch`, `--gap` | AT4 e `all` | Configuram pontuações inteiras de correspondência, substituição e lacuna; padrões: `2`, `-1` e `-2`. |
| `--format text\|csv\|json` | AT1–AT3 | Escolhe o formato exibido no terminal. |
| `--format text\|json` | AT4 e `all` | Escolhe relatório textual ou JSON no terminal. |
| `--output ARQUIVO` | AT1–AT3 | Define o caminho do arquivo de resultado. |
| `--out-dir PASTA` | Todas as atividades | Define diretório de saída dos artefatos. |
| `--no-save` | Todas as atividades | Executa sem criar arquivos de exportação. |
| `--force` | Todas as atividades | Permite sobrescrever destinos existentes. |
| `--quiet` | Todas as atividades | Suprime a saída normal, preservando mensagens de erro. |
| `--fast` | AT1–AT4 e `all` | Exibe o resultado sem pausas; é o comportamento padrão. |
| `--step` | AT1–AT4 | Permite acompanhar a execução em etapas em um terminal interativo. |
| `--explain` | AT1–AT4 | Exibe explicações dos eventos sem exigir avanço manual. |
| `--granularidade fase\|linha\|celula` | AT4 | Controla o detalhamento de `--step` ou `--explain`. |
| `--interactive` | AT1–AT4 | Solicita as entradas por meio de perguntas no terminal. |
| `--delimiter semicolon\|comma` | AT4 e `all` | Escolhe `;` ou `,` para os arquivos CSV de alinhamento. |
| `--ascii` | Comandos de processamento | Substitui determinadas setas e marcas Unicode por caracteres ASCII na saída textual. |

Algumas opções são incompatíveis entre si; por exemplo, `--no-save` não pode ser combinado com `--output` nem com `--out-dir`. Consulte `--help` para os detalhes de cada subcomando.

### Exemplo: parâmetros de alinhamento

No alinhamento, `match` é a pontuação atribuída a bases iguais, `mismatch` a bases distintas e `gap` a uma lacuna inserida no alinhamento. A penalidade de lacuna é **linear**, conforme o enunciado da AT4.

```bash
python3 main.py at4 --seq1 ACGTAC --seq2 ACGTTC --method global --match 2 --mismatch=-1 --gap=-2 --no-save
python3 main.py at4 --seq1 ACGTAC --seq2 ACGTTC --method global --explain --granularidade fase --no-save
python3 main.py at1 --seq ATGGCTAAACCGTAA --format json --no-save
python3 main.py at1 --seq ATGGCTAAACCGTAA --format csv --no-save
python3 main.py at1 --seq ATGGCTXAACCGTAA --no-save  # saída 2
```

No exemplo `ACGTAC` × `ACGTTC`, com `match = +2`, `mismatch = -1` e `gap = -2`, o alinhamento global esperado possui cinco correspondências, uma substituição e **score 9**.

### Modo interativo e passo a passo

Em um terminal interativo, executar `python3 main.py` sem argumentos abre um menu de atividades. Também é possível iniciar diretamente uma atividade com `--interactive`.

- **`--step`**: apresenta os eventos progressivamente; pressione Enter para avançar, `p` para pular o restante da sequência atual ou `q` para encerrar o acompanhamento.
- **`--explain`**: apresenta os eventos do processamento sem solicitar confirmação a cada etapa.
- **`--fast`**: obtém o resultado direto; não há espera por animações ou eventos.

O modo `--step` exige terminal interativo e não deve ser usado em redirecionamentos ou *pipes*. O comando `all` é destinado ao processamento integrado direto; o acompanhamento detalhado por etapas pode ser realizado individualmente nas ATs.

## Formatos

### AT1, AT2 e AT3 — arquivos `.txt`

Cada **linha física** contém uma entrada independente, sem separadores internos. As sequências são processadas na ordem do arquivo e suas posições são preservadas no relatório. A entrada é lida em UTF-8, inclusive arquivos com BOM.

**Exemplo de AT1 — `entrada.txt`:**

```text
CCCATGGCTAAACCGTAA
GGGATGCCCGGGTAG
TTTATGAAACCCGGGTGA
```

As entradas de DNA da AT1 usam `A`, `T`, `C` e `G`; pré-mRNA e regiões transcritas de RNA usam `A`, `U`, `C` e `G`. Os diagnósticos seguem as convenções específicas de cada atividade.

### AT4 e modo `all` — exatamente duas sequências

Um arquivo `.txt` contém uma sequência em cada uma das duas linhas. Alternativamente, pode ser usado FASTA, com **dois registros**, cada qual identificado por um cabeçalho iniciado por `>`:

```fasta
>Seq1
ACGTAC
>Seq2
ACGTTC
```

O leitor FASTA aceita sequências distribuídas por várias linhas dentro de cada registro. A AT4 converte `a`, `c`, `g`, `t` minúsculas para maiúsculas; outras bases são rejeitadas.

## Exportações

Por padrão, a execução sem `--no-save` grava os resultados em `saidas/`. Pode-se alterar o destino com `--out-dir` ou, em AT1–AT3, indicar um arquivo com `--output`. Na ausência de destino explícito, nomes alternativos são utilizados quando já existe uma saída, evitando sobrescrevê-la acidentalmente.

| Atividade | Arquivos gerados | Conteúdo |
| --- | --- | --- |
| AT1 | `at1_resultados.txt` | `linha;status;resultado;pre_mRNA` |
| AT2 | `at2_resultados.txt` | `linha;status;resultado;mRNA_maduro` |
| AT3 | `at3_resultados.txt` | `linha;status;resultado;proteina` |
| AT4, método local | `alinhamento_local.txt`, `matriz_pontuacao_local.csv`, `matriz_traceback_local.csv`, `alinhamento_local.csv` | Relatório, matrizes e colunas alinhadas |
| AT4, método global | `alinhamento_global.txt`, `matriz_pontuacao_global.csv`, `matriz_traceback_global.csv`, `alinhamento_global.csv` | Relatório, matrizes e colunas alinhadas |
| AT4, ambos | Arquivos dos dois métodos, além de `comparacao.txt` | Comparação das pontuações e alinhamentos |
| `all` | `relatorio_mestre.txt`, arquivos de AT1–AT3 e artefatos pertinentes da AT4 | Resultados das duas cadeias e do alinhamento |

Os relatórios e arquivos CSV são gravados em **UTF-8**. Nas AT1–AT3, o cabeçalho e os rótulos textuais dos diagnósticos permitem a correção conforme os documentos das atividades; os arquivos de saída preservam as sequências completas sem abreviá-las.

## Interface web

A interface web é **opcional** e não é necessária para executar ou avaliar os algoritmos pelo terminal.

### Preparação

Instale apenas as dependências de apresentação:

```bash
python3 -m pip install -r requirements-web.txt
```

No Windows, o comando equivalente é `py -3 -m pip install -r requirements-web.txt`.

### Iniciar o servidor

```bash
python3 main.py serve --host 127.0.0.1 --port 8765
```

Abra **http://127.0.0.1:8765/** no navegador. Mantenha o terminal do servidor aberto durante o uso; para encerrá-lo, pressione **Ctrl+C**.

A interface foi concebida para execução local. Não é necessário instalar Node.js nem iniciar um servidor JavaScript separado. Após a instalação de Jinja2, a aplicação utiliza recursos locais e não requer serviços remotos.

### Telas disponíveis

| Caminho | Conteúdo |
| --- | --- |
| `/` | Laboratório completo: integração AT1 → AT2 → AT3 e alinhamento AT4; inclui mapa da expressão gênica, comparação e relatório. |
| `/at1` | Identificação de regiões codificantes e transcrição de DNA. |
| `/at2` | Reconhecimento de íntrons, splicing e maturação do RNA. |
| `/at3` | Leitura de códons e formação da sequência de aminoácidos. |
| `/at4` | Matrizes de alinhamento local/global, inspeção de células e traceback. |
| `/casos` | Exemplos didáticos e diagnósticos previstos nas atividades. |
| `/historico` | Histórico local de execuções da sessão. |
| `/sobre` | Metodologia e convenções do laboratório. |

As visualizações podem oferecer execução rápida, exploração guiada ou animação, além de controles para acompanhar e pular etapas. **Esses recursos apresentam os resultados calculados pelo núcleo Python; não constituem uma segunda implementação dos algoritmos.**

Se Jinja2 não estiver instalado, o comando `serve` apresentará uma orientação para instalação, enquanto a CLI continuará funcionando normalmente.

## Testes

O projeto possui testes unitários e de arquitetura separados dos testes do servidor e da apresentação no navegador.

**Testes do núcleo e da CLI**, sem dependências externas:

```text
python3 -m unittest discover -s tests -v
python3 -S -m unittest discover -s tests -v
```

**Testes específicos da interface web**, com Jinja2 e, para os testes de navegador, Chrome/Chromium com suporte a CDP:

```text
python3 -m unittest discover -s tests_web -v
```

O comando `python3 main.py test` executa a suíte principal a partir da própria CLI. A existência dos testes não substitui a necessidade de executar e conferir seus resultados no ambiente de entrega.

## Estrutura

```text
biocompiler-studio/
├── main.py                   # Entrada alternativa da CLI
├── requirements-web.txt      # Dependência opcional do frontend
├── biocompiler/
│   ├── __main__.py           # Entrada de python -m biocompiler
│   ├── cli.py                # Interação por terminal
│   ├── io_formats.py         # Leitura de TXT, FASTA e stdin
│   ├── exports.py            # Relatórios e exportações
│   ├── servicos.py           # Serviços comuns à CLI e à web
│   ├── modelos.py            # Estruturas de dados dos resultados
│   ├── core/
│   │   ├── at1.py            # Algoritmo de transcrição
│   │   ├── at2.py            # Algoritmo de processamento de RNA
│   │   ├── at3.py            # Algoritmo de tradução
│   │   ├── at4.py            # Algoritmos de alinhamento
│   │   ├── genetic_code.py   # Tabela do código genético
│   │   └── pipeline.py       # Integração dos algoritmos
│   ├── webserver.py          # Servidor HTTP local opcional
│   └── web/
│       ├── templates/       # Páginas Jinja2
│       └── static/          # CSS, JavaScript e recursos locais
├── exemplos/                # Dados reproduzíveis de demonstração
├── tests/                   # Testes dos algoritmos, CLI e arquitetura
├── tests_web/               # Testes da interface e servidor
├── docs/                    # Documentação técnica complementar
└── README.md
```

A organização mantém os quatro algoritmos independentes. O módulo `core/pipeline.py` é responsável pela composição; `servicos.py` oferece uma interface comum para chamadas da CLI e do servidor web.

## Demonstração

Para apresentar o trabalho, recomenda-se iniciar pelo laboratório completo e depois demonstrar uma execução individual de cada atividade, incluindo a inspeção das matrizes da AT4.

A demonstração de integração utiliza duas sequências de DNA que diferem em uma base. Após as etapas de processamento, os resultados esperados incluem as proteínas **Met-Ala-Lys-Pro** e **Met-Ala-Asn-Pro**. A AT4 permite examinar a diferença entre os DNAs originais.

O roteiro completo está em [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md), com alternativa de apresentação inteiramente pelo terminal. A correspondência entre requisitos e testes está registrada em [`docs/RASTREABILIDADE.md`](docs/RASTREABILIDADE.md).

## Critérios dos enunciados

| Atividade | Requisitos centrais |
| --- | --- |
| AT1 | Leitura em lote, validação do DNA, START/STOP em fase, análise de quadro, transcrição `T → U` e seis categorias didáticas de resultado. |
| AT2 | Reconhecimento `GU ... A ... AG`, validação de branch point, remoção de íntron, junção de éxons, CAP 5′, 100 adeninas e quatro categorias de resultado. |
| AT3 | Validação de mRNA maduro, START `AUG`, STOP em fase, tabela completa de códons, aminoácidos em três letras, seis categorias de resultado e lote. |
| AT4 | Exatamente dois DNAs, parâmetros de pontuação editáveis, ambos os algoritmos, matrizes, desempate determinístico, traceback, alinhamentos e score. |

Os casos de teste de entradas incorretas têm finalidade didática: o programa não deve presumir qual caso está recebendo, mas classificá-lo a partir das regras implementadas.

## Limites e convenções didáticas

- **Transcrição (AT1):** o modelo recebe uma fita codificante de DNA e substitui `T` por `U`; não representa a totalidade dos mecanismos reais de transcrição. A classificação de *frameshift* e STOP prematuro segue uma política computacional do exercício, não uma inferência clínica.
- **Splicing (AT2, D009):** a distância válida entre branch point e `AG` é de **10 a 30 nucleotídeos intermediários**, inclusive (`10 ≤ ag − branch − 1 ≤ 30`, com posições baseadas em zero). Trata-se de uma gramática didática; a identificação real de íntrons é mais complexa.
- **Tradução (AT3):** `m7Gppp` é um marcador textual da CAP; a cauda poli-A tem 100 adeninas. **A interpretação atual (D013) usa o bloco terminal máximo de `A`**, o que exige atenção quando o próprio RNA processado termina em adeninas: nesse caso, a fronteira entre RNA e cauda não é inequívoca apenas pelo texto. O projeto não simula dobramento proteico.
- **Diagnósticos (D019):** a interface apresenta as classificações devolvidas pelo núcleo e não deve inferir diagnósticos biológicos adicionais no navegador.
- **Alinhamento (AT4):** o gap é linear, e empates seguem a prioridade diagonal → vertical → horizontal. O limite implementado é de **2.000 bases por sequência** para controlar o custo da matriz de programação dinâmica, cujo tempo e memória são `O(m × n)`.
- **Execução e exportação (D015):** resultados com erro didático usam código de saída `2`; arquivos CSV usam `;` por padrão e destinos explícitos não são sobrescritos sem `--force`.
- **Integração (D017):** AT4 compara os DNAs originais, enquanto AT1–AT3 formam cadeias independentes por amostra; uma etapa inválida impede apenas as etapas que dependem dela.
- **Visualização (D020):** grandes sequências podem ser apresentadas por janelas. Na web, matrizes com mais de 1.000.000 de células recebem aviso de limite de desenho, sem alterar a matriz computada nem as exportações disponíveis pela CLI.

**Observação acadêmica:** o BioCompiler Studio é um simulador educacional baseado nas regras dos trabalhos propostos. Os resultados não constituem anotação genômica, diagnóstico de mutações biológicas reais ou análise clínica.

## Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Todas as entradas processadas com sucesso. |
| `1` | Falha de uso, argumento, leitura/gravação de arquivo ou indisponibilidade da interface opcional. |
| `2` | Pelo menos uma entrada produziu diagnóstico didático de erro (`BUG - ...` ou erro de validação representado no resultado). |
| `3` | Erro interno não previsto. |

As mensagens de resultado também são exibidas no terminal, facilitando identificar o motivo de uma entrada rejeitada e reproduzir o comportamento observado.
