# Data and code availability (draft, package v6_20261009, Etapa 7c.2)

## Sources (RECORD 1.3, 12.1)
- **SINASC live birth microdata, 2015–2024** (plus 2014 for the lagged access index; Ministry of Health, SVSA/DAENT/CGIAE; distributed
  by DATASUS). Files by state of residence (DNRES), documented path `ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/`
  (files DN{UF}{YYYY}.dbc); 2024 from the national file (DNBR2024). The analyses used final-release national files obtained via the
  CliMaterna data hub (Torezzan et al., Data Brief 2025;62:111920; doi:10.1016/j.dib.2025.111920), whose local copies are dated March 6,
  2026 (2014–2022), March 25, 2026 (2023), and June 27, 2026 (2024), and verified against an independent download from the DATASUS server
  on October 2, 2026 (identical record counts by state and year; all files from the final, non-preliminary directory).
- **SIM fetal deaths (SIM-DOFET), 2015–2024**, for the live-birth bounds: DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOFET/`
  (files DOFET{YY}.dbc, final directory); downloaded on 2026-10-02.
- **Health regions (territorial base, December 2024)**: ftp://ftp.datasus.gov.br/territorio/tabelas/2024/12-base territorial_dez24.zip (FTP file dated 12-19-24 02:49PM, 1517583 bytes); accessed 2026-10-08 12:42 -03; MD5 (base_territorial_dez24.zip) = 469fa5bfc171e47c54a9b903fda85098.
- **IBGE 2022 Census, SIDRA table 9605** (resident population by color or race, municipality level): https://apisidra.ibge.gov.br/values/t/9605/n6/all/v/93/p/2022/c86/95251,2776,2777,2778,2779,2780/f/c; accessed 2026-10-08 16:07 -03; MD5 (sidra_9605_n6_2022.json) = 50c1289306d167c108927cf7b0c7a7cb.
- **INTERGROWTH-21st newborn size standards** (birth weight centiles): R package gigs; official tables (grow_*_bw_table.pdf) downloaded on 2026-10-08 for validation.
- **Data dictionaries**: SINASC data structure (CGIAE, 2024) and SIM data dictionary (updated June 2025), accessed 2026-10-08; variables
  and codes in Online Resource 2 (Table S7a, RECORD 6.1).

## Software
- Python 3.12.7: pandas 2.2.2, numpy 1.26.4, scipy 1.13.1, statsmodels 0.14.2, patsy 0.5.6, pyarrow 16.1.0, duckdb 1.5.6, scikit-learn 1.5.1, matplotlib 3.9.2
- R version 4.5.1 (2025-06-13): lme4 1.1-37, data.table 1.17.8, MASS 7.3-65, gigs 0.5.2.9000, growthstandards 0.1.7, arrow 21.0.0.1
- Own implementations (no external package): aggregated Poisson estimation with cluster-robust variance and marginal standardization
  (scripts/etapa1_lib.py); interaction contrasts (scripts/etapa3_lib.py); multinomial logit by Newton–Raphson (scripts/etapa6_lib.py,
  fit_mnl; validated against statsmodels MNLogit in scripts/etapa7c1_01_valida_mnl.py); MAIHDA AUC and its DeLong confidence interval
  (scripts/etapa5_02_maihda.R; the pROC package is not used).
- Analysis code: local git repository, to be deposited at [URL after the repository is created and tagged]. Reference version of the analyses and of this package: the commit
  "Etapa 7c.2: tertile, SEXO do SIM e proveniência dos dados" (its hash is given by `git log --grep "Etapa 7c.2"`; a file cannot contain the hash of the commit that adds it).
  Commit 173fecd, cited in earlier drafts, is the Etapa 7b.2 commit (package v3), not the reference version.

## Draft statement (English)
> Data availability: This study used de-identified, publicly available data from the Brazilian Live Birth Information System
> (SINASC) and Mortality Information System (SIM), distributed by DATASUS, Ministry of Health of Brazil, and the 2022 Census of the
> Brazilian Institute of Geography and Statistics (IBGE, SIDRA table 9605). The data can be obtained from these sources without
> restriction. Aggregated tables underlying the results are provided in the Online Resources. The analysis code (Python and R) will
> be deposited at [URL after the repository is created and tagged] upon publication.

Ethics: secondary analysis of public-domain, de-identified data (Brazilian National Health Council Resolution 510/2016) — wording to be confirmed by the authors.
