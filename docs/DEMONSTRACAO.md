# Roteiro de Demonstração — BioCompiler Studio

Duração prevista: **5–8 min** (7 passos práticos).

Antes de começar, inicie o servidor web local em um terminal:

```text
python3 main.py serve --port 8765
```

Sequências usadas no caso integrado (SPEC §11.1):
- **Seq1 (referência):** `CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG`
- **Seq2 (variante):** `CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG`

## Passo 1 — Abertura no Laboratório Completo

**Ação:** Abrir `http://127.0.0.1:8765/` e clicar em **Carregar exemplo integrado** e depois em **Executar**.

**Resultado esperado:** As duas cadeias (`Seq1` e `Seq2`) são processadas de ponta a ponta (`AT1 → AT2 → AT3`), e a aba **Mapa da expressão gênica** exibe ambas como `Cadeia completa`.

**Fala:** O BioCompiler Studio executa as quatro atividades de forma isolada ou encadeada. Aqui estamos no Laboratório Completo comparando duas sequências de DNA que diferem em um único nucleotídeo.

## Passo 2 — Transcrição (AT1) passo a passo

**Ação:** Acessar `http://127.0.0.1:8765/at1?seq=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG&modo=guiado&executar=1` e avançar pelo player até o resultado final.

**Resultado esperado:** O player destaca a substituição `T → U`, identifica o códon `AUG` na posição 2 e o códon de parada `UAA` em fase na posição 44, gerando o pré-mRNA completo sem descartar os flancos.

**Fala:** Na AT1, a transcrição converte a fita inteira e valida o quadro de leitura aberto do primeiro `AUG` até o primeiro `STOP` em fase, usando apenas implementação própria em Python padrão.

## Passo 3 — Splicing e maturação (AT2): íntron de 30 nt e branch 16 posições antes (15 nt entre)

**Ação:** Acessar `http://127.0.0.1:8765/at2?seq=CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGUAAGG&modo=guiado&executar=1` e inspecionar os eventos no SpliceLab.

**Resultado esperado:** O núcleo identifica o íntron de **30 nt** (`posicao_gu = 8` até o final de `AG` com `posicao_ag = 36`, em base 0) e o branch point `A` em `posicao_branch = 20`. O `A` está **16 posições antes** do `AG` (`36 − 20 = 16`, conforme a frase da SPEC §11.1 — 16 nt de deslocamento), havendo **15 nt entre** eles (`36 − 20 − 1 = 15`), que é o valor exibido na régua D009 da tela (`Branch → AG: 15`, dentro da janela 10–30). Em seguida une os éxons em `CCAUGGCUAAACCGUAAGG` e adiciona `m7Gppp` e a cauda de 100 adeninas.

**Fala:** Na AT2, o inspetor mostra exatamente por que o íntron de 30 nt foi removido: em base 0, o `A` na posição 20 fica 16 posições (16 nt de deslocamento) antes do `AG` na posição 36, resultando em 15 nucleotídeos entre os dois sítios na régua D009 (janela válida de 10 a 30).

## Passo 4 — Tradução (AT3) e impacto da variante no Comparador

**Ação:** Acessar `http://127.0.0.1:8765/?seq1=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG&seq2=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG&executar=1&aba=Comparador` (ou clicar na aba **Comparador molecular**).

**Resultado esperado:** O comparador exibe lado a lado os quatro níveis moleculares e destaca a diferença observada: na `Seq1`, a proteína traduzida é **Met-Ala-Lys-Pro**; na `Seq2`, a alteração no éxon resulta em **Met-Ala-Asn-Pro**.

**Fala:** Sem rotular categorias clínicas no JavaScript, o Comparador projeta os resultados reais da API nos quatro níveis e evidencia como uma troca pontual altera o terceiro aminoácido de `Lys` para `Asn`.

## Passo 5 — Laboratório de mutações e retorno para AT4

**Ação:** Ainda na aba **Comparador molecular**, selecionar `seq2`, operação `substituir`, índice `0`, base `G`, clicar em **Aplicar mutação** e depois em **Alinhar com origem** (ou abrir `http://127.0.0.1:8765/at4?seq1=ACGTAC&seq2=ACGTTC&executar=1`).

**Resultado esperado:** Ao mutar, o laboratório reenvia a entrada para `/api/all` e atualiza o comparador e o histórico de mutações. No alinhamento do exemplo `ACGTAC` × `ACGTTC` em `/at4`, o resultado exibe **Score 9** (global e local).

**Fala:** Cada mutação editada no laboratório reexecuta o núcleo Python pela API e permite enviar origem contra variante diretamente para a matriz da AT4.

## Passo 6 — Matriz e traceback na AT4 + Modo apresentação

**Ação:** Na página `http://127.0.0.1:8765/at4?seq1=ACGTAC&seq2=ACGTTC&modo=guiado&executar=1`, avançar no player pelos passos da matriz e clicar em **Apresentação** no topo.

**Resultado esperado:** A matriz exibe bordas inicializadas, preenchimento célula a célula com candidatos da API no inspetor, caminho ótimo de traceback em setas SVG e alinhamento progressivo com **Score 9**. O modo apresentação oculta a barra lateral e amplia a tipografia.

**Fala:** Toda a programação dinâmica — matriz, critérios de desempate e traceback — vem do núcleo Python; o navegador apenas anima e inspeciona os eventos.

## Passo 7 — Casos oficiais, histórico e metodologia

**Ação:** Navegar rapidamente por `http://127.0.0.1:8765/casos`, `http://127.0.0.1:8765/historico` e `http://127.0.0.1:8765/sobre`.

**Resultado esperado:** A página de casos lista todas as entradas dos enunciados AT1–AT4; o histórico registra as execuções da sessão; e Sobre/Metodologia documenta regras, limites e decisões.

**Fala:** Com isso cobrimos as quatro atividades, o fluxo integrado e as garantias de reprodutibilidade entre CLI, API e interface web.

## Plano B — Demonstração integral via CLI (sem interface web)

Caso o navegador ou `Jinja2` não esteja disponível no ambiente de apresentação, todos os passos acima podem ser demonstrados diretamente no terminal com apenas Python padrão:

```bash
python3 main.py at1 --input exemplos/at1_casos.txt --no-save   # saída 2
python3 main.py at2 --input exemplos/at2_casos.txt --no-save   # saída 2
python3 main.py at3 --input exemplos/at3_casos.txt --no-save   # saída 2
python3 main.py at4 --input exemplos/at4_par.fasta --explain --no-save
python3 main.py all --input exemplos/integrado.txt --no-save
```
