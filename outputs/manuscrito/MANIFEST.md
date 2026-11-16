# MANIFEST — pacote de resultados (Etapas 7b–7d, v15_20261115)

Gerado em 2026-11-15. Commit do repositório ao gerar o pacote: a3859de (o pacote v15_20261115 entra no commit 'Etapa 7d: montagem da Submissao (pacote v15)'). Nenhuma análise nova no pacote: todo número vem de outputs/tables/*_v1_20261008.csv (EP por região de saúde). v5 = v4 com rótulos novos (IC, Brown), sem a sensibilidade 'Excluding 2024' e com a Tabela S7a (variáveis e códigos); v6 = v5 com 'tertile', 'Asian (amarela)' na S7a, SEXO do SIM recodificado (q do PIG idêntico) e proveniência dos dados; v7 = v6 com 'Asian (amarela)' em todo o pacote, N do M2cc/M3 no rodapé da Tabela 2 e números-chave das especificações alternativas do acesso (EP por região de saúde); v8 = v7 com a Tabela S2b (especificações alternativas do acesso) no ESM_1; v9 = v8 com a justificativa da exclusão da raça Asian (amarela) no rodapé da S1 e na disponibilidade (número-chave pct_amarela_fonte) e Submissao/ montada sem arquivos ._* (dot_clean); v10 = v9 com o denominador do índice de acesso explícito nos rodapés (nascimentos com mês de início do pré-natal conhecido); v11 = v10 com os campos commit_pacote (antigo commit), commit_registro e commit_analise nos números-chave; v12 = v11 com o rodapé da Tabela 4 dizendo que os testes de Wald conjuntos não foram calculados na imputação múltipla, os números-chave n_regsaude_CE e n_regsaude_DF (regiões de saúde no mapa município → região de saúde da base territorial, tab_e7c7_01_regsaude_uf) e suplementar/ sem arquivos ._* (dot_clean no 02); v13 = v12 com a cobertura da Atenção Básica na Tabela S2b (colunas d e e, nascimentos de 2015–2021; tab_e8_04_*, tab_e8_03_*, Etapa 8), os números-chave da Etapa 8 e a nota geral 'n.a.' no rodapé da Tabela 4; v14 = v13 com o Wald de 6 gl (termos raça × tercil) nas colunas d e e da Tabela S2b e seus 6 números-chave (Etapa 8b); v15 = v14 com a Submissao/ final (Etapa 7d): Online Resources renumeradas na ordem de 1ª citação (OR1 STROBE + RECORD, OR2 variáveis, OR3 Supplementary Methods, OR4 tabelas S, OR5 Fig. S9), a Tabela 3b movida para a S3b (ESM_4.xlsx), TIFF em RGB sem alfa (mesmos pixels), o manuscrito montado com as Tabelas 1–4 e as Figs. 1–4 e o checklist com página e linha (montagem/). Scripts em scripts/. As autoauditorias das etapas (audita_*.csv, na raiz de outputs/manuscrito/) ficam fora da lista de arquivos: são gravadas depois do pacote, para conferi-lo.

## Correspondência material suplementar → Online Resource (Springer)

| Suplementar | Conteúdo | Arquivo em Submissao/ |
|---|---|---|
| S8 | Online Resource 1: checklist STROBE + RECORD, com página e linha do Manuscript final | ESM_1.pdf |
| S7 (S7a, S7b) | Online Resource 2: variáveis e códigos (S7a, RECORD 6.1), dicionário operacional (S7b) e código 8 | ESM_2.pdf |
| — | Online Resource 3: Supplementary Methods (texto dos autores, com a URL da cobertura da Atenção Básica) | ESM_3.pdf |
| S1, S1b | Online Resource 4: fluxo STROBE, excluídos × incluídos; dados faltantes | ESM_4.xlsx (abas S1_flow_excluded, S1b_missing_data) |
| S2 | Online Resource 4: Knol & VanderWeele, PTB espontâneo | ESM_4.xlsx (S2_knol_spontaneous) |
| S2b | Online Resource 4: especificações alternativas do acesso (tercis nacionais, índice contínuo; cobertura da Atenção Básica e índice, 2015–2021; EP por região de saúde) | ESM_4.xlsx (S2b_access_specifications) |
| S3 | Online Resource 4: multinomial termo/espontâneo/indicado | ESM_4.xlsx (S3_multinomial) |
| S3b | Online Resource 4: cortes dos tercis por macrorregião (antiga Tabela 3b) | ESM_4.xlsx (S3b_terciles_region) |
| S4, S4b | Online Resource 4: exploratórias com p ajustado por BH | ESM_4.xlsx (S4_exploratory_strata, S4b_exploratory_family) |
| S5 | Online Resource 4: plausibilidade peso × IG | ESM_4.xlsx (S5_weight_ga_plausibility) |
| S5c | Online Resource 4: outro método separado em código 1 e código 2 (diagnóstico de datação) | ESM_4.xlsx (S5c_other_method_by_code) |
| S5d | Online Resource 4: PTB espontâneo por código e Wald dos termos indígenas (2 gl) | ESM_4.xlsx (S5d_spontaneous_by_code_wald) |
| S5b | Centro-Oeste, modelo da RSP por método | **NÃO enviado** (só em outputs/manuscrito/suplementar; aguarda orientadores) |
| S6 | Online Resource 4: MAIHDA (PIG) | ESM_4.xlsx (S6_maihda) |
| S9 | Online Resource 5: caterpillar MAIHDA | ESM_5.pdf |

## Arquivos

| Arquivo | Script | Origem | MD5 |
|---|---|---|---|
| manuscrito/tabelas/tab01_characteristics_v15_20261115.csv | etapa7b_01_tabelas.py | tab_e1_03_tabela1_long, tab_e3_01_n_casos_raca_tercil_regiao, tab_e3_00a_ig_metodo_raca, tab_e6b_01_ptb_raca_metodo | 8b6175d7e6bb |
| manuscrito/tabelas/tab02_models_m1m3_v15_20261115.csv | etapa7b_01_tabelas.py | tab_e6b_01_modelos_m1m3, tab_e3_00b_atenuacao_ic_rs (atenuação só com \|PR_M2cc − 1\| ≥ 0.10) | 5fc670307989 |
| manuscrito/tabelas/tab03_knol_tercile_v15_20261115.csv | etapa7b_01_tabelas.py | tab_e6_01a_{conjunto,dentro,interacao,wald}, tab_e3_01_n_casos_raca_tercil_regiao, tab_e7b1_05_reri_recod | d2c6e55de443 |
| manuscrito/tabelas/tab04_sensitivity_v15_20261115.csv | etapa7b_01_tabelas.py | tab_e6_01a_m2, tab_e6_01a_interacao, tab_e6b_01_m2_cenarios, tab_e6_01b_interacao, tab_e6_04_m2, tab_e6_04_interacao, tab_e4_06_mi_m2_rubin_rs, tab_e4_06_mi_rubin_rs, tab_e6_07b_limites, tab_e7b1_01_cenarios_{interacao,wald}, tab_e6_01a_wald, tab_e6_04_wald, tab_e7b1_04_{m2,interacao}, tab_e7b2_01_{m2,interacao,wald}, tab_e7b2_02_reclass_{m2,interacao,wald}, tab_e7b3_02_wald_ind | eddb96a60b10 |
| manuscrito/tabelas/tabelas_principais_v15_20261115.docx | etapa7b_01_tabelas.py | Tables 1, 2, 3, 4 | 918d4e1a6d98 |
| manuscrito/tabelas/tabelas_principais_v15_20261115.xlsx | etapa7b_01_tabelas.py | Tables 1, 2, 3, 4 | 4ba3f635c68a |
| manuscrito/figuras/fig01_flowchart_v15_20261115.png | etapa7b_03_figuras.py | tab06, tab07, tab_e6_01a_wald, tab_e6b_01_ptb_raca_metodo, tab_e6_04_m2, tab_e3_00a_ig_metodo_raca | 9bf84e502704 |
| manuscrito/figuras/fig01_flowchart_v15_20261115.tif | etapa7b_03_figuras.py | tab06, tab07, tab_e6_01a_wald, tab_e6b_01_ptb_raca_metodo, tab_e6_04_m2, tab_e3_00a_ig_metodo_raca | d2d2d1dde079 |
| manuscrito/figuras/fig02_pr_race_m1m3_v15_20261115.png | etapa7b_03_figuras.py | tab_e6b_01_modelos_m1m3 | 14ece41be95d |
| manuscrito/figuras/fig02_pr_race_m1m3_v15_20261115.tif | etapa7b_03_figuras.py | tab_e6b_01_modelos_m1m3 | 0b1a25c3eb8b |
| manuscrito/figuras/fig03_rd_race_tercile_v15_20261115.png | etapa7b_03_figuras.py | tab_e6_01a_conjunto, tab_e6_01a_interacao | 9d76388b3ed7 |
| manuscrito/figuras/fig03_rd_race_tercile_v15_20261115.tif | etapa7b_03_figuras.py | tab_e6_01a_conjunto, tab_e6_01a_interacao | 0a2c985ebcab |
| manuscrito/figuras/fig04_dating_v15_20261115.png | etapa7b_03_figuras.py | tab_e6b_01_ptb_raca_metodo, tab_e4b_01_implausivel_brasil, tab_e6b_01_m2_cenarios, tab_e6_01a_m2, tab_e6_04_m2 | 7395425de597 |
| manuscrito/figuras/fig04_dating_v15_20261115.tif | etapa7b_03_figuras.py | tab_e6b_01_ptb_raca_metodo, tab_e4b_01_implausivel_brasil, tab_e6b_01_m2_cenarios, tab_e6_01a_m2, tab_e6_04_m2 | 39baf2b7f2cf |
| manuscrito/suplementar/ESM_4_tables_S1_S6_v15_20261115.xlsx | etapa7b_02_suplementar.py | S1–S6 com S3b (sem S5b) | 5b094d1cf7e2 |
| manuscrito/suplementar/S1_flow_excluded_v15_20261115.csv | etapa7b_02_suplementar.py | tab06_fluxograma_regiao, tab07_fluxograma_motivos, tab_e7b1_02_s1_restrito, tab08_ptb_incluidos_excluidos, tab_e7b1_04_naoclass | 3335b79e86df |
| manuscrito/suplementar/S1b_missing_data_v15_20261115.csv | etapa7b_02_suplementar.py | tab01_completude_ano, tab_e2_01_tpmetestim_ano_regiao, tab_e6_03a_robson | 284bedf461f4 |
| manuscrito/suplementar/S2_knol_spontaneous_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e6_01a_* (ptb_esp), tab_e3_01_n_casos_raca_tercil_regiao, tab_e7b1_04_{m2,interacao,naoclass} | eb09d311bd2a |
| manuscrito/suplementar/S2b_access_specifications_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e3_02_interacao_rs, tab_e3_02_wald_rs, tab_e3_03a_indice_continuo_rs, tab_e8_04_interacao, tab_e8_04_wald, tab_e8_03_spearman, tab_e8_03_concordancia_resumo, tab_e8_03_raca_por_tercil (EP por região de saúde) | 91cd39fe4a66 |
| manuscrito/suplementar/S3_multinomial_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e6_03b_rrr | 6cb729e08a51 |
| manuscrito/suplementar/S3b_terciles_region_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e3_01_tercis_regiao_cortes, tab_e3_01_n_casos_raca_tercil_regiao (antiga Tabela 3b) | ea2e9912bbcb |
| manuscrito/suplementar/S4_exploratory_strata_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e6_05_multiplicidade | 170ff63a7b51 |
| manuscrito/suplementar/S4b_exploratory_family_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e6_05_multiplicidade | 75deb4060c82 |
| manuscrito/suplementar/S5_weight_ga_plausibility_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e4b_01_implausivel_brasil | 0ff98b4e5762 |
| manuscrito/suplementar/S5b_centerwest_rsp_by_method_INTERNAL_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e4b_04_co_estratos_rs (INTERNAL) | c32304e7277f |
| manuscrito/suplementar/S5c_other_method_by_code_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e7b2_01_{dist,dist_tercil,m2,interacao,wald,p97,casos_ind} | d74554c55b48 |
| manuscrito/suplementar/S5d_spontaneous_by_code_wald_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e7b3_01_esp_{m2,interacao}, tab_e7b3_02_wald_ind, tab_e7b2_02_reclass_interacao | 23a2b4322353 |
| manuscrito/suplementar/S6_maihda_v15_20261115.csv | etapa7b_02_suplementar.py | tab_e5_02_modelos, tab_e6_06_maihda_area, tab_e6b_02_auc_area, tab_e7b1_03_auc_fixa, tab_e5_03_predicoes | 522cb3011674 |
| manuscrito/suplementar/S7_variables_codes_v15_20261115.pdf | etapa7b_02_suplementar.py | S7a (docs/referencias/SINASC_Estrutura_2024.pdf, Dicionario_SIM_2025.pdf; códigos da ficha 7c.0), dicionario_variaveis_v3, tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_2010_2014 | 75a2d83342e3 |
| manuscrito/suplementar/S7a_variables_codes_v15_20261115.csv | etapa7b_02_suplementar.py | docs/referencias/SINASC_Estrutura_2024.pdf, Dicionario_SIM_2025.pdf; códigos da ficha 7c.0; tab_e6_02a_concordancia, tab_e6_02b_tpmetestim_2010_2014 | 81134fcfca2e |
| manuscrito/suplementar/S7b_dictionary_v15_20261115.csv | etapa7b_02_suplementar.py | dicionario_variaveis_v3 | 0df197cf025b |
| manuscrito/suplementar/S8_strobe_record_checklist_v15_20261115.csv | etapa7b_02_suplementar.py | docs/referencias/RECORD_checklist_acesso20261009.docx (CC BY; ver docs/referencias/ATRIBUICAO.txt) | ddf2005bc741 |
| manuscrito/suplementar/S8_strobe_record_checklist_v15_20261115.pdf | etapa7b_02_suplementar.py | docs/referencias/RECORD_checklist_acesso20261009.docx (CC BY; ver docs/referencias/ATRIBUICAO.txt) | 660749ff7368 |
| manuscrito/suplementar/S9_maihda_caterpillar_v15_20261115.png | etapa7b_03_figuras.py | tab_e5_03_predicoes | 2a4fbb27fabf |
| manuscrito/suplementar/S9_maihda_caterpillar_v15_20261115.tif | etapa7b_03_figuras.py | tab_e5_03_predicoes | 6493598b990f |
| manuscrito/montagem/ESM_1_strobe_record_located_v15_20261115.csv | etapa7d_01_montagem.py | S8 + página e linha do Manuscript (PDF do Word) | b0e534714070 |
| manuscrito/montagem/ESM_1_strobe_record_located_v15_20261115.pdf | etapa7d_01_montagem.py | S8 + página e linha do Manuscript (PDF do Word) | ec4b5356c0e9 |
| manuscrito/montagem/ESM_3_supplementary_methods_v15_20261115.docx | etapa7d_01_montagem.py | manuscrito/ESM_3_Supplementary_Methods.docx + URL de docs/referencias/aps_cobertura_ab/ACESSO.txt; PDF pelo Microsoft Word | 0b560f074d8e |
| manuscrito/montagem/ESM_3_supplementary_methods_v15_20261115.pdf | etapa7d_01_montagem.py | manuscrito/ESM_3_Supplementary_Methods.docx + URL de docs/referencias/aps_cobertura_ab/ACESSO.txt; PDF pelo Microsoft Word | 8f94b9317c90 |
| manuscrito/montagem/Manuscript_v15_20261115.docx | etapa7d_01_montagem.py | manuscrito/Manuscript.docx + Tabelas 1–4 (tabelas/) + Figs. 1–4 (figuras/, PNG); PDF pelo Microsoft Word | 436239f4a204 |
| manuscrito/montagem/Manuscript_v15_20261115.pdf | etapa7d_01_montagem.py | manuscrito/Manuscript.docx + Tabelas 1–4 (tabelas/) + Figs. 1–4 (figuras/, PNG); PDF pelo Microsoft Word | 01c8c36a4b5d |
| manuscrito/montagem/confere_7d_numeros_v15_20261115.csv |  |  | d36c4e0cf340 |
| manuscrito/montagem/confere_7d_v15_20261115.csv |  |  | 358f9e6b4ceb |
| manuscrito/checa_7b_v15_20261115.csv |  |  | fa7c8a668ec3 |
| manuscrito/data_code_availability.md | etapa7b_02_suplementar.py | docs/referencias/*/ACESSO.txt | 2d47a0100268 |
| manuscrito/ficha_metodos_7c0_v1_20261009.md |  |  | 992dfadecfbe |
| manuscrito/legendas_figuras.md | etapa7b_03_figuras.py | — | 793f1646ebab |
| manuscrito/numeros_chave_v15_20261115.json | etapa7b_01_tabelas.py | ver cada item | ce1d91ed2c7d |
| manuscrito/numeros_chave_v15_20261115.md | etapa7b_01_tabelas.py | ver cada item | f018247c00b1 |
| Submissao/Cover_Letter.docx | etapa7b_04_submissao.py | cópia de manuscrito/ (Title_Page, Cover_Letter) | ac2be89cf60c |
| Submissao/ESM_1.pdf | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | ec4b5356c0e9 |
| Submissao/ESM_2.pdf | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 75a2d83342e3 |
| Submissao/ESM_3.pdf | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 8f94b9317c90 |
| Submissao/ESM_4.xlsx | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 5b094d1cf7e2 |
| Submissao/ESM_5.pdf | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 80597bb9e8b7 |
| Submissao/Fig1.tif | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | d2d2d1dde079 |
| Submissao/Fig2.tif | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 0b1a25c3eb8b |
| Submissao/Fig3.tif | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 0a2c985ebcab |
| Submissao/Fig4.tif | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 39baf2b7f2cf |
| Submissao/Manuscript.docx | etapa7b_04_submissao.py | cópia/montagem de outputs/manuscrito | 436239f4a204 |
| Submissao/Title_Page.docx | etapa7b_04_submissao.py | cópia de manuscrito/ (Title_Page, Cover_Letter) | 0de70a597b67 |
