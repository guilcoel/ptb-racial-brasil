"""
Auditoria própria da Etapa 4b.
  1. % implausível (a, b, c) por raça × ig_metodo recalculada em DuckDB SQL (join com a grade gigs) = pandas
  2. Σ células = n em cada estrato (N dos modelos 4b.3 e 4b.4 recontados)
  3. M1/M5 do CO sem estratificar = Tabela 2 da RSP; estratos DUM + outro + ignorado = CO total
  4. ICR de 4b.3 reconstruído à mão a partir de (i)
  5. confronto com audit_independente/etapa4b quando existir
Saída: tab_e4b_05_auditoria_propria.
"""
import duckdb
import numpy as np
import pandas as pd

import etapa3_lib as T
import etapa0_lib as L

log = L.Logger("05_auditoria", etapa="etapa4b")
TB, S = L.TAB, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


# 1
g = str(L.PROC / f"pig_grade_intergrowth_v1_{S}.parquet")
q = f"""
WITH p AS (SELECT CASE RACACORMAE WHEN 1 THEN 'Branca' WHEN 2 THEN 'Preta' WHEN 4 THEN 'Parda' WHEN 5 THEN 'Indigena' END raca,
                  CASE WHEN TPMETESTIM = 8 THEN 'DUM' WHEN TPMETESTIM IN (1, 2) THEN 'outro_metodo' ELSE 'ignorado' END ig_metodo,
                  SEMAGESTAC, SEXO, PESO
           FROM read_parquet('{T.V3}/*/part-0.parquet', hive_partitioning=true)
           WHERE incl AND GRAVIDEZ = 1 AND SEMAGESTAC BETWEEN 24 AND 36 AND SEXO IN (1, 2) AND PESO BETWEEN 100 AND 7000)
SELECT raca, ig_metodo, count(*) n, avg(CASE WHEN PESO >= 2500 THEN 1 ELSE 0 END) * 100 a,
       avg(CASE WHEN g.centil_k3 > 0.97 THEN 1 ELSE 0 END) * 100 b, avg(CASE WHEN g.centil_k3 > 0.90 THEN 1 ELSE 0 END) * 100 c
FROM p JOIN read_parquet('{g}') g USING (SEMAGESTAC, SEXO, PESO) GROUP BY ALL"""
sq = duckdb.sql(q).df()
pb = pd.read_csv(TB / f"tab_e4b_01_implausivel_brasil_v1_{S}.csv").pivot_table(index=["raca", "ig_metodo"], columns="criterio", values="pct")
nb = pd.read_csv(TB / f"tab_e4b_01_implausivel_brasil_v1_{S}.csv").query("criterio == 'b'").set_index(["raca", "ig_metodo"]).n_prematuros
m = sq.set_index(["raca", "ig_metodo"]).join(nb)
dm = float(np.max(np.abs(sq.set_index(["raca", "ig_metodo"])[["a", "b", "c"]].to_numpy() - pb.loc[m.index, ["a", "b", "c"]].to_numpy())))
check("% implausível (a, b, c) por raça × ig_metodo: pandas = SQL", f"{len(m)} grupos; máx |dif| = {dm:.1e}; n iguais = {bool((m.n == m.n_prematuros).all())}",
      len(m) == 12 and dm < 1e-9 and (m.n == m.n_prematuros).all())

# 2 e 3
w3 = pd.read_csv(TB / f"tab_e4b_03_wald_v1_{S}.csv")
w32 = pd.read_csv(TB / f"tab_e3_02_wald_v1_{S}.csv").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'").set_index("desfecho").N
okn = all(int(w3[w3.desfecho == f"{b}_plaus_{c}"].N.iloc[0]) == int(w32[b]) for b in ("ptb", "ptb_esp") for c in ("a", "b"))
check("N dos modelos 4b.3 (3.2) = N da 3.2 original (denominador inalterado)", okn, okn)
co = pd.read_csv(TB / f"tab_e4b_04_co_estratos_v1_{S}.csv")
nn = co.drop_duplicates("estrato").set_index("estrato")
oks = int(nn.loc[["DUM", "outro_metodo", "ignorado"], "N"].sum()) == int(nn.loc["todos", "N"]) == 2156674
okc = int(nn.loc[["DUM", "outro_metodo", "ignorado"], "casos"].sum()) == int(nn.loc["todos", "casos"]) == 241899
check("CO: DUM + outro + ignorado = total (N 2,156,674; casos 241,899)", f"{nn.N.to_dict()}", oks and okc)
v = co[(co.estrato == "todos") & (co.modelo == "M1") & (co.medida == "OR") & (co.ep == "modelo")].set_index("raca")
pub = {"Indigena": (1.709, 1.663, 1.757), "Preta": (1.053, 1.032, 1.074), "Parda": (0.991, 0.981, 1.000)}
ok1 = all(tuple(round(v.loc[r, k], 3) for k in ("est", "lo", "hi")) == pub[r] for r in pub)
v5 = co[(co.estrato == "todos") & (co.modelo == "M5") & (co.raca == "Indigena")]
o5 = v5[(v5.medida == "OR") & (v5.ep == "modelo")].iloc[0]
r5 = v5[(v5.medida == "RP") & (v5.ep == "hc0")].iloc[0]
ok5 = (round(o5.est, 3), round(o5.lo, 3), round(o5.hi, 3)) == (1.504, 1.461, 1.549) and (round(r5.est, 2), round(r5.lo, 2), round(r5.hi, 2)) == (1.41, 1.38, 1.45)
r1 = co[(co.estrato == "todos") & (co.modelo == "M1") & (co.medida == "RP") & (co.ep == "hc0") & (co.raca == "Indigena")].iloc[0]
ok1r = (round(r1.est, 2), round(r1.lo, 2), round(r1.hi, 2)) == (1.58, 1.55, 1.62)
check("CO sem estratificar = Tabela 2 RSP (M1 OR 3 raças, M1 RP Indígena, M5 OR e RP Indígena)", f"M1 OR {ok1}; M1 RP {ok1r}; M5 {ok5}", ok1 and ok1r and ok5)

# 4
cj = pd.read_csv(TB / f"tab_e4b_03_conjunto_v1_{S}.csv")
it = pd.read_csv(TB / f"tab_e4b_03_interacao_v1_{S}.csv")
bad, n = 0, 0
for desf, x in cj.groupby("desfecho"):
    D = x.set_index(["raca", "nivel"]).DR_pp
    for _, r in it[it.desfecho == desf].iterrows():
        n += 1
        bad += int(abs(D[r.raca, r.nivel] - D[r.raca, "T3"] - D["Branca", r.nivel] - r.ICR_pp) > 1e-8)
check("ICR 4b.3 reconstruído à mão a partir de (i)", f"{n - bad}/{n}", bad == 0)

AUD = L.PROJ / "audit_independente" / "etapa4b"
if AUD.exists():
    log("arquivos do auditor: " + ", ".join(sorted(p.name for p in AUD.iterdir() if not p.name.startswith("._"))))
    # A: o P97 do gigs é a equação; comparar com a coluna pct_eq do auditor (pct_tab = tabela oficial, só reportada)
    aa = pd.read_csv(AUD / f"A_pct_critb_raca_igmetodo_v1_{S}.csv").replace({"igm": {"outro": "outro_metodo", "ign": "ignorado"}})
    aa = aa[aa.igm != "TOTAL"].set_index(["raca_nome", "igm"])
    mb = pb.b.rename_axis(["raca_nome", "igm"])
    da = float((aa.pct_eq - mb.loc[aa.index]).abs().max())
    dt = float((aa.pct_tab - mb.loc[aa.index]).abs().max())
    check("independente A: % (b) por raça × ig_metodo (equação) = gigs; tabela oficial difere ≤ 0.2 p.p.",
          f"máx |dif| equação {da:.1e}; tabela {dt:.3f} p.p.", da < 1e-3 and dt < 0.2)
    bb = pd.read_csv(AUD / f"B_icr_ptb_esp_plausivel_b_v1_{S}.csv")
    bi = bb[bb.desfecho.str.contains("equação") & (bb.grupo == "Indigena")].iloc[0]
    mi = it[(it.desfecho == "ptb_esp_plaus_b") & (it.raca == "Indigena") & (it.nivel == "T1")].iloc[0]
    db = max(abs(bi.ICR_pp - mi.ICR_pp), abs(bi.LI - mi.ICR_lo), abs(bi.LS - mi.ICR_hi))
    check("independente B: ICR Indígena×T1 ptb_esp_plaus_b (equação) = meu", f"{bi.ICR_pp:.4f} vs {mi.ICR_pp:.4f}; máx |dif| {db:.1e}", db < 1e-3)
    cc = pd.read_csv(AUD / f"C_rp_m5_co_indigena_por_igmetodo_v1_{S}.csv").set_index("ig_metodo")
    rp = co[(co.modelo == "M5") & (co.medida == "RP") & (co.raca == "Indigena")].set_index(["estrato", "ep"])
    dc = max(abs(cc.loc[a, x] - rp.loc[(e, ep), y]) for a, e in [("DUM", "DUM"), ("outro", "outro_metodo"), ("ign", "ignorado"), ("TODOS", "todos")]
             for x, ep, y in [("RP", "hc0", "est"), ("LI_HC0", "hc0", "lo"), ("LS_HC0", "hc0", "hi"), ("LI_cl", "cluster", "lo"), ("LS_cl", "cluster", "hi")])
    check("independente C: RP M5 Indígena CO por ig_metodo (HC0 e cluster) = meu", f"máx |dif| {dc:.1e}", dc < 1e-4)
pd.DataFrame(chk).to_csv(TB / f"tab_e4b_05_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 4b: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
