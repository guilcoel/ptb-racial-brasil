"""
Auditoria própria da Etapa 1 (pandas) + confronto com a auditoria independente (DuckDB/R).

  1. agregado = individual: Σ células (raça × município) = n e casos individuais em cada desfecho × região × raça;
     prevalências da tab 1.4 = média individual
  2. denominadores: lbw_termo só em 37–41 sem com peso 100–7000; PIG só nos elegíveis; nulos fora disso
  3. base v2 vs v1: n por ano e incl idênticos à cascata da Etapa 0
  4. PIG reforçado: 20 casos estratificados (10 PIG + 10 não PIG, seed 42) contra a tabela oficial e a grade gigs;
     n de nascimentos a < 10 g do limiar P10 (sensibilidade ao arredondamento das tabelas)
  5. independente: tabA (contagens), tabB (RP Brasil), tabC (validação CO) vs meus números
Saída: tab_e1_08_auditoria_propria; casos do item 4 ficam em data/ (não versionado).
"""
import numpy as np
import pandas as pd

import etapa1_lib as E

log = E.logger("08_auditoria")
T, S = E.L.TAB, E.L.STAMP
AUD = E.L.PROJ / "audit_independente" / "etapa1"
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


d = E.load(["raca", "regiao", "uf", "CODMUNRES", "ptb", "ptb_sub", "ptb_tipo", "lbw_termo", "pig", "pig_tabela_oficial",
            "pig_elegivel", "SEMAGESTAC", "PESO", "SEXO", "GRAVIDEZ", "ano"])
d["ptb_extremo"] = (d.ptb_sub == "1_extremo_lt28").astype(int)
d["ptb_muito"] = (d.ptb_sub == "2_muito_28a31").astype(int)
d["ptb_mod_tardio"] = (d.ptb_sub == "3_moderado_tardio_32a36").astype(int)
check("n amostra v2 = Etapa 0", f"{len(d):,}", len(d) == 25808740)

# 3 v1 vs v2
v1 = pd.read_parquet(E.L.BASE_DIR, columns=["RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "ano"])
ok1 = E.L.cascade_flags(v1)
a = v1[ok1.incluido.values].groupby("ano").size()
b = d.groupby("ano").size()
check("incl por ano: v1 (cascata Etapa 0) = v2", int((a.values != b.values).sum()), (a.values == b.values).all())
del v1, ok1

# 1 agregado = individual; prevalências
prev = pd.read_csv(T / f"tab_e1_04_prevalencias_v1_{S}.csv")
OUT = ["ptb", "ptb_extremo", "ptb_muito", "ptb_mod_tardio", "lbw_termo", "pig"]
bad_cells, bad_prev, n_cmp = 0, 0, 0
for o in OUT:
    for reg in ["Brasil"] + E.L.REGIOES:
        s = d if reg == "Brasil" else d[d.regiao == reg]
        cells = E.agrega(s, o, ["raca"])
        for g in E.L.RACA_ORDER:
            ind = s.loc[(s.raca == g) & s[o].notna(), o]
            c = cells[cells.raca == g]
            bad_cells += int(c.n.sum() != len(ind) or c.Y.sum() != ind.sum())
            p = prev[(prev.desfecho == o) & (prev.raca == g) &
                     (prev.estrato == ("brasil" if reg == "Brasil" else "regiao")) & (prev.nivel == reg)].iloc[0]
            bad_prev += int(p.casos != ind.sum() or p.denominador != len(ind) or abs(p.prev_pct - 100 * ind.mean()) > 1e-9)
            n_cmp += 1
check("Σ células agregadas = n e casos individuais (desfecho×região×raça)", f"{n_cmp - bad_cells}/{n_cmp}", bad_cells == 0)
check("prevalências 1.4 = média individual", f"{n_cmp - bad_prev}/{n_cmp}", bad_prev == 0)

# 2 denominadores
lbw_def = d.SEMAGESTAC.between(37, 41) & d.PESO.between(100, 7000)
check("lbw_termo definido ⇔ 37–41 sem e peso válido", int((d.lbw_termo.notna() != lbw_def.fillna(False)).sum()),
      (d.lbw_termo.notna() == lbw_def.fillna(False)).all())
pe = (d.GRAVIDEZ == 1) & d.SEMAGESTAC.between(24, 42) & d.SEXO.isin([1, 2]) & d.PESO.between(100, 7000)
pe = pe.fillna(False)
check("pig definido ⇔ elegível (única, 24–42, sexo, peso)", int((d.pig.notna() != pe).sum()), (d.pig.notna() == pe).all())
check("ptb_tipo definido ⇔ ptb = 1", int((d.ptb_tipo.notna() != (d.ptb == 1)).sum()), (d.ptb_tipo.notna() == (d.ptb == 1)).all())
check("Σ subtipos = ptb", f"{int(d[['ptb_extremo','ptb_muito','ptb_mod_tardio']].sum().sum()):,}",
      d[["ptb_extremo", "ptb_muito", "ptb_mod_tardio"]].sum().sum() == d.ptb.sum())

# 4 PIG reforçado
ref = pd.read_csv(E.L.PROJ / "docs/referencias/intergrowth21_bw_centis_oficial.csv")
p10 = ref[(ref.centil == 10) & (ref.dias == 3)].assign(SEXO=lambda x: np.where(x.sexo == "M", 1, 2))
p10 = p10.rename(columns={"semanas": "SEMAGESTAC", "peso_kg": "p10_of"})[["SEMAGESTAC", "SEXO", "p10_of"]]
lim = pd.read_csv(T / f"tab_e1_pig_limiares_p10_v1_{S}.csv")
el = d[d.pig_elegivel][["SEMAGESTAC", "SEXO", "PESO", "pig"]].copy()
rng = np.random.default_rng(42)
amostra = pd.concat([el[el.pig == 1].sample(10, random_state=42), el[el.pig == 0].sample(10, random_state=42)])
amostra = amostra.astype(int).merge(p10, on=["SEMAGESTAC", "SEXO"]).merge(lim, on=["SEMAGESTAC", "SEXO"])
amostra["pig_oficial"] = (amostra.PESO / 1000 < amostra.p10_of).astype(int)
amostra["pig_gigs_limiar"] = (amostra.PESO / 1000 < amostra.p10_gigs_kg_k3).astype(int)
amostra.to_csv(E.L.PROC / f"auditoria_pig_amostra20_v1_{S}.csv", index=False)  # nível de caso: fica em data/
check("PIG 20 casos (10 PIG + 10 não PIG): base = tabela oficial", f"{int((amostra.pig == amostra.pig_oficial).sum())}/20",
      (amostra.pig == amostra.pig_oficial).all())
check("PIG 20 casos: base = limiar gigs (P10)", f"{int((amostra.pig == amostra.pig_gigs_limiar).sum())}/20",
      (amostra.pig == amostra.pig_gigs_limiar).all())
e2 = el.astype(int).merge(lim, on=["SEMAGESTAC", "SEXO"])
perto = int(((e2.PESO - 1000 * e2.p10_gigs_kg_k3).abs() < 10).sum())
check("nascimentos elegíveis a < 10 g do P10 (gigs) — informativo", f"{perto:,} ({100 * perto / len(e2):.2f}%)", True)
disc = int((d.pig != d.pig_tabela_oficial).sum())
check("discordância pig (gigs) × pig_tabela_oficial — informativo", f"{disc:,} ({100 * disc / int(d.pig.notna().sum()):.3f}%)", True)

# 5 independente
A = pd.read_csv(AUD / f"tabA_desfechos_raca_regiao_v1_{S}.csv", dtype=str)
RC = {"1": "Branca", "2": "Preta", "4": "Parda", "5": "Indigena", "Todas": "Total"}
RG = {"1": "N", "2": "NE", "3": "SE", "4": "S", "5": "CO", "Brasil": "Brasil"}
MAP = {"ptb": "ptb", "ptb_lt28": "ptb_extremo", "ptb_28_31": "ptb_muito", "ptb_32_36": "ptb_mod_tardio",
       "lbw_termo": "lbw_termo", "pig": "pig_tabela_oficial"}
bad, n = 0, 0
for _, r in A.iterrows():
    g, reg = RC[r.raca], RG[r.regiao]
    s = d if reg == "Brasil" else d[d.regiao == reg]
    s = s if g == "Total" else s[s.raca == g]
    if r.desfecho in MAP:
        col = MAP[r.desfecho]
        cas, den = int(s[col].sum()), int(s[col].notna().sum())
    else:
        tipo = {"ptbtipo_espontaneo": "espontaneo", "ptbtipo_indicado": "indicado", "ptbtipo_sem_class": "sem_classif"}[r.desfecho]
        cas, den = int((s.ptb_tipo == tipo).sum()), int(s.ptb_tipo.notna().sum())
    n += 1
    if cas != int(r.casos) or den != int(r.denom):
        bad += 1
        log(f"  divergência tabA {r.desfecho} {g} {reg}: meu {cas}/{den} vs indep {r.casos}/{r.denom}")
check("independente tabA: casos e denominadores (9 desfechos × raça × região)", f"{n - bad}/{n}", bad == 0)
B = pd.read_csv(AUD / f"tabB_rp_bruta_brasil_cluster_v1_{S}.csv")
mine = pd.read_csv(T / f"tab_e1_05c_rp_or_da_brutas_v1_{S}.csv")
bad = 0
for _, r in B.iterrows():
    dsf = {"pig": "pig_tabela_oficial", "lbw": "lbw_termo"}.get(r.desfecho, r.desfecho)
    m = mine[(mine.desfecho == dsf) & (mine.regiao == "Brasil") & (mine.raca == r.raca)].set_index("medida")
    ok = (round(m.loc["RP", "est"], 3), round(m.loc["RP", "lo"], 3), round(m.loc["RP", "hi"], 3)) == (r.RP, r.li, r.ls)
    ok &= round(m.loc["DA_pp", "est"], 3) == r.dif_pp
    if not ok:
        bad += 1
        log(f"  divergência tabB {r.desfecho} {r.raca}: meu RP {m.loc['RP','est']:.4f} ({m.loc['RP','lo']:.4f}–{m.loc['RP','hi']:.4f}) "
            f"DA {m.loc['DA_pp','est']:.4f} vs indep {r.RP} ({r.li}–{r.ls}) DA {r.dif_pp}")
check("independente tabB: RP bruta Brasil (3 casas) e diferença absoluta", f"{len(B) - bad}/{len(B)}", bad == 0)
C = pd.read_csv(AUD / f"tabC_validacao_centro_oeste_v1_{S}.csv")
V = pd.read_csv(T / f"tab_e1_05b_validacao_co_v1_{S}.csv")
bad, n = 0, 0
for _, r in C.iterrows():
    for col, (med, ep) in {"OR_modelo": ("OR", "modelo"), "OR_cluster": ("OR", "cluster"),
                           "RP_HC0": ("RP", "hc0"), "RP_cluster": ("RP", "cluster")}.items():
        v = V[(V.modelo == r.modelo) & (V.raca == r.raca) & (V.medida == med) & (V.ep == ep)].iloc[0]
        mine_s = f"{v.agg_est:.3f} ({v.agg_lo:.3f}-{v.agg_hi:.3f})"
        n += 1
        if mine_s != r[col]:
            bad += 1
            log(f"  divergência tabC {r.modelo} {r.raca} {col}: meu {mine_s} vs indep {r[col]}")
check("independente tabC: validação CO (M1/M5 × OR/RP × EP)", f"{n - bad}/{n}", bad == 0)

pd.DataFrame(chk).to_csv(T / f"tab_e1_08_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 1: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
