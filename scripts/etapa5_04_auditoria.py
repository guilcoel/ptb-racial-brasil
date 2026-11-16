"""
Auditoria própria da Etapa 5.
  1. Σ n e Σ casos dos estratos = PIG elegível com tercil, recontado em DuckDB direto da base v3 (ano do arquivo de
     tercis = ano do nascimento; o índice já está em t−1) (e estratos × ano,
     estratos "outro método" somam certo)
  2. VPC = σ²/(σ² + π²/3) e PCV recalculados à mão a partir das variâncias gravadas (Evans 2024)
  3. predições de 5 estratos sorteados (seed 42) recalculadas a partir dos coeficientes fixos e de û_j
  4. confronto com audit_independente/etapa5 quando existir
Saída: tab_e5_04_auditoria_propria.
"""
import duckdb
import numpy as np
import pandas as pd
from scipy.special import expit

import etapa3_lib as T
import etapa0_lib as L

log = L.Logger("04_auditoria", etapa="etapa5")
TB, PR, S = L.TAB, L.PROC, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


# 1
tr = str(PR / f"tercil_reg_regsaude_ano_v1_{S}.csv")
q = f"""
WITH t AS (SELECT CAST(CO_REGSAUD AS VARCHAR) CO_REGSAUD, ano ano_nasc, tercil_reg FROM read_csv('{tr}', types={{'CO_REGSAUD': 'VARCHAR'}}))
SELECT count(*) n, sum(pig) casos, count(DISTINCT raca || '|' || CASE WHEN esc_cat IN ('1_nenhuma', '2_1a3anos', '3_4a7anos') THEN 'le7'
       WHEN esc_cat = '4_8a11anos' THEN '8a11' ELSE 'ge12' END || '|' || idade_cat || '|' || regiao || '|' || tercil_reg) estratos,
       sum(CASE WHEN ig_metodo = 'outro_metodo' THEN 1 ELSE 0 END) n_outro
FROM read_parquet('{T.V3}/*/part-0.parquet', hive_partitioning = true) b
JOIN t ON b.CO_REGSAUD = t.CO_REGSAUD AND b.ano = t.ano_nasc
WHERE incl AND pig IS NOT NULL"""
sq = duckdb.sql(q).df().iloc[0]
a = pd.read_csv(PR / f"maihda_estratos_v1_{S}.csv")
ay = pd.read_csv(PR / f"maihda_estratos_ano_v1_{S}.csv")
ao = pd.read_csv(PR / f"maihda_estratos_outro_v1_{S}.csv")
ok = int(sq.n) == int(a.n.sum()) == int(ay.n.sum()) and int(sq.casos) == int(a.casos.sum()) == int(ay.casos.sum()) \
    and int(sq.estratos) == len(a) == 540 and int(sq.n_outro) == int(ao.n.sum())
check("Σ n e casos dos estratos (e estrato × ano, e outro método) = SQL direto na v3",
      f"SQL n {int(sq.n):,} casos {int(sq.casos):,} estratos {int(sq.estratos)} outro {int(sq.n_outro):,}; "
      f"estratos n {int(a.n.sum()):,} casos {int(a.casos.sum()):,}", ok)
yy = ay.groupby("estrato")[["n", "casos"]].sum().reindex(a.estrato)
check("estrato × ano agregado por estrato = estratos", "", (yy.n.to_numpy() == a.n.to_numpy()).all() and (yy.casos.to_numpy() == a.casos.to_numpy()).all())

# 2
m = pd.read_csv(TB / f"tab_e5_02_modelos_v1_{S}.csv").set_index("modelo")
E2 = np.pi ** 2 / 3
dv = max(abs(100 * m.s2[k] / (m.s2[k] + E2) - m.VPC_pct[k]) for k in m.index)
dvl = max(abs(100 * m.s2_lo_perfil[k] / (m.s2_lo_perfil[k] + E2) - m.VPC_lo[k]) for k in m.index)
pcv = 100 * (m.s2["M1 nulo"] - m.s2["M2 efeitos principais"]) / m.s2["M1 nulo"]
pco = 100 * (m.s2["M1 nulo — outro método"] - m.s2["M2 — outro método"]) / m.s2["M1 nulo — outro método"]
check("VPC = σ²/(σ² + π²/3) recalculado à mão (6 modelos, ponto e limite inferior)", f"máx |dif| {max(dv, dvl):.1e}", max(dv, dvl) < 1e-9)
check("PCV recalculado à mão (principal e outro método)",
      f"{pcv:.3f}% vs {m.PCV_pct['M2 efeitos principais']:.3f}%; {pco:.3f}% vs {m.PCV_pct['M2 — outro método']:.3f}%",
      abs(pcv - m.PCV_pct["M2 efeitos principais"]) < 1e-9 and abs(pco - m.PCV_pct["M2 — outro método"]) < 1e-9)

# 3
fe = pd.read_csv(TB / f"tab_e5_02_fixos_m2_v1_{S}.csv").set_index("termo").beta
p = pd.read_csv(TB / f"tab_e5_03_predicoes_v1_{S}.csv")
REF = {"raca": "Branca", "esc3": "ge12", "idade3": "20a34", "regiao": "SE", "tercil": "T3"}
amostra = p.sample(5, random_state=42)
dif = []
for _, r in amostra.iterrows():
    xb = fe["(Intercept)"] + sum(fe[f"{v}{r[v]}"] for v in REF if r[v] != REF[v])
    ph = 100 * expit(xb + r.u)
    dif.append(abs(ph - r.p_pct))
    log(f"  {r.estrato}: à mão {ph:.4f}% vs gravado {r.p_pct:.4f}% (obs {r.obs_pct:.2f}%, n {r.n:,})")
check("predição de 5 estratos sorteados (seed 42) = expit(Xβ + û)", f"{', '.join(amostra.estrato)}; máx |dif| {max(dif):.1e} p.p.", max(dif) < 1e-9)
rf = p[p.estrato == "Branca|ge12|20a34|SE|T3"].iloc[0]
check("razão e diferença do estrato de referência = 1 e 0", f"{rf.razao:.6f}; {rf.dif_pp:.6f}", abs(rf.razao - 1) < 1e-12 and abs(rf.dif_pp) < 1e-12)
ap = a.set_index("estrato").loc[p.estrato]
cas, nca = ap.casos.to_numpy(float), (ap.n - ap.casos).to_numpy(float)
for col, mod in [("p_m1_pct", "M1 nulo"), ("p_pct", "M2 efeitos principais")]:
    sc = p[col].to_numpy()
    # AUC = P(p̂ caso > p̂ não caso) + ½ P(empate), por comparação par a par entre estratos (Evans 2024)
    gt = (sc[:, None] > sc[None, :]).astype(float) + 0.5 * (sc[:, None] == sc[None, :])
    au = float(cas @ gt @ nca / (cas.sum() * nca.sum()))
    check(f"AUC {mod} recalculada par a par", f"{au:.6f} vs {m.AUC[mod]:.6f}; IC {m.AUC_lo[mod]:.4f}–{m.AUC_hi[mod]:.4f}",
          abs(au - m.AUC[mod]) < 1e-6 and m.AUC_lo[mod] < m.AUC[mod] < m.AUC_hi[mod])
bt = pd.read_csv(TB / f"tab_e5_02_bootstrap_v1_{S}.csv")
check("bootstrap: 500 réplicas, convergência", f"{len(bt)} réplicas; {int(bt.conv.sum())} sem aviso", len(bt) == 500)

AUD = L.PROJ / "audit_independente" / "etapa5"
if AUD.exists():
    log("arquivos do auditor: " + ", ".join(sorted(x.name for x in AUD.iterdir() if not x.name.startswith("._"))))
    # auditor: ML marginal com Gauss–Hermite adaptativa (numpy/scipy), sem lme4
    pa = pd.read_csv(AUD / f"audit_e5_parametros_v1_{S}.csv")
    for mod, nm in [("M1", "M1 nulo"), ("M2", "M2 efeitos principais")]:
        q25 = pa[(pa.modelo == mod) & (pa.nos == 25)].iloc[0]
        la = pa[(pa.modelo == mod) & (pa.metodo == "Laplace")].iloc[0]
        rel = abs(q25.s2 / m.s2[nm] - 1)
        check(f"independente {mod}: σ² (AGHQ 25 nós; e Laplace próprio) e VPC, AUC",
              f"AGHQ {q25.s2:.6f} vs {m.s2[nm]:.6f} (rel {rel:.1e}); Laplace {la.s2:.6f}; VPC {q25.VPC_pct:.3f}% vs {m.VPC_pct[nm]:.3f}%; "
              f"AUC {q25.AUC:.5f} vs {m.AUC[nm]:.5f}", rel < 1e-3 and abs(la.s2 - m.s2[nm]) < 1e-5 and abs(q25.AUC - m.AUC[nm]) < 1e-5)
    q25 = pa[(pa.modelo == "M2") & (pa.nos == 25)].iloc[0]
    check("independente: PCV", f"{q25.PCV_pct:.3f}% vs {m.PCV_pct['M2 efeitos principais']:.3f}%", abs(q25.PCV_pct - m.PCV_pct["M2 efeitos principais"]) < 0.05)
    ip = pd.read_csv(AUD / f"audit_e5_predicoes_v1_{S}.csv")
    MAP = {"Ate7": "le7", "8a11": "8a11", "12mais": "ge12", "<20": "lt20", "20-34": "20a34", ">=35": "ge35"}
    ip["estrato"] = ip.raca + "|" + ip.esc3.map(MAP) + "|" + ip.idade_cat.map(MAP) + "|" + ip.regiao + "|" + ip.tercil_reg
    cmp_ = p.merge(ip[["estrato", "n", "casos", "p_pct_M2"]], on="estrato", suffixes=("", "_aud"))
    t15 = p.sort_values("p_pct", ascending=False).head(15).estrato.tolist()
    t15a = ip.sort_values("p_pct_M2", ascending=False).head(15).estrato.tolist()
    dp = float((cmp_.p_pct - cmp_.p_pct_M2).abs().max())
    check("independente: n/casos dos 540 estratos, predições (AGHQ) e ordem do top 15",
          f"{len(cmp_)} estratos; n e casos iguais = {bool((cmp_.n == cmp_.n_aud).all() and (cmp_.casos == cmp_.casos_aud).all())}; "
          f"máx |dif p| {dp:.1e} p.p.; top 15 igual e na mesma ordem = {t15 == t15a}",
          len(cmp_) == 540 and (cmp_.n == cmp_.n_aud).all() and (cmp_.casos == cmp_.casos_aud).all() and dp < 0.01 and t15 == t15a)
pd.DataFrame(chk).to_csv(TB / f"tab_e5_04_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 5: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
