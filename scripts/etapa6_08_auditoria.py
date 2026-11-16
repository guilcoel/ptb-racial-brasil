"""
Auditoria própria da Etapa 6.
  1. N e casos das subamostras: 3.2 por região de saúde = 3.2 original; 6.4 = outro método − PTB implausíveis; 6.3 = amostra −
     sem classificação; 6.6 = Etapa 5; imputação múltipla --rs com as mesmas imputações (ICR por imputação = original).
  2. Estimativas pontuais com EP por região de saúde = com EP por município (M2, 3.2, Etapa 3 completa, 6.1b × Etapas 4/4b).
  3. ICR recalculado à mão a partir de (i) (6.1a e 6.4).
  4. IC por região de saúde ≥ IC por município (esperado; reporta a proporção e os casos mais estreitos).
  5. confronto com audit_independente/etapa6.
Saída: tab_e6_08_auditoria_propria.
"""
import numpy as np
import pandas as pd

import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("08_auditoria")
TB, S = L.TAB, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


rd = lambda f: pd.read_csv(TB / f"{f}_v1_{S}.csv")
# 1
w0 = rd("tab_e3_02_wald").query("analise == '3.2_tercil_reg' and estrato == 'Brasil'").set_index("desfecho")
w1 = rd("tab_e6_01a_wald").set_index("desfecho")
ok = all(int(w1.N[k]) == int(w0.N[k]) for k in w1.index) and (w1.G == 433).all()
check("3.2 por região de saúde: N = 3.2 original (5 desfechos); G = 433", w1.N.to_dict(), ok)
m4 = rd("tab_e6_04_m2")
check("6.4: subamostra = 10,650,839 (outro método) − 42,893 (PTB implausíveis) = 10,607,946", int(m4[m4.desfecho == "ptb"].N.iloc[0]),
      int(m4[m4.desfecho == "ptb"].N.iloc[0]) == 10650839 - 42893)
r3 = rd("tab_e6_03b_rrr")
check("6.3: N multinomial = 25,808,740 − 131,809 sem classificação", int(r3.query("analise == 'Brasil'").N.iloc[0]),
      int(r3.query("analise == 'Brasil'").N.iloc[0]) == 25808740 - 131809)
a6 = pd.read_csv(L.PROC / f"maihda_estratos_regsaude_v1_{S}.csv")
check("6.6: Σ células estrato × região = Etapa 5 (N, casos)", f"{int(a6.n.sum()):,}; {int(a6.casos.sum()):,}",
      int(a6.n.sum()) == 25028320 and int(a6.casos.sum()) == 2347145)
mi0, mi1 = rd("tab_e4_06_mi_icr_por_imputacao"), rd("tab_e4_06_mi_icr_por_imputacao_rs")
k = ["imputacao", "desfecho", "raca", "nivel"]
mm = mi0.merge(mi1, on=k, suffixes=("_mun", "_rs"))
dd = float((mm.ICR_pp_mun - mm.ICR_pp_rs).abs().max())
check("imputação múltipla --rs: mesmas imputações (ICR pontual por imputação = original)", f"{len(mm)} linhas; máx |dif| {dd:.1e}",
      len(mm) == len(mi0) and dd < 1e-9)

# 2
m2 = rd("tab_e6_01a_m2")
pv = m2.pivot_table(index=["desfecho", "raca"], columns="cluster", values="RP")
e2 = rd("tab_e2_04_modelos_long").query("modelo == 'M2' and regiao == 'Brasil'").set_index(["desfecho", "raca"]).RP
dp = max(float((pv.municipio - pv.regsaude).abs().max()), float((pv.municipio - e2.reindex(pv.index)).abs().max()))
check("M2: RP idêntica com EP por município e por região de saúde, e = Etapa 2", f"máx |dif| {dp:.1e}", dp < 1e-9)
ii = {"orig": rd("tab_e3_02_interacao"), "rs": rd("tab_e3_02_interacao_rs")}
kk = ["analise", "desfecho", "estrato", "raca", "nivel"]
c3 = ii["orig"].merge(ii["rs"], on=kk, suffixes=("_mun", "_rs"))
dp3 = float((c3.ICR_pp_mun - c3.ICR_pp_rs).abs().max())
check("Etapa 3 completa --rs: ICR pontual = original em todas as análises", f"{len(c3)} ICR; máx |dif| {dp3:.1e}",
      len(c3) == len(ii["orig"]) == len(ii["rs"]) and dp3 < 1e-9)
b = rd("tab_e6_01b_interacao")
orig = pd.concat([rd("tab_e4_01b_interacao"), rd("tab_e4_02_interacao"),
                  rd("tab_e4b_03_interacao").replace({"sensibilidade": {"4b.3": "4b.3_plausivel"}})])
cb = b.merge(orig, on=["sensibilidade", "desfecho", "raca", "nivel"], suffixes=("_rs", "_mun"))
dpb = float((cb.ICR_pp_rs - cb.ICR_pp_mun).abs().max())
check("6.1b: ICR pontual = Etapas 4/4b (mesma subamostra)", f"{len(cb)}/{len(b)} pareados; máx |dif| {dpb:.1e}", len(cb) == len(b) and dpb < 1e-9)

# 3
bad, n = 0, 0
for nome in ["tab_e6_01a", "tab_e6_04"]:
    cj, it = rd(f"{nome}_conjunto"), rd(f"{nome}_interacao")
    for desf, x in cj.groupby("desfecho"):
        D = x.set_index(["raca", "nivel"]).DR_pp
        for _, r in it[it.desfecho == desf].iterrows():
            n += 1
            bad += int(abs(D[r.raca, r.nivel] - D[r.raca, "T3"] - D["Branca", r.nivel] - r.ICR_pp) > 1e-8)
check("ICR recalculado à mão a partir de (i) (6.1a e 6.4)", f"{n - bad}/{n}", bad == 0)

# 4
lar = (c3.ICR_hi_rs - c3.ICR_lo_rs) / (c3.ICR_hi_mun - c3.ICR_lo_mun)
larb = (cb.ICR_hi_rs - cb.ICR_lo_rs) / (cb.ICR_hi_mun - cb.ICR_lo_mun)
m2w = m2.pivot_table(index=["desfecho", "raca"], columns="cluster", values=["RP_lo", "RP_hi"])
larm = (np.log(m2w.RP_hi.regsaude) - np.log(m2w.RP_lo.regsaude)) / (np.log(m2w.RP_hi.municipio) - np.log(m2w.RP_lo.municipio))
todas = pd.concat([lar, larb, larm])
# Não é garantido algebricamente: o sanduíche agrupado num nível mais grosso pode ser menor quando os escores dos
# municípios de uma mesma região se compensam (modificadores que variam dentro do cluster) ou quando há poucos
# clusters (3.2 estratificada por macrorregião). Exigido onde importa: 3.2 principal e M2; o resto é descritivo.
princ = lar[(c3.analise == "3.2_tercil_reg") & (c3.estrato == "Brasil")]
check("IC por região de saúde ≥ IC por município na 3.2 principal e no M2 (razão de larguras)",
      f"3.2: {int((princ >= 1).sum())}/{len(princ)} (mín {princ.min():.2f}); M2: {int((larm >= 1).sum())}/{len(larm)} (mín {larm.min():.2f})",
      (princ >= 1).all() and (larm >= 1).all())
nb = c3.assign(razao=lar)[lar < 1]
log(f"descritivo, todas as interações: {int((todas >= 1).sum())}/{len(todas)} com razão ≥ 1; mediana {todas.median():.2f}; "
    f"mín {todas.min():.2f}; máx {todas.max():.2f}. Razão < 1 por análise (Etapa 3): "
    + nb.groupby("analise").size().to_string().replace("\n", " | ") + f"; 6.1b: {int((larb < 1).sum())}")
log("ICR com IC por região de saúde mais estreito que por município (razão < 1):\n" +
    c3.assign(razao=lar)[lar < 1][kk + ["razao"]].round(3).head(20).to_string(index=False))

AUD = L.PROJ / "audit_independente" / "etapa6"
if AUD.exists():
    log("arquivos do auditor: " + ", ".join(sorted(x.name for x in AUD.iterdir() if not x.name.startswith("._"))))
    cp = pd.read_csv(AUD / f"d_comparacao_v1_{S}.csv")
    dr = pd.to_numeric(cp.dif_rel, errors="coerce").abs()
    por = cp.assign(d=dr).groupby("tarefa").d.agg(["size", "max"])
    check("independente (R + DuckDB): A ICR por região de saúde, B concordância por código, C RRR multinomiais",
          "; ".join(f"{t}: {int(r['size'])} itens, máx |dif rel| {r['max']:.1e}" for t, r in por.iterrows()), bool((dr.fillna(0) < 1e-4).all()))
pd.DataFrame(chk).to_csv(TB / f"tab_e6_08_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 6: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
