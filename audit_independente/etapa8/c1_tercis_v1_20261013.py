"""Bloco C (parte 1) — tercis e descritivos refeitos com código próprio: nascimentos por (região de saúde, ano, macro, raça) agregados
por DuckDB direto do parquet v3 (incl = true), cobertura recalculada do JSON (DuckDB), índice lido do CSV da Etapa 2 (insumo anterior).
Grava o mapa par → tercil do auditor (só rótulos, sem contagens) em terc_auditor_v1_20261013.csv para o R (c2)."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from comum_v1_20261013 import PROJ, RAW, PROC, TB, AUD, Res

R = Res("C1")
con = duckdb.connect()
con.execute(f"SET temp_directory='{AUD}/duck_tmp_v1_20261013'")
V3 = PROC / "sinasc_brasil_2015_2024_v3_20261008"
# nascimentos por par e raça (agregado em memória; nunca gravado)
nb = con.execute(f"""SELECT CO_REGSAUD, ano, regiao, CAST(raca AS VARCHAR) raca, count(*) n FROM read_parquet('{V3}/*/*.parquet', hive_partitioning=true)
  WHERE incl AND CO_REGSAUD IS NOT NULL GROUP BY ALL""").df()
nb["ano"] = nb.ano.astype(int)
assert nb.groupby(["CO_REGSAUD", "ano"]).regiao.nunique().max() == 1
# cobertura t−1 (recalculada do JSON) e população
rl = pd.read_csv(PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv", dtype=str)
con.register("rl", rl)
glob = str(RAW / "cobertura_ab_uf*_201401_202012.json")
cob = con.execute(f"""WITH j AS (SELECT CAST(substr(nuComp,1,4) AS INT) ano, nuComp, coMunicipioIbge mun,
  CAST(replace(qtPopulacao, ',', '') AS DOUBLE) pop, CAST(replace(pcCoberturaAb, ',', '') AS DOUBLE) pc
  FROM read_json('{glob}', format='array', columns={{nuComp:'VARCHAR', coMunicipioIbge:'VARCHAR', qtPopulacao:'VARCHAR', pcCoberturaAb:'VARCHAR'}})),
  k AS (SELECT j.*, rl.CO_REGSAUD reg FROM j JOIN rl ON j.mun = rl.CO_MUNICIP),
  p AS (SELECT reg, ano, avg(s) pop FROM (SELECT reg, ano, nuComp, sum(pop) s FROM k GROUP BY ALL) GROUP BY ALL)
  SELECT k.reg CO_REGSAUD, k.ano + 1 ano, sum(k.pc*k.pop)/sum(k.pop) cob_t1, any_value(p.pop) pop_t1 FROM k JOIN p ON k.reg = p.reg AND k.ano = p.ano
  GROUP BY k.reg, k.ano""").df()
ind = pd.read_csv(PROC / "indice_acesso_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str})[["CO_REGSAUD", "ano", "indice"]]
ind = ind.assign(ano=ind.ano + 1).rename(columns={"indice": "ind_t1"})
pares = nb.groupby(["CO_REGSAUD", "ano", "regiao"], as_index=False).n.sum()
pares = pares.merge(ind, how="left", on=["CO_REGSAUD", "ano"]).merge(cob, how="left", on=["CO_REGSAUD", "ano"])


def tercil_auditor(df, col):
    """Pares ponderados por nascimentos, dentro da macro; corte_k = menor valor cuja fração acumulada (ordem crescente) ≥ k/3."""
    out = pd.Series(index=df.index, dtype=object)
    cortes = {}
    for reg, g in df.groupby("regiao"):
        v = g[col].to_numpy()
        o = np.argsort(v, kind="stable")
        cf = np.cumsum(g.n.to_numpy()[o]) / g.n.sum()
        c1, c2 = v[o][np.argmax(cf >= 1 / 3)], v[o][np.argmax(cf >= 2 / 3)]
        out[g.index] = np.where(v <= c1, "T1", np.where(v <= c2, "T2", "T3"))
        cortes[reg] = (c1, c2)
    return out, cortes


# conferência do algoritmo: 2015–2024, índice → tercil_reg do projeto (Etapa 3)
pr, _ = tercil_auditor(pares, "ind_t1")
tr = pd.read_csv(PROC / "tercil_reg_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str})
m0 = pares.assign(t=pr).merge(tr, on=["CO_REGSAUD", "ano"], how="outer", indicator=True)
R.ok("C1.01 meu algoritmo de tercis reproduz o tercil_reg da análise principal (2015–2024, todos os pares)",
     (m0._merge == "both").all() and (m0.t == m0.tercil_reg).all(), f"{len(m0)} pares; divergentes {(m0.t != m0.tercil_reg).sum()}")

P = pares[pares.ano <= 2021].copy()
R.ok("C1.02 2015–2021: todo par com cobertura e índice t−1; 433 regiões × 7 anos", P.cob_t1.notna().all() and P.ind_t1.notna().all()
     and len(P) == 3031 and P.CO_REGSAUD.nunique() == 433, f"{len(P)} pares; N = {P.n.sum():,}")
P["tercil_aps"], ca = tercil_auditor(P, "cob_t1")
P["tercil_ind21"], ci = tercil_auditor(P, "ind_t1")
T = pd.read_csv(PROC / "tercil_aps_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str})
m = P.merge(T, on=["CO_REGSAUD", "ano"], how="outer", indicator=True, suffixes=("", "_p"))
R.ok("C1.03 tercil_aps e tercil_ind21 por par = arquivo do projeto (tercil_aps_regsaude_ano)",
     (m._merge == "both").all() and (m.tercil_aps == m.tercil_aps_p).all() and (m.tercil_ind21 == m.tercil_ind21_p).all(),
     f"{len(m)} pares; dif aps {(m.tercil_aps != m.tercil_aps_p).sum()}; dif ind21 {(m.tercil_ind21 != m.tercil_ind21_p).sum()}")
R.ok("C1.04 cob_t1, indice_t1, pop_t1 e n_nasc por par = arquivo do projeto",
     (m.cob_t1 - m.cob_t1_p).abs().max() < 1e-9 and (m.ind_t1 - m.indice_t1).abs().max() < 1e-9 and (m.pop_t1 - m.pop_t1_p).abs().max() < 1e-6
     and (m.n == m.n_nasc).all(), f"dif. máx. cob {(m.cob_t1 - m.cob_t1_p).abs().max():.1e}")
C = pd.read_csv(TB / "tab_e8_03_cortes_v1_20261008.csv")
dc = max(max(abs(C.set_index(["medida", "regiao"]).loc[(md, r)].corte_T1_T2 - cc[r][0]),
             abs(C.set_index(["medida", "regiao"]).loc[(md, r)].corte_T2_T3 - cc[r][1])) for md, cc in (("tercil_aps", ca), ("tercil_ind21", ci)) for r in cc)
sh = P.groupby(["regiao", "tercil_aps"]).n.sum() / P.groupby("regiao").n.sum() * 100
R.ok("C1.05 cortes por macro e medida = tab_e8_03_cortes; % de nascimentos por tercil entre 32 e 35", dc < 1e-9 and sh.between(32, 35).all(),
     f"dif. máx. cortes {dc:.1e}; % aps {sh.min():.2f}–{sh.max():.2f}")

# Spearman (pares, sem ponderação)
sp = pd.read_csv(TB / "tab_e8_03_spearman_v1_20261008.csv").set_index(["par", "estrato"]).rho
mine = {}
for est, g in [("Brasil", P)] + list(P.groupby("regiao")):
    mine[("cobertura_x_indice", est)] = stats.spearmanr(g.cob_t1, g.ind_t1).statistic
    mine[("cobertura_x_populacao", est)] = stats.spearmanr(g.cob_t1, g.pop_t1).statistic
dsp = max(abs(sp[k] - v) for k, v in mine.items())
R.ok("C1.06 Spearman (região × ano, t−1) cobertura × índice = −0.10 e cobertura × população = −0.49 (Brasil); por macro = tab_e8_03_spearman",
     dsp < 1e-12 and f"{mine[('cobertura_x_indice', 'Brasil')]:.2f}" == "-0.10" and f"{mine[('cobertura_x_populacao', 'Brasil')]:.2f}" == "-0.49",
     f"dif. máx. {dsp:.1e}; Brasil {mine[('cobertura_x_indice', 'Brasil')]:.4f} / {mine[('cobertura_x_populacao', 'Brasil')]:.4f}; "
     "dentro das macros (índice): " + ", ".join(f"{k[1]} {v:.2f}" for k, v in mine.items() if k[0] == "cobertura_x_indice" and k[1] != "Brasil"))
# Spearman ponderado por nascimentos e por ranks dentro da macro (descritivo para a revisão metodológica)
P["rk_c"] = P.groupby("regiao").cob_t1.rank(pct=True)
P["rk_i"] = P.groupby("regiao").ind_t1.rank(pct=True)
r_within = stats.pearsonr(P.rk_c, P.rk_i).statistic
R.ok("C1.07 [descritivo] correlação de postos DENTRO da macro (escala em que os tercis são definidos), cobertura × índice", True,
     f"ρ dos postos percentuais intra-macro = {r_within:.3f} (o −0.10 nacional mistura diferenças entre macros)")

# concordância nos nascimentos e kappa ponderado linear (implementação própria, fórmula de Cohen com pesos 1 − |i−j|/2)
ct = P.pivot_table(index="tercil_aps", columns="tercil_ind21", values="n", aggfunc="sum").loc[["T1", "T2", "T3"], ["T1", "T2", "T3"]].to_numpy(float)
N = ct.sum()
pij = ct / N
W = np.array([[1 - abs(i - j) / 2 for j in range(3)] for i in range(3)])
po = (W * pij).sum()
pe = (W * np.outer(pij.sum(1), pij.sum(0))).sum()
kap = (po - pe) / (1 - pe)
diag = 100 * np.trace(pij)
CR = pd.read_csv(TB / "tab_e8_03_concordancia_resumo_v1_20261008.csv").iloc[0]
CT = pd.read_csv(TB / "tab_e8_03_concordancia_v1_20261008.csv").pivot(index="tercil_aps", columns="tercil_ind21", values="n_nasc").to_numpy(float)
R.ok("C1.08 concordância: 33.2% na diagonal, κ linear = 0.05, N = 18,624,544; tabela cruzada = tab_e8_03_concordancia",
     abs(diag - CR.pct_diagonal) < 1e-9 and abs(kap - CR.kappa_ponderado_linear) < 1e-12 and N == CR.n_nasc == 18624544 and (CT == ct).all()
     and f"{diag:.1f}" == "33.2" and f"{kap:.2f}" == "0.05", f"diag {diag:.3f}%; κ {kap:.4f}; acaso (diag esperada) {100 * np.trace(np.outer(pij.sum(1), pij.sum(0))):.2f}%")
# raça por tercil
rp = pd.read_csv(TB / "tab_e8_03_raca_por_tercil_v1_20261008.csv").set_index(["medida", "raca"])
Pr = nb[nb.ano <= 2021].merge(P[["CO_REGSAUD", "ano", "tercil_aps", "tercil_ind21"]], on=["CO_REGSAUD", "ano"])
dmax, ind_txt = 0, []
for md in ("tercil_aps", "tercil_ind21"):
    x = Pr.pivot_table(index="raca", columns=md, values="n", aggfunc="sum")
    x = x.div(x.sum(1), axis=0) * 100
    for rc in x.index:
        dmax = max(dmax, max(abs(x.loc[rc, t] - rp.loc[(md, rc), t]) for t in ("T1", "T2", "T3")))
    ind_txt.append(f"{md}: Ind T1 {x.loc['Indigena', 'T1']:.1f}% T3 {x.loc['Indigena', 'T3']:.1f}%")
R.ok("C1.09 distribuição de cada raça entre os tercis = tab_e8_03_raca_por_tercil (Indígena: APS T1 16.2% / T3 47.5%; índice T1 53.2% / T3 16.4%)",
     dmax < 1e-9, f"dif. máx. {dmax:.1e}; {'; '.join(ind_txt)}; raças {sorted(Pr.raca.unique())}")
# n por raça × tercil_aps (agregado grande: só o menor n Indígena por macro, sem gravar células)
mn = Pr[Pr.raca == "Indigena"].groupby(["regiao", "tercil_aps"]).n.sum()
R.ok("C1.10 [descritivo] nascimentos indígenas por macro × tercil_aps: menor célula", True, f"menor {mn.min():,} ({mn.idxmin()}); "
     f"Indígenas 2015–2021 = {Pr[Pr.raca == 'Indigena'].n.sum():,}")
# saídas: mapa par → tercis (só rótulos)
P[["CO_REGSAUD", "ano", "tercil_aps", "tercil_ind21"]].to_csv(AUD / "terc_auditor_v1_20261013.csv", index=False)
pares.assign(tercil_reg=pr)[["CO_REGSAUD", "ano", "tercil_reg"]].to_csv(AUD / "tercreg_auditor_v1_20261013.csv", index=False)
R.grava()
