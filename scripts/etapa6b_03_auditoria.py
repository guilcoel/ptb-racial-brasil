"""
Auditoria própria da Etapa 6b.
  1. Estimativas pontuais com EP por região de saúde = Etapas anteriores (M1/M2/M2cc/M3 = Etapa 2; M2 = 6.1a; M2cc/M3 do
     bootstrap = 6b.1; cenários: N = subamostras conhecidas; Centro-Oeste = 4b.4; imputação: ICR = rodada --rs da Etapa 6).
  2. Bootstrap da atenuação: 500 réplicas por desfecho × raça; clusters = região de saúde.
  3. % PTB por raça × método: Σ n por raça = Tabela de n final da Etapa 0; prevalência total = Etapa 1.
  4. IC por região de saúde ≥ IC por município (M1, M2, M3; descritivo para as demais).
  5. confronto com audit_independente/etapa6b quando existir.
Saída: tab_e6b_03_auditoria_propria.
"""
import numpy as np
import pandas as pd

import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("6b_03_auditoria")
TB, S = L.TAB, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


rd = lambda f: pd.read_csv(TB / f"{f}_v1_{S}.csv")
b = rd("tab_e6b_01_modelos_m1m3")
e2 = rd("tab_e2_04_modelos_long").query("regiao == 'Brasil'")
k = ["modelo", "desfecho", "raca"]
m = b.merge(e2[k + ["RP", "RP_lo", "RP_hi", "N"]], on=k, suffixes=("", "_mun"))
dp = float((m.PR - m.RP).abs().max())
check("M1/M2/M2cc/M3: PR pontual = Etapa 2 e N iguais", f"{len(m)}/{len(b)} pareados; máx |dif| {dp:.1e}",
      len(m) == len(b) and dp < 1e-9 and (m.N == m.N_mun).all())
lar = (np.log(m.PR_hi) - np.log(m.PR_lo)) / (np.log(m.RP_hi) - np.log(m.RP_lo))
check("M1/M2/M3: IC por região de saúde ≥ IC por município", f"{int((lar >= 1).sum())}/{len(lar)}; mín {lar.min():.2f}; máx {lar.max():.2f}",
      (lar >= 1).all())
m2 = rd("tab_e6_01a_m2").query("cluster == 'regsaude'")
mm = b[b.modelo == "M2"].merge(m2, on=["desfecho", "raca"])
dd = float(np.max(np.abs(mm[["PR", "PR_lo", "PR_hi"]].to_numpy() - mm[["RP", "RP_lo", "RP_hi"]].to_numpy())))
check("M2 (6b.1) = M2 por região de saúde da 6.1a (ponto e IC)", f"máx |dif| {dd:.1e}", dd < 1e-9)
ar = rd("tab_e3_00b_atenuacao_ic_rs")
am = ar.merge(rd("tab_e3_00b_atenuacao_ic")[["desfecho", "raca", "RP_M2cc", "RP_M3", "dRP_lo", "dRP_hi"]], on=["desfecho", "raca"], suffixes=("", "_mun"))
x = b[b.modelo.isin(["M2cc", "M3"])].pivot_table(index=["desfecho", "raca"], columns="modelo", values="PR").reset_index()
am = am.merge(x, on=["desfecho", "raca"])
dpa = float(max((am.RP_M2cc - am.RP_M2cc_mun).abs().max(), (am.RP_M3 - am.M3).abs().max(), (am.RP_M2cc - am.M2cc).abs().max()))
check("bootstrap --rs: PR M2cc/M3 da amostra = bootstrap por município = 6b.1", f"máx |dif| {dpa:.1e}", dpa < 1e-7)
rep = rd("tab_e3_00b_bootstrap_replicas_rs")
nrep = rep.groupby(["desfecho", "raca"]).replica.nunique()
check("bootstrap --rs: 500 réplicas por desfecho × raça", f"{nrep.min()}–{nrep.max()} em {len(nrep)} combinações", (nrep == 500).all())
lb = (am.dRP_hi - am.dRP_lo) / (am.dRP_hi_mun - am.dRP_lo_mun)
log(f"descritivo: largura do IC bootstrap de ΔPR, região/município: mediana {lb.median():.2f}; mín {lb.min():.2f}; máx {lb.max():.2f}")
c = rd("tab_e6b_01_m2_cenarios")
nn = c.groupby(["cenario", "desfecho"]).N.first()
check("cenários: N só DUM (PTB) = 13,221,799; só outro método (PTB) = 10,650,839; sem CE/DF (PTB) = 24,542,919; sem 2024 = 23,504,847",
      f"{nn['so_DUM', 'ptb']:,}; {nn['so_outro_metodo', 'ptb']:,}; {nn['sem_CE_DF', 'ptb']:,}; {nn['sem_2024', 'ptb']:,}",
      (nn["so_DUM", "ptb"], nn["so_outro_metodo", "ptb"], nn["sem_CE_DF", "ptb"], nn["sem_2024", "ptb"]) == (13221799, 10650839, 24542919, 23504847))
p = rd("tab_e6b_01_ptb_raca_metodo")
nf = rd("tab09_n_final_raca").query("regiao == 'Brasil'").set_index("raca").n
pt = p[(p.desfecho == "ptb") & (p.ig_metodo == "todos")].set_index("raca")
sm = p[(p.desfecho == "ptb") & (p.ig_metodo != "todos")].groupby("raca").n.sum()
ok = all(int(pt.n[g]) == int(sm[g]) for g in pt.index) and int(pt.n.sum()) == 25808740
check("% PTB por raça × método: Σ métodos = total por raça; Σ raças = 25,808,740", f"{pt.n.to_dict()}", ok)
co = rd("tab_e4b_04_co_estratos_rs").merge(rd("tab_e4b_04_co_estratos"), on=["estrato", "modelo", "medida", "ep", "raca"], suffixes=("_rs", "_mun"))
dco = float((co.est_rs - co.est_mun).abs().max())
nh = co[co.ep != "cluster"]
dhc = float(np.max(np.abs(nh[["lo_rs", "hi_rs"]].to_numpy() - nh[["lo_mun", "hi_mun"]].to_numpy())))
check("Centro-Oeste --rs: estimativas = 4b.4; IC do modelo e HC0 inalterados (validação RSP preservada)", f"máx |dif| ponto {dco:.1e}; HC0/modelo {dhc:.1e}",
      dco < 1e-9 and dhc < 1e-9)
mi = rd("tab_e4_06_mi_rubin_rs")
log("imputação --rs --m2: Rubin do ICR regravado (mesmas imputações): " + mi[(mi.raca == "Indigena") & (mi.nivel == "T1")][["desfecho", "ICR_pp"]].round(4).to_string(index=False).replace("\n", " | "))
q = rd("tab_e4_06_mi_m2_rubin_rs")
o = m2.set_index(["desfecho", "raca"]).RP
dq = (np.log(q.set_index(["desfecho", "raca"]).PR) - np.log(o.reindex(q.set_index(["desfecho", "raca"]).index))).abs()
check("imputação M2 (Rubin): PR próxima da observada (|Δ log PR| < 0.10) e fmi < 0.5", f"máx |Δ log PR| {dq.max():.3f}; fmi máx {q.fmi.max():.3f}",
      dq.max() < 0.10 and q.fmi.max() < 0.5)
AUD = L.PROJ / "audit_independente" / "etapa6b"
if AUD.exists() and any(AUD.glob("comparacao*.csv")):
    cp = pd.read_csv(sorted(AUD.glob("comparacao*.csv"))[0])
    dr = pd.to_numeric(cp.dif_rel, errors="coerce").abs()
    check("independente (R + DuckDB): itens da 6b", f"{len(cp)} itens; máx |dif rel| {dr.max():.1e}", bool((dr.fillna(0) < 1e-4).all()))
pd.DataFrame(chk).to_csv(TB / f"tab_e6b_03_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 6b: {sum(c_['ok'] for c_ in chk)}/{len(chk)} OK")
