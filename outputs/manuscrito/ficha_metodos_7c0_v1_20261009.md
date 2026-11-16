# Ficha técnica dos Métodos, extraída do código (Etapa 7c.0)

ptb-racial-brasil · commit de referência 6a08c55 (7b.3) · pacote v4_20261009 · gerada em 2026-10-09

- **Como foi feita:** só leitura de scripts, bibliotecas, logs, RESUMOs e `docs/referencias`. Nenhuma análise foi rodada.
- **Caminhos:** relativos a `/Volumes/Forja/ptb-racial-brasil`, salvo quando indicado.
- **Fonte de cada resposta:** é o que o código executa. Quando a fonte é log, RESUMO ou documento, isso está dito.
- **NÃO DETERMINÁVEL:** usado quando nem o código nem um registro resolvem a pergunta.

## 0. Onde o código diverge das premissas das perguntas (ler primeiro)

1. **TPROBSON não entra na regra espontâneo × indicado.** A regra usa STTRABPART, STCESPARTO e **PARTO**. O TPROBSON só aparece na tabulação de validação da 6.3(a) (pergunta 2).
2. **A escolaridade do M3 tem 5 categorias, não 3.** As faixas ≤7 / 8–11 / ≥12 existem só no MAIHDA e na modificação por escolaridade da 3.5 (pergunta 3).
3. **O M2 (modelo principal) não tem escolaridade nem estado civil.** É raça + idade (3 faixas) + ano + macrorregião. Escolaridade e estado civil entram só no M3 (pergunta 3).
4. **Número de clusters:**
   - 456 = 433 + 23 UF só nos modelos sem tercil.
   - Nos modelos com tercil (3.2 e derivados), G = 433, porque os 533 nascimentos sem região de saúde saem (pergunta 5).
5. **AUC e DeLong são implementação própria em R.** O pROC está instalado (1.19.0.1), mas nenhum script o carrega (pergunta 9).
6. **Graus de liberdade da imputação.** O docstring diz "gl de Barnard–Rubin", mas o código usa os gl de Rubin (1987): (m − 1)/λ² (pergunta 10).
7. **Óbito fetal.** O projeto usa um "OU" simples entre IG, faixa de gestação e peso. O FONTE.md do hub do SIM descreve uma regra hierárquica diferente (pergunta 11).
8. **Não há registro de download em 2026-10-07.** Os metadados dos parquets do SINASC usados mostram datas de março a junho de 2026 (pergunta 17).

---

## 1. Exclusão da raça Amarela

**Resposta:** não há justificativa substantiva registrada. O único registro é que a cascata replica os critérios do artigo da RSP.

- **Comentário no código:** "Cascata do artigo da RSP (lib_baseB.build_cascade, Racial-PTB-SINASC) […] 1 raça/cor: exclui nulo, amarela (3) e qualquer código fora de {1,2,4,5}" (`scripts/etapa0_lib.py:48–58`).
- **Implementação:** `RACACORMAE.isin([1, 2, 4, 5])` (`scripts/etapa0_lib.py:65`). Rótulos: 1 Branca, 2 Preta, 4 Parda, 5 Indígena (`scripts/etapa0_lib.py:45`).
- **Especificação da Etapa 0** (prompt do Guilherme na sessão, fora do repositório): "com os critérios do artigo da RSP aplicados ao Brasil: excluir, em sequência: raça/cor ausente, ignorada ou amarela".
- **Protocolo v3.5** (colado na sessão, fora do repositório): não trata da Amarela.
- **n excluídos:**
  - Amarela: 117,549.
  - Raça ausente: 964,890.
  - Total do passo 1: 1,082,439.
  - Fonte: `outputs/RESUMO_ETAPA0_v1_20261008.md:30`; `scripts/etapa7b_lib.py:37`.
- **Na imputação múltipla:** a Amarela é uma das 5 categorias do modelo, e as mães imputadas como Amarela saem da análise (`scripts/etapa4_06_imputacao_raca.py:8, 151`).
- **Para a redação:** a razão de fundo precisa vir dos autores ou do próprio artigo da RSP.

## 2. PTB espontâneo × indicado

**Regra** (só para PTB, isto é, SEMAGESTAC < 37; códigos crus do SINASC; nulos viram −1 antes da comparação e não satisfazem nenhuma condição):

```
indicado    = STTRABPART == 1  OU  (PARTO == 2 E STCESPARTO == 1)
espontâneo  = NÃO indicado  E  STTRABPART == 2  E  (PARTO == 1  OU  (PARTO == 2 E STCESPARTO == 2))
sem_classif = todo PTB que não cai em nenhum dos dois
```

- **Fontes:** `scripts/etapa1_01_base_v2.py:46, 51–57`; dicionário da base em `scripts/etapa1_01_base_v2.py:127`.
- **Ordem de prioridade:** o indicado é avaliado primeiro, porque o espontâneo exige `~ind` (`scripts/etapa1_01_base_v2.py:55`).
- **Códigos:**
  - STTRABPART: 1 Sim (induzido), 2 Não, 3 Não se aplica, 9 Ignorado.
  - STCESPARTO (cesárea antes do trabalho de parto): 1 Sim, 2 Não, 3 Não se aplica, 9 Ignorado.
  - PARTO: 1 vaginal, 2 cesáreo, 9 ignorado.
  - Textos do dicionário transcritos em `/Volumes/Forja/Doc/dados_artigos_perinatais_clima/01_sinasc/FONTE.md` (tabela da seção 4).
- **Polaridade de STTRABPART = 1 (induzido):** conferida no dicionário e no dado, porque STTRABPART = 1 nunca aparece nos grupos de Robson 1 e 3 (`scripts/etapa0_06_viabilidade_fenotipo.py:4–5`).
- **STCESPARTO no parto vaginal:** não entra, porque em 2015 o vaginal veio nulo; o código 3 só aparece a partir de 2016 (`scripts/etapa0_06_viabilidade_fenotipo.py:9–10`).
- **Consequências literais da regra:**
  - Indução com parto vaginal conta como indicado.
  - Ficam "sem classificação":
    - STTRABPART 3, 9 ou nulo, exceto cesárea com STCESPARTO 1 (que é indicado);
    - PARTO 9 ou nulo, exceto STTRABPART 1;
    - cesárea com STTRABPART 2 e STCESPARTO 3, 9 ou nulo.
- **TPROBSON:** não é usado na regra. Só aparece na 6.3(a), na tabulação ptb_tipo × TPROBSON × raça (`scripts/etapa6_03_ptb_indicado.py:3–4, 21–29`). O grupo 11 é tratado como não documentado (`scripts/etapa0_03_completude.py:9`).
- **Desfechos derivados** (`scripts/etapa2_01_base_v3.py:10–12, 49–55`):
  - `ptb_esp`: 1 = espontâneo; 0 = termo ou PTB indicado; NA = sem classificação.
  - `ptb_ind`: definido de forma simétrica.
  - Denominador: amostra menos os PTB sem classificação.
- **Definição de "não classificado"** (`ptb_tipo == "sem_classif"`): PTB que não atende a nenhuma das duas regras.
  - Amostra analítica: 131,809.
  - Amostra com região de saúde: 131,801.
  - Fonte: assert em `scripts/etapa7b1_01_analises.py:59`.

## 3. Covariáveis (código SINASC → categoria analítica)

| Variável | Código SINASC → categoria | Referência | Fonte |
|---|---|---|---|
| Idade materna | IDADEMAE (10–60 pela cascata): <20; 20–34; ≥35 (35–60) | 20–34 | `etapa1_01_base_v2.py:81–83`; `etapa3_lib.py:30` |
| Escolaridade, **5 categorias** (M3, M2cc, bootstrap, imputação) | **ESCMAE** (não ESCMAE2010): 1 nenhuma; 2 1–3 anos; 3 4–7; 4 8–11; 5 ≥12; 9/nulo = NA (já excluídos pela cascata, que exige ESCMAE 1–5) | 5_12mais (≥12) | `etapa1_01_base_v2.py:26, 84`; `etapa0_lib.py:67`; `etapa2_04_modelos.py:39` |
| Escolaridade, **3 categorias** (estratos do MAIHDA; modificação na 3.5) | ≤7 = ESCMAE 1–3; 8–11 = 4; ≥12 = 5 | ≥12 | `etapa5_01_estratos.py:22`; `etapa3_02_knol.py:35–36` |
| Estado civil (só M3) | ESTCIVMAE 2 (casada) ou 5 (união estável) = com companheiro; 1 (solteira), 3 (viúva) ou 4 (separada) = sem companheiro; 9/nulo = NA; M3 em casos completos | com companheiro | `etapa1_01_base_v2.py:27–28, 85, 136`; `etapa2_04_modelos.py:7, 71` |
| Ano | **categórico**, `C(ano)`, 10 níveis | 2015 (primeiro nível ordenado; patsy sem `Treatment` explícito) | `etapa3_lib.py:31`; `etapa2_04_modelos.py:9` |
| Macrorregião | 1º dígito do código da UF em CODMUNRES: N, NE, SE, S, CO | SE | `etapa0_lib.py:38`; `etapa0_02_base.py:45–47`; `etapa3_lib.py:32` |
| Raça/cor | ver pergunta 1 | Branca | `etapa3_lib.py:29` |
| Tercil de acesso | T1 (pior), T2, T3 | T3 | `etapa4_lib.py:40` |

**Especificações dos modelos** (`scripts/etapa2_04_modelos.py:4–9, 35–41`; `scripts/etapa6b_01_modelos_rs.py:33`):
- **M1:** raça.
- **M2:** raça + idade + ano + macrorregião.
- **M2s:** M2 sem idade.
- **M3:** M2 + escolaridade (5) + estado civil (2).
- **M2cc:** M2 refeito na amostra de casos completos do M3.
- **3.2:** M2 + tercil_reg + 6 indicadores raça × tercil (`scripts/etapa3_lib.py:97–102`; `scripts/etapa4_lib.py:40`).

## 4. Índice de acesso

- **Fórmula:**
  - índice(r, t) = 100 × [nº de nascidos vivos de mães residentes em r, no ano t, com MESPRENAT 1–3] / [nº com MESPRENAT válido, 1–9].
  - O código 99, o nulo e qualquer valor fora de 1–9 saem do numerador e do denominador.
  - Universo: **todos** os nascidos vivos residentes do bruto, 2014–2024, não só a amostra analítica.
  - Fonte: `scripts/etapa2_03_indice_acesso.py:4–6, 38–41, 46–47, 50–51`.
- **Completude e alcance** (log `outputs/logs/etapa2_20261008.log`):
  - MESPRENAT válido: 92.43% em 2014 a 96.61% em 2024 (linhas 19–29).
  - 4,763 pares região-ano; índice de 41.1 a 98.8; nenhum par com < 50 registros válidos (linha 30).
  - Spearman com % de 7+ consultas: 0.771 (linha 31).
- **Unidade:** região de saúde (CIR) de **residência**, obtida pelo mapa CODMUNRES → CO_REGSAUD.
  - Tabela DATASUS da base territorial de dezembro/2024 (`rl_municip_regsaud.csv`), fixa para 2015–2024.
  - Arquivo `ftp://ftp.datasus.gov.br/territorio/tabelas/2024/12-base territorial_dez24.zip`, datado de 19/12/2024 no FTP; baixado em 2026-10-08 12:42 (−03); MD5 469fa5bfc171e47c54a9b903fda85098.
  - Fontes: `scripts/etapa2_02_regiao_saude.py:2–11`; `docs/referencias/territorio_dez24/ACESSO.txt`.
  - 5,572 municípios formam 433 regiões. Dos 5,593 códigos CODMUNRES do SINASC 2014–2024, só os 23 códigos UF0000 (município ignorado) ficam sem região: 980 nascidos vivos em 2014–2024, e nenhum código válido sem região (log etapa2, linhas 1–6).
- **Defasagem t−1:** cada nascimento do ano t recebe o índice do ano t−1 (merge com `ano + 1`). O ano de 2015 recebe o índice de **2014**, calculado do bruto `sinasc_2014.parquet` (`scripts/etapa2_03_indice_acesso.py:7, 34–35, 74–75`; `scripts/etapa3_lib.py:54`).
- **Tercis da análise principal (`tercil_reg`, 3.2):** calculados **dentro de cada macrorregião**, sobre o **período todo**, não ano a ano.
  - Pares (região de saúde × ano, 2015–2024) ordenados pelo índice t−1; desempate por CO_REGSAUD e ano.
  - Pares ponderados pelo **número de nascimentos da amostra analítica** do par, sem os 533. Ou seja, a ponderação é por nascimentos, não por região.
  - corte1 = menor índice com fração acumulada ≥ 1/3; corte2 = idem com ≥ 2/3.
  - T1 = índice ≤ corte1 (pior acesso); T2 = corte1 < índice ≤ corte2; T3 = índice > corte2.
  - O tercil é atribuído ao par região-ano, então uma região pode mudar de tercil entre anos.
  - Fonte: `scripts/etapa3_01_tercis_regiao.py:4–7, 26–32`.
- **Tercil nacional (3.3b, análise secundária):** mesmo algoritmo, sem estratificar por macrorregião. Cortes: T1 ≤ 80.607 < T2 ≤ 85.743 < T3 (`scripts/etapa2_03_indice_acesso.py:8–10, 80–86`; log etapa2, linha 33).
- **Os 533 nascimentos sem região de saúde** (município ignorado):
  - Não têm índice nem tercil.
  - Ficam **fora** de todo modelo com tercil: 3.2, MAIHDA, multinomial por tercil (`scripts/etapa4_lib.py:33`).
  - Ficam **dentro** dos modelos sem tercil (M1–M3, multinomial Brasil, bootstrap), em 23 clusters `UF_xx` (`scripts/etapa6_lib.py:7, 17–20`).
  - O número 533 é conferido por assert em `scripts/etapa2_03_indice_acesso.py:76–78` e `scripts/etapa3_02_knol.py:47`.

## 5. Clusters

- **Unidade de cluster:** região de saúde de residência.
  - Cada nascimento sem região forma cluster com sua UF (`"UF_" + 2 dígitos`): 23 clusters.
  - Log: "433 regiões de saúde + 23 UF (n = 533 sem região)" (`outputs/logs/etapa6_20261008.log:3`; `scripts/etapa6_01_cluster_rs.py:39–42`).
- **Número de clusters por tipo de modelo:**
  - Sem tercil (M1, M2, M2cc, M3, multinomial Brasil, bootstrap): **G = 456** (433 + 23).
    - `outputs/tables/tab_e6_01a_m2_v1_20261008.csv`, coluna G = 456 (`regsaude`).
    - Log etapa6, linhas 258 e 770.
  - Com tercil (3.2 e derivados): **G = 433** (`tab_e6_01a_wald_v1_20261008.csv`).
  - Subamostras têm G menor. Exemplos:
    - 3.2 sem CE/DF: 427.
    - M2 nos códigos 1, 2 e 8 de TPMETESTIM: 450, 448 e 456.
    - Fonte: log da 7b.3.
- **Implementação:**
  - As células são agregadas por município.
  - Depois, `para_rs` troca CODMUNRES pelo identificador do cluster.
  - A estimativa pontual não muda; só o agrupamento dos escores.
  - Fonte: `scripts/etapa6_lib.py:4–7, 23–27`.
- **Estimador** (`scripts/etapa1_lib.py:10–15, 92–104`):
  - V = A⁻¹ M A⁻¹, com A = Σ_c n_c w(μ_c) x_c x_c′ (informação de Fisher; w = μ no Poisson).
  - M = Σ_g s_g s_g′, com s_g = Σ_{c∈g} x_c (Y_c − n_c μ_c). Isso equivale ao escore individual somado por cluster.
- **Correção de pequena amostra:** a mesma do statsmodels, do tipo CR1. M × G/(G−1) × (N−1)/(N−K), com N = Σ n_c (nascimentos) e K = nº de parâmetros (`scripts/etapa1_lib.py:99`).
- **Correção no multinomial:** idem com K·J parâmetros (`scripts/etapa6_lib.py:74–77`).
- **Inferência:**
  - IC normal com z = `scipy.stats.norm.ppf(0.975)` = 1.959964 (`scripts/etapa1_lib.py:26`).
  - p bilateral pela normal (`scripts/etapa1_lib.py:151`).
  - Wald conjunto em χ² com gl = nº de termos, sem F (`scripts/etapa3_lib.py:154–158`).
  - Não há t com G − 1 gl.

## 6. Modelo: Poisson em dados agregados, PR, RD e ICR

- **Células:** padrão de covariáveis × município de residência (CODMUNRES), só com as linhas de desfecho definido. Y_c = casos; n_c = nascimentos (`scripts/etapa1_lib.py:64–71`).
  - M1/M2: raça × idade × ano × macrorregião × município (`scripts/etapa2_04_modelos.py:70`; `scripts/etapa6_01_cluster_rs.py:50`).
  - M2cc/M3: acrescenta escolaridade (5) × estado civil (2) (`scripts/etapa2_04_modelos.py:72`).
  - 3.2: raça × idade × ano × macrorregião × tercil_reg × município (`scripts/etapa4_lib.py:34`). São 424,373 células na PTB total (`tab_e6_01a_wald`, coluna `n_celulas`).
- **Pesos:** não há pesos de frequência. O ajuste é um GLM Poisson com link log e **offset log(n_c)** (`statsmodels.GLM`), que dá o mesmo β do Poisson individual (`scripts/etapa1_lib.py:5–8, 79`).
  - Pesos de frequência só aparecem no bootstrap, como multiplicidade do cluster sorteado (pergunta 7).
- **PR (M1/M2/M3):** exp(β_raça), com IC exp(β ± z·EP_cluster) (`scripts/etapa1_lib.py:142–155`; `scripts/etapa6b_01_modelos_rs.py:41–43`).
  - Num modelo log-linear sem interação com raça, exp(β) é exatamente a razão das probabilidades padronizadas (o caso geral está documentado em `scripts/etapa3_lib.py:10`).
- **RD (padronização marginal):**
  - P_g = Σ_c n_c μ_c(raça = g) / Σ_c n_c, trocando a raça em **todas** as células do modelo.
  - Ou seja, a distribuição de referência é a das covariáveis observadas na amostra do próprio modelo, com todas as raças juntas.
  - RD = P_g − P_Branca, com IC delta pela covariância de cluster (`scripts/etapa1_lib.py:109–139`).
- **Análise 3.2 (Knol & VanderWeele):**
  - P(g, m) = Σ_c n_c μ_c(raça = g, tercil = m) / Σ_c n_c, sobre todas as células ("padronização total"), com gradiente analítico ∂P/∂β = Σ_c n_c μ_c x_c / Σ_c n_c (`scripts/etapa3_lib.py:7–9, 77–87, 105–110`).
  - **ICR (por 100):** 100 × {[P(g,m) − P(Branca,m)] − [P(g,T3) − P(Branca,T3)]} (`scripts/etapa3_lib.py:142–144`).
  - **Interação multiplicativa:** [P(g,m)/P(B,m)] / [P(g,T3)/P(B,T3)] (`scripts/etapa3_lib.py:139–141`).
  - **RERI:** RP11 − RP10 − RP01 + 1, com referência Branca–T3 e IC delta. É marcado como "aplicável" quando RP10 > 1 e RP01 > 1 (`scripts/etapa3_lib.py:145–153`).
  - **RERI recodificado** (7b.1, só PTB indicado):
    - Referência = célula conjunta de menor risco de cada 2×2 (Knol et al. 2011).
    - Fórmula: (P_dupla − P_s1 − P_s2)/P_ref + 1, com IC delta.
    - Fonte: `scripts/etapa7b1_01_analises.py:104–117`.
  - **Wald de 6 gl:** os 6 termos `ix__`, com V_cluster, em χ²(6) (`scripts/etapa3_lib.py:154–158`).
  - **Wald indígena de 2 gl:** só `ix__Indigena__T1` e `ix__Indigena__T2`, mesma V, em χ²(2) (`scripts/etapa7b3_01_esp_wald.py:36, 50–55`).
  - **Período** (3.5 e 6.7): padronização "within", só nas células do período (`scripts/etapa3_lib.py:8–9, 107–108`).
- **IC do ICR, pelo método delta:**
  - EP = √(∇′ V_cluster ∇), com ∇ = combinação dos gradientes de P(g,m).
  - IC = ICR ± 1.959964·EP; p bilateral pela normal.
  - Fonte: `scripts/etapa3_lib.py:90–94, 142–144`.
- **Atenuação (Tabela 2):**
  - ΔPR = PR_M2cc − PR_M3 é a medida principal.
  - % = (PR_M2cc − PR_M3)/(PR_M2cc − 1) × 100, mostrada só quando |PR_M2cc − 1| ≥ 0.10 (valor não arredondado).
  - Fonte: `scripts/etapa7b_01_tabelas.py:100–105, 114–121`.

## 7. Bootstrap da atenuação

- **Script e versão usada no pacote:** `scripts/etapa3_00b_bootstrap_atenuacao.py 500 --rs`, que gera `tab_e3_00b_atenuacao_ic_rs` (`scripts/etapa7b_lib.py:56`; `scripts/etapa7b_01_tabelas.py:92`).
  - A versão por município (G = 5,593) existe, mas não é usada.
- **Réplicas:** 500.
- **Reamostragem:**
  - Clusters reamostrados com reposição: regiões de saúde + `UF_xx`, G = **456** (log etapa6, linha 770).
  - Amostra: analítica com `estciv_cat` completo, isto é, os casos completos do M3 (`scripts/etapa3_00b_bootstrap_atenuacao.py:79–89`).
- **Sorteio:**
  - `numpy.random.default_rng(42).integers(0, G, size=(500, G))`; a réplica b usa a linha b.
  - Clusters em ordem lexicográfica.
  - Peso de cada célula = número de vezes que seu cluster foi sorteado (pesos de frequência).
  - Fonte: `scripts/etapa3_00b_bootstrap_atenuacao.py:4–7, 14–15, 66, 81–83`.
- **Ajuste por réplica:**
  - IRLS de Poisson próprio (link log, offset log n, pesos de frequência).
  - Partida no β da amostra completa; convergência quando max|Δβ| < 1e-10.
  - Conferido com pesos 1 contra o statsmodels.
  - M2cc e M3 são reajustados em cada réplica.
  - Fonte: `scripts/etapa3_00b_bootstrap_atenuacao.py:46–59, 98–103`.
- **Tipo de IC:** **percentil** 2.5–97.5 da distribuição das réplicas (`pandas.quantile`, interpolação linear padrão), para ΔPR e para a atenuação por réplica (`scripts/etapa3_00b_bootstrap_atenuacao.py:120–131`).
  - A estimativa pontual vem da amostra completa.
- **Seed:** 42 (`default_rng(42)`). O paralelismo em 8 processos não altera o sorteio, porque a matriz de sorteio é fixa.

## 8. Multinomial

- **Função:** `etapa6_lib.fit_mnl`, implementação própria.
  - Logit de categoria-base, Newton–Raphson na verossimilhança multinomial exata sobre células agregadas (equivalente ao ajuste individual).
  - Convergência quando max|passo| < 1e-10, com até 50 iterações.
  - Fonte: `scripts/etapa6_lib.py:30–63`.
- **Validação contra o statsmodels `MNLogit`:** β, EP do modelo e EP por cluster idênticos numa subamostra de 1% (diferença ≤ 1e-13).
  - Registrada em `scripts/etapa6_03_ptb_indicado.py:6–7` e `outputs/RESUMO_ETAPA6_v1_20261009.md:53`.
  - O script dessa validação não está no repositório.
- **Categorias:** base = termo (y0); espontâneo (y1); indicado (y2). Os PTB sem classificação são excluídos (`scripts/etapa6_03_ptb_indicado.py:35–38`).
- **Covariáveis:**
  - Modelo Brasil: as do M2 (raça + idade + ano + macrorregião).
  - Modelo por tercil: M2 + tercil_reg + raça × tercil_reg, na amostra com região de saúde.
  - Fonte: `scripts/etapa6_03_ptb_indicado.py:57–67`.
- **EP:** sanduíche agrupado por região de saúde, com correção G/(G−1)·(N−1)/(N−KJ).
  - Brasil: N = 25,676,931; G = 456.
  - Por tercil: N = 25,676,406; G = 433.
  - Fonte: log etapa6, linhas 258 e 261.
- **Medidas** (`scripts/etapa6_03_ptb_indicado.py:43–54, 72–79`):
  - RRR = exp(β) de cada raça vs Branca.
  - RRR dentro do tercil = exp(β_raça + β_raça×tercil), com IC delta.
  - Razão de RRR T1/T3 = exp(β_raça×T1).

## 9. MAIHDA (PIG)

- **Amostra:** PIG elegível com tercil, ou seja, sem os 533. N = 25,028,320; casos = 2,347,145 (log etapa5, linha 2; `scripts/etapa5_02_maihda.R:61`).
- **540 estratos** (= 4 × 3 × 3 × 5 × 3) (`scripts/etapa5_01_estratos.py:5–6, 22–32`):
  - raça: Branca, Parda, Preta, Indígena;
  - escolaridade: ≤7 = ESCMAE 1–3; 8–11 = 4; ≥12 = 5;
  - idade: <20, 20–34, ≥35;
  - macrorregião: 5;
  - tercil_reg: T1–T3, com índice t−1.
  - Os 540 estratos têm observações (`stopifnot(nrow(a) == 540)`).
- **Dados:** agregados por estrato, `cbind(casos, não casos)`. A verossimilhança binomial é igual à individual (`scripts/etapa5_02_maihda.R:1–2`).
- **Ajuste:** `lme4::glmer`, `family = binomial` (link logit, o padrão), `optimizer = "bobyqa"`, `maxfun = 1e5`, nAGQ padrão (= 1, Laplace) (`scripts/etapa5_02_maihda.R:30–33`).
  - Checagem com nAGQ = 25: σ² do M1 = 0.077245 contra 0.077222 com Laplace; σ² do M2 = 0.010222 contra 0.010221 (`scripts/etapa5_02_maihda.R:71–74`; log etapa5, linha 567).
- **Modelos:**
  - M1 = 1 + (1|estrato).
  - M2 = raça + esc3 + idade3 + região + tercil + (1|estrato), com referências Branca, ≥12, 20–34, SE, T3 (`scripts/etapa5_02_maihda.R:24–27, 31–32`).
  - Sensibilidades: estrato × ano com + ano (`scripts/etapa5_02_maihda.R:100–111`); só "outro método" (`scripts/etapa5_02_maihda.R:149–157`).
- **VPC:** σ²_u / (σ²_u + π²/3), na escala de resposta latente (`scripts/etapa5_02_maihda.R:4, 19, 35`).
  - IC de σ² por perfil de verossimilhança (`confint(..., method = "profile")`, θ²).
  - IC do VPC: transformação dos limites do perfil (`scripts/etapa5_02_maihda.R:57, 91–94`).
- **PCV:** (σ²_M1 − σ²_M2)/σ²_M1 (`scripts/etapa5_02_maihda.R:5, 97`).
  - IC por **bootstrap paramétrico**: 500 réplicas de `simulate(m2, nsim = 500, seed = 42)`, com reajuste de M1 e M2 e percentil 2.5–97.5 (`scripts/etapa5_02_maihda.R:10–11, 76–88`).
- **AUC:** P(p̂_caso > p̂_não caso) + ½ P(empate), com p̂ = probabilidade ajustada do estrato (`fitted`, Xβ + û). É um Mann–Whitney ponderado (`scripts/etapa5_02_maihda.R:6, 36–43`).
  - IC: **DeLong** com valores de colocação ponderados, **implementação própria**, z = 1.959964 (`scripts/etapa5_02_maihda.R:44–55`).
  - **O pROC não é usado.**
  - AUC só com a parte fixa (7b.1): p̂ = plogis(Xβ), mesma função DeLong (`scripts/etapa7b1_02_auc_fixa.R:1–3, 11–21, 30`).
- **Fontes das fórmulas:** Evans et al. 2024 (PMC11059336); transcrição em `docs/referencias/maihda_formulas_fonte_v1_20261008.md`.
- **Ordem do perfil:** os efeitos aleatórios (ranef) são extraídos **antes** de `confint(profile)`, porque no lme4 1.1.37 o perfil altera o ranef (`scripts/etapa5_02_maihda.R:63–65`).
- **Modelo cruzado com região de saúde (6.6 e 6b.2):**
  - Células estrato × região de saúde: 29,838 células, 540 estratos, 433 regiões, N = 25,028,320 (`scripts/etapa6_06a_estratos_area.py:12–25`; log etapa6, linha 623).
  - A1 = 1 + (1|estrato) + (1|rs); A2 = efeitos fixos do M2 + (1|estrato) + (1|rs).
  - `glmer` binomial, bobyqa, `maxfun = 2e5`, Laplace (`scripts/etapa6_06_maihda_area.R:1–4, 22–26`).
  - VPC_k = σ²_k / (σ²_estrato + σ²_região + π²/3), conforme BMJ Open 2020;10:e036130 (PMC7590346), fórmulas 5–6.
  - PCV do estrato; IC por perfil (`scripts/etapa6_06_maihda_area.R:5–9, 34–49`).
  - AUC DeLong com p̂ da célula estrato × região, incluindo os efeitos fixos e os dois û (`scripts/etapa6b_02_auc_area.R:1–5, 19–30, 49`).

## 10. Imputação múltipla da raça

- **Universo:**
  - Registros que passam nos critérios IG 22–44, ESCMAE 1–5 e IDADEMAE 10–60.
  - Treino: RACACORMAE 1–5, incluindo Amarela; 25,924,294 registros.
  - A imputar: RACACORMAE nula; 849,059 registros.
  - Fontes: `scripts/etapa4_06_imputacao_raca.py:2–3, 69–73`; log etapa6, linha 773.
- **Variáveis do modelo de imputação** (todas categóricas):
  - macrorregião, ano, idade_cat, esc_cat (5), estado civil (+ "ausente");
  - tipo de PTB (termo / espontâneo / indicado / sem classificação);
  - PIG (0 / 1 / não elegível);
  - tercil_reg (+ "sem_reg");
  - faixa de composição racial do município;
  - interações tipo de PTB × tercil, PIG × tercil e macrorregião × faixa.
  - Os desfechos entram como preditores.
  - Fonte: `scripts/etapa4_06_imputacao_raca.py:8–13, 81–88, 98–103`.
- **Como entra o Censo 2022:**
  - SIDRA, tabela 9605, nível N6 (município), variável 93, classificação 86, período 2022.
  - URL, acesso em 2026-10-08 16:07 (−03) e MD5 em `docs/referencias/censo2022/ACESSO.txt`.
  - % Branca = categoria 2776 / total 95251; % Indígena = 2780 / 95251.
  - Faixas: % Branca em 5 (cortes 20, 40, 60, 80) × % Indígena em 4 (cortes 1, 5, 20). Isso gera 24 combinações observadas em 5,570 municípios.
  - Registros sem município no Censo recebem "sem_censo" (585 registros).
  - O município entra pela faixa, não como efeito fixo; é um desvio declarado.
  - Fontes: `scripts/etapa4_06_imputacao_raca.py:5–6, 14, 58–65, 78–79`; log etapa6, linhas 772–773.
  - **NÃO DETERMINÁVEL pelo arquivo local:** os rótulos "2776 = Branca" e "2780 = Indígena" existem só no código. O JSON salvo traz apenas códigos (`/f/c`). Conferir no SIDRA.
- **Método:** **logit multinomial** com 5 categorias (não hot-deck), ajustado sobre 216,141 padrões de covariáveis com pesos iguais às contagens.
  - Chamada: `sklearn.linear_model.LogisticRegression(penalty=None, solver="lbfgs", max_iter=1000, tol=1e-8)` (`scripts/etapa4_06_imputacao_raca.py:145–147`; log etapa6, linha 788).
  - `multi_class` não é fixado. No sklearn 1.5.1, o lbfgs com mais de 2 classes resolve para multinomial (`sklearn/linear_model/_logistic.py`, `_check_multi_class`).
- **Incerteza dos parâmetros:** a cada imputação, as contagens observadas são reamostradas por Poisson(n), um bootstrap aproximado, antes do ajuste (`scripts/etapa4_06_imputacao_raca.py:15–16, 143–146`).
- **Sorteio:** multinomial da raça por célula (padrão × município), com as probabilidades previstas (`scripts/etapa4_06_imputacao_raca.py:148–150`).
- **m e seed:** m = 10 imputações, com um único gerador `numpy.random.default_rng(42)` para tudo (`scripts/etapa4_06_imputacao_raca.py:40, 49`).
- **Depois da imputação:**
  - Saem as imputadas como Amarela e as sem tercil (`sem_reg`).
  - Observados + imputados alimentam a 3.2 (`knol`) e o M2 (`--m2`), com EP por região de saúde (`--rs`).
  - O M2 é ajustado nas células da 3.2, isto é, na amostra de acesso, sem os 533.
  - Fonte: `scripts/etapa4_06_imputacao_raca.py:151–178`.
- **Regras de Rubin** (`scripts/etapa4_06_imputacao_raca.py:185–209`):
  - Q̄ = média das estimativas; W = média das variâncias; B = variância entre imputações (ddof = 1).
  - T = W + (1 + 1/m)B; λ = (1 + 1/m)B/T; **gl = (m − 1)/λ²**; IC = Q̄ ± t₀.₉₇₅,gl·√T.
  - **Atenção:** o docstring cita "Barnard–Rubin (n grande ≈ Rubin 1987)", mas a correção de amostra finita de Barnard–Rubin **não** está implementada. A fórmula usada é a de Rubin (1987).
  - **ICR:** combinado na escala de p.p. A variância de cada imputação vem do EP delta recuperado do IC: [(IC_hi − IC_lo)/(2 × 1.959964)]² (`scripts/etapa4_06_imputacao_raca.py:177, 188`).
  - **PR do M2:** combinado na escala de log PR, com EP = √V_cluster[j,j], e depois exponenciado (`scripts/etapa4_06_imputacao_raca.py:170–175, 200–209`).
  - Versões usadas no pacote: `tab_e4_06_mi_rubin_rs` e `tab_e4_06_mi_m2_rubin_rs` (`scripts/etapa7b_01_tabelas.py:335`).
  - O Wald combinado não foi implementado; aparece como n.a. na Tabela 4.

## 11. Limites de nascidos vivos

- **Fonte do óbito fetal:** SIM-DOFET, 2015–2024.
  - Cópia local: `/Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim/_dofet/parquet/ano=*/uf=*.parquet` (`scripts/etapa6_07_tempo_nascidos_vivos.py:59`; `scripts/etapa1_06_sim_checagem.py:4–7`).
  - Origem: `ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOFET/DOFET{AA}.dbc`, diretório definitivo, baixado em 2026-10-02 entre 09:44 e 09:58 (−03).
  - Registros: `…/dados_artigos_perinatais_clima/logs/integridade.csv` e `…/02_sim/FONTE.md`, seções 1–2. Esses arquivos estão **fora** do repositório do projeto.
- **Critério de óbito fetal** (o mesmo da 1.6, conferido por assert):
  - TIPOBITO = 1 E [SEMAGESTAC válido (≠ 9 e ≠ 99) ≥ 22 **OU** (SEMAGESTAC nulo, 9 ou 99 E GESTACAO 2–6) **OU** PESO ≥ 500 g].
  - O "OU" é simples, não hierárquico. O FONTE.md do hub descreve um critério hierárquico, mas o projeto usa o "OU".
  - Fontes: `scripts/etapa6_07_tempo_nascidos_vivos.py:6–8, 61–70`; `scripts/etapa1_06_sim_checagem.py:11`.
- **Razão de óbito fetal nacional:** f = Σ óbitos fetais / (Σ óbitos fetais + Σ nascidos vivos), 2015–2024.
  - Nascidos vivos = todos os residentes do SINASC, sem a cascata.
  - f = **9.70 por 1,000 nascimentos totais** (`scripts/etapa6_07_tempo_nascidos_vivos.py:72–82`; log etapa6, linha 598).
- **Fórmula (seleção simples):**
  - P*_g = (NV_g·p_g + OF_g·q)/(NV_g + OF_g), com OF_g/NV_g = k_g·f/(1 − f).
  - Implementada como (p_g + odds·q)/(1 + odds) (`scripts/etapa6_07_tempo_nascidos_vivos.py:9–14, 99–101`).
  - p_g = prevalência bruta observada nos nascidos vivos (amostra analítica, Brasil).
  - q = proporção do desfecho entre os óbitos fetais (`scripts/etapa6_07_tempo_nascidos_vivos.py:84–94`):
    - PTB: % < 37 semanas entre os óbitos fetais com SEMAGESTAC 22–44 = 74.8% (n = 245,528).
    - PIG: % < P10 (grade gigs, +3 dias) entre óbitos fetais de gestação única casados na grade (24–42 semanas, sexo 1/2, peso 100–7000 g) = 33.2% (n = 198,153).
    - Também o limite q = 1.
- **A que se aplica a razão 1–2×:** à **razão óbito fetal / nascido vivo** das indígenas, k·f/(1 − f).
  - k = 1, 1.5 e 2 para indígenas; k = 1 para brancas.
  - Pretas e pardas não entram no fator (`scripts/etapa6_07_tempo_nascidos_vivos.py:14, 98–103`).
- **Correção** (`scripts/etapa6_07_tempo_nascidos_vivos.py:15–16, 102–108`):
  - fator = RP*_bruta / RP_bruta (Indígena / Branca).
  - PR do M2 corrigida = PR_M2 × fator; os limites do IC são multiplicados pelo mesmo fator.
  - É uma aproximação declarada: o fator bruto é aplicado à PR ajustada.
- **Desfechos:** só PTB e PIG; o PTB indicado aparece como n.a.
  - A Tabela 4 mostra o intervalo mínimo–máximo da PR do M2 corrigida sobre k ∈ {1, 1.5, 2} × q ∈ {observado, 1} (`scripts/etapa7b_01_tabelas.py:307–311, 319–321`).

## 12. PIG e o critério > P97

- **Função:** `gigs::value2centile(y = PESO/1000, x = 7*SEMAGESTAC + k, sex = "M"/"F", family = "ig_nbs", acronym = "wfga")`. É o peso-para-IG ao nascer do INTERGROWTH-21st, com os padrões de RN e de muito prematuro.
  - Calculada uma vez numa grade SEMAGESTAC 24–42 × SEXO 1/2 × PESO 100–7000 g, depois casada com cada registro (`scripts/etapa1_02b_pig_grade.R:1–6, 16–21`; `scripts/etapa1_01_base_v2.py:24, 65–77`).
  - k = 3 dias na análise principal; k = 0 e 6 na sensibilidade.
- **Validação:**
  - gigs contra a tabela oficial (2 casas decimais): 1721 de 1862 pontos iguais, diferença máxima de 0.01 kg.
  - gigs contra growthstandards 0.1.7: diferença máxima de 1.3e-15 kg.
  - Fontes: log etapa1, linhas 2–3; `scripts/etapa1_02a_pig_validacao.R`.
- **Sexo ignorado:** SEXO fora de {1, 2} (0 ou nulo) torna o registro **não elegível**. O PIG fica NA, fora do numerador e do denominador; o sexo não é imputado (`scripts/etapa1_01_base_v2.py:65–66`).
- **Elegibilidade:** gestação única (GRAVIDEZ = 1), SEMAGESTAC 24–42, SEXO 1/2 e PESO 100–7000 g.
  - As semanas 22–23 e 43–44 ficam fora porque o padrão cobre de 168 a 300 dias (`scripts/etapa1_02b_pig_grade.R:6`).
- **Corte:** PIG = centil **< 0.10**, estrito (`scripts/etapa1_01_base_v2.py:76`).
  - Sensibilidade "tabela oficial": PESO < P10 oficial (PDF, semanas + 3 dias), na coluna `pig_tabela_oficial` (`scripts/etapa1_01_base_v2.py:78–80`).
- **Critério > P97 da reclassificação** (critério b da 4b):
  - Entre os PTB de gestação única (GRAVIDEZ = 1), com SEMAGESTAC **24–36**, SEXO 1/2 e PESO 100–7000.
  - Centil `centil_k3` **> 0.97** (estrito), da mesma grade gigs, com IG = 7·semanas + 3.
  - Esses PTB passam a **não caso**, e o denominador não muda.
  - Vale para `ptb` e `ptb_esp`. Os PTB sem classificação continuam NA no `ptb_esp`.
  - 410,747 PTB reclassificados, dos quais 244,676 espontâneos (assert em `scripts/etapa6_01_cluster_rs.py:37`).
  - Fontes: `scripts/etapa4b_01_plausibilidade.py:4–8, 27, 35, 56–59`; `scripts/etapa4b_03_ptb_plausivel.py:2–4, 25–37`; `scripts/etapa7b3_01_esp_wald.py:27–34`.
  - Critério a, só em sensibilidade: PESO ≥ 2,500 g.

## 13. Benjamini–Hochberg

- **Script:** `scripts/etapa6_05_multiplicidade.py`.
- **Hierarquia**, definida antes de olhar os q-valores (`scripts/etapa6_05_multiplicidade.py:4–11, 32–37`):
  - **Principal:** 3.2 para PIG, PTB, PTB espontâneo e PTB indicado (ICR das 3 raças × T1/T2 e Wald por desfecho).
  - **Secundária:** 3.3a contínuo (desfechos principais), 3.3b tercil nacional, 3.6 limites dos não classificados, 6.3 razão de RRR T1/T3, 6.4 análise robusta à datação.
  - **Exploratória:** o restante.
  - As sensibilidades (Etapas 4, 4b, 6.1b e imputação) não entram.
- **Família exploratória:** 390 testes, com ICR e Wald juntos (`outputs/tables/tab_e6_05_multiplicidade_v1_20261008.csv`):

| Análise | ICR | Wald | Outros |
|---|---:|---:|---:|
| 3.2 para lbw_termo | 6 | 1 | — |
| 3.3a índice contínuo, lbw_termo (RP de interação por 5 p.p.) | — | — | 3 |
| 3.3c: 3.2 estratificado por macrorregião (5 desfechos × 5 regiões) | 150 | 25 | — |
| 3.4 raça × macrorregião | 60 | 5 | — |
| 3.5 raça × idade | 30 | 5 | — |
| 3.5 raça × escolaridade (3 níveis) | 30 | 5 | — |
| 3.5 raça × período | 30 | 5 | — |
| 4.1c raça × método da IG | 30 | 5 | — |
| **Total** | **336** | **51** | **3** |

- **Método:** BH (1995) step-up, com q-valor ajustado por monotonicidade e truncado em 1, só dentro da família exploratória (`scripts/etapa6_05_multiplicidade.py:12, 90–98`).
- **Nível q:** o código **não fixa limiar de decisão**. Ele calcula os q-valores e resume as contagens com q < 0.05 e q < 0.10 (`scripts/etapa6_05_multiplicidade.py:100–103`). São 145 testes com q < 0.05.
- **Fora da tabela de multiplicidade:** os testes das Etapas 7b.1–7b.3 (cenários de datação, Wald indígena de 2 gl).

## 14. Exclusão de CE e DF

- **Justificativa no código:** "as duas UFs com pior completude de RACACORMAE na Etapa 0" (`scripts/etapa1_07_sensibilidade_ce_df.py:2`).
  - Números: % ausente + ignorado de RACACORMAE, média simples de 2015–2024: **CE 17.5%, DF 16.9%**. As seguintes são PB 7.8%, BA 6.3% e GO 6.1% (`outputs/RESUMO_ETAPA0_v1_20261008.md:23`, gerado por `scripts/etapa0_03_completude.py`).
- **Especificação da Etapa 4** (prompt da sessão, fora do repositório): acrescenta "e índice de acesso mais grosseiro". Essa segunda razão não está quantificada em nenhum script nem log: **NÃO DETERMINÁVEL** pelo código.
- **Implementação:** `~uf.isin(["CE", "DF"])`, pela UF de residência (CODMUNRES). Os tercis não são recalculados (`scripts/etapa7b3_01_esp_wald.py:89`; `scripts/etapa7b1_01_analises.py:31`).

## 15. Exclusão de 2024

- **Justificativa:** nenhuma registrada em código, log, RESUMO ou no protocolo v3.5. A especificação da Etapa 4 diz só "4.4 Sem 2024: refaça 3.2." **NÃO DETERMINÁVEL.**
- **Implementação:** `ano != 2024`, pelo ano de DTNASC. Os tercis não são recalculados (`scripts/etapa7b3_01_esp_wald.py:90`).
- **Arquivo de 2024 usado:** `/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_2024.parquet`, convertido do arquivo nacional `DNBR2024.dbc` ("2024 = DNBR final"; `outputs/RESUMO_ETAPA0_v1_20261008.md:4`).
  - Data de modificação dos dois: **2026-06-27**, 16:52–16:53. É metadado do sistema de arquivos (exFAT).
- **Status do arquivo:**
  - Uma cópia independente por UF baixou 2024 do diretório **definitivo** DNRES em 2026-10-02, e a diferença contra o arquivo usado é 0 por UF.
  - Fontes: `…/dados_artigos_perinatais_clima/logs/integridade.csv`; `outputs/RESUMO_ETAPA0_v1_20261008.md:4`. A comparação em si não está em script do projeto.
  - Segundo o FONTE.md do hub (acesso em 2026-10-01), o portal de dados abertos mostrava o arquivo de 2024 atualizado em **08/05/2026**, sem rótulo de preliminar.
  - A página "Dados prévios" da CGIAE ainda chamava 2024 de preliminar.
- **Data de disponibilização pelo DATASUS:** **NÃO DETERMINÁVEL** pelo código. A data mais próxima registrada é a atualização no portal (08/05/2026), segundo documento de outro projeto.

## 16. Versões de software

Versões obtidas em 2026-10-09, sem instalar nada. O `pip freeze` desta instalação Anaconda mostra a maioria dos pacotes como `@ file://…`, então as versões abaixo vêm de `__version__` e de `sessionInfo()`. Não há registro de versão em tempo de execução, exceto em `outputs/manuscrito/data_code_availability.md` (Etapa 7b), que bate com esta lista.

**Python 3.12.7** (Anaconda, macOS arm64, `/Users/guilherme/Applications/anaconda3/bin/python3`):

| Pacote | Versão | Uso |
|---|---|---|
| pandas | 2.2.2 | todos os scripts |
| numpy | 1.26.4 (OpenBLAS 0.3.21) | todos os scripts |
| scipy | 1.13.1 | distribuições normal, t e χ² |
| statsmodels | 0.14.2 | GLM Poisson, logit e WLS (`fit_agg`) |
| patsy | 0.5.6 | matrizes de desenho |
| pyarrow | 16.1.0 | Parquet |
| duckdb | 1.5.6 | SIM (1.6, 6.7) e auditorias |
| scikit-learn | 1.5.1 | imputação (4.6) |
| matplotlib | 3.9.2 | figuras |
| Pillow | 10.4.0 | TIFF |
| openpyxl | 3.1.5 | ESM_1.xlsx |
| python-docx | 1.2.0 | checklist RECORD |
| tabulate | 0.9.0 | `to_markdown` dos RESUMOs |

**R 4.5.1** (2025-06-13, aarch64-apple-darwin20; BLAS de referência do R; LAPACK 3.12.1):

| Pacote | Versão | Uso |
|---|---|---|
| lme4 | 1.1-37 | MAIHDA (`glmer`) |
| Matrix | 1.7-3 | dependência do lme4 |
| minqa | 1.2.8 | otimizador bobyqa |
| nloptr | 2.2.1 | dependência do lme4 |
| data.table | 1.17.8 | MAIHDA e AUC |
| MASS | 7.3-65 | `mvrnorm` nas predições do MAIHDA |
| gigs | 0.5.2.9000 | INTERGROWTH-21st |
| growthstandards | 0.1.7 | validação cruzada do gigs |
| arrow | 21.0.0.1 | grava a grade do PIG |
| pROC | 1.19.0.1 | **instalado, não usado** |

- **Divergência no `data_code_availability.md`** (`scripts/etapa7b_02_suplementar.py:407–431`):
  - Lista o `nnet` 7.3.20, que nenhum script usa.
  - Omite MASS e growthstandards.
  - Chama o commit 173fecd de "commit for the analyses (Etapas 0–6b)", mas esse é o commit da 7b.2.

## 17. Origem dos dados

- **SINASC usado nas análises:** `/Volumes/Forja/CliMaterna/01_data/raw/SINASC/sinasc_{ano}.parquet` (`scripts/etapa0_lib.py:18`), a mesma fonte do artigo da RSP.
  - O README da pasta diz: "Nascidos Vivos (.dbc por UF-ano) — Projeto CliMaterna, Hub de Dados. Gerado: 2026-03-18".
  - `outputs/RESUMO_ETAPA0_v1_20261008.md:4`: um arquivo nacional por ano, DNRES; 2024 = DNBR final.
  - O FONTE.md do hub identifica essa base como a publicada em Torezzan et al., Data in Brief 2025;62:111920.
- **Datas dos parquets** (metadado do sistema de arquivos):
  - `sinasc_2014` a `sinasc_2022`: 2026-03-06 10:22. O de 2014 serve só para o índice t−1.
  - `sinasc_2023`: 2026-03-25 04:33.
  - `sinasc_2024`: 2026-06-27 16:53.
- **"Download em 2026-10-07":** não encontrei essa data no projeto, no README nem nos logs do hub. Os metadados acima são anteriores. **Precisa de confirmação de Guilherme antes de entrar no texto.**
- **URL do download original desses arquivos:** **NÃO DETERMINÁVEL**. Não está registrada no projeto nem no README; a pendência já está declarada em `scripts/etapa7b_02_suplementar.py:419–422`.
  - O endereço documentado para os mesmos arquivos é `ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/DN{UF}{AAAA}.dbc`, segundo o FONTE.md do hub.
  - O hub baixou desse endereço a cópia independente por UF (2011–2024, todos do diretório definitivo) em 2026-10-02. A diferença contra a base usada é 0 por UF × ano (`outputs/RESUMO_ETAPA0_v1_20261008.md:4`).
- **Versão dos arquivos de 2024:** arquivo nacional DNBR2024 (definitivo, segundo a cópia por UF; ver pergunta 15).
- **Bases derivadas do projeto:** v1, v2 e v3 gravadas em 2026-10-08 (carimbo `STAMP = 20261008`), em `data/processed/`, fora do git.
- **SIM-DOFET:** ver pergunta 11. URL do FTP e download em 2026-10-02, registrados no hub e não no projeto.
- **Outras fontes, com URL e data registradas no projeto:**
  - Base territorial dez/2024: pergunta 4.
  - Censo 2022 (SIDRA 9605): pergunta 10.
  - Tabelas oficiais do INTERGROWTH-21st (`docs/referencias/grow_*_bw_table.pdf`): baixadas em 2026-10-08 (`scripts/etapa1_02a_pig_validacao.R:7–8`).

---

## Pendências para os autores (sem mudar análise)

1. **Justificativas a escrever:** exclusão da Amarela (1), exclusão de 2024 (15) e o "índice de acesso mais grosseiro" de CE/DF (14).
2. **SINASC:** confirmar a data e a URL de download, porque a data informada (2026-10-07) não bate com os metadados (17).
3. **Texto dos Métodos:**
   - escolaridade em 5 categorias no M3;
   - M2 sem escolaridade e estado civil;
   - regra do PTB com PARTO e sem TPROBSON;
   - gl de Rubin (1987);
   - DeLong implementado à mão (sem pROC);
   - critério de óbito fetal com "OU".
4. **Corrigir no `data_code_availability.md`:**
   - lista de pacotes do R (tirar `nnet`; incluir MASS e growthstandards);
   - rótulo do commit 173fecd.
5. **Censo 2022:** conferir no SIDRA os rótulos das categorias 2776 (Branca) e 2780 (Indígena).
