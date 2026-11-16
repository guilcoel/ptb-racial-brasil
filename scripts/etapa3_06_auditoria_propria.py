"""
Auditoria própria da Etapa 3.
  1. Σ células = n individual por estrato raça × tercil_reg (cada desfecho) e N dos modelos 3.2
  2. cortes dos tercis por região reproduzidos em DuckDB SQL (janela ponderada)
  3. efeitos dentro do estrato (3.2 ii) vs modelos M2 ajustados separadamente em cada tercil
     (diferença esperada: no modelo conjunto idade, ano e região têm coeficientes comuns aos tercis)
  4. contraste de interação recalculado à mão a partir de (i): ICR = DR(g,m) − DR(g,T3) − DR(Branca,m)
  5. bootstrap: 500 réplicas por desfecho × raça, sem falhas; IC contém a estimativa pontual
Saída: tab_e3_06_auditoria_propria (+ confronto com audit_independente/etapa3 quando existir).
"""
import duckdb
import numpy as np
import pandas as pd

import etapa1_lib as E
import etapa3_lib as T
import etapa0_lib as L

log = T.logger("06_auditoria")
S, TB = L.STAMP, L.TAB
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


OUT = ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]
d = T.anexa_acesso(T.load(["raca", "idade_cat", "regiao", "CODMUNRES", "CO_REGSAUD"] + OUT))
a = d[d.CO_REGSAUD.notna()]
W = pd.read_csv(TB / f"tab_e3_02_wald_v1_{S}.csv")

# 1
bad = 0
for desf in OUT:
    s = a[a[desf].notna()]
    c = E.agrega(s, desf, ["raca", "idade_cat", "ano", "regiao", "tercil_reg"])
    gi = s.groupby(["raca", "tercil_reg"], observed=True)[desf].agg(["size", "sum"])
    gc = c.groupby(["raca", "tercil_reg"], observed=True)[["n", "Y"]].sum()
    bad += int(not (np.allclose(gi["size"], gc.n) and np.allclose(gi["sum"], gc.Y)))
    n_mod = W[(W.analise == "3.2_tercil_reg") & (W.desfecho == desf)].N.iloc[0]
    bad += int(n_mod != len(s))
check("Σ células = n e casos por raça × tercil_reg; N do modelo 3.2 = n individual (5 desfechos)", f"{bad} divergências", bad == 0)

# 2
ind = str(L.PROC / f"indice_acesso_regsaude_ano_v1_{S}.csv")
q = f"""
WITH s AS (SELECT CO_REGSAUD, CAST(ano AS INT) ano, regiao, count(*) n
           FROM read_parquet('{T.V3}/*/part-0.parquet', hive_partitioning=true)
           WHERE incl AND CO_REGSAUD IS NOT NULL GROUP BY ALL),
     i AS (SELECT CAST(CO_REGSAUD AS VARCHAR) CO_REGSAUD, CAST(ano AS INT) + 1 ano, indice FROM read_csv('{ind}', all_varchar=false,
           types={{'CO_REGSAUD':'VARCHAR'}})),
     j AS (SELECT s.*, i.indice FROM s JOIN i USING (CO_REGSAUD, ano)),
     w AS (SELECT *, sum(n) OVER (PARTITION BY regiao ORDER BY indice, CO_REGSAUD, ano ROWS UNBOUNDED PRECEDING)
                     / sum(n) OVER (PARTITION BY regiao) cf FROM j)
SELECT regiao, min(indice) FILTER (WHERE cf >= 1.0/3) c1, min(indice) FILTER (WHERE cf >= 2.0/3) c2 FROM w GROUP BY regiao"""
sq = duckdb.sql(q).df()
ct = pd.read_csv(TB / f"tab_e3_01_tercis_regiao_cortes_v1_{S}.csv").merge(sq, on="regiao")
dmax = float(np.max(np.abs(np.r_[ct.corte_T1_T2 - ct.c1, ct.corte_T2_T3 - ct.c2])))
check("cortes dos tercis por região: pandas = SQL", f"5 regiões; máx |dif| = {dmax:.1e}", len(ct) == 5 and dmax < 1e-9)

# 3
dn = pd.read_csv(TB / f"tab_e3_02_dentro_v1_{S}.csv")
dn = dn[(dn.analise == "3.2_tercil_reg") & (dn.estrato == "Brasil")]
comp = []
for desf in ["ptb", "ptb_esp", "ptb_ind", "pig"]:
    s = a[a[desf].notna()]
    for m in ["T1", "T2", "T3"]:
        c = E.agrega(s[s.tercil_reg == m], desf, ["raca", "idade_cat", "ano", "regiao"])
        c["CODMUNRES"] = c.CODMUNRES.astype(str)
        f = E.fit_agg(c, T.M2, "poisson")
        for t in E.termos(f, T.R + "[T."):
            g = t["termo"].split("[T.")[1].rstrip("]")
            r = dn[(dn.desfecho == desf) & (dn.raca == g) & (dn.nivel == m)].iloc[0]
            comp.append(dict(desfecho=desf, tercil=m, raca=g, RP_conjunto=r.RP, RP_estrato=t["est"],
                             dif_log=np.log(r.RP) - np.log(t["est"])))
cp = pd.DataFrame(comp)
cp.to_csv(TB / f"tab_e3_06_dentro_vs_estrato_v1_{S}.csv", index=False)
check("(ii) modelo conjunto vs M2 por tercil — informativo (covariáveis comuns)",
      f"máx |Δ log RP| = {cp.dif_log.abs().max():.3f} ({cp.loc[cp.dif_log.abs().idxmax(), ['desfecho', 'tercil', 'raca']].tolist()}); "
      f"mesmo lado de 1 em {int(((cp.RP_conjunto > 1) == (cp.RP_estrato > 1)).sum())}/{len(cp)}", True)

# 4
cj = pd.read_csv(TB / f"tab_e3_02_conjunto_v1_{S}.csv")
it = pd.read_csv(TB / f"tab_e3_02_interacao_v1_{S}.csv")
bad, n = 0, 0
for (an, desf, est), x in cj.groupby(["analise", "desfecho", "estrato"]):
    ref = {"3.2_tercil_reg": "T3", "3.3b_tercil_nac": "T3_melhor", "3.3c_estratificado": "T3", "3.4_regiao": "SE",
           "3.5_idade": "20-34", "3.5_escolaridade": "ge12", "3.5_periodo": "2015-2019"}[an]
    D = x.set_index(["raca", "nivel"]).DR_pp
    for _, r in it[(it.analise == an) & (it.desfecho == desf) & (it.estrato == est)].iterrows():
        icr = D[r.raca, r.nivel] - D[r.raca, ref] - D["Branca", r.nivel]
        n += 1
        bad += int(abs(icr - r.ICR_pp) > 1e-8)
check("ICR = DR(g,m) − DR(g,ref) − DR(Branca,m) a partir de (i), todas as análises", f"{n - bad}/{n}", bad == 0)

# 5
br = pd.read_csv(TB / f"tab_e3_00b_bootstrap_replicas_v1_{S}.csv")
at = pd.read_csv(TB / f"tab_e3_00b_atenuacao_ic_v1_{S}.csv")
cnt = br.groupby(["desfecho", "raca"]).replica.nunique()
okb = (cnt == 500).all() and br[["RP_M2cc", "RP_M3"]].notna().all().all()
cont = ((at.dRP >= at.dRP_lo) & (at.dRP <= at.dRP_hi)).all()
check("bootstrap: 500 réplicas por desfecho × raça, sem falha; IC de ΔRP contém o ponto", f"{cnt.min()}–{cnt.max()} réplicas", okb and cont)

# 6 independente
AUD = L.PROJ / "audit_independente" / "etapa3"
if AUD.exists():
    ia = pd.read_csv(AUD / f"A_cortes_tercis_v1_{S}.csv").assign(regiao=lambda x: x.mr.astype(str).map(L.REGIAO))
    m = ct.merge(ia, on="regiao", suffixes=("", "_ind"))
    dm = float(np.max(np.abs(np.r_[m.corte_T1_T2 - m.c1_ind, m.corte_T2_T3 - m.c2_ind])))
    check("independente: cortes dos tercis por região", f"{len(m)}/5; máx |dif| = {dm:.1e}", len(m) == 5 and dm < 1e-9)
    ib = pd.read_csv(AUD / f"B_rp_conjuntas_prob_ptb_esp_v1_{S}.csv")
    mb = cj[(cj.analise == "3.2_tercil_reg") & (cj.desfecho == "ptb_esp")].merge(ib, left_on=["raca", "nivel"], right_on=["raca", "tercil"])
    dm = float(np.max(np.abs(np.r_[mb.RP_x - mb.RP_y, mb.RP_lo - mb.LI, mb.RP_hi - mb.LS, mb.P_pct_x - mb.P_pct_y])))
    check("independente: 12 RP conjuntas + P padronizadas (ptb_esp, 3.2 i)", f"{len(mb)}/12; máx |dif| = {dm:.1e}", len(mb) == 12 and dm < 1e-4)
    ic = pd.read_csv(AUD / f"C_icr_ptb_esp_v1_{S}.csv").query("raca in [\"Indigena\", \"Preta\"]")
    mi = it[(it.analise == "3.2_tercil_reg") & (it.desfecho == "ptb_esp") & (it.nivel == "T1")].merge(ic, on="raca")
    dm = float(np.max(np.abs(np.r_[mi.ICR_pp_x - mi.ICR_pp_y, mi.ICR_lo - mi.LI, mi.ICR_hi - mi.LS])))
    check("independente: ICR Indígena×T1 e Preta×T1 (ptb_esp) com IC", f"{len(mi)}/2; máx |dif| = {dm:.1e}", len(mi) == 2 and dm < 1e-4)
    idb = pd.read_csv(AUD / f"D_bootstrap_r1a20_v1_{S}.csv")
    md = br[(br.desfecho == "ptb") & (br.replica <= 20)].merge(idb, on=["replica", "raca"], suffixes=("", "_ind"))
    dm = float(np.max(np.abs(np.r_[md.RP_M2cc - md.RP_M2cc_ind, md.RP_M3 - md.RP_M3_ind])))
    check("independente: bootstrap réplicas 1–20 (ptb, 3 raças × 2 modelos; 6 casas)", f"{len(md)}/60; máx |dif| = {dm:.1e}",
          len(md) == 60 and dm < 1e-6)

pd.DataFrame(chk).to_csv(TB / f"tab_e3_06_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 3: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
