# BioCompiler Studio — Especificação funcional e técnica unificada

**Versão:** 1.1 (compatibilidade modular, CLI independente e frontend opcional)  
**Escopo:** AT1 BioCompiler 1.0, AT2 BioCompiler 2.0, AT3 Ribossomo e AT4 Smith–Waterman/Needleman–Wunsch  
**Natureza:** documento normativo do projeto; não constitui implementação pronta.  
**Linguagem recomendada:** Python 3.11+ para núcleo e CLI; HTML5, CSS3, JavaScript e Jinja2 opcional para a interface web.  
**Princípio de projeto:** o algoritmo pertence ao estudante; a interface o torna observável.

## 1. Visão executiva

Construir **uma aplicação única e local, utilizável offline**, que satisfaça integralmente os contratos das quatro atividades, amplie a compreensão dos algoritmos com inspeção passo a passo e possa ser apresentada com aparência e fluidez de software científico profissional.

A aplicação terá três acessos à **mesma implementação canônica**:

1. **Interface web local**, rica e interativa; consome serviços de aplicação em Python por uma API HTTP local, sem conexão externa, **com dependências de apresentação opcionais**.
2. **CLI completa**, incluindo importação de arquivos, entrada manual, execução em lote, impressão dos diagnósticos, exportação e inspeção por etapas; não depende do frontend.
3. **API Python importável**, com funções puras e resultados estruturados para executar e testar cada atividade por código.

**Regra fundamental:** não implementar os algoritmos novamente no frontend ou na CLI. As três interfaces chamam as mesmas funções de domínio/serviço, assegurando o mesmo diagnóstico e a mesma saída para entradas equivalentes. **Nenhuma funcionalidade individual, CLI, exportação ou teste acadêmico depende do frontend, do Jinja2, de servidor ou de navegador.**

## 2. Modos de execução

### 2.1 Modo padrão: Laboratório Completo (AT1 + AT2 + AT3 + AT4)

- Entrada padrão: **exatamente dois DNAs** identificados como Seq1 e Seq2. Aceitar digitação, `.txt` com duas linhas ou `.fasta` com dois registros.
- Para **cada DNA**, executar AT1 → AT2 → AT3, respeitando dependências e isolando resultados por sequência.
- Em paralelo lógico, executar **AT4 nas duas sequências originais de DNA**, com método **Local, Global ou Ambos** (modo de comparação Ambos é extensão). Alinhamento é uma análise paralela do DNA, **não uma etapa da síntese proteica**.
- Mostrar um painel comparativo com: DNA original; pré-mRNA; sítios de splicing/íntrons; mRNA maduro; códons; proteína; status por etapa; alinhamento de DNA; score(s).
- Padrão de navegação: a página inicial abre o **Laboratório Completo**. Após carregamento, oferecer exemplos didáticos válidos; o usuário também pode substituir integralmente as entradas.
- Se uma das sequências falhar numa etapa, as etapas posteriores **dessa sequência** recebem `NÃO EXECUTADO — dependência inválida`; manter o erro original, sem inventar saída. A outra sequência continua, e AT4 pode continuar com os dois DNAs originais **se ambos forem DNAs válidos**, independentemente do sucesso das etapas AT1–AT3.
- Com apenas um DNA informado: informar que **AT4 exige duas sequências**; não duplicar automaticamente a primeira. Permitir executar AT1–AT3 mediante escolha explícita ou adicionar Seq2.
- Permitir reprocessar somente uma etapa a partir de entradas manuais adequadas, mas sinalizar quando o encadeamento deixou de corresponder à origem anterior.

### 2.2 Modos individuais

- **AT1 — Transcrição:** DNA → pré-mRNA, com as validações e diagnósticos do enunciado.
- **AT2 — Processamento:** pré-mRNA → mRNA maduro, com splicing, CAP e poli-A.
- **AT3 — Tradução:** mRNA maduro → sequência de aminoácidos.
- **AT4 — Alinhamento:** exatamente dois DNAs → Smith–Waterman (local) ou Needleman–Wunsch (global); ambos opcionalmente executados em comparação.
- **Modo Lote:** disponível nas AT1, AT2 e AT3, com uma sequência por linha, inclusive múltiplas entradas no mesmo `.txt`, preservando a ordem. AT4 permanece limitada a **duas sequências por execução**, inclusive quando a aplicação também oferecer processamento sequencial de múltiplos arquivos externos.

### 2.3 Modo de visualização, independente do modo de cálculo

| Visualização | Comportamento |
|---|---|
| **Exploração guiada** | O usuário acompanha o próximo evento, com explicação e valor intermediário. |
| **Reprodução automática** | Controla iniciar, pausar, velocidade 0,5×/1×/2×/4× e retroceder. |
| **Resultado imediato** | Calcula e mostra o resultado final sem animação. É a opção para acelerar. |
| **Inspeção posterior** | Depois de um cálculo rápido, permite abrir a trilha de decisões sem recalcular resultados incoerentes. |
| **CLI `--step`** | Exibe cada marco do algoritmo no terminal, avançando por Enter. |

**É proibido** obrigar o usuário a esperar animações para obter uma saída. O cálculo não dependerá de temporizadores de UI; a animação será uma reprodução opcional de eventos/dados já calculados.

## 3. Matriz de conformidade dos quatro trabalhos

| Trabalho | Entrada obrigatória | Núcleo obrigatório | Saída e formato obrigatórios |
|---|---|---|---|
| **AT1** | `.txt`, uma sequência de DNA por linha; somente A/T/C/G, sem separadores internos | localizar primeiro `ATG`; procurar STOP em fase `TAA/TAG/TGA`; analisar quadro de leitura; identificar seis casos; converter `T → U` **na sequência completa** | diagnóstico detalhado no terminal/tela, pré-mRNA somente se válido; arquivo UTF-8 em linhas `linha;status;resultado;pre_mRNA` |
| **AT2** | `.txt`, uma sequência de pré-mRNA por linha | buscar `GU ... A ... AG`, com A entre **10 e 30 nucleotídeos antes do AG**; remover íntron completo; juntar éxons; prefixar `m7Gppp`; acrescentar **100 A** | quatro diagnósticos do enunciado, mRNA maduro somente se válido; arquivo UTF-8 em linhas `linha;status;resultado;mRNA_maduro` |
| **AT3** | `.txt`, um mRNA maduro por linha, começando com `m7Gppp` e terminando com cauda poli-A | validar CAP/cauda; localizar primeiro `AUG`; traduzir códons conforme tabela genética completa; parar no primeiro STOP em fase `UAA/UAG/UGA`; reconhecer seis casos | proteína em códigos de 3 letras; saída detalhada; arquivo UTF-8 em linhas `linha;status;resultado;proteina` |
| **AT4** | **exatamente dois DNAs** A/C/G/T por execução, digitados ou lidos de `.txt`/`.fasta`; converter minúsculas em maiúsculas | Smith–Waterman e Needleman–Wunsch com **matriz O(mn)**, score configurável, direção e traceback; desempate **diagonal > vertical > horizontal** | modo, originais, parâmetros, matrizes, alinhamento e score na tela/CLI; exportar texto completo, matriz de score CSV, traceback CSV e alinhamento CSV |

**Observação:** AT4 não é somente Smith–Waterman. O enunciado exige também **Needleman–Wunsch** e comparação entre alinhamentos local e global para o mesmo par. Para AT1/AT2/AT3, as classes textuais dos erros e dos arquivos de correção não poderão ser alteradas por refinamentos de interface.

## 4. Núcleo algorítmico — regras obrigatórias

### 4.1 AT1 — BioCompiler 1.0: DNA Transcriber

**Contrato:** `transcrever_dna(sequencia: str) -> ResultadoAT1`.

1. Validar que a entrada foi lida, não é vazia, não contém separadores internos, e seus caracteres pertencem estritamente a `{A,T,C,G}`. Em AT1, obedecer ao requisito de letras maiúsculas: não converter silenciosamente caracteres inválidos; oferecer opção de normalização **explícita** na UI, antes de validar.
2. Encontrar o primeiro `ATG` por busca sequencial a partir da esquerda.
3. A partir de seu índice, examinar trincas em fase, sem confundir ocorrência de `TAA`, `TAG` ou `TGA` em outra fase com STOP válido.
4. Distinguir falhas de STOP, quadro e STOP prematuro pela convenção definida na §5, que documenta ambiguidades dos exemplos.
5. Se válido, realizar transcrição literal de **toda a fita codificante recebida**, substituindo cada `T` por `U` e preservando bases antes do START e depois do STOP. Não produzir somente a ORF.
6. Retornar `status`, `resultado`, `pre_mRNA`, validações, posições do primeiro START/STOP, sequência de códons, regiões não traduzidas e rastro de decisões.

**Resultados exatos do enunciado:**

- `CORRETO`
- `BUG - base inválida`
- `BUG - START ausente`
- `BUG - STOP ausente`
- `BUG - frameshift`
- `BUG - nonsense / STOP prematuro`

**Formato compatível com correção:** cabeçalho `linha;status;resultado;pre_mRNA`; sucesso `1;OK;CORRETO;AUGGCUAAACCGUAA`; falha `2;ERRO;BUG - base inválida;NÃO GERADO`.

### 4.2 AT2 — BioCompiler 2.0: RNA Processor

**Contrato:** `maturar_pre_mrna(sequencia: str) -> ResultadoAT2`.

1. Validar entrada não vazia, sem espaços internos e com letras `{A,U,C,G}`. Erros de formato extras devem ter mensagens próprias **sem substituir** os quatro resultados exigidos.
2. Identificar candidatos `GU ... A ... AG` por varredura explícita; o `GU` inicial e o `AG` terminal integram o íntron.
3. Para um `AG` iniciado na posição `j`, um branch point na posição `k` é elegível quando `10 <= j-k <= 30` e `k` fica **dentro do candidato**, depois do `GU` e antes do `AG` (distância medida até o primeiro `A` do `AG`, sem incluir esse próprio AG).
4. Encontrar íntrons válidos e não sobrepostos; remover todo o intervalo inclusivo `[GU ... AG]`, concatenando apenas os éxons. Não excluir nucleotídeos adjacentes.
5. Em caso de sucesso, prefixar o **marcador textual** `m7Gppp`; adicionar literalmente `'A' * 100` à extremidade 3′; retornar também o RNA sem CAP/cauda e metadados de intervalos.
6. Quando houver vários candidatos, empregar desempate determinístico explicitado em §5. Apresentar ao professor as escolhas e as alternativas reconhecidas.

**Resultados exatos do enunciado:**

- `CORRETO`
- `BUG - sítio 5' ausente`
- `BUG - sítio 3' ausente`
- `BUG - branch point`

**Formato compatível:** cabeçalho `linha;status;resultado;mRNA_maduro`; por exemplo `1;OK;CORRETO;m7Gppp...` e `2;ERRO;BUG - sítio 5' ausente;NÃO GERADO`. No arquivo real, `...` deve ser substituído pela sequência completa, inclusive **100 A**, sem abreviação nem espaços extras.

**Limite didático:** as letras GU, A e AG podem ocorrer em éxons verdadeiros. Sem anotação estrutural não é possível inferir todos os íntrons biológicos. A interface deve dizer que implementa a **gramática simplificada do exercício**, sem insinuar precisão genômica real.

### 4.3 AT3 — Ribossomo: Protein Translator

**Contrato:** `traduzir_mrna(sequencia: str) -> ResultadoAT3`.

1. Confirmar prefixo **exatamente** `m7Gppp` (sensível a caixa de letras).
2. Confirmar a cauda poli-A na extremidade 3′, com **100 A consecutivos** segundo a política de interpretação da §5; separar CAP, parte transcrita e cauda, sem traduzir CAP/cauda.
3. Validar a parte transcrita como `{A,U,G,C}`; localizar o primeiro `AUG` da parte transcrita e iniciar a leitura nele.
4. Percorrer a região em trincas; usar mapa codon → aminoácido implementado pelo estudante para os **64 códons** (61 codificadores + 3 STOP) e nomes **Met, Ala, Lys, Pro** etc. com três letras padronizadas.
5. Encerrar no **primeiro** `UAA`, `UAG` ou `UGA` **em fase**. Não incluir STOP na proteína. Ignorar trecho anterior ao START e posterior ao STOP, exceto para diagnóstico e visualização.
6. Produzir proteína somente se toda a entrada for válida; caso contrário, `NÃO GERADA`. Não simular dobramento nem modificações pós-traducionais.

**Resultados exatos do enunciado:**

- `CORRETO`
- `BUG - CAP 5'`
- `BUG - START ausente`
- `BUG - STOP ausente`
- `BUG - quadro de leitura`
- `BUG - cauda poli-A`

**Formato compatível:** cabeçalho `linha;status;resultado;proteina`; por exemplo `1;OK;CORRETO;Met-Ala-Lys-Pro` e `2;ERRO;BUG - CAP 5';NÃO GERADA`.

**Validação da tabela genética:** testar os 64 códons, inclusive os três STOP, codificações redundantes e AUG inicial; tabela **escrita manualmente** no repositório (não importada de BioPython).

### 4.4 AT4 — Alinhamento de duas sequências: programação dinâmica

**Contrato:** `alinhar_dna(seq1: str, seq2: str, metodo: str, match: int, mismatch: int, gap: int) -> ResultadoAT4`.

**Entrada:** exatamente dois DNAs, não vazios, letras `A,C,G,T`, minúsculas normalizadas. Os parâmetros numéricos são configuráveis e não constantes fixas; utilizar inteiros no contrato padrão (conforme exemplos e modelos de tela). Recomendar `match > 0`, `mismatch < 0`, `gap < 0`, mas não confundir recomendações didáticas com erro obrigatório, desde que sejam números finitos aceitos pela implementação. Não usar gaps afins.

Definir `s(a,b) = match` se `a == b`, caso contrário `mismatch`. Com linhas `i` referentes à `Seq1` e colunas `j` à `Seq2`:

**Smith–Waterman — LOCAL:**

```text
H(0,j) = 0, H(i,0) = 0
H(i,j) = max(
    0,
    H(i-1,j-1) + s(Seq1[i-1], Seq2[j-1]),
    H(i-1,j)   + gap,
    H(i,j-1)   + gap
)
```

Iniciar traceback na maior célula da matriz; parar em célula `0`. Score = valor máximo da matriz. Se **todas** as células forem zero, retornar score `0` e alinhamento vazio identificado como “sem região de similaridade positiva”, sem inventar comparação.

**Needleman–Wunsch — GLOBAL:**

```text
F(0,0) = 0
F(i,0) = i * gap
F(0,j) = j * gap
F(i,j) = max(
    F(i-1,j-1) + s(Seq1[i-1], Seq2[j-1]),
    F(i-1,j)   + gap,
    F(i,j-1)   + gap
)
```

Iniciar traceback no canto inferior direito e terminar em `(0,0)`. Score = `F(m,n)`.

**Desempate obrigatório em cada célula:** diagonal `↖` antes de vertical `↑` antes de horizontal `←`. Guardar direção determinística, inclusive para traceback. Para empates entre **células máximas** no modo local (não definido pelo enunciado), selecionar a primeira em ordem linha/coluna crescente; tornar essa decisão visível.

Movimentos:
- `↖`: consome uma base de cada sequência; `|` para match, `.` para mismatch.
- `↑`: consome base de Seq1 e insere `-` em Seq2.
- `←`: insere `-` em Seq1 e consome base de Seq2.

**Resultados obrigatórios:** originais, modo, parâmetros, matriz de valores, matriz de direções, caminho de traceback, duas sequências alinhadas com gaps, indicador visual de matches/mismatches/gaps, score e tamanho do alinhamento. Permitir executar **local e global com a mesma dupla** sem nova digitação. Validar score final por soma independente das colunas alinhadas.

**Complexidade:** `O(m*n)` tempo e `O(m*n)` espaço para as matrizes exigidas. Descrever honestamente limites de memória; não trocar por solução linear de memória que impossibilite exibir a matriz completa.

## 5. Regras determinísticas para lacunas e ambiguidades dos enunciados

Esta seção é parte indispensável do projeto: evita códigos que apenas classificam os exemplos do professor por coincidência.

### 5.1 Precedência e interpretação na AT1

Os exemplos de AT1 usam convenções **didáticas**, não detecção clínica de mutações. Aplicar:

1. Caractere proibido → `BUG - base inválida`.
2. Ausência de `ATG` → `BUG - START ausente`.
3. Varrer códons em fase após o primeiro ATG. Se houver **dois ou mais STOP em fase** depois do START, classificar `BUG - nonsense / STOP prematuro`, interpretando o primeiro como prematuro, conforme exemplo com `ATGGCTTAACCGGGCTAA`. **Explicitar a ressalva:** biologicamente, um segundo STOP pode simplesmente estar na região 3′ não traduzida; não existe confirmação de nonsense sem referência/contexto.
4. Na ausência de STOP em fase: se existir `TAA`, `TAG` ou `TGA` **fora de fase** após o START, ou restarem bases incompletas para leitura trinca a trinca, classificar `BUG - frameshift`. Se não houver tais indícios, `BUG - STOP ausente`.
5. Com exatamente um STOP em fase, classificar `CORRETO`; bases antes do START e depois do STOP não são traduzidas, e a transcrição continua sendo feita na **sequência inteira**.

*Nota de implementação:* os passos 3–5 são **política de compatibilidade proposta** para tornar os seis casos reprodutíveis; os PDFs não oferecem uma gramática formal suficiente para distinguir todos os possíveis casos reais. Adicionar testes específicos que documentem essa escolha.

### 5.2 Escolha de múltiplos candidatos na AT2

- Enumerar posições `GU` e `AG` por varredura; um candidato exige `GU` antes do `AG` e branch point A elegível.
- Escolher primeiro o candidato com **menor posição do GU**, depois **menor posição do AG terminal** que satisfaça o branch point. Se houver vários A elegíveis, escolher aquele **mais próximo do AG**, documentando o critério.
- Para múltiplos íntrons, após escolher um intervalo avançar para depois do seu `AG` na sequência **original**, evitando sobreposições; concatenar os segmentos conservados ao final, sem reinterpretação acidental das junções recém-formadas.
- Se nenhum candidato for válido: preferir `BUG - sítio 3' ausente` quando existe GU sem AG posterior compatível; `BUG - sítio 5' ausente` quando há AG sem GU anterior possível; `BUG - branch point` quando o par GU/AG existe, mas não há A a 10–30 nt do AG. Caso nenhum sinal GU/AG exista, registrar diagnóstico adicional `BUG - íntron ausente` (caso não coberto pelos quatro exemplos, e não uma substituição dos rótulos exigidos).
- Um `GU` residual em éxon **não invalida automaticamente** uma entrada que já teve íntron válido reconhecido; não é possível saber, somente pela sequência, se ele seria um sítio 5′. Exibir esses sinais como *não selecionados* e justificar a escolha.
- A AT2 não deve impor requisitos de preservação de ORF como condição da maturação, pois seu enunciado não pede isso. A integração poderá avisar caso o splicing resulte em RNA que a AT3 não traduza.

### 5.3 Ambiguidade intrínseca da cauda poli-A

Em texto puro, uma sequência que termina em 101 adeninas pode ser interpretada como **101 A de cauda** ou como **1 A do RNA anterior + 100 A de cauda**. Não existe separador sintático no enunciado. Assim:

- **Entrada avulsa de AT3 (.txt, terminal, web):** adotar convenção verificável do teste: o **bloco terminal máximo** de `A` deve medir **exatamente 100**. Em caso contrário, `BUG - cauda poli-A`.
- **Pipeline completo:** AT2 também devolve metadados separados `rna_processado`, `cap`, `cauda_adicionada`; a verificação sem perda de informação da procedência usa `cauda_adicionada == 'A'*100`. Contudo, a **exportação textual** pode ser ambígua quando o RNA processado já termina em `A`. A UI deve sinalizar isso, oferecer aviso de ambiguidade e incluir testes de integração usando RNAs com nucleotídeo final não `A`.
- Nunca inserir separadores invisíveis, sentinelas ou abreviações na exportação exigida. Não anunciar que uma simples contagem de A distingue todos os casos biológicos.

### 5.4 Quadro de leitura na AT3

Se não existir STOP em fase, mas houver STOP fora de fase ou trecho final incompleto após o AUG, preferir `BUG - quadro de leitura`; se não houver sinal de STOP e o percurso terminar em trincas completas, `BUG - STOP ausente`. Tornar essa regra explícita na seção “Por que este diagnóstico?”.

### 5.5 Precisão e padronização

- Índices internos: base zero; interface: posições humanas **1-based**, sempre exibindo ambos no inspector técnico, quando relevante.
- Strings dos diagnósticos: **exatamente** as dos documentos (maiúsculas, hífen e apóstrofo), com UTF-8.
- O status de exportação é `OK` ou `ERRO`. Para etapas não executadas do modo integrado, usar estado estruturado `SKIPPED` **somente no relatório integrado**, nunca falsificar `ERRO` de uma etapa não executada nem inseri-lo como caso do professor.
- Diferenças entre o modelo didático e a biologia real devem ser marcadas no produto como “Convenção da atividade”.

## 6. Interface web: conceito visual

**Direção de arte:** *laboratório científico contemporâneo*, com identidade visual séria e elementos lúdicos discretos. Não reproduzir visual infantil dos slides; apresentar uma ferramenta de experimentação clara e sofisticada.

- **Tema padrão:** escuro profundo, com superfícies em camadas, bordas discretas e alto contraste. **Tema claro** obrigatório.
- **Cores semânticas consistentes:** DNA azul/índigo; pré-mRNA ciano; splicing violeta; RNA maduro turquesa; tradução verde; alinhamento âmbar. Para erros, vermelho acompanhado de texto/ícone. Cores são apoio, nunca a única forma de transmitir informações.
- **Tipografia:** fontes nativas do sistema (`system-ui`) e fonte monoespaçada (`ui-monospace`); sem downloads/fontes externas.
- **Elementos gráficos:** fitas e bases em SVG, animação de ribossomo desenhada em SVG/CSS, gradientes leves e Canvas 2D para matrizes extensas; tudo original e offline.
- **Responsividade:** desktop como experiência ideal; tablet plenamente funcional; mobile permite editor, resultados, cartões e matrizes com rolagem/pinça, sem distorcer letras.
- **Acessibilidade:** navegação por teclado, foco visível, labels, leitores de tela, contraste, legendas nos estados, preferência `prefers-reduced-motion` e controles explícitos de animação.
- **Performance:** simulações por **eventos incrementais**; nunca criar DOM individual para milhões de células; usar Canvas/virtualização quando necessário. Mostrar resultado e dados completos mesmo se animação detalhada for reduzida.

### 6.1 Estrutura global da navegação

Barra lateral com: **Laboratório Completo** (padrão), **AT1 · Transcrição**, **AT2 · Maturação**, **AT3 · Tradução**, **AT4 · Alinhamento**, **Casos de Teste**, **Histórico local** e **Sobre/Metodologia**. Barra superior com seletor de modo de reprodução, tema, ajuda contextual e comando global **Exportar**.

Cada área analítica conterá subabas estáveis: **Entrada**, **Etapas/Algoritmo**, **Visualização**, **Resultados** e **Exportação**. Subabas específicas de cada tarefa são descritas a seguir; não esconder matrizes, códons ou dados brutos atrás de animação.

## 7. Telas e interações por atividade

### 7.1 Laboratório Completo — home principal

**Aba “Montar experimento”**
- Dois editores separados de DNA, Seq1 e Seq2, com contador de bases, indicadores A/T/C/G, copiar/colar, importar `.txt`/`.fasta`, substituir por exemplo e validação visível sem recalcular automaticamente a cada tecla.
- Configuração de AT4: Local, Global, Ambos; Match, Mismatch e Gap. Inicial: **Ambos**, com `+2/-1/-2` como exemplo alterável.
- Seleção: `Execução rápida` / `Execução guiada` / `Execução animada`; padrão recomendado **rápido com inspeção disponível**.
- CTA central: **Executar laboratório completo**; botão “Pular animações”.

**Aba “Mapa da expressão gênica”**
- Duas trilhas paralelas, uma por DNA; cada trilha mostra 3 fases com status, tempo lógico (etapas), pontos de falha e saída.
- Fitas de DNA/ RNA com marcadores de ORF, sítios GU/AG, branch point, CAP, cauda poli-A e códons; clicar em qualquer elemento abre coordenadas e regra usada.
- Quarta trilha independente abaixo: alinhamento entre os DNAs originais, com score(s) e diferenças.

**Aba “Comparador molecular”**
- Comparar os resultados de Seq1/Seq2 lado a lado, destacar posições distintas e indicar se a diferença foi preservada na sequência de RNA e/ou na proteína **quando ambos os percursos foram válidos**.
- A interpretação “mutação silenciosa/missense/nonsense” exige alinhamento de códons comparáveis e contexto suficiente; se ausentes, mostrar apenas “diferença observada”, não produzir diagnóstico biológico categórico.

**Aba “Relatório final”**
- Quadro único: parâmetros, datas locais (opcionais), entrada original, status AT1–AT4, decisões, intermediários completos, proteínas, matriz e scores; reexecutar etapas, copiar diagnóstico, exportar tudo.

### 7.2 AT1 — BioCompiler 1.0

**Subaba “DNA de entrada”**: editor monoespaçado com posição da base, validação manual, carregamento `.txt`, alternância lote/única, indicadores e exemplos dos **seis casos**. Exibir sequências inválidas com posições exatas e descrição sem corrigi-las automaticamente.

**Subaba “Analisador de ORF”**: faixa de DNA com busca destacada do primeiro ATG; agrupamento visual em códons; STOP em fase e fora de fase com marcadores diferentes; 5′/3′ UTR; inspector “por que não é STOP válido?” e painel sobre precedência de erros.

**Subaba “Transcritor T → U”**: DNA acima/pré-mRNA abaixo, alinhados por índice, substituições T/U destacadas; avanço por base, por códon, até o fim ou direto; contadores de T convertidos; botão de cópia do pré-mRNA.

**Subaba “Diagnóstico e lote”**: seis categorias com mensagens exatas, resultado de cada linha em tabela filtrável, exportação de `resultados.txt/.csv`; demonstrar que apenas entradas válidas produzem pré-mRNA.

### 7.3 AT2 — BioCompiler 2.0

**Subaba “pré-mRNA”**: importação `.txt`, colagem ou **receber saída de AT1**; contador de bases e caracteres inválidos; exemplos dos quatro casos.

**Subaba “Reconhecimento de íntrons”**: barra de sequência com marcação `GU`, possíveis `AG` e adeninas candidatas; lista dos pares considerados e por que foram aceitos/recusados; régua interativa de **10–30 nt** entre branch point e AG; quando houver candidatos ambíguos, mostrar desempate.

**Subaba “SpliceLab”**: ilustração animada de éxons/íntrons; a porção `[GU ... A ... AG]` é destacada e removida, as extremidades exônicas se aproximam; ao clicar num íntron, mostrar antes/depois e coordenadas; pular/retroceder sem perder resultado.

**Subaba “Maturação”**: `m7Gppp` anexado visualmente à extremidade 5′; cauda composta por **100 A** (representação comprimida na tela, mas contador exato e expansão possível), base por base ou instantaneamente; separar marcador químico textual da sequência real.

**Subaba “Resultado e lote”**: mRNA maduro literal completo, regiões removidas, validações dos quatro casos, CSV/TXT compatíveis e botão “Enviar para Ribossomo”.

### 7.4 AT3 — Ribossomo

**Subaba “mRNA maduro”**: carregar `.txt`, digitar ou importar saída de AT2; validar CAP, comprimento da cauda e bases, com mensagens específicas.

**Subaba “Localizar START/STOP”**: fita linear com regiões 5′ UTR, códons, 3′ UTR, CAP e poli-A, procura progressiva do primeiro `AUG`, STOPs dentro/fora de fase; detalhe de coordenadas.

**Subaba “Ribossomo em ação”**: ilustração SVG original de ribossomo lendo a fita em passos de três bases; aminoácido aparece sob cada códon e é anexado à cadeia visual; STAR[T] `AUG → Met`, STOP encerra sem aminoácido; controle “próximo códon”, velocidade, reproduzir/pausar, finalizar agora e voltar ao início.

**Subaba “Código genético”**: tabela interativa 64 códons construída a partir do próprio dicionário do núcleo, com filtro de codon/aminoácido, realce dos códons realmente percorridos, sem usar biblioteca pronta.

**Subaba “Proteína e diagnóstico”**: sequência `Met-Ala-Lys-Pro`, quantidade de aminoácidos, verificações CAP/START/frame/STOP/cauda, resultado por linha e exportação. Indicar explicitamente que não modela dobramento.

### 7.5 AT4 — Alinhamento

**Subaba “Entrada e parâmetros”**: campos Seq1/Seq2, importação `.txt/.fasta`, selector Local/Global/Ambos, match/mismatch/gap editáveis; mensagens para bases inválidas, mais/menos de duas sequências e pontuação inválida; exemplos com `ACGTAC` e `ACGTTC`.

**Subaba “Matriz de pontuação”**: tabela com cabeçalhos Seq1/Seq2, zeros ou penalidades iniciais, score das células, destaque do caminho escolhido, zoom e arraste; clicar em `(i,j)` revela **candidatos calculados** (diagonal, vertical, horizontal, zero se local), máximo e regra de desempate; preencher em ordem de leitura ou saltar ao resultado.

**Subaba “Matriz de traceback”**: direções `↖ ↑ ←` para todas as células e destaque do caminho final; animação reversa do ponto inicial até a origem/zero; inspecionar justificativa de cada deslocamento.

**Subaba “Alinhamento reconstruído”**: representações monoespaçadas e visuais sincronizadas `|`, `.`, gaps; score, contagem de matches/mismatches/gaps, tamanho; conferir que a soma das operações reproduz o score.

**Subaba “Local × Global”**: executar ambos com as mesmas entradas e parâmetros, duas matrizes independentes e dois alinhamentos lado a lado; explicar as diferenças sem comparar scores como se os critérios representassem sempre a mesma coisa.

**Subaba “Exportação”**: `.txt` completo, `matriz_pontuacao.csv`, `matriz_traceback.csv`, `alinhamento.csv`; no modo Ambos, nomes sufixados `_local` e `_global`, além de `comparacao.txt`; opção “Exportar tudo” para pasta ou `.zip` gerado com `zipfile` padrão.

### 7.6 Telas transversais diferenciadoras

**Laboratório de mutações (diferencial):** usuário seleciona uma base no DNA e aplica substituição/inserção/deleção **como manipulação da entrada**. Reexecuta o pipeline e compara resultados com a sequência anterior; não afirmar que toda inserção/deleção pode ser diagnosticada biologicamente como frameshift sem referência. Trilha de antes/depois e botão “Reverter”. Para AT4, permitir alinhar a variante com seu DNA de origem, sempre duas sequências.

**Inspetor “Por que este resultado?” (diferencial):** para cada verificação/célula/códon, mostrar entrada examinada, condição, posição e decisão. **Nunca** apresentar explicações geradas artificialmente sem vínculo com o traço computado.

**Desafios do professor (diferencial):** cases clicáveis correspondentes aos seis casos AT1, quatro AT2, seis AT3, ao exemplo de score `9` da AT4, a empates de traceback e a entradas inválidas; a UI não deve usar o nome do caso para decidir o resultado, somente a sequência.

**Modo apresentação (diferencial):** tela cheia com tipografia ampliada, atalhos (`Espaço` executar/pausar, `→` próximo, `←` anterior, `F` resultado final, `E` exportar), textos para explicar oralmente a matriz e a trajetória DNA → proteína; não requer internet.

**Histórico local (diferencial):** sessão atual com experimentos recentes, comparações e reexecução; **sem telemetria**. Não exigir banco de dados. Opcional salvar `.json` no disco mediante ação explícita; não armazenar sequências permanentemente por padrão.

## 8. Interface de linha de comando (CLI): contrato completo

### 8.1 Comandos

```bash
python -m biocompiler --help
python -m biocompiler at1 --input dna.txt
python -m biocompiler at2 --input pre_mrna.txt
python -m biocompiler at3 --input mrna.txt
python -m biocompiler at4 --input duplas.fasta --method local --match 2 --mismatch -1 --gap -2
python -m biocompiler at4 --seq1 ACGTAC --seq2 ACGTTC --method global
python -m biocompiler at4 --input duas.txt --method both
python -m biocompiler all --input dna_duplas.txt --method both
python -m biocompiler serve --host 127.0.0.1 --port 8765
python -m biocompiler examples
python -m biocompiler test
```

`test` pode funcionar como invocador de `unittest` do próprio pacote, sem framework externo.

**Atalho na raiz (D006):** `python main.py <args>` é equivalente a `python -m biocompiler <args>` para todos os comandos acima (ex.: `python main.py at1 --input dna.txt`).

### 8.2 Parâmetros comuns

| Opção | Função |
|---|---|
| `-i, --input CAMINHO` | Arquivo de entrada; `--input -` lê de `stdin` por pipe. |
| `--seq SEQUENCIA` | Entrada única direta para AT1/AT2/AT3. |
| `--seq1`, `--seq2` | Entradas diretas obrigatoriamente em par para AT4 ou `all`. |
| `-o, --output CAMINHO` | Caminho explícito do relatório principal, sem extensão inferida indevidamente. |
| `--out-dir PASTA` | Pasta de resultados adicionais. |
| `--format text\|csv\|json` | Saída principal, respeitando CSV canônico das AT1–AT3. |
| `--interactive` | Prompts no terminal para caminho/entrada/parâmetros; não usado automaticamente em pipes. |
| `--step` | Avançar manualmente pelos eventos do algoritmo no terminal. |
| `--fast` | Mostrar resultado final sem pausar/animar; padrão para scripts e pipes. |
| `--explain` | Mostrar validações e cálculos detalhados no terminal. |
| `--quiet` | Reduzir saída informativa; não ocultar erros relevantes. |
| `--no-save` | Desabilitar exportação automática **somente mediante escolha explícita**. |
| `--force` | Permitir sobrescrever saída existente; padrão evita sobrescrita silenciosa. |
| `--help` | Ajuda por comando, com exemplos e códigos de saída. |

Parâmetros da AT4 e do modo completo: `--method local|global|both`, `--match`, `--mismatch`, `--gap`; valores iniciais configuráveis, exemplos `2`, `-1`, `-2`. Não permitir argumentos incompatíveis passarem silenciosamente.

### 8.3 Comportamento padrão da CLI

- Com arquivo informado: processar **sem perguntas**, imprimir resultado legível e criar arquivo exportado, por padrão em `./saidas/` com nomes estáveis e sem colisão; a opção `--output resultados.txt` permite replicar o nome sugerido pelo professor.
- Sem arquivo/`--seq` num terminal interativo: apresentar escolha de modo e prompt para colar sequências ou informar caminho; permitir que o usuário use **tudo exclusivamente por terminal**, inclusive seleção de modo e parâmetros.
- Com `stdin` não TTY e dados ausentes/inválidos: falhar com erro claro, **sem aguardar interação**.
- Modo `--step`: AT1 destaca base/códon, AT2 candidatos/sítios, AT3 códons, AT4 inicialização/cálculo de cada célula/traceback; para matrizes grandes permitir mudar granularidade `célula`, `linha`, `fase` a fim de não gerar milhares de pausas obrigatórias.
- Saídas e diagnósticos em **UTF-8**; terminais sem suporte a Unicode podem usar `--ascii` para setas/textos visuais, **mas não alterar** os rótulos normativos em arquivos UTF-8.
- Códigos de saída: `0` execução concluída sem erros nos registros; `1` falha de entrada/argumentos/arquivo; `2` execução concluída com pelo menos um diagnóstico `ERRO` biológico/didático; `3` erro interno ou recurso esgotado. **Mesmo com código 2, salvar todos os resultados de lote processados**.
- Número da `linha` refere-se à **linha física** do `.txt`, começando em 1; linhas vazias intermediárias são reportadas como entrada vazia para preservar correspondência, não ignoradas silenciosamente. Quebra final normal do arquivo não cria uma entrada vazia extra.
- O modo `all` exige exatamente dois DNAs; exporta resultados individuais de cada etapa **com a origem identificada** e relatório mestre, além do material AT4. Falhas downstream ficam “NÃO EXECUTADO” no relatório mestre.

### 8.4 Contrato de formatos de arquivo

**AT1–AT3 `.txt`:** um registro textual por linha, sem cabeçalho, sem separadores internos. Em AT1/AT2/AT3, preservar regra estrita dos alfabetos correspondentes; `.fasta` **não é exigido** para essas três atividades (pode ser adicionado como formato opcional claramente separado sem alterar `.txt`).

**AT4 `.txt`:** exatamente **duas linhas de sequência** (Seq1, Seq2) sem cabeçalhos; `.fasta`: exatamente dois registros com cabeçalhos `>`, permitindo sequências distribuídas em múltiplas linhas por registro (reunir fragmentos sem inventar bases). Em ambos, normalizar letras minúsculas antes de validar.

**CSV canônico das AT1–AT3:** delimitador `;`; nenhum campo supérfluo; um registro correspondente a cada linha de entrada, preservando ordem; textos dos erros rigorosamente iguais aos documentos. Exemplo:

```text
linha;status;resultado;pre_mRNA
1;OK;CORRETO;AUGGCUAAACCGUAA
2;ERRO;BUG - base inválida;NÃO GERADO
```

**AT4 quatro artefatos mínimos:**

1. `alinhamento_[modo].txt`: informações exibidas, originais, parâmetros, score, alinhamento e resumo de decisões.
2. `matriz_pontuacao_[modo].csv`: todos os scores com rótulos de linhas/colunas.
3. `matriz_traceback_[modo].csv`: direções por célula, inclusive bordas e paradas.
4. `alinhamento_[modo].csv`: `posicao;seq1;marcador;seq2;contribuicao_score`, mantendo `-` para gaps.

CSV do AT4 também terá delimitador `;` em padrão português, anunciado na interface. Se a correção automatizada do professor exigir vírgula, fornecer `--delimiter comma` **somente para AT4**. Todos os CSVs serão gravados por `csv` da biblioteca padrão, evitando erro de escape.

**JSON opcional:** campos `schema_version`, `atividade`, `entrada`, `configuracao`, `status`, `resultado`, `validacoes`, `passos`, `saidas`, `avisos`; sem tornar JSON pré-requisito para correção.

### 8.5 Uso por importação Python

```python
from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.at4 import alinhar_dna
from biocompiler.core.pipeline import executar_fluxo

r1 = transcrever_dna("ATGGCTAAACCGTAA")
r2 = maturar_pre_mrna("CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGUAAGG")
# r2.mrna_maduro será enviado à AT3 somente quando r2.ok for True
r3 = traduzir_mrna(r2.mrna_maduro) if r2.ok else None
r4 = alinhar_dna("ACGTAC", "ACGTTC", metodo="global", match=2,
                 mismatch=-1, gap=-2)
tudo = executar_fluxo("CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG",
                       "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG")
```

A API deverá expor resultados como `dataclass` tipadas/imutáveis sempre que possível, com `ok`, `status`, `resultado`, intermediários, diagnósticos e trilha de eventos. **Nenhuma importação** pode iniciar servidor, acessar arquivos, imprimir ou abrir navegador.

## 9. Arquitetura modular: núcleo e CLI independentes; frontend opcional

### 9.1 Grafo de dependências obrigatório

```text
AT1 ─┐
AT2 ─┼──> serviços de aplicação <── CLI (argparse, stdin, arquivo, texto)
AT3 ─┤                    ▲
AT4 ─┘                    └────────── Web (HTTP + Jinja2 opcional + JS)
    │
    └──> orquestrador `all` (único local que conecta etapas)
```

O diagrama expressa uma direção de uso, não autoriza dependências invertidas. **AT1, AT2, AT3 e AT4 são módulos autônomos**: cada um recebe dados em memória, calcula e devolve resultado estruturado. Um módulo AT não pode importar outro módulo AT, o orquestrador, a CLI, servidor web, arquivos de template ou bibliotecas opcionais. É permitido compartilhar tipos puros, utilitários determinísticos e a tabela genética interna. O orquestrador `all` pode importar os quatro módulos.

**Serviços de aplicação** são o ponto comum para CLI e web; chamam o núcleo, validam opções de execução, organizam lote e retornam resultados, sem UI, I/O de arquivos, transporte HTTP ou impressões no terminal. **A seleção é preguiçosa por comando:** chamar AT1 não importa nem inicializa AT2, AT3, AT4 ou `pipeline`; o mesmo vale para as demais ATs. Não criar um agregador que importe antecipadamente todos os algoritmos. A leitura de TXT/FASTA e a escrita de CSV/TXT/JSON pertencem a adaptadores independentes. A API importável também pode chamar diretamente os módulos AT.

**CLI é uma interface independente**, não um servidor: `python -m biocompiler at1`, `at2`, `at3`, `at4`, `all`, `--help` e todos os exportadores funcionam com **somente Python e sua biblioteca padrão**. A CLI não pode importar `biocompiler.webserver`, `jinja2`, templates ou componentes visuais — nem durante a inicialização. O `__main__.py` precisa de importações preguiçosas: somente `serve` carrega o pacote web. O subcomando `serve` pode requerer a instalação opcional de Jinja2 e, se ausente, deve falhar com mensagem clara, sem impedir os demais comandos.

**Frontend reutiliza o núcleo que a CLI já utiliza**, mas **não chama a CLI por subprocessos**, não faz scraping da saída textual e não duplica a lógica dos algoritmos no JavaScript. O backend web chama os mesmos serviços Python da CLI, retornando resultados estruturados por JSON. A UI consome esses resultados e reproduz eventos sem recalcular scores, classificações, tradução ou splicing. Uma falha/remoção total da pasta web não pode quebrar testes acadêmicos, CLI, API Python ou exportação.

### 9.2 Estrutura sugerida (pequena e sem sobrearquitetura)

```text
biocompiler-studio/
├── README.md
├── main.py                            # atalho: python main.py ≡ python -m biocompiler
├── requirements-web.txt               # OPCIONAL: Jinja2; só para `serve`
├── biocompiler/
│   ├── __init__.py
│   ├── __main__.py                      # despacho preguiçoso CLI / serve
│   ├── modelos.py                       # dataclasses imutáveis e tipos puros
│   ├── servicos.py                      # ponto compartilhado CLI/web
│   ├── cli.py                           # argparse, input(), stdout/stderr
│   ├── io_formats.py                    # leitores TXT, FASTA, stdin
│   ├── exports.py                       # saídas TXT, CSV, JSON
│   ├── core/
│   │   ├── __init__.py
│   │   ├── at1.py                       # DNA → pré-mRNA
│   │   ├── at2.py                       # pré-mRNA → mRNA maduro
│   │   ├── at3.py                       # mRNA → proteína
│   │   ├── at4.py                       # alinhamentos local e global
│   │   ├── genetic_code.py              # tabela dos 64 códons
│   │   └── pipeline.py                  # único módulo que encadeia ATs
│   ├── webserver.py                     # carregado apenas por `serve`
│   └── web/
│       ├── templates/                   # Jinja2: montagem visual, sem algoritmo
│       └── static/                      # CSS, JS, SVG originais
├── examples/                            # fixtures independentes de UI
├── tests/                               # unittest padrão (sem Jinja2)
└── docs/                                # especificação e rastreabilidade
```

Não criar serviços, interfaces, abstrações ou adaptadores genéricos só para antecipar requisitos hipotéticos. A estrutura pode ser simplificada quando isso preservar as fronteiras e os contratos públicos.

### 9.3 Política de dependências

1. **Proibidas no núcleo:** bibliotecas que realizem alinhamento, matrizes de programação dinâmica, transcrição, tradução, splicing ou reconhecimento de códons prontos. Também são vedadas dependências de UI, rede, banco de dados e de bibliotecas de terceiros em `core/`, `modelos.py`, `servicos.py`, `cli.py`, `io_formats.py` e `exports.py`.
2. **Permitidas na web, se justificadas:** Jinja2 como motor de templates é a dependência opcional recomendada. CSS/JavaScript/SVG/Canvas nativos são preferidos. Uma biblioteca adicional estritamente de apresentação exige justificativa de ganho, autorização do CTO e registro em `requirements-web.txt`; nunca resolver cálculos biológicos na camada visual.
3. **A web não é requisito para executar ou avaliar AT1–AT4.** Nenhum teste dos algoritmos, CLI ou exportações pode importar Jinja2 ou executar servidor. Testes específicos da interface são uma suíte separada e opcional, com pré-requisitos explícitos.
4. **Offline em runtime:** tanto CLI quanto web local operam sem chamadas externas, CDNs, serviços, coleta de dados, contas ou telemetria. Instalar a dependência opcional durante setup é distinto de exigir internet durante o uso.
5. **Testes com biblioteca padrão:** `python -m unittest discover -s tests -v`. Aceite adicional de isolamento: `python -S -m biocompiler --help`, importações diretas dos quatro ATs com `python -S`, e execução CLI em fixture com `python -S` (o `-S` evita carregar pacotes de terceiros via `site`).

### 9.4 Contrato de API e modos independentes

- `from biocompiler.core.at1 import transcrever_dna` funciona sem importar AT2/3/4.
- Idem para `maturar_pre_mrna`, `traduzir_mrna`, `alinhar_dna`.
- `biocompiler.core.pipeline.executar_fluxo` é opcional para qualquer AT individual; recebe dados e chama componentes somente se o fluxo for solicitado.
- `servicos.py` define a mesma semântica de entrada, resultado e rastro para CLI e web; formatos de serialização ficam fora das regras biológicas. **Cada chamada importa apenas o módulo AT selecionado**; as demais ATs podem estar ausentes/quebradas sem impedir a execução da tarefa escolhida.
- AT4 deve funcionar sozinho sem AT1–AT3. O modo completo chama AT4 em paralelo **lógico**, sobre os DNAs originais, sem condicionar alinhamento ao sucesso da tradução.

## 10. Modelo de eventos para passo a passo sem custo excessivo

Cada algoritmo pode opcionalmente emitir eventos estruturados `fase`, `tipo`, `posicao`, `entrada_observada`, `candidatos`, `decisao`, `saida_parcial`, `explicacao`. Exemplos:

- AT1: `BASE_VALIDADA`, `START_ENCONTRADO`, `CODON_LIDO`, `STOP_EM_FASE`, `STOP_FORA_DE_FASE`, `T_PARA_U`, `RESULTADO`.
- AT2: `GU_CANDIDATO`, `AG_CANDIDATO`, `BRANCH_TESTADO`, `INTRON_SELECIONADO`, `EXONS_UNIDOS`, `CAP_ADICIONADA`, `POLIA_ADICIONADA`.
- AT3: `CAP_VALIDADA`, `POLIA_VALIDADA`, `AUG_ENCONTRADO`, `CODON_TRADUZIDO`, `STOP_ENCONTRADO`, `PROTEINA_GERADA`.
- AT4: `BORDA_INICIALIZADA`, `CELULA_CALCULADA`, `DIRECAO_ESCOLHIDA`, `TRACEBACK_PASSO`, `ALINHAMENTO_FINAL`.

Para sequências longas, não salvar cópia integral da matriz ou da fita **a cada passo**. Guardar somente dados mínimos/decisões e reproduzir incrementalmente; tornar o rastreamento verboso opcional e limitar renderização individual na UI. Os valores finais e as matrizes AT4 permanecem integralmente disponíveis, salvo limite honesto e configurável de recursos do dispositivo.

## 11. Demonstrações preparadas e evidência técnica

### 11.1 Exemplo integrado que realmente atravessa as três fases

Usar o DNA abaixo como **um dos exemplos de integração**, e uma variação com uma única substituição na parte exônica como Seq2:

```text
Seq1 (DNA): CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG
Seq2 (DNA): CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG
```

- AT1 encontra `ATG`, STOP terminal `TAA` em fase e realiza `T→U` no DNA inteiro.
- AT2 detecta o íntron de **30 nt** `GU` + `C`×10 + `A` + `C`×15 + `AG`; a posição da adenina é **16 nt antes** do primeiro nucleotídeo do AG, dentro de 10–30. As sequências processadas são `CCAUGGCUAAACCGUAAGG` e `CCAUGGCUAAUCCGUAAGG` (o `GG` final é uma 3′ UTR didática, que também mantém inequívoca a contagem textual das 100 adeninas); em cada uma são adicionados `m7Gppp` e 100 adeninas.
- AT3 lê `AUG GCU AAA CCG UAA` na Seq1 → `Met-Ala-Lys-Pro`; na Seq2 lê `AUG GCU AAU CCG UAA` → `Met-Ala-Asn-Pro`. A diferença de uma base produz um contraste claro sem exigir inferência biológica fora do exercício.
- AT4 compara os **DNAs originais**, evidencia a substituição em alinhamento local/global, score e matriz; o exemplo não depende de bibliotecas de alinhamento.

**Observação:** este é um caso de demonstração construído para a gramática do trabalho, não uma anotação de gene biológico real. Validar no núcleo implementado, não codificar o resultado como exceção especial.

### 11.2 Caso de verificação da AT4 fornecido no enunciado

```text
Seq1 = ACGTAC
Seq2 = ACGTTC
match = 2; mismatch = -1; gap = -2
GLOBAL: ACGTAC / ACGTTC; 5 matches, 1 mismatch; score 9.
```

Todos os valores da matriz, inclusive `F(6,6) = 9`, traceback e CSV devem coincidir com a recorrência descrita; não basta exibir somente o score correto.

### 11.3 Roteiro para apresentação ao professor (5–8 minutos, ajustável)

1. **30–45 s:** abrir o modo completo e explicar a arquitetura: quatro implementações algorítmicas independentes com um fluxo integrado.
2. **60–90 s:** executar o par de DNAs de demonstração em modo rápido, mostrando que os resultados das três etapas e o alinhamento surgem corretamente.
3. **60 s:** clicar em uma base diferente e abrir o comparador de proteína para ver `Lys` versus `Asn`.
4. **60–90 s:** inspecionar splicing e a régua do branch point de 10–30 nt; mostrar início GU, branch A, término AG, remoção e 100 A.
5. **60–90 s:** abrir AT4, demonstrar o cálculo manual de uma célula e o desempate, depois visualizar traceback animado. Conferir o exemplo global score 9.
6. **45–60 s:** abrir terminal e executar `python -m biocompiler at1`, `at2`, `at3` ou `at4` a partir de arquivos; mostrar arquivos CSV com textos exatos.
7. **30 s:** abrir Casos de Teste e demonstrar erro específico e que nenhuma saída indevida é produzida.

## 12. Testes, auditoria e critérios de aceite

**Conjunto obrigatório de testes:**

- AT1: seis casos do documento, base inválida, START ausente, STOP ausente, STOP fora de fase, STOPs múltiplos, flancos antes/depois da ORF, transcrição T→U da sequência inteira, arquivo multirregistro e pontuação das posições.
- AT2: quatro casos do documento, limites exatos **10 e 30**, distâncias 9 e 31 inválidas, múltiplos A, múltiplos GU/AG, remoção inclusiva, múltiplos íntrons sem sobreposição, CAP literal `m7Gppp`, cauda de exatamente 100 A e arquivo multirregistro.
- AT3: seis casos do documento, os 64 códons, STOP nos três valores, primeiro AUG, STOP fora de fase, CAP alterada, cauda com 99/100/101 A, aminoácido de três letras, não traduzir regiões flanqueadoras e lote.
- AT4: exemplo score `9`; local com todas as células zero; global com comprimentos diferentes; gaps; empates e prioridade; reconstrução de traceback; validação de **exatamente duas** sequências; normalização de minúsculas; parâmetros não numéricos; `.txt` e FASTA; exportações de matrizes completas.
- Integração: exemplo integrado Seq1/Seq2 acima; erro AT1 não produz AT2/AT3 artificiais; falha AT2 bloqueia só AT3 daquela amostra; erro numa sequência não bloqueia a outra; AT4 funciona independentemente quando ambos os DNAs são válidos; execução só individual não precisa do modo completo.
- CLI: `--help`, argumentos, stdin, modos interativo e rápido, nomes e conteúdo dos arquivos, UTF-8, ausência de prompts em pipe, códigos de saída, erro de arquivo inexistente, preservação da ordem e teste de importação Python sem efeitos colaterais.
- UI: modo claro/escuro; responsividade; tabulação por teclado; reduced motion; pausar, pular, retroceder, resultado direto; ausência de conexão externa; consistência com saída do core; matrizes extensas navegáveis; tema e animação não alteram pontuações.

**Testes de propriedades importantes:**

- Se AT1 é válido, `len(pre_mrna) == len(dna)` e `pre_mrna == dna.replace('T','U')`.
- Se AT2 é válido, `mrna_maduro == 'm7Gppp' + rna_sem_introns + 'A'*100`, e todo nucleotídeo excluído pertence a intervalo de íntron selecionado.
- Se AT3 é válido, o número de aminoácidos coincide com o número de códons desde AUG até antes do STOP; tabela nunca traduz STOP.
- Se AT4 é válido, remover gaps da reconstrução recupera as bases alinhadas; em global, recupera as **duas sequências inteiras**. Recomputar a soma de matches/mismatches/gaps reproduz o score do algoritmo.
- Para mesma entrada e parâmetros, CLI, API e web apresentam o mesmo status, valores intermediários e score.

**Condições de conclusão da entrega:**

1. Todos os casos previstos pelos quatro enunciados passam **sem reconhecer o nome/índice do caso**.
2. Cada atividade executa separadamente pela CLI, API e interface web.
3. `all` executa as quatro, com dependências corretas e sem fingir que AT4 é parte da tradução.
4. Lotes AT1/AT2/AT3 e par AT4 funcionam para arquivos reais, com exportações fiéis.
5. Matriz AT4 e traceback exibidos e exportados integralmente; modo local e global funcional.
6. Controle de velocidade, passo, pausa e **pular para o resultado** funciona em todas as atividades.
7. **Núcleo, CLI e API Python** rodam offline apenas com Python padrão, inclusive sem Jinja2. A **interface web opcional** pode exigir instalar Jinja2, mas funciona offline após a instalação.
8. Os erros, as ambiguidades das convenções didáticas e os limites computacionais estão documentados.
9. README contém comandos reais, estrutura, instalação, caso de demonstração, critérios do professor e roteiro de apresentação.

## 13. Ordem de implementação recomendada

**Fase A — Correção acadêmica:** implementar módulos AT1–AT4 como funções puras e tabela genética manual; criar casos de teste; resolver regras didáticas e compatibilidade textual; implementar exportadores.

**Fase B — CLI funcional:** leitura `txt/fasta`, `argparse`, `stdin`, execução individual/integrada, `--interactive`, `--step`, geração automática de arquivos e códigos de saída; testar antes da UI.

**Fase C — Orquestração:** conectar AT1→AT2→AT3, AT4 paralelo, duas amostras, falhas independentes, eventos estruturados; validar exemplo integrado.

**Fase D — Frontend opcional:** Home completa, editores, validação, resultados, AT1/AT2/AT3, AT4 matriz e traceback; tema responsivo. A CLI e todos os algoritmos já devem estar corretos; instalar Jinja2 aqui não altera requisitos do núcleo.

**Fase E — Diferenciais:** animação molecular, régua interativa do branch point, inspector de células, laboratório de mutações, comparador, modo apresentação e exportação completa.

**Fase F — Auditoria final:** teste cruzado CLI/web/API, casos do professor, acessibilidade e performance; documentação e roteiro de demonstração; remover dependências e código duplicado.

## 14. Proibições e compromissos de engenharia

- **Não** instalar nem importar bibliotecas que executem splicing, tradução genética, detecção de ORFs, alinhamento, pontuação/traceback ou preenchimento de matriz por conta do estudante.
- **Não** usar hardcode de respostas, lista de sequências do professor como reconhecedor de casos, heurísticas que retornem diagnósticos sem verificar regras, nem matrizes/alinhamentos pré-fabricados.
- **Não** exigir internet, registro/login, banco de dados, IA, chaves de API, CDN ou serviços externos.
- **Não** transformar convenções didáticas em alegações biológicas universais.
- **Não** sacrificar o funcionamento do terminal em favor da interface bonita, nem fazer CLI/API importar frontend ou Jinja2.
- **Não** substituir erro específico por mensagem genérica; **não** completar automaticamente dados ausentes sem o usuário saber.
- **Não** limitar AT4 a apenas Smith–Waterman ou omitir Needleman–Wunsch, matriz de traceback ou exportações.
- **Não** renderizar animações longas como requisito para receber a resposta.

**Entrega conceitual:** uma plataforma unificada, demonstrável e auditável na qual a beleza do frontend explica o algoritmo — e o algoritmo continua correto e executável quando o frontend está fechado.

---

## 15. Rastreabilidade aos documentos de origem

- **AT1 — BioCompiler 1.0.pdf:** páginas 1–6, seções 2–14 (entrada em lote, ATG/STOP, transcrição, seis diagnósticos, saída na tela e em arquivo); páginas 8–9 ilustram a atividade.
- **AT2 — 4.2 Especificacao_BioCompiler_2_0 2026.2_VERSION 2.docx:** páginas 1–4, seções 2–14 (GU/A/AG, branch 10–30, splicing, CAP, 100 A, quatro diagnósticos, lote e saída).
- **AT3 — Ribossomo.pdf:** páginas 3–9, seções 2–14 (CAP/cauda, AUG/STOP, tabela genética, seis diagnósticos, lote e saída); página 2 apresenta fluxograma ilustrado.
- **AT4 — Smith-Waterman.pdf:** páginas 2–7, seções 1–4 (entrada/validação, Smith–Waterman, Needleman–Wunsch, desempate, matrizes, traceback, complexidade e saída); páginas 8–10 apresentam modelos de tela e quatro exportações mínimas.

**Toda regra de extensão, especialmente nas ambiguidades da seção 5, deverá ser marcada na implementação e na documentação como “política de projeto — não especificada formalmente pelo professor”.**
