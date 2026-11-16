# MAIHDA — fórmulas usadas na Etapa 5 e de onde vieram

Fonte principal: Evans CR, Leckie G, Subramanian SV, Bell A, Merlo J. A tutorial for conducting intersectional
multilevel analysis of individual heterogeneity and discriminatory accuracy (MAIHDA). SSM Popul Health 2024;26:101664.
PMID 38690117; PMCID PMC11059336; doi:10.1016/j.ssmph.2024.101664.
Texto completo obtido do PMC em 2026-10-08 (`evans2024_maihda_tutorial_PMC11059336.txt`; as equações foram
perdidas na extração e transcritas da página HTML do PMC).

| Quantidade | Fórmula | Fonte (Evans 2024, seção) |
|---|---|---|
| VPC | σ²_u / (σ²_u + σ²_e) | "Between-stratum variance and the Variance Partition Coefficient" |
| σ²_e no logístico (resposta latente) | π²/3 ≈ 3.29 | "The VPC, AUC and PCV in logistic models" |
| PCV | (σ²_u,A − σ²_u,B) / σ²_u,A (escala logit) | "The between-stratum variance attributable to interaction effects"; idem logístico |
| VPC do modelo B | proporção da variância total remanescente atribuível a interações (mesma fórmula, σ²_u,B) | idem |
| AUC | P(p̂ de um caso > p̂ de um não caso), p̂ = probabilidade prevista do estrato (empates = ½) | "The VPC, AUC and PCV in logistic models" |
| Efeito de interação na escala de probabilidade | π^B_j = logit⁻¹(Xβ + u_j) − logit⁻¹(Xβ) | seção de visualização (Fig. 4C) |
| IC das predições com MLE | aproximado por simulação, supondo ausência de covariância amostral entre efeitos fixos e aleatórios | seção sobre MLE vs MCMC |

Merlo J. Multilevel analysis of individual heterogeneity and discriminatory accuracy (MAIHDA) within an intersectional
framework. Soc Sci Med 2018;203:74–80. PMID 29305018; doi:10.1016/j.socscimed.2017.12.026.
Comentário conceitual. O texto completo não está no PMC, e a editora devolveu HTTP 403 em 2026-10-08. Nenhuma fórmula
foi tirada desta fonte; ela é citada apenas pelo enquadramento (discriminatory accuracy, VPC como medida de
"general contextual effect").

## Etapa 6.6 — MAIHDA cruzada (estrato × região de saúde)

Fonte: Cross-classified Multilevel Analysis of Individual Heterogeneity and Discriminatory Accuracy (MAIHDA) to evaluate
hospital performance. BMJ Open 2020;10:e036130. PMID 33099490; PMCID PMC7590346; doi:10.1136/bmjopen-2019-036130.
Texto do PMC obtido em 2026-10-09.

| Quantidade | Fórmula | Fonte |
|---|---|---|
| VPC de uma classificação no modelo cruzado (logístico, resposta latente) | VPC_H = σ²_H / (σ²_H + σ²_RS + π²/3); VPC_RS = σ²_RS / (σ²_H + σ²_RS + π²/3) | Fórmulas 5 e 6 |
| Aplicação aqui | VPC_estrato = σ²_e / (σ²_e + σ²_r + π²/3); VPC_região = σ²_r / (σ²_e + σ²_r + π²/3) | mesma fórmula, H → região de saúde, RS → estrato |
| PCV (estrato), M1 → M2 com área | (σ²_e,M1 − σ²_e,M2) / σ²_e,M1 | Evans 2024 (acima) |

Evans 2024 (seção 4.3.2) descreve o modelo cruzado estrato × contexto como teste de robustez da MAIHDA principal, sem fórmula própria.
