# Data and code availability (draft, Etapa 7b, v4_20261009)

## Sources (RECORD 1.3, 12.1)
- **SINASC live birth microdata, 2015–2024** (DATASUS, Ministry of Health; files DNRES by state/year, 2024 = national final file).
  Local copy: CliMaterna data hub (generated 2026-03-18), cross-checked against an independent per-state download of 2026-10-02
  (difference 0 by state × year; RESUMO_ETAPA0). **PENDING: exact download URL and access date of the DATASUS files were not
  recorded in the project; Guilherme to confirm (e.g., DATASUS FTP / OpenDataSUS path) before submission.**
- **Health regions (territorial base, Dec 2024)**: ftp://ftp.datasus.gov.br/territorio/tabelas/2024/12-base territorial_dez24.zip (FTP datado 12-19-24 02:49PM, 1517583 bytes); accessed 2026-10-08 12:42 -03; MD5 (base_territorial_dez24.zip) = 469fa5bfc171e47c54a9b903fda85098.
- **IBGE 2022 Census, SIDRA table 9605** (resident population by color or race, municipality level): https://apisidra.ibge.gov.br/values/t/9605/n6/all/v/93/p/2022/c86/95251,2776,2777,2778,2779,2780/f/c; accessed 2026-10-08 16:07 -03; MD5 (sidra_9605_n6_2022.json) = 50c1289306d167c108927cf7b0c7a7cb.
- **SIM fetal deaths (SIM-DOFET)** for live-birth bounds: DATASUS; local copy in the Forja hub (path in scripts/etapa1_06_sim_checagem.py). **PENDING: URL/access date.**
- **INTERGROWTH-21st newborn size standards** (birth weight centiles): R package gigs; official tables in docs/referencias (grow_*_bw_table.pdf).

## Software
- Python 3.12.7: pandas 2.2.2, numpy 1.26.4, statsmodels 0.14.2, scipy 1.13.1, duckdb 1.5.6, pyarrow 16.1.0, patsy 0.5.6, sklearn 1.5.1, matplotlib 3.9.2
- R version 4.5.1 (2025-06-13): lme4 1.1.37, data.table 1.17.8, gigs 0.5.2.9000, arrow 21.0.0.1, nnet 7.3.20
- Analysis code: git repository (local), commit 173fecd for the analyses (Etapas 0–6b); this package adds the Etapa 7b commit.

## Draft statement (English)
> Data availability: This study used de-identified, publicly available data from the Brazilian Live Birth Information System
> (SINASC) and Mortality Information System (SIM), distributed by DATASUS, Ministry of Health of Brazil, and the 2022 Census of the
> Brazilian Institute of Geography and Statistics (IBGE, SIDRA table 9605). The data can be obtained from these sources without
> restriction. Aggregated tables underlying the results are provided in the Online Resources. The analysis code (Python and R) will
> be deposited in [REDU/GitHub — repository to be defined by the authors] upon publication.

Ethics: secondary analysis of public-domain, de-identified data (Brazilian National Health Council Resolution 510/2016) — wording to be confirmed by the authors.
