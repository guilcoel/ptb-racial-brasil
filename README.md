# Racial disparities in fetal growth and preterm birth across levels of prenatal care access in Brazil: the role of gestational age dating

**Code and aggregated outputs** · release `v1.0-submission` · **Status: submitted to the *Journal of Racial and Ethnic Health Disparities*** (not yet peer reviewed)

Authors: Guilherme Coelho (ORCID [0000-0003-3045-4057](https://orcid.org/0000-0003-3045-4057)), Charles M'poca Charles, Clarimar José Coelho, Danielle Satie Kassada, Rodolfo de Carvalho Pacagnella.
Contact: guilcoel@unicamp.br

## Overview
This is a population-based cross-sectional study of 25,808,740 live births in Brazil, 2015–2024, from the Live Birth Information System (SINASC). It:
- estimates racial disparities in preterm birth (total, spontaneous, and provider-initiated) and small for gestational age (SGA), using Poisson models with standard errors clustered by health region;
- assesses effect modification by area-level access to early prenatal care, on the additive scale (Knol & VanderWeele);
- examines how the gestational age dating method affects the Indigenous excess of preterm birth.

**This repository contains code and aggregated outputs only. It contains no individual-level data.** SINASC and SIM microdata are public and must be downloaded from DATASUS (see *Data sources*).

## Repository structure
```
scripts/                 analysis code (Python and R), run from the repository root; file names follow the analysis stages (etapa0 … etapa8)
  etapa0_lib.py          paths, constants, seed (42), aggregate-only logger
  etapa7b_*.py           results package: main tables, supplementary tables, figures, Submissao/ and the checker (etapa7b_checa.py)
  etapa7d_*.py           assembly of the submission files and final checks
outputs/manuscrito/      aggregated results package v15 (current) and earlier versions (_arquivo_v1 … _arquivo_v14)
  tabelas/               Tables 1–4 (CSV, xlsx, docx)
  suplementar/           Tables S1–S8 (CSV; S7 and S8 also as PDF), Online Resources 2 and 4 sources, Fig. S9
  figuras/               Figs. 1–4 (TIFF and PNG)
  numeros_chave_*.json   every number cited in the manuscript, with its source file, script and commit
  MANIFEST.md            files, generating script, source tables, MD5
  data_code_availability.md
Submissao/               figures and Online Resources as submitted (manuscript files are not included)
audit_independente/      code and reports of the independent re-computations (case-level CSVs are not included)
docs/referencias/        access logs (dates, URLs, MD5) of the public sources; RECORD checklist (CC BY 4.0)
requirements.txt         Python packages and versions
R_sessionInfo.txt        R version and packages
```

## Data sources (public; access dates as recorded)
| Source | Use | Access / version |
|---|---|---|
| **SINASC** (live births), DATASUS, files by state of residence `DN{UF}{YYYY}.dbc` (`ftp://ftp.datasus.gov.br/dissemin/publicos/SINASC/1996_/Dados/DNRES/`); 2024 from `DNBR2024` | Study population, 2015–2024 (plus 2014 for the lagged access index) | Final-release files; local copies dated 2026-03-06 (2014–2022), 2026-03-25 (2023) and 2026-06-27 (2024), obtained through the CliMaterna data hub (Torezzan et al., *Data Brief* 2025;62:111920); checked against an independent DATASUS download on 2026-10-02 (identical counts by state and year) |
| **SIM** fetal deaths (SIM-DOFET), DATASUS `ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DOFET/` | Live-birth bounds | Downloaded 2026-10-02 |
| **IBGE, 2022 Census, SIDRA table 9605** (population by color or race, municipality) | Multiple imputation of race/skin color | Accessed 2026-10-08 (`docs/referencias/censo2022/ACESSO.txt`) |
| **DATASUS territorial base, December 2024** (municipality → health region) | Health regions (433), access index, clustering | Accessed 2026-10-08 (`docs/referencias/territorio_dez24/ACESSO.txt`) |
| **Ministry of Health, "Cobertura da Atenção Básica (2007–2020)"**, https://relatorioaps.saude.gov.br/cobertura/ab | Post hoc sensitivity analysis (Table S2b, columns d–e) | Queried 2026-10-13 (`docs/referencias/aps_cobertura_ab/ACESSO.txt`, with MD5 of the 27 files) |
| INTERGROWTH-21st newborn standards | SGA centiles (R package `gigs`) | Official tables downloaded 2026-10-08 for validation |

**Input format expected by the code.** The scripts read one national Parquet file per year, `sinasc_{YYYY}.parquet`, from the folder set in the environment variable `SINASC_RAW`. They use the original SINASC variable names (see `KEEP` in `scripts/etapa0_lib.py` and Online Resource 2). The conversion from the DATASUS `.dbc` files to these Parquet files was done in the CliMaterna data hub and is **not** part of this repository: convert each year's state files (or `DNBR`) and keep the original columns and codes. Fetal deaths are read from `SIM_RAW` / `SIM_DOFET_PARQUET`, and the territorial base files are read from `docs/referencias/territorio_dez24/` (download them from the URL in its `ACESSO.txt`).

## Reproduction
Environment: Python 3.12.7 with the packages in `requirements.txt`; R 4.5.1 with `lme4`, `data.table`, `MASS`, `gigs`, `growthstandards` and `arrow` (`R_sessionInfo.txt`). Run every script from the repository root (`python3 scripts/<name>.py`, `Rscript scripts/<name>.R`); R scripts can also use `PTB_PROJ`. Seed 42 throughout. Intermediate data go to `data/processed/` (individual-level, never versioned); aggregated source tables go to `outputs/tables/`; logs go to `outputs/logs/`.

Steps, in order. Times are wall-clock on an Apple M4 with 32 GB RAM, taken from the run logs. Peak memory was not recorded; every step ran within 32 GB, and the analytic base occupies about 0.8 GB on disk.

| # | Stage | Scripts | Approx. time |
|---|---|---|---|
| 1 | Analytic base, completeness, flow diagram | `etapa0_01` → `etapa0_04` | ~5 min |
| 2 | Outcomes, INTERGROWTH-21st SGA, Table 1, prevalences, SIM checks | `etapa1_01`, `etapa1_02a/b` (R), `etapa1_03` → `etapa1_07` | ~10 min |
| 3 | Dating method, health regions, access index, models M1–M3 | `etapa2_01`, `etapa2_01b`, `etapa2_02` → `etapa2_04` | ~10 min |
| 4 | Tertiles, Knol & VanderWeele, attenuation bootstrap | `etapa3_00a`, `etapa3_00b 500 --rs`, `etapa3_01`, `etapa3_02 --rs` | ~1 h |
| 5 | Dating sensitivity, multiple imputation, plausibility | `etapa4_01`, `etapa4_02`, `etapa4_06 10 --rs --m2`, `etapa4b_01` → `etapa4b_04` | ~45 min |
| 6 | MAIHDA (SGA) | `etapa5_01`, `etapa5_02` (R) | 15–45 min |
| 7 | Health-region clustering, provider-initiated/multinomial, dating-robust, multiplicity, MAIHDA with area, live-birth bounds | `etapa6_01` → `etapa6_07`, `etapa6_06` (R), `etapa6b_01`, `etapa6b_02` (R) | ~1.5 h |
| 8 | Additional analyses for the results package | `etapa7b1_01`, `etapa7b1_02` (R), `etapa7b2_01`, `etapa7b3_01`, `etapa7c1_01`, `etapa7c2_01`, `etapa7c7_01` | ~15 min |
| 9 | Primary care coverage sensitivity (download, regions, tertiles, models) | `etapa8_01` → `etapa8_04` | ~35 min |
| 10 | Results package and checks | `etapa7b_01`, `etapa7b_02`, `etapa7b_03`, `etapa7b_04`, `etapa7b_checa` | ~5 min |

Command-line arguments are documented in each script's docstring and in `SRC` (`scripts/etapa7b_lib.py`). The `*_audita*` / `*_auditoria*` scripts are optional self-checks. `etapa7d_01_montagem.py` assembles the submission documents and needs Microsoft Word on macOS. `etapa7b_checa.py` compares every package version with the archived ones; in this public release, the internal table S5b and the manuscript files are not distributed, so the checks that read them will not run here.

Notes on provenance fields. Commit hashes cited inside `outputs/` (for example `commit_pacote`, `commit_registro` and `commit_analise` in the key-number files, the reference commit in `data_code_availability.md`, and commits cited in the reports under `audit_independente/`) refer to the authors' local development history, which is not part of this repository; this repository holds a single snapshot of release v1.0-submission. `data_code_availability.md` is the draft generated with the results package; the final statement is in the article.

## Online Resources → files
| Online Resource | Content | File |
|---|---|---|
| 1 | STROBE + RECORD checklist, with page and line | `Submissao/ESM_1.pdf` |
| 2 | Variables and codes (SINASC, SIM), operational definitions, dating code 8 | `Submissao/ESM_2.pdf` (`outputs/manuscrito/suplementar/S7*`) |
| 3 | Supplementary methods | `Submissao/ESM_3.pdf` |
| 4 | Supplementary tables S1, S1b, S2, S2b, S3, S3b, S4, S4b, S5, S5c, S5d, S6 | `Submissao/ESM_4.xlsx` (CSV in `outputs/manuscrito/suplementar/`) |
| 5 | Intersectional MAIHDA of SGA (Fig. S9) | `Submissao/ESM_5.pdf` |

Figs. 1–4: `Submissao/Fig1.tif` – `Fig4.tif`. Tables 1–4: `outputs/manuscrito/tabelas/`.

## How to cite
Please cite the article (when published) and this release. Use `CITATION.cff` (GitHub: "Cite this repository"):

> Coelho G, Charles CM, Coelho CJ, Kassada DS, Pacagnella RC. Code and aggregated data for: Racial disparities in fetal growth and preterm birth across levels of prenatal care access in Brazil: the role of gestational age dating. Version v1.0-submission. 2026. https://github.com/guilcoel/ptb-racial-brasil. Archived at the Research Data Repository of UNICAMP (REDU): DOI to be added.

## License
Code: MIT (`LICENSE`). Aggregated outputs (`outputs/`, `Submissao/`): CC BY 4.0. Third-party material: see `docs/referencias/ATRIBUICAO.txt`.
