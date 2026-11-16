# Auditoria independente final — Etapa 7c.6 (commit `b9d6272`)

Projeto `/Volumes/Forja/ptb-racial-brasil` · data: 2026-10-10 · HEAD auditado: `b9d6272` (pai `8314417`; versão anterior ao amend: `a38f550`, no reflog).

**Scripts** (nesta pasta; rodar de qualquer lugar com `PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_v1_20261010.py`):

- `audita_7c6_final_v1_20261010.py`: orquestrador. Grava `comparacao_7c6_final_v1_20261010.csv`.
- `audita_7c6_final_lib_v1_20261010.py`: utilitários. O git fica restrito a comandos de leitura e há uma trava de independência.
- `audita_7c6_final_{K,L,M}_v1_20261010.py`: um módulo por bloco.
- `audita_7c6_final_web_v1_20261010.py`: GETs públicos. Grava `web_7c6_final_v1_20261010.json`.
- `audita_7c6_final_excecao_L2b_v1_20261010.py`: a única leitura do `checa_7b_v11`, feita por último. Grava `excecao_L2b_7c6_final_v1_20261010.json`.
- `etapa7c6_01_resumo_copia_saida_auditor.py`: cópia do gerador do RESUMO com só o caminho de saída trocado (L3). Gerou `RESUMO_ETAPA7C6_reproduzido_v1_20261010.md`.

**Saídas auxiliares:**

- `k3_arquivos_commit_…csv`
- `l1_32_logs_…json`
- `l4_commits_por_id_…csv` (os 226 ids, com o JSON e o recálculo lado a lado)
- `m3_maiores_blobs_…csv`
- `m4_referencias_nao_rastreadas_…csv`
- `m7_m10_termos_…json`

## Resultado

**116 verificações; 113 OK; 3 falhas, todas de redação ou precisão menor.** Nenhuma falha afeta números, commit, dados ou licença.

| Bloco | Tema | Verificações | OK |
|---|---|---|---|
| K | Integridade do commit b9d6272 | 11 | 11 |
| L | Afirmações do RESUMO e do relato final, reprodução e commits | 80 | 77 |
| M | Fatos das decisões pendentes (levantamento) | 25 | 25 |
| **Total** | | **116** | **113** |

As três afirmações do relato final ao usuário **conferem**:
- **(a)** 4 de 21 números calculados na 7c.3; 17 vêm das Etapas 6 e 6b (L2a);
- **(b)** 4 rodadas e 178/178; autoauditoria 100/100 (L2b);
- **(c)** o material suplementar da PLoS Med não traz o checklist; o docx vem do site do RECORD e é CC BY 4.0 (L2c.01–L2c.04).

## Falhas (com evidência)

1. **L1.49, seção "Pendências" 4 do RESUMO.** O RESUMO diz: "A autoauditoria e o gerador deste RESUMO leem o .csv do auditor, então não rodam num clone limpo."
   - **Para o gerador, vale:** `scripts/resumos/etapa7c6_01_resumo.py:26` faz `pd.read_csv(...)` incondicional.
   - **Para a autoauditoria, não:** `scripts/etapa7b_checa.py:715–716` só lê o CSV do auditor com `if aud76.exists():`. O mesmo vale para 7b1–7b3 e 7c1–7c4 (L201–L231, L710–L737). Sem o arquivo, o checa pula a checagem.
   - O checa também não roda num clone limpo, mas por outro motivo: lê `outputs/tables/`, que o git ignora.
2. **L1.53, seção 4 do RESUMO.** O RESUMO diz: "9 na Etapa 6 (2285207): tercis nacionais e índice contínuo, `tab_e3_02_*_rs`".
   - Os 3 ids `RP_int_5pp_indice_continuo_*` vêm de `outputs/tables/tab_e3_03a_indice_continuo_rs_v1_20261008.csv`, que não segue esse padrão.
   - A contagem (9) e o commit (2285207) estão corretos (L2a.03–L2a.04).
3. **L2c.05, seção 2 do RESUMO e `docs/referencias/ATRIBUICAO.txt`.** O RESUMO diz: "a versão 4.0 vem só do link do site; o docx e o artigo dizem apenas 'CC BY'".
   - O docx diz só "CC BY" (L1.38).
   - O artigo também aponta a versão. Na página da PLOS, a declaração de copyright liga "Creative Commons Attribution License" a `http://creativecommons.org/licenses/by/4.0/`. O XML do artigo no PMC (PMC4595218) tem `<license xlink:href="http://creativecommons.org/licenses/by/4.0/">`.
   - A conclusão (CC BY 4.0) não muda. Só fica mais bem fundamentada.

## Ressalvas (não reprovam)

- **L1.09 e L1.06, sobre "Só o JSON e o .md dos números-chave mudam".** Também mudaram, só em rótulos ou metadados:
  - o título do docx das tabelas ("package v10_20261009" → "v11_20261009");
  - as linhas 1 e 30 de `data_code_availability.md`;
  - o rótulo de `legendas_figuras.md` e o `MANIFEST.md`;
  - os bytes de `Submissao/ESM_1–4` (data de criação).

  Tabelas, rodapés, figuras e texto dos ESM ficaram idênticos à v10: 20 CSV byte a byte, 27 abas e 14.195 células, 5 PDFs no texto, 14 imagens nos pixels.
- **L1.13, sobre "um clone limpo já monta a S8".** Vale para a entrada do RECORD: o bloco S8 do `etapa7b_02` (L560–L584) só lê o docx versionado. Mas o `etapa7b_02` inteiro lê 41 tabelas de `outputs/tables/` antes da S8 e não roda num clone limpo.
- **L1.34.** A abertura da seção 1 diz "sem ler os resultados da autoauditoria (exceção na rodada 3)". A exceção da rodada 3 foi ler o *código* do checa (L566–L612), não resultados. O parágrafo da rodada 3 descreve isso corretamente.
- **L1.27.** O máximo de 13 colunas empata entre `etapa5/audit_e5_compara_log_v1_20261008_antes.txt` e `…_depois.txt`. O RESUMO cita só o `_antes`.
- **L1.17.** O LEIAME diz que "todos, exceto o etapa7c5b_01, leem B.V". Isso vale para os 10 movidos, mas o `etapa7c6_01` da mesma pasta também fixa `V = "v11_20261009"`.
- **Não verificáveis:**
  - "nada foi movido" (`._*`): a contagem atual coincide com a da rodada 1;
  - "desde a rodada 3 o etapa7b_lib.py só mudou na docstring": o estado da rodada 3 não está versionado, e o próprio auditor anterior registra que não guardou cópia. Verificável: a lib é idêntica em a38f550 e b9d6272;
  - "os Métodos v5.1 dizem 'among births with a known month of first visit (1–9)'": o documento está fora do projeto, e "first visit" não aparece em nenhum arquivo;
  - "RSP 2026;60:e44": é recomendação de redação; só aparece em RESUMOs anteriores.
- **L5, limitação de reprodutibilidade:** o checa falharia hoje (ver abaixo), e nem o RESUMO nem o LEIAME avisam disso.

## Exceções e exposições à independência

1. **Exposição acidental.** Um `grep -rn "dot_clean" scripts …` (rodado antes de eu excluir o arquivo das buscas) mostrou 3 linhas (L326–L328) de `scripts/etapa7c6_02_audita_final.py`. O arquivo é a autoauditoria do autor, criada às 10:15, depois do início desta auditoria. As linhas tratam de uma checagem "M1.02" sobre quarentena e dot_clean. Os fatos correspondentes (xattr `com.apple.quarantine` com agente Chrome; `dot_clean` só no `etapa7b_04`) eu já tinha levantado antes, com `xattr` e `grep` próprios. Depois disso, todas as buscas excluíram o arquivo, e a lib desta auditoria recusa abri-lo.
2. **Exceção registrada do L2b.** Li `outputs/manuscrito/checa_7b_v11_20261009.csv` (disco e blob de b9d6272) só para o L2b, **depois** de concluir K, L (exceto L2b.04–05), M e a web.
   - Encontrei 100 linhas, colunas `verificacao, ok, valor`, ok=True em todas.
   - A tabela "Checagens da 7c.6" do RESUMO é igual às 11 linhas "7c.6" do CSV.
   - Na mesma leitura conferi a forma do arquivo para o K3 (K3.05).
   - O `checa_7b_v10` (R100) e `outputs/manuscrito/audita_final_7c6_v1_20261010.csv` não foram abertos.
3. **L3.** O gerador do RESUMO, rodado como pedido, lê internamente o `checa_7b_v11`. Eu não abri o arquivo nesse passo.
4. **L1.54.** Para conferir "o log das análises não grava o commit", contei por etiqueta as linhas de `outputs/logs/*.log` que contêm um hash de commit. Só o `[7b_checa]` (31 linhas, em `etapa7b_20261008.log`) contém hash. Não li o conteúdo dessas linhas.

## Efeitos colaterais

- **Escrita:** só nesta pasta. Os dados sintéticos do M2 (`m2_sintetico/`) e um `__pycache__` desta pasta foram apagados por mim. Nenhum `.txt` foi gravado aqui.
- **Log do projeto:** a execução do L3 (10:16:43) acrescentou 1 linha em `outputs/logs/etapa7c6_20261008.log` (ignorado pelo git). As linhas de 10:16:32, 10:18:20, 10:19:04, 10:20:00 e 10:22:47 são de outro processo (o do autor).
- **Git:** só leitura, e `status` com `--no-optional-locks`. `.git/index` continua com mtime 2026-10-10 09:10:27, anterior a esta auditoria.
- **Arquivos do projeto:** nenhum foi modificado. Nenhum script do projeto foi executado, exceto a cópia do gerador.
- **Rede:** só GETs públicos: record-statement.org (página e docx; o docx foi lido só em memória), Europe PMC REST, NCBI E-utilities (efetch PMC4595218 e PMC11059336) e a página do artigo na PLOS. Nada do projeto foi enviado.

---

## K. Integridade do commit

- **K1, amend.**
  - `b9d6272` é `commit (amend)` de `a38f550`, com o mesmo pai, o mesmo autor e a mesma mensagem.
  - Entre as duas árvores, só 2 arquivos diferem: `outputs/RESUMO_ETAPA7C6_v1_20261009.md` e `outputs/manuscrito/_resumo7c6_texto_v1_20261009.md`.
  - Em cada um, 1 linha mudou: "Foram duas rodadas; a segunda conferiu o que mudou depois da primeira." → "Foram quatro rodadas; cada uma conferiu o que mudou depois da anterior." Confere com o que o autor afirmou; a troca inclui também o fim da frase.
- **K2, trailers e refs.**
  - A mensagem termina exatamente em `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e `Claude-Session: [session URL removed for publication]`, mais o `\n` final. O `git interpret-trailers --parse` reconhece as duas linhas.
  - Sem remoto, sem tags e sem `packed-refs`. A única ref é `refs/heads/main`.
- **K3, arquivos do commit.** Em relação a 8314417, com `-M`, são 119 entradas: A 60, M 11, R100 48, D 0. Sem detecção de renomeação: A 108, D 48, M 11.
  - **R100:** os 10 geradores (`scripts/` → `scripts/resumos/`) e 38 arquivos v10 movidos para `_arquivo_v10/`.
  - **M:** `Submissao/ESM_1–4`, `MANIFEST.md`, `data_code_availability.md`, `legendas_figuras.md`, e `etapa7b_lib`, `etapa7b_02`, `etapa7b_04` e `etapa7b_checa`.
  - **Lixo do macOS:** nenhum `._*` ou `.DS_Store` versionado, nem no commit nem em nenhuma das árvores de 27 commits (`--all --reflog`, 1.092 caminhos).
  - **Dado individual:** li o conteúdo de 117 arquivos do commit (CSV, xlsx, docx, PDF, md, py, json, txt). Não há coluna com nome de identificador (DTNASC, HORANASC, NUMERODN, CODESTAB, CNES, CNS, CPF, DTOBITO…) nem padrão de data de 1900–2024, CPF ou CNS de 15 dígitos. A maior tabela é o ESM_1 (395×15).
  - O `checa_7b_v11` (100×3) foi conferido só na exceção do L2b, sem dado individual.
- **K4, árvore de trabalho.**
  - No início (10:12): limpa, exceto **93** não rastreados em `docs/referencias/`.
  - Agora há também `scripts/etapa7c6_02_audita_final.py` e `outputs/manuscrito/audita_final_7c6_v1_20261010.csv`, do autor (criados a partir das 10:15), e esta pasta.
  - Nenhum arquivo rastreado foi modificado.

## L. Afirmações do RESUMO e do relato final

- **L1, RESUMO.** Conferi item a item contra o blob de b9d6272, que é igual ao disco.
  - **Pacote v11 e "nenhum número mudou":**
    - os 226 ids estão na mesma ordem, com `valor_bruto` exato, `valor_formatado`, descrição e origem iguais;
    - os 20 CSV (9.555 células) são idênticos byte a byte;
    - os 3 xlsx (27 abas) são iguais célula a célula;
    - o docx é igual, fora o rótulo de versão do título;
    - os 5 PDFs têm o mesmo texto;
    - as 14 imagens têm os mesmos pixels.
  - **Campos de commit:** `commit` → `commit_pacote` (= 8314417, o pai) e entraram `commit_registro` e `commit_analise`, sem vazios. O md passou de 6 para 8 colunas.
  - **Auditoria anterior** (relatório e CSV de `audit_independente/etapa7c6/`):
    - 4 rodadas e 178 linhas, 178 OK;
    - blocos A19 B12 C7 D7 E7 F9 G46 H42 I25 J4, igual à tabela do RESUMO;
    - as 6 sinalizações da 1ª execução, a falha H4.06 (rodada 2: 41/42) e a I1.08 (rodada 3: 173/174) estão como descritas;
    - o `ATRIBUICAO.txt` do commit é o blob `ee3e33b` (já com "CC BY 4.0").
  - **Código do índice:** L4–L5, L36, L39, L40, L51 e L74 de `etapa2_03_indice_acesso.py` estão como citados. Meu teste sintético (Int16 e string) mostra que 99, nulo, 0 e 10 ficam fora do numerador e do denominador.
  - **Asian:** 117.549 / 27.489.150 = 0,4276% → 0.43%, igual ao `pct_amarela_fonte` (diferença 0). O texto aprovado é idêntico nos dois ESM_1 e no `data_code_availability.md`.
  - **Os 41 `.txt`:**
    - foram adicionados em 8314417 e não mudaram depois;
    - não têm padrão de dado individual;
    - o máximo é de 163 linhas, em `etapa7b3/relatorio_etapa7b3_v1_20261009.txt`;
    - o máximo de colunas é 13 (empate _antes/_depois); a medida bruta é de 80 tokens, em `etapa4b/log_duckdb_v1_20261008.txt`.
  - **MESPRENAT de 2014:** há 2.607 registros com outros códigos, todos em 2014. A S7a diz "any other value excluded".
  - **H2 e os logs:** as 35 tabelas de origem dos 215 ids lidos direto têm uma linha de log do próprio script de origem a ≤3 s do mtime.
  - **Geradores e travas:**
    - os 10 geradores são R100, com blob igual a `8314417:scripts/<nome>`; o LEIAME está versionado;
    - o `etapa7b_04` tem 0 `assert` e 2 `raise RuntimeError` (L28, L50);
    - o congelamento está no código (`commits_analise`, L188–L233);
    - o checa tem 6 casos sintéticos.
  - **RECORD:**
    - o docx tem 17.088 bytes, MD5 `d50bd10feb3c20398ccce6f3c27b7777` e mtime local 2026-10-09 10:02;
    - a frase de licença está no docx, que não cita "4.0";
    - o bloco da seção 2 é igual ao `ATRIBUICAO.txt` versionado;
    - o ESM_3 traz a atribuição.
  - **Seção 4:** as tabelas de distribuição, a de "onde diferem" (9 pares, 139 ids) e a de exemplos conferem com o JSON. A contagem também confere: 11 derivados e 215 lidos direto.
  - **Pendências:** a quarentena com agente "Chrome" está nos PDFs S7/S8 da v11, e não há remoto.
- **L2a.** Dos 21 ids novos da v7 (JSON adicionado em 3092186), só os 4 `n_excl_estciv_*` são derivados no pacote: N(M2) − N(M3). O cálculo entra no `etapa7b_01_tabelas.py` em 3092186 e não existe em 2cde6a0. Os outros 17 são lidos direto das tabelas:
  - **9 da Etapa 6:** `tab_e3_02_interacao_rs`, `tab_e3_02_wald_rs` e `tab_e3_03a_indice_continuo_rs`. O mtime é 08/10 23:20:14 e o 1º commit depois é 2285207. O último commit do `etapa3_02_knol.py` até 3092186 também é 2285207, e a opção `--rs` só existe a partir dele. O log `[3.2-3.6_knol_rs]` está nos logs da Etapa 6.
  - **8 da Etapa 6b:** `tab_e6b_01_modelos_m1m3`. O mtime é 09/10 09:42:10 e o 1º commit depois é 6905d9d; o `etapa6b_01_modelos_rs.py` só tem o commit 6905d9d.
  - Nenhuma tabela de `outputs/tables` tem mtime na janela da 7c.3.
- **L2b.**
  - 4 rodadas e 178/178 (relatório e CSV do auditor).
  - Para o 100/100, contei as execuções de `ok()` no código do checa (AST: 91 chamadas; laços ×3, ×5, ×4; 8 condicionais, todas com o CSV do auditor existente) e cheguei a **100**. Depois, na exceção, confirmei 100/100 no CSV.
- **L2c.** Confere a parte de licença e de material suplementar (detalhes em L2c.01–L2c.04).
  - O material suplementar do artigo é só a S1 Table (`pmed.1001885.s001.xlsx`, "List of stakeholders…"), tanto no PMC quanto na PLOS.
  - O checklist é a Table 1 do artigo.
  - O site do RECORD diz "protected on a Creative Common Attribution (CC BY) license", com link para by/4.0.
  - O docx do site tem o mesmo MD5 do versionado.
  - O artigo é CC BY.
  - Ver a falha 3 sobre "4.0 só do site".
- **L3.** A cópia do gerador difere do original em 1 linha, a de saída. Rodada da raiz com `PYTHONPATH=scripts`, ela gerou um RESUMO **idêntico byte a byte** ao de b9d6272 (MD5 `f241186bfce8e8d9ac442328d46d9a26`). O Logger gravou 1 linha no log.
- **L4.** Recalculei sem `etapa7b_lib`, com JSON v1–v10 lidos do git (iguais às cópias em `_arquivo_vN`). Também com igualdade exata, o resultado é o mesmo.
  - `commit_registro`: 226/226 iguais.
  - `commit_analise`: 226/226 iguais. Isso cobre a amostra pedida: os 21 da 7c.3 e mais 20 sorteados.
  - Todos os `commit_analise` são ancestrais do respectivo `commit_registro`.
  - O `.md` traz as mesmas duas colunas.
- **L5.** O checa falharia se rodado hoje.
  - `etapa7b_lib.COMMIT = git rev-parse --short HEAD` (lib L24), e o checa exige `commit_pacote == B.COMMIT` em todos os ids (L526). O JSON tem `8314417` e o HEAD agora é `b9d6272`, então essa checagem dá False. O `ok()` faz `assert`, e o checa pararia na 1ª checagem do bloco 9g, sem gravar o CSV.
  - O `rev-list --since=<mtime> HEAD` (L552) não é afetado.
  - Nem o RESUMO nem o LEIAME avisam disso.

## M. Fatos (levantamento, sem recomendação)

- **M1, `._*`.**
  - **Contagem:** 37 no projeto (fora de `.git`): 36 em 17 pastas de `outputs/` (igual ao RESUMO) e 1 em `data/processed`. A `Submissao/` tem 0.
  - **Git:** nenhum está versionado, nem no histórico, e todos são cobertos por `._*` no `.gitignore`.
  - **Globs sem exclusão de `._*`:** nenhum deles casa hoje com um `._*` existente. O pathlib casa `*` com nomes que começam por ponto; a 1ª versão do meu L1.48 pegou `._S7/._S8` por isso.
  - **Saídas que dependem deles:** os geradores 7c.5 e 7c.6 contam os `._*` (seção 3 do RESUMO). Apagá-los mudaria uma regeração do RESUMO 7c.6.
  - **Quarentena:** `com.apple.quarantine` (agente Chrome) está em 34 de 46 PDFs: os S7/S8 da v11 e dos arquivos, e os ESM das `_arquivo_v4–v7/Submissao`. `Submissao/` e `_arquivo_v8–v10/Submissao` não têm. Os 3 `._*` fora de `outputs/manuscrito` guardam `com.apple.provenance`.
  - **`dot_clean`:** só é executado em `etapa7b_04_submissao.py:25` (`limpa_macos`, chamada em L34 e L51), sobre `Submissao/`. O `etapa7b_02`, que gera os PDFs, não o chama.
- **M2, docstring do `etapa2_03`.**
  - A docstring descreve corretamente o numerador (1–3) e o denominador (1–9). Ela é incompleta: não cita os outros códigos excluídos (2.607 em 2014) nem os nascimentos sem região de saúde (L46).
  - Nenhum número-chave tem o `etapa2_03` como script de origem.
  - Pelo algoritmo, um commit só de docstring não muda `commit_registro` nem `commit_analise`: o (b) usa o `commit_registro` antigo, e há congelamento. O mesmo vale para o recálculo do checa (`_ca` com v1–v10, `_calc` com o mais antigo depois do mtime). Só mudaria o `commit_pacote`.
  - Meu teste sintético (funções extraídas por AST, git falso) confirma: os resultados são iguais com e sem o commit novo. A contraprova também funciona: tabela regravada sem congelamento → muda.
- **M3, tamanho do repositório.**
  - **Medidas:** o `git count-objects -vH` diz 748 MiB, mas isso é inflado pelo cluster do exFAT. Os 741 objetos soltos somam **22,45 MB** (por `stat`), sem packs. São 511 blobs únicos, 44,82 MB sem compressão. A árvore de HEAD tem 165,98 MB, dos quais **147,04 MB (88,6%)** estão em `_arquivo_v*`.
  - **Peso dos arquivos:** os blobs de `_arquivo_v*` são todos repetições de blobs que já existiam fora deles (0 MB exclusivos). Eles pesam no checkout, não no armazenamento do histórico.
  - **Maiores blobs:** são as versões da Fig. 1 (até 4,77 MB). Nenhum passa de 50 MB ou de 100 MB.
  - **Varredura do histórico:** nos 1.092 caminhos não há `.parquet/.dbc/.dbf/.gz/.rds/.zip`, coluna com cara de identificador nem arquivo com ≥ 100 mil linhas. O maior CSV é a S4b, com 390 linhas.
- **M4, `docs/referencias/` não rastreados.**
  - **Inventário:** 93 arquivos, 23.812.821 bytes: 81 da base territorial (10,8 MB), o JSON do SIDRA (4,7 MB), 9 PDFs, o CSV INTERGROWTH e o texto de Evans. Há mais 20 `.dbf` ignorados.
  - **Lidos por script:**
    - `sidra_9605_n6_2022.json`, pelo `etapa4_06:58`;
    - `intergrowth21_bw_centis_oficial.csv`, pelo `etapa1_02a:18`, `etapa1_02b:22` e `etapa1_08:75`;
    - `rl_municip_regsaud.csv`, `tb_regsaud.csv` e `tb_municip.csv`, pelo `etapa2_02` (L20–L22), e o `tb_regsaud` também pelo `etapa2_06:88`.
    - Os outros 88 não são abertos por nenhum script. Da base territorial, só 3 de 81 arquivos são lidos.
  - **Fonte registrada:**
    - os dois `ACESSO.txt` (território e SIDRA): URL, data e MD5;
    - `tpmetestim_codigo8_busca` (estrutura CGIAE "diaad" e manual da DN): URL e MD5;
    - `maihda_formulas_fonte` (Evans): a referência completa;
    - INTERGROWTH: só "intergrowth21.com, baixadas em 2026-10-08";
    - STROBE: nada além da tabela do RESUMO 7c.5b.
  - **Licença:** só a do RECORD está registrada.
- **M5, Evans 2024.**
  - **Referência:** Evans CR, Leckie G, Subramanian SV, Bell A, Merlo J. A tutorial for conducting intersectional multilevel analysis of individual heterogeneity and discriminatory accuracy (MAIHDA). *SSM Popul Health* 2024;26:101664. doi:10.1016/j.ssmph.2024.101664; PMID 38690117; PMC11059336.
  - **Licença:** o XML do PMC declara "This is an open access article under the CC BY license (http://creativecommons.org/licenses/by/4.0/)", com "© 2024 The Authors". O Europe PMC dá license "cc by". O serviço OA antigo `oa.fcgi` respondeu 404.
  - **Uso:** nenhum script abre o `.txt`, que não traz no próprio texto o título, os autores nem a licença.
- **M6, CSVs ignorados em `audit_independente/`.**
  - **Inventário:** 112 CSVs, 21.631.320 bytes, em 18 pastas.
  - **Quem lê:**
    - leitura incondicional: `etapa1_08` e o gerador do RESUMO 7c.6;
    - leitura "se a pasta existir" (num clone limpo a pasta existe, então falham): `etapa2_06`, `3_06`, `4b_05`, `5_04` e `6_08`;
    - pulam a checagem se o arquivo faltar: o checa e o `etapa6b_03`.
  - **Dado individual:**
    - não há coluna com nome de identificador;
    - o maior arquivo é o `etapa2/agregado_m2_raca_idade_ano_macro_mun.csv`: 424.688 linhas × 9 colunas, agregadas (raça × faixa × ano × macro × município);
    - nesse arquivo, 65.178 células têm contagem 1 e 157.488 têm contagem de 1 a 4;
    - nos 44 arquivos com coluna de contagem, 113.540 células têm contagem 1.
- **M7, denominador do índice.**
  - "among births with known month of prenatal care initiation" aparece 22 vezes, em 4 arquivos: xlsx das tabelas principais (4), docx (4), ESM_1 da suplementar (7) e `Submissao/ESM_1` (7).
  - "first visit" e "known month of first visit": 0.
  - "valid MESPRENAT": 6, nas S7/S7a/S7b e no `ESM_2`.
  - O código usa MESPRENAT (mês de início do pré-natal): numerador 1–3, denominador 1–9.
- **M8, CE e DF.**
  - **Justificativas registradas:**
    - pior completude de RACACORMAE (`etapa1_07:2`), quantificada: CE 17,5%, DF 16,9% (RESUMO_ETAPA0);
    - "índice mais grosseiro", que vem da especificação da Etapa 4, fora do repositório, e só tem registro qualitativo (RESUMO_ETAPA2 L13). Não está quantificada.
  - **Base territorial dez/2024:**
    - CE tem 25 regiões em `tb_regsaud`, 5 delas com município (184 municípios);
    - DF tem 8 regiões, 1 com município (códigos 530000 e 530010).
  - **Na análise com tercil:** entram 5 do CE e 1 do DF, entre 433; sem CE/DF, G = 427.
- **M9, Tabela 4.**
  - Na linha "Multiple imputation of race/skin color (m = 10)", as duas colunas de Wald da PTB total ("6 race×tertile terms" e "Indigenous terms (2 df)") estão "n.a.".
  - O rodapé diz só "Multiple imputation: PR M2 and IC fitted in the access sample, combined with Rubin's rules." Ele não explica o n.a. do Wald e não usa "n.a.".
- **M10, termos.**
  - **Medida de efeito:**
    - "PR" aparece 379 vezes e "prevalence ratio(s)" 5 (título e rodapé da Tabela 2 e legenda da Fig. 2);
    - "RR" e "risk ratio" não aparecem;
    - "relative risk" aparece só no texto STROBE da S8;
    - "RRR" aparece 45 vezes, no multinomial.
  - **PTB indicado:**
    - no código (`etapa1_01_base_v2.py` L54–L55), indicado = STTRABPART 1 ou (PARTO 2 e STCESPARTO 1); espontâneo = não indicado, STTRABPART 2 e (PARTO 1 ou PARTO 2 com STCESPARTO 2);
    - a S7a, o rodapé da S1b e o da Tabela 1 descrevem isso de forma consistente;
    - "provider-initiated" aparece 645 vezes e "indicated" 0.
  - **SGA:** aparece 592 vezes; "small for gestational age" por extenso, 3 (S7/`ESM_2` e legendas).

---

# Rodada 2 — correções da 7c.6b, autoauditoria e RESUMO 7c.6b

**Script:** `audita_7c6_final_R2_v1_20261010.py`.
- Acrescenta 26 linhas `R2.*` ao `comparacao_7c6_final_v1_20261010.csv`.
- Antes de gravar, confere que as 116 linhas da rodada 1 continuam byte a byte iguais (MD5 `6e131c769b4f4e65f2a99059cd133a6c`).

**Evidência auxiliar nesta pasta:**
- `etapa7c6b_01_resumo_copia_saida_auditor.py` e `RESUMO_ETAPA7C6b_reproduzido_r2_v1_20261010.md` (R2.05);
- `etapa7c6_02_audita_final_copia_auditor_r2.py`, `audita_final_reexecucao_auditor_r2_v1_20261010.csv` e `RESUMO_ETAPA7C6_reexec_autoaud_r2_v1_20261010.md` (R2.02);
- `etapa7c6_01_resumo_copia_saida_auditor_r2.py` e `RESUMO_ETAPA7C6_reproduzido_r2_v1_20261010.md` (R2.01).

**Independência nesta rodada.** Com autorização do coordenador, li a autoauditoria do autor (`scripts/etapa7c6_02_audita_final.py` e `outputs/manuscrito/audita_final_7c6_v1_20261010.csv`), porque ela é um dos objetos da rodada. Também rodei uma cópia dela com estes desvios:
- toda a saída vai para esta pasta;
- o `status` roda sem reescrever o índice;
- o arquivo de memória em `~/.claude`, que fica fora do projeto, não foi lido;
- um contorno no L4.01 explicado no R2.02.05.

## Resultado da rodada 2

**26 verificações, 16 OK, 10 falhas.** O CSV inteiro tem agora 142 linhas, 129 OK.

| Item | Verificações | OK |
|---|---|---|
| R2.00 errata do próprio auditor | 1 | 0 |
| R2.01 ATRIBUICAO.txt | 3 | 3 |
| R2.02 autoauditoria | 5 | 3 |
| R2.03 errata do RESUMO 7c.6b | 2 | 2 |
| R2.04 fatos das seções 1, 2, 4 e 5 | 11 | 4 |
| R2.05 reprodução do RESUMO 7c.6b | 1 | 1 |
| R2.06 triagem do que vai para o git | 1 | 1 |
| R2.07 nada mais mudou; pacote intacto | 2 | 2 |

## Errata do auditor (R2.00)

O relatório da rodada 1 (seção M6) e a resposta final ao coordenador disseram "113.540 células com contagem 1 em 44 arquivos". Está errado.
- **De onde veio:** de uma execução intermediária que somava a coluna `k` de `etapa3/boot_contagens_r1a20_v1_20261008.csv`. Essa coluna é o número de vezes que um município foi sorteado num bootstrap, não uma contagem de nascimentos (`audit_independente/etapa3/auditoria_etapa3_sorteio_v1_20261008.py`).
- **Valor certo:** a linha M6.03 do CSV final já o trazia. São **72.415** células com contagem 1, em 43 arquivos:
  - 65.178 no único arquivo municipal (`etapa2/agregado_m2_raca_idade_ano_macro_mun.csv`);
  - 7.237 em arquivos por região de saúde (`etapa6/cel_*`).
- **Consequência:** o RESUMO 7c.6b copiou o número errado (R2.04.04).
- **Registro:** o texto da rodada 1 acima foi mantido como estava; esta é a correção.

## R2.01 — ATRIBUICAO.txt (3/3)

- **Escopo da diff contra b9d6272:** só mexe no bloco "Licença:". A nota entre parênteses passou de 1 linha para 2, e entraram 2 linhas depois da citação do artigo. As 14 primeiras linhas estão iguais.
- **Conferência com as fontes** (GETs de 2026-10-10):
  - o docx diz só "CC BY";
  - a página do checklist e a declaração de copyright do artigo na PLOS ligam a `http://creativecommons.org/licenses/by/4.0/`;
  - o XML do PMC (PMC4595218) traz `<license xlink:href=".../by/4.0/">`;
  - a citação "no artigo" é o texto da PLOS. O texto do PMC diz "open-access" e "properly credited", mas o ATRIBUICAO só afirma que o PMC traz a mesma URL.
- **Efeitos da correção:**
  - a checagem de RECORD do `etapa7b_checa` continua satisfeita;
  - o gerador do RESUMO 7c.6 rodado hoje difere do commit em 3 trechos: o bloco do ATRIBUICAO e a lista de `scripts/resumos/`.

## R2.02 — Autoauditoria (3/5)

**OK:**
- **Fixar o ATRIBUICAO em b9d6272 é legítimo e não mascarou nada.** O CSV foi gravado às 11:22:31 e o ATRIBUICAO só mudou às 11:22:44, então o disco ainda era igual ao commit na execução.
- **O L8.01 e o bloco L10 conferem com os meus achados.** Os 7 False são erros reais do RESUMO 7c.6:
  - as minhas 3 falhas (L10.01–L10.03);
  - 2 ressalvas minhas que são imprecisões literais (L10.04 e L10.05);
  - a omissão do aviso sobre o checa (L8.01);
  - a omissão de escopo do "36" (L4.05).

**Falha R2.02.04.** Dos 50 True, 3 trazem fato errado no detalhe. São levantamentos, por isso ok=True, mas o CSV vai para o git:
- **M3.01:** diz "748.0 MB comprimidos". Esse número é espaço alocado no exFAT; a soma real é 22.45 MB. E "_arquivo_v* 33.4 MB" atribui cada blob ao 1º caminho que o rev-list mostra; os bytes exclusivos dos `_arquivo_v*` são 0.
- **M4.01:** diz "lidos por script" para 14 arquivos; só 5 são lidos. A busca por nome ou radical conta citações e o próprio `etapa7c6_02`.
- **M5.01:** diz "lido por script: True". É falso positivo: o único script que contém `evans2024` é o próprio `etapa7c6_02`.

Ressalvas sobre os outros itens:
- o rótulo do M1.02 diz "dot_clean só no etapa7b_04", mas o detalhe lista também o checa;
- o L1.04 confere só o texto das verificações, não os valores;
- o L9.01 lê um arquivo fora do projeto;
- o rótulo do L7.01 não diz que o ATRIBUICAO foi trocado pelo de b9d6272.

**Falha R2.02.05: a autoauditoria não reproduz hoje.**
- O original para com `CalledProcessError` no L4.01. Ele faz `git show 8314417:scripts/<nome>` para todo `scripts/resumos/*.py`, e o `etapa7c6b_01_resumo.py` (criado às 11:29:50) não existe em 8314417.
- Com o meu contorno (excluir também o `etapa7c6b_01`), dá **47/57**. Mudam três itens:
  - K4.01: o ATRIBUICAO foi modificado e há 3 arquivos novos da 7c.6b;
  - L7.01: a seção 5 agora lista 12 `.py`, mesmo com o ATRIBUICAO de b9d6272;
  - L9.01: não li o arquivo fora do projeto.
- O 50/57 é um retrato das 11:22:31 e não se repetirá depois do commit da 7c.6b.

## R2.03 — Errata do RESUMO 7c.6b (2/2)

- **Fidelidade:** as 8 linhas são fiéis aos achados e à evidência. Conferi os números citados: 12 arquivos diferem em bytes; 41 chamadas `B.rd()` em 38 linhas, todas antes da S8 (L560); 37 `._*`; checa L526.
- **Completude:** nada que achei sobre o RESUMO 7c.6 ficou de fora.
- **Proporção:** nada foi exagerado. A errata não diz que algum número mudou.
- **Detalhe de redação:** o "(12 arquivos diferem em bytes)" da linha 4 inclui também os 3 `.md` e o docx de rótulo de versão.

## R2.04 — Fatos do RESUMO 7c.6b (4/11)

**Conferem:**
- **Seção 1:** 50/57, os blocos e a tabela das falhas. O histórico da 1ª versão (51/51 etc.) não é verificável.
- **Seção 2:** confere, com omissão menor: cita 2 das 4 exceções à independência.
- **Seção 4, itens 1, 2, 4, 5, 7, 8 e 9:**
  - 37 `._*` (34 PDFs, 1 CSV, 1 log, 1 parquet) e "34 PDFs com quarentena";
  - "22 vezes em 4 arquivos";
  - CE com 5 regiões com município (184 municípios) e DF com 1; 433 → 427;
  - PB 7.8%;
  - Evans CC BY 4.0;
  - 93 arquivos não rastreados, 5 lidos.
  - Omissão menor: o gerador da 7c.5 também conta os `._*`.
- **Seção 5, demais fatos:**
  - "o checa lê 8 comparacao_*.csv sempre com if exists()";
  - 9.5 MB empacotado (9.53 MB por `git pack-objects --stdout`, nada gravado no `.git`), 22.45 MB comprimidos e 44.7 MB sem compressão;
  - o Online Resource 2 cita `scripts/etapa2_03_indice_acesso.py`;
  - Res. CNS 510/2016, art. 1º, parágrafo único, incisos II e V (texto oficial obtido do gov.br);
  - as tabelas de origem da imputação múltipla não têm Wald;
  - o checa na L526.

**Falhas:**
- **R2.04.03 (material):** o RESUMO diz que "os '~131 MB' anotados antes são efeito do cluster do exFAT". Não são: os 131.5 MB são o tamanho lógico real da árvore de c8eddce, quando a 7c.5b os anotou. Hoje a árvore tem 166.0 MB. Só os 748 MiB vêm do exFAT.
- **R2.04.04 (material):**
  - "113,540 células com contagem 1 … em nível de município" é o meu erro (R2.00). O certo é 72.415 no total, 65.178 em nível de município.
  - "os 10 comparacao_*.csv (até 34 KB)": são 11 fora desta pasta, 12 com o meu (48.8 KB).
  - Falta citar que o gerador da 7c.6b lê sem condição o CSV desta auditoria, ignorado pelo git, e também falha num clone limpo.
- **R2.04.06 (redação):** "SGA aparece 592 vezes, das quais só 3 por extenso". As 3 ocorrências por extenso não estão entre as 592.
- **R2.04.07 (menor):** "o mesmo segundo" vale para 34 das 35 tabelas. Na `tab07_fluxograma_motivos` o log está 2 s antes do mtime.
- **R2.04.08 (menor):** INTERGROWTH "só valida o PIG". O CSV também define a variável de sensibilidade `pig_tabela_oficial`, que está na S7b, e é entrada obrigatória do `etapa1_02b` (grade de centis).
- **R2.04.09:** a decisão 7 diz que o gerador da 7c.6 deixou de reproduzir por causa do ATRIBUICAO e que "a autoauditoria confere contra b9d6272". As duas coisas estão incompletas ou desatualizadas:
  - a lista de `scripts/resumos/` também mudou;
  - o L7.01 da autoauditoria falharia hoje;
  - a autoauditoria nem roda.
- **R2.04.11:** o RESUMO fala em "8 decisões", mas são 7 (os itens de redação são mesmo 8).

## R2.05 — Reprodução do RESUMO 7c.6b (1/1)

- **Como rodei:** a cópia do gerador difere só na linha de saída. Rodei às 16:19:52, **antes** de acrescentar as linhas R2, com o meu CSV no estado da rodada 1 (MD5 `6e131c…`).
- **Resultado:** saída idêntica byte a byte ao RESUMO 7c.6b do disco (MD5 `bf8640744026e7cb7fb53a6fbfbb6708`).
- **Depois desta rodada:** a saída do gerador muda, porque ele lê este CSV. Ao regenerar, o texto "sem ler os resultados da autoauditoria" da seção 2 deixa de valer para a rodada 2.

## R2.06 — Triagem do que vai para o git (1/1)

Triei 27 arquivos novos ou modificados fora do `.gitignore`: os 6 do autor e 21 desta pasta (`.py`, `.md`, `.json`).
- Nenhuma data de 1900–2024, CNS, CPF ou linha de log.
- O único CSV não ignorado, `audita_final_7c6_v1_20261010.csv`, tem as colunas `verificacao, ok, detalhe`.
- Nenhum dado individual nem contagem fina copiada de log. Os números citados são agregados.

## R2.07 — Nada mais mudou (2/2)

- **git status:** só o `ATRIBUICAO.txt` está modificado. Os não rastreados novos são exatamente os 5 listados pelo coordenador, mais esta pasta e os 93 de `docs/referencias/`. HEAD = b9d6272, sem entrada nova no reflog.
- **Pacote:** tabelas, suplementar, figuras, números-chave e `Submissao/` são iguais a b9d6272.
- **Ignorados alterados:** só `outputs/logs/etapa7c6_20261008.log`. Minhas linhas nesta rodada: 16:19:52, 17:51:20 e 17:57:36.

## Efeitos colaterais da rodada 2

- **Log:** 3 linhas acrescentadas em `outputs/logs/etapa7c6_20261008.log`, pelas cópias dos geradores e pela reexecução da autoauditoria.
- **Escrita fora desta pasta:** gravei por engano uma cópia do meu próprio CSV no scratchpad da sessão (`/private/tmp/.../scratchpad/comparacao_r1_backup.csv`). Apaguei logo em seguida; o arquivo não tinha dado do projeto.
- **`__pycache__`:** os que surgiram nesta pasta foram apagados.
- **Git:** nenhum comando que mude índice ou HEAD. O `pack-objects --stdout` só escreve na saída padrão.

---

# Rodada 3 — correções feitas depois da rodada 2

**Script:** `audita_7c6_final_R3_v1_20261010.py`.
- Acrescenta 26 linhas `R3.*` ao `comparacao_7c6_final_v1_20261010.csv`.
- Antes de gravar, confere que as 142 linhas das rodadas 1 e 2 continuam byte a byte iguais (MD5 `616f3002d9463e11b6f6ce9c0180c9af`).

**Evidência auxiliar nesta pasta:**
- `etapa7c6b_01_resumo_copia_saida_auditor_r3.py` e `RESUMO_ETAPA7C6b_reproduzido_r3_v1_20261010.md` (R3.04);
- `etapa7c6_02_audita_final_copia_auditor_r3.py`, `audita_final_reexecucao_auditor_r3_v1_20261010.csv` e `RESUMO_ETAPA7C6_reexec_autoaud_r3_v1_20261010.md` (R3.01).

**Leituras liberadas e desvios:**
- Como na rodada 2, li e rodei uma cópia da autoauditoria, com estes desvios:
  - saída e arquivo temporário nesta pasta;
  - `status` sem reescrever o índice;
  - a memória em `~/.claude` não foi lida;
  - a auto-exclusão continua pelo nome original.
- Li o CSV anterior da autoauditoria no scratchpad (`audita_final_antes_r2.csv`), que o coordenador ofereceu para comparação.
- O teste do K1.01 usou um repositório git descartável criado e apagado dentro desta pasta. Ele não toca no repositório do projeto.

## Resultado da rodada 3

**26 verificações, 20 OK, 6 falhas.** O CSV inteiro tem agora 168 linhas, 149 OK.

| Item | Verificações | OK |
|---|---|---|
| R3.01 autoauditoria | 5 | 3 |
| R3.02 LEIAME | 2 | 1 |
| R3.03 fatos do RESUMO 7c.6b | 15 | 12 |
| R3.04 reprodução do RESUMO 7c.6b | 1 | 1 |
| R3.05 triagem para o git | 1 | 1 |
| R3.06 nada mais mudou | 2 | 2 |

## Falhas

1. **R3.01.03: o K1.01 aceita mais do que deve.**
   - **O problema:** ele usa `git diff --name-only b9d6272 HEAD` com a detecção de renomeação padrão, que mostra só o caminho de destino de um arquivo movido.
   - **Teste sintético** (repositório descartável, git 2.39.5): mover `outputs/manuscrito/tabelas/tab01.csv` para `audit_independente/etapa7c6_final/` aparece só como `audit_independente/etapa7c6_final/tab01.csv`, que `da7c6b()` aceita. Com `--no-renames` aparecem os dois caminhos.
   - **Consequência:** um commit que tirasse arquivos do pacote movendo-os para a pasta do auditor, ou para um nome do conjunto E7C6B, passaria no K1.01.
   - **O K4.01 falha do lado seguro:** renomeações aparecem como `R antigo -> novo` ou ` D antigo`, fora do conjunto.
2. **R3.01.04 (menor):** no M6.01, a lista de "leitores" inclui 3 scripts que não leem CSV de auditoria: `etapa4_07_auditoria_sintese`, `resumos/etapa7c5_01` e `resumos/etapa7c5b_01`. Os números do item conferem.
3. **R3.02.02:** a linha 6 do LEIAME, que não mudou, diz que todos os geradores, exceto o `etapa7c5b_01`, leem `B.V`. Não vale para dois:
   - o `etapa7c6_01` fixa `V = "v11_20261009"`;
   - o `etapa7c6b_01` nem importa a `etapa7b_lib`.

   É a minha ressalva L1.17 da rodada 1, ainda aberta.
4. **R3.03.11:** as afirmações do RESUMO 7c.6b sobre "quem lê" deixam de fora a própria autoauditoria, que está em `scripts/` e vai para o git. Ela lê:
   - o `.txt` do Evans (L428);
   - o `comparacao_7c6_v1` sem condição (L105);
   - o `rl_municip_regsaud.csv` (M8.01);
   - tabelas de `outputs/tables/`.

   Por isso três afirmações não valem como estão:
   - o item 5 da seção 4 diz que "nenhum script lê nem cita o .txt". É falso;
   - o item 4 diz que "os scripts leem só 5", sem essa leitura;
   - o item 6 omite a autoauditoria entre quem lê os `comparacao_*.csv` e entre o que falha num clone limpo.

   Isso pesa na decisão 4 ("não versionar o .txt, porque nenhum script o lê"): sem o `.txt`, o `etapa7c6_02` para com FileNotFoundError na L428.
5. **R3.03.12:** a seção 2 diz que a minha ressalva da rodada 1 era "o LEIAME não dizia que o gerador da 7c.6 também lê o disco. Agora diz." Não era essa. A ressalva era sobre a versão fixa (`V = v11`), e na rodada 2 o RESUMO ainda a citava assim. O texto troca o conteúdo da ressalva e a dá por resolvida, mas ela segue aberta (R3.02.02).
6. **R3.03.13:** o "efeito colateral" da decisão 2 (mover os `._*`) cita só os geradores da 7c.5 e da 7c.6 passando a mostrar 0. Falta que a autoauditoria também passaria a falhar:
   - o L4.04 exige 36 e a tabela por pasta igual ao disco;
   - o L7.01 depende da seção 3 do RESUMO 7c.6, que o gerador recalcula do disco.

   Isso contradiz a decisão 7 e o LEIAME ("a autoauditoria o reproduz com esses dois fixados"), que só valem enquanto os `._*` não forem mexidos.

## O que confere

- **Autoauditoria:**
  - roda até o fim no estado atual (exit 0). Minha cópia deu 49/57, com diferenças só no L9.01 (não li a memória) e no caminho temporário do L7.01;
  - as fixações em b9d6272 (ATRIBUICAO, LEIAME, lista de `scripts/resumos/`) são legítimas e não mascaram nada, e o L7.01 passa;
  - o ok de antes e o de depois são iguais item a item (57 itens; 10 rótulos reescritos; mesmas 7 falhas);
  - os detalhes novos de M3.01, M4.01, M5.01, M1.02, L2.08 e M10.01 conferem.
- **LEIAME (itens novos):**
  - o checa está preso ao HEAD na L526;
  - o `etapa7c6_01` lê do disco o ATRIBUICAO, a lista de `scripts/resumos/` e os `._*`, e lê sem condição o `comparacao_7c6`;
  - o `etapa7c6b_01` lê sem condição o CSV desta auditoria;
  - a autoauditoria reproduz o RESUMO 7c.6 com os dois fixados.
- **RESUMO 7c.6b:**
  - checkout de 166.0/147.0 MB em b9d6272 e de 131.5/113.0 MB em c8eddce;
  - tirar os `_arquivo_v*` quebraria o checa: as linhas 312–318 os definem, as 319–325 leem os JSON v4–v10 e a 530 lê os v1–v10. Ele também quebraria o congelamento na `etapa7b_lib`;
  - a descrição do INTERGROWTH confere;
  - os PDFs de dicionário só são citados (docstring, comentário, MANIFEST); nenhum script os lê;
  - 72.415 = 65.178 + 2.348 + 2.336 + 2.553, em 4 arquivos;
  - há 11 `comparacao_*.csv` fora desta pasta, até 34.223 bytes;
  - PR aparece 379 vezes; SGA 592, mais 3 por extenso (S7, `Submissao/ESM_2`, legendas); "relative risk" só na S8;
  - os incisos II e V conferem;
  - a nova linha 4 da errata confere, com uma ressalva: nos 3 `.md` também mudaram o commit de referência e, no MANIFEST, os MD5 e a nota da S8;
  - as 4 exceções da seção 2 conferem;
  - os demais fatos alterados conferem.
- **Reprodução:** a cópia do gerador do RESUMO 7c.6b, rodada às 08:35:29 de 13/10, **antes** das linhas R3 e com o CSV de 142 linhas, gerou saída idêntica byte a byte ao arquivo do disco (MD5 `521c4fa23f70c38612d7f5d1deeee83b`).
- **Triagem:** 33 arquivos novos ou modificados fora do `.gitignore` (26 desta pasta, mais o LEIAME, o ATRIBUICAO e os do autor). Nenhum dado individual nem linha de log.
- **Nada mais mudou:** HEAD = b9d6272 e o reflog tem as mesmas 27 entradas. Os rastreados modificados são só o ATRIBUICAO e o LEIAME. O pacote, `Submissao/`, os números-chave e o checa CSV estão iguais a b9d6272.

## Ressalvas

- **O que sobrou da rodada 2:**
  - a linha 6 do LEIAME (R3.02.02 e R3.03.12);
  - o L1.04 da autoauditoria, que ainda confere só o texto das verificações do checa, não os valores.

  As falhas da rodada 2 foram todas corrigidas.
- **Contagem de CSVs que muda sozinha:** o "118 CSVs, 21.7 MB" do RESUMO é a contagem de 12/10. Muda a cada CSV novo desta auditoria; agora são 119.
- **Não verificáveis:** a conferência do autor no PMC em 12/10 e o histórico da 1ª versão da autoauditoria (51/51).

## Efeitos colaterais da rodada 3

- **Log:** 2 linhas novas em `outputs/logs/etapa7c6_20261008.log` (08:35:29 e 08:37:55, pelos geradores rodados nas cópias).
- **Repositório de teste:** o repositório git descartável `_teste_k101_git` foi criado e apagado dentro desta pasta.
- **`__pycache__`:** os desta pasta foram apagados.
- **Escrita:** nada gravado fora desta pasta.
- **Git do projeto:** nenhum comando que mude índice ou HEAD; `.git/index` continua com mtime de 2026-10-10 09:10:27.

---

# Rodada 4 — correções feitas depois da rodada 3

**Script:** `audita_7c6_final_R4_v1_20261010.py`.
- Acrescenta 20 linhas `R4.*` ao `comparacao_7c6_final_v1_20261010.csv`.
- Antes de gravar, confere que as 168 linhas das rodadas 1–3 continuam byte a byte iguais (MD5 `7ffca56b792844ba10184b9001ce3b19`).
- Seed 42; esta rodada não sorteia nada.

**Evidência auxiliar nesta pasta:**
- `etapa7c6b_01_resumo_copia_saida_auditor_r4.py` e `RESUMO_ETAPA7C6b_reproduzido_r4_v1_20261010.md` (R4.04);
- `etapa7c6_02_audita_final_copia_auditor_r4.py`, `audita_final_reexecucao_auditor_r4_v1_20261010.csv` e `RESUMO_ETAPA7C6_reexec_autoaud_r4_v1_20261010.md` (R4.01).

**Leituras liberadas e desvios:**
- Com autorização, li a autoauditoria e rodei uma cópia dela, com estes desvios:
  - saída e arquivo temporário nesta pasta;
  - `status` sem reescrever o índice;
  - a memória em `~/.claude` não foi lida;
  - a auto-exclusão e a auto-leitura apontam para o arquivo original.
- O teste do K1.01 usou um repositório git descartável (`_teste_k101_git_r4`), criado e apagado dentro desta pasta.

## Resultado da rodada 4

**20 verificações, 19 OK, 1 falha menor.** O CSV inteiro tem agora 188 linhas, 168 OK.

| Item | Verificações | OK |
|---|---|---|
| R4.01 autoauditoria | 4 | 4 |
| R4.02 LEIAME | 2 | 2 |
| R4.03 texto/RESUMO 7c.6b | 10 | 9 |
| R4.04 reprodução do RESUMO 7c.6b | 1 | 1 |
| R4.05 triagem para o git | 1 | 1 |
| R4.06 nada mais mudou | 2 | 2 |

## Falha

**R4.03.09 (menor), decisão 4.** O texto diz: "O da 7c.6 roda, mas não reproduz o RESUMO byte a byte, porque conta os `._*` do disco." A causa está incompleta. Num clone limpo depois do commit da 7c.6b, a saída também difere em dois pontos:
- o ATRIBUICAO corrigido (seção 2);
- a lista de `scripts/resumos/`, que terá 12 `.py` (seção 5).

A própria decisão 7 cita esses dois pontos. A conclusão (não reproduz) está certa.

## O que confere

- **R4.01, autoauditoria:**
  - **K1.01:** com `--no-renames`, ele recusa a renomeação. No teste descartável, mover `outputs/manuscrito/tabelas/tab01.csv` para a pasta do auditor dá False, e um commit que só muda arquivos da 7c.6b continua True.
  - **M6.01:** os 11 leitores e a classificação conferem com a minha leitura linha a linha, e nenhum ficou de fora:
    - `etapa1_08` é "sem condição" (L97, L118, L131 no nível de topo);
    - `etapa2_06` e `etapa3_06` são "com if exists()" (L96, L108).
  - **M4.01 e M5.01:** conferem. Os outros scripts leem os mesmos 5 arquivos. A autoauditoria lê o Evans (L432) e o `rl_municip_regsaud.csv`. Só ela cita o `.txt`.
  - **Execução:** a cópia roda até o fim, com 49/57, porque o L9.01 dá False quando a memória não é lida. Os ok são idênticos item a item aos da rodada 3, e o CSV do autor continua em 50/57 com as mesmas 7 falhas.
- **R4.02, LEIAME:**
  - os 10 geradores movidos e os 2 criados conferem;
  - os 9 geradores que leem `B.V` conferem; o `7c5b_01` fixa v10, o `7c6_01` fixa v11, e o `7c6b_01` não lê o pacote;
  - o aviso sobre os `._*` confere com o código: o L4.04 exige 36, e o L7.01 recalcula do disco;
  - a autoauditoria de fato lê `outputs/tables/`, o `comparacao_7c6`, o Evans e a base territorial;
  - a L526 do checa confere.
  - Detalhe: o `7c6b_01` importa só o `etapa0_lib`.
- **R4.03, texto/RESUMO 7c.6b:**
  - INTRO e PEND (quatro rodadas) conferem.
  - O parágrafo "Corrigida depois da rodada 3" confere.
  - A tabela "O que a rodada 3 corrigiu" traz as minhas 6 falhas. A L1.17 reescrita está certa. A limitação do L1.04 e a conferência do autor no PMC estão registradas.
  - A nova linha 4 da errata confere com o diff:
    - no MANIFEST mudaram etapa, commit, 13 linhas só de MD5 e a nota da S8;
    - no `data_code_availability` mudaram etapa e commit;
    - nas legendas e no docx, só o rótulo.
  - O item 1 (checa × autoauditoria) e os itens 4 e 5 conferem.
  - Item 6:
    - os 112 CSVs com 21.6 MB fora de `etapa7c6_final` conferem;
    - a lista de leitores confere;
    - "o checa, a autoauditoria e as auditorias próprias das Etapas 1–6 também leem `outputs/tables/` ou `data/`" confere: todas usam `L.TAB`/`E.L.TAB` ou `read_parquet`, antes do bloco do auditor.
  - O efeito colateral da decisão 2 e a decisão 7 conferem.
- **R4.04, reprodução:** a cópia do gerador rodou às 09:37:43, **antes** das linhas R4 e com o CSV de 168 linhas. A saída é idêntica byte a byte ao RESUMO do disco (MD5 `12970a42508f18d59fcae8e5f3583fd8`). Esse MD5, citado na mensagem do coordenador como sendo do CSV, é o do RESUMO; o do CSV era `7ffca56b…`.
- **R4.05, triagem:** 38 arquivos fora do `.gitignore` (31 desta pasta, mais LEIAME, ATRIBUICAO e os 5 do autor). Nenhuma data individual, CNS, CPF ou linha de log. O único CSV não ignorado é o da autoauditoria (`verificacao, ok, detalhe`).
- **R4.06, nada mais mudou:**
  - HEAD = b9d6272 e o reflog tem 27 entradas;
  - só o ATRIBUICAO e o LEIAME estão modificados;
  - os não rastreados novos são os mesmos 5;
  - o pacote, `Submissao/`, os números-chave, o checa, o MANIFEST, a disponibilidade, as legendas e o `_arquivo_v10` estão iguais a b9d6272.

## Ressalvas

- **O que o "com if exists()" do M6.01 significa** (R4.01.02 e R4.03.07):
  - nas auditorias próprias das Etapas 2, 3, 4b, 5 e 6, o `exists()` testa a **pasta** `audit_independente/etapaN`, que está no git (4 a 13 arquivos rastreados cada). Num clone, a condição é verdadeira e a leitura do CSV falha do mesmo jeito;
  - só o checa e o `etapa6b_03` testam o próprio CSV e pulam de fato;
  - a frase "num clone limpo, os quatro que leem sem condição param na falta do CSV do auditor" é verdadeira, mas sugere que os outros pulam. Hoje não tem efeito prático, porque essas auditorias leem `outputs/tables/` ou parquet bem antes do bloco do auditor.
- **Texto do "Corrigida depois da rodada 3":** a frase "mudaram só o K1.01, o M4.01, o M5.01 e o M6.01" vale para o código. No CSV mudaram os detalhes de M4.01, M5.01, M6.01 e o caminho temporário do L7.01.
- **Próxima regeneração do RESUMO 7c.6b:** a seção 2 deve passar a dizer que a autoauditoria foi lida nas rodadas 2 a 4. O gerador também vai mudar de saída por causa das linhas R4.

## Efeitos colaterais da rodada 4

- **Log:** 2 linhas novas em `outputs/logs/etapa7c6_20261008.log`, uma da cópia do gerador da 7c.6b (09:37:43) e outra do L7.01 da cópia da autoauditoria.
- **Repositório de teste:** criado e apagado dentro desta pasta.
- **`__pycache__`:** apagados.
- **Escrita:** nada gravado fora desta pasta.
- **Git do projeto:** nenhum comando que mude índice ou HEAD.

---

# Rodada 5 — texto corrigido depois da rodada 4

**Script:** `audita_7c6_final_R5_v1_20261010.py`.
- Acrescenta 11 linhas `R5.*` ao `comparacao_7c6_final_v1_20261010.csv`.
- Antes de gravar, confere que as 188 linhas das rodadas 1–4 continuam byte a byte iguais (MD5 `7d66d3e4e843dfcc99963d28c8e1b156`, o citado pelo coordenador).

**Escopo:** a autoauditoria não foi rodada de novo. O R5.03.01 mostra que o código dela não mudou desde a rodada 4.

**Evidência auxiliar:** `etapa7c6b_01_resumo_copia_saida_auditor_r5.py` e `RESUMO_ETAPA7C6b_reproduzido_r5_v1_20261010.md`.

## Resultado da rodada 5

**11 verificações, 10 OK, 1 falha menor.** O CSV inteiro tem agora 199 linhas, 178 OK.

| Item | Verificações | OK |
|---|---|---|
| R5.01 frases novas ou alteradas | 7 | 6 |
| R5.02 reprodução do RESUMO 7c.6b | 1 | 1 |
| R5.03 estado e triagem | 3 | 3 |

## Falha

**R5.01.05 (menor), item 6.** O texto diz: "a pasta do auditor, que está no git por causa dos `.txt`". A causa é incompleta: essas pastas também têm versionados os scripts do auditor.

| Pasta | Tipos de arquivo versionados |
|---|---|
| `etapa2` | `.py`, `.R`, `.txt` |
| `etapa3` | `.py`, `.R`, `.txt` |
| `etapa4b` | `.py`, `.R`, `.txt` |
| `etapa5` | `.py`, `.txt` |
| `etapa6` | `.py`, `.R`, `.txt` |

Num clone, a pasta existiria mesmo sem os `.txt`.

O resto do item 6 confere:
- só o checa e o `etapa6b_03` testam o próprio CSV;
- nas Etapas 2, 3, 4b, 5 e 6, a condição é verdadeira num clone e a leitura falha;
- num clone limpo, os geradores da 7c.6 e da 7c.6b param na falta do CSV.

## O que confere

- **INTRO e PEND:** "cinco rodadas" e a linha da rodada 5.
- **AUTO, código × CSV:**
  - no CSV, mudaram os rótulos de M4.01 e M5.01;
  - mudaram os detalhes de M4.01, M5.01, M6.01 e o caminho temporário do L7.01;
  - no código, mudaram K1.01, M4.01, M5.01 e M6.01, além da docstring.
- **INDEP e gerador:** "rodadas 2 a 4" e "a rodada 5 conferiu só o texto" conferem. `NOMES` ganhou R4 e R5.
- **Tabela "O que a rodada 4 corrigiu":** traz a minha falha R4.03.09 e as 2 ressalvas da rodada 4. A 3ª ressalva ("rodadas 2 a 4") foi corrigida no gerador.
- **Decisão 4:** agora traz a causa completa (ATRIBUICAO, lista de `scripts/resumos/` e `._*`).
- **Mudanças fora da lista:** não há. O diff contra o RESUMO da rodada 4 só tem as mudanças listadas e as tabelas geradas a partir do meu CSV.
- **Reprodução:** a cópia do gerador atual rodou às 10:03:27, **antes** das linhas R5 e com o CSV de 188 linhas. A saída é idêntica byte a byte ao RESUMO do disco (MD5 `2bf6ffcd268820376cfbd72fa1cc3a37`).
- **Estado:**
  - HEAD = b9d6272 e o reflog tem 27 entradas;
  - só o ATRIBUICAO e o LEIAME estão modificados;
  - os não rastreados novos são os mesmos 5;
  - o pacote e `Submissao/` estão iguais a b9d6272.
- **Triagem:** 41 arquivos fora do `.gitignore`, sem dado individual nem linha de log.

## Efeitos colaterais da rodada 5

- **Log:** 1 linha nova em `outputs/logs/etapa7c6_20261008.log`, às 10:03:27, da cópia do gerador.
- **`__pycache__`:** apagados.
- **Escrita:** nada gravado fora desta pasta.
- **Git do projeto:** nenhum comando que mude índice ou HEAD.

---

# Rodada 6 — frase corrigida depois da rodada 5

**Script:** `audita_7c6_final_R6_v1_20261010.py`.
- Acrescenta 8 linhas `R6.*` ao `comparacao_7c6_final_v1_20261010.csv`.
- Antes de gravar, confere que as 199 linhas das rodadas 1–5 continuam byte a byte iguais (MD5 `75c265cf8d0c770368956a5d9c1c3054`, o citado pelo coordenador).

**Evidência auxiliar:** `etapa7c6b_01_resumo_copia_saida_auditor_r6.py` e `RESUMO_ETAPA7C6b_reproduzido_r6_v1_20261010.md`.

## Resultado da rodada 6

**8 verificações, 8 OK, nenhuma falha.** O CSV inteiro tem agora 207 linhas, 186 OK.

| Item | Verificações | OK |
|---|---|---|
| R6.01 frases novas ou alteradas | 4 | 4 |
| R6.02 reprodução e diff | 2 | 2 |
| R6.03 estado e triagem | 2 | 2 |

## O que confere

- **R6.01, frases:**
  - **Item 6:** "testam a pasta do auditor, que está no git, com os `.txt` e os scripts do auditor" confere. As pastas `etapa2`, `etapa3`, `etapa4b` e `etapa6` têm `.py`, `.R` e `.txt`, e a `etapa5` tem `.py` e `.txt`.
  - **INTRO e PEND:** "seis rodadas" e a linha da rodada 6 conferem.
  - **INDEP:** "O que a rodada 5 corrigiu" cita a R5.01.05 e a frase antiga. O "(`.py` e `.R`)" vale para o conjunto das pastas.
  - **Gerador:** a frase "as rodadas 5 e 6 conferiram só o texto" e o `NOMES` com R6 conferem. Fora a linha de saída da minha cópia, a diff contra o gerador da rodada 5 tem só essas 5 linhas.
- **R6.02, reprodução e diff:**
  - A cópia do gerador rodou às 10:11:07, **antes** das linhas R6 e com o CSV de 199 linhas. A saída é idêntica byte a byte ao RESUMO do disco (MD5 `daea1117b7280ba63a92ff44beaa24f8`).
  - O diff contra o RESUMO da rodada 5 tem 15 linhas ±. São só as mudanças listadas e as tabelas geradas do meu CSV: a linha R5 do quadro por bloco, a falha R5.01.05 e o total 178/199.
- **R6.03, estado e triagem:**
  - HEAD = b9d6272 e o reflog tem 27 entradas;
  - só o ATRIBUICAO e o LEIAME estão modificados;
  - os não rastreados novos são os mesmos 5;
  - o pacote e `Submissao/` estão iguais ao commit;
  - a autoauditoria tem o mesmo MD5 da rodada 5, e o CSV dela, o LEIAME e o ATRIBUICAO não mudaram;
  - os 44 arquivos fora do `.gitignore` não têm dado individual nem linha de log.

## Efeitos colaterais da rodada 6

- **Log:** 1 linha nova em `outputs/logs/etapa7c6_20261008.log`, às 10:11:07.
- **`__pycache__`:** apagados.
- **Escrita:** nada gravado fora desta pasta.
- **Git do projeto:** nenhum comando que mude índice ou HEAD.
