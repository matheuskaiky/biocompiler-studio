# Roteiro de Demonstração — BioCompiler Studio

Duração prevista: **5–8 min** (7 passos práticos).

Antes de começar, inicie o servidor web local em um terminal:

```text
python3 main.py serve --port 8765
```

Sequências usadas no caso integrado (SPEC §11.1):
- **Seq1 (referência):** `CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG`
- **Seq2 (variante):** `CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG`

## Passo 1 — Abertura no Laboratório Completo e detalhe no Mapa

**Ação:** Abrir `http://127.0.0.1:8765/?seq1=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG&seq2=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG&executar=1`, abrir a aba **Mapa da expressão gênica** e clicar em **Detalhar** no cartão da AT2.

**Resultado esperado:** As duas cadeias (`Seq1` e `Seq2`) são processadas de ponta a ponta (`AT1 → AT2 → AT3`), o Mapa exibe ambas como `Cadeia completa` com 6 botões **Detalhar**, e o painel detalhado da AT2 abre no próprio Laboratório exibindo os sítios, o íntron e a régua D009.

**Fala:** O BioCompiler Studio abre direto no Laboratório Completo comparando duas sequências de DNA que diferem em um único nucleotídeo. Pelo botão **Detalhar**, inspecionamos cada etapa sem perder a visão geral do fluxo.

## Passo 2 — Transcrição (BioCompiler 1.0 / AT1) e envio para a etapa seguinte

**Ação:** Acessar `http://127.0.0.1:8765/at1?seq=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG&modo=guiado&executar=1`, avançar pela **linha do tempo** ou pelo botão próximo do player e depois clicar em **Pular para o resultado** e em **Enviar para BioCompiler 2.0**.

**Resultado esperado:** O cursor desliza pela fita de DNA até o `ATG` (posição 2), forma as trincas a partir do START, marca o `STOP` em fase na posição 44 e, no evento `T_PARA_U`, o pré-mRNA nasce abaixo do DNA com alinhamento posicional exato (`T → U`). Clicar em **Enviar para BioCompiler 2.0** abre `/at2` já preenchida com o pré-mRNA gerado.

**Fala:** Na AT1, a transcrição converte a fita inteira e valida o quadro de leitura aberto do primeiro `ATG` até o primeiro `STOP` em fase. Ao enviar o produto para o BioCompiler 2.0, o pré-mRNA vira a entrada da maturação.

## Passo 3 — Splicing e maturação (BioCompiler 2.0 / AT2) e envio para tradução

**Ação:** Em `http://127.0.0.1:8765/at2?seq=CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGUAAGG&modo=guiado&executar=1`, avançar pelos passos de splicing e maturação até **Pular para o resultado** e clicar em **Enviar para o Ribossomo**.

**Resultado esperado:** O núcleo identifica o íntron de **30 nt** (`posicao_gu = 8` até a base 37 inclusive, com `posicao_ag = 36` marcando o início do `AG`, em base 0) e o branch point `A` em `posicao_branch = 20` (**16 nt** de deslocamento antes do `AG`, `Branch → AG: 15` na régua D009). Na mesma fita, o íntron se ergue e esmaece enquanto os éxons se encostam em `CCAUGGCUAAACCGUAAGG`, o quepe `m7Gppp` se encaixa no 5′ e a cauda `A×100` surge no 3′ com legenda de `30 nt` removidos, `19 nt` preservados e `m7Gppp + 100 A` adicionados. Clicar em **Enviar para o Ribossomo** abre `/at3` com o mRNA maduro.

**Fala:** Na AT2, vemos na mesma fita o que foi removido, preservado e adicionado, com a régua D009 comprovando os 15 nucleotídeos entre o `A` e o `AG` (16 posições antes). Em seguida enviamos o mRNA maduro para o Ribossomo.

## Passo 4 — Tradução no Ribossomo (AT3) e impacto no Comparador

**Ação:** Em `/at3` (ou abrindo `http://127.0.0.1:8765/at3?seq=m7GpppCCAUGGCUAAACCGUAAGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&modo=guiado&executar=1`), percorrer a tradução pela **linha do tempo** e depois abrir `http://127.0.0.1:8765/?seq1=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG&seq2=CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG&executar=1&aba=Comparador`.

**Resultado esperado:** Na AT3, o **ribossomo** posiciona-se no `AUG`, avança de 3 em 3 bases formando a cadeia polipeptídica (**Met-Ala-Lys-Pro**) com ligação visual códon ↔ aminoácido e para no `STOP`. No **Comparador molecular**, a troca pontual na `Seq2` aparece lado a lado nos quatro níveis, alterando a proteína para **Met-Ala-Asn-Pro**.

**Fala:** O ribossomo avança exatamente de três em três nucleotídeos até o `STOP` em fase, e clicar em um aminoácido destaca o códon de origem. No Comparador, a diferença pontual entre `Seq1` e `Seq2` se traduz na troca de `Lys` para `Asn`.

## Passo 5 — AT4: preenchimento, inspetor e comparação lado a lado

**Ação:** Abrir `http://127.0.0.1:8765/at4?seq1=ACGTAC&seq2=ACGTTC&modo=guiado&executar=1`, avançar no preenchimento, clicar em uma célula da matriz e acionar **Lado a lado** na barra da visualização.

**Resultado esperado:** A matriz exibe o preenchimento célula a célula, o inspetor mostra os candidatos vindos de `/api/at4/celula` com destaque das dependências, o traceback marca o caminho ótimo com **Score 9**, e a vista **Lado a lado** exibe os métodos Local (Smith–Waterman) e Global (Needleman–Wunsch) em paralelo.

**Fala:** Toda a programação dinâmica — matriz, critérios de desempate e traceback — vem do núcleo Python; o navegador apenas anima, inspeciona dependências e compara Local e Global lado a lado.

## Passo 6 — Modo Apresentação e controles de acessibilidade

**Ação:** Na barra superior em vidro fino, clicar em **Apresentação** e alternar o tema entre escuro e claro.

**Resultado esperado:** O modo **Apresentação** oculta a barra lateral de navegação, amplia a tipografia da área principal e exibe o rodapé de atalhos; a alternância de tema preserva contraste legível em controles e superfícies de dados.

**Fala:** Para projeção em sala, o modo Apresentação limpa o entorno da tela mantendo os controles do player e a legibilidade nos dois temas.

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
