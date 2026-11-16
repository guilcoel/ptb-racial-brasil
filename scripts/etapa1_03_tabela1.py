"""
1.3 Tabela 1 — características maternas e do parto por raça (Brasil) e por raça × região.

Amostra analítica (incl). Categóricas: n e % entre os válidos; contínuas: média e DP.
Completude por variável e grupo: % válido (não nulo e não ignorado).
Códigos de ignorado conferidos na Etapa 0 (tab00_distribuicao_codigos): 9 em CONSULTAS, ESTCIVMAE,
GRAVIDEZ, PARTO, STTRABPART; 99 em MESPRENAT, QTDFILVIVO; SEXO 0; PESO fora de 100–7000.
Saídas: tab_e1_03_tabela1_long (todas as células), tab_e1_03_tabela1_brasil (formatada).
"""
import numpy as np
import pandas as pd

import etapa1_lib as E

log = E.logger("03_tabela1")
d = E.load(["raca", "regiao", "IDADEMAE", "idade_cat", "esc_cat", "estciv_cat", "CONSULTAS", "MESPRENAT",
            "QTDFILVIVO", "unica", "PARTO", "STTRABPART", "SEXO", "SEMAGESTAC", "PESO", "periodo"])
log("amostra", len(d))


def catvar(s, mapping):
    return s.map(mapping)


V = {
    "Idade materna (anos)": ("cont", d.IDADEMAE.astype(float)),
    "Faixa etária": ("cat", d.idade_cat.astype(object)),
    "Escolaridade (anos)": ("cat", d.esc_cat.astype(object)),
    "Situação conjugal": ("cat", d.estciv_cat.astype(object)),
    "Consultas pré-natal": ("cat", catvar(d.CONSULTAS, {1: "0", 2: "1-3", 3: "4-6", 4: "7+"})),
    "Início do pré-natal": ("cat", pd.cut(d.MESPRENAT.where(d.MESPRENAT.between(1, 9)).astype(float),
                                          [0, 3, 6, 9], labels=["1º trimestre", "2º trimestre", "3º trimestre"]).astype(object)),
    "Filhos vivos anteriores": ("cat", pd.cut(d.QTDFILVIVO.where(d.QTDFILVIVO != 99).astype(float),
                                              [-1, 0, 1, 2, 98], labels=["0", "1", "2", "3+"]).astype(object)),
    "Gravidez": ("cat", catvar(d.unica, {1: "única", 0: "múltipla"})),
    "Tipo de parto": ("cat", catvar(d.PARTO, {1: "vaginal", 2: "cesárea"})),
    "Trabalho de parto induzido": ("cat", catvar(d.STTRABPART, {1: "sim", 2: "não"})),
    "Sexo do RN": ("cat", catvar(d.SEXO, {1: "masculino", 2: "feminino"})),
    "Idade gestacional (semanas)": ("cont", d.SEMAGESTAC.astype(float)),
    "Peso ao nascer (g)": ("cont", d.PESO.where(d.PESO.between(100, 7000)).astype(float)),
    "Período": ("cat", d.periodo.astype(object)),
    "Região": ("cat", d.regiao.astype(object)),
}
grupos = [("Brasil", "Total", np.ones(len(d), bool))]
for g in E.L.RACA_ORDER:
    grupos.append(("Brasil", g, (d.raca == g).to_numpy()))
for r in E.L.REGIOES:
    mr = (d.regiao == r).to_numpy()
    grupos.append((r, "Total", mr))
    for g in E.L.RACA_ORDER:
        grupos.append((r, g, mr & (d.raca == g).to_numpy()))

rows = []
for reg, g, m in grupos:
    N = int(m.sum())
    for nome, (tipo, s) in V.items():
        if reg != "Brasil" and nome == "Região":
            continue
        x = s[m]
        nv = int(x.notna().sum())
        base = dict(regiao=reg, raca=g, N=N, variavel=nome, n_valido=nv, pct_completude=round(100 * nv / N, 2))
        if tipo == "cont":
            rows.append({**base, "categoria": "média (DP)", "n": nv, "pct": np.nan,
                         "media": round(x.mean(), 2), "dp": round(x.std(), 2)})
        else:
            for k, v in x.value_counts().sort_index().items():
                rows.append({**base, "categoria": k, "n": int(v), "pct": round(100 * v / nv, 2), "media": np.nan, "dp": np.nan})
t = pd.DataFrame(rows)
t.to_csv(E.L.TAB / f"tab_e1_03_tabela1_long_v1_{E.L.STAMP}.csv", index=False)
log(f"tabela longa: {len(t):,} linhas")

# formatada (Brasil, por raça): "n (%)" ou "média (DP)"; linha de completude por variável
b = t[t.regiao == "Brasil"].copy()
b["valor"] = np.where(b.categoria == "média (DP)", b.media.map(lambda v: E.fmt_f(v, 1)) + " (" + b.dp.map(lambda v: E.fmt_f(v, 1)) + ")",
                      b.n.map(E.fmt_n) + " (" + b.pct.map(lambda v: E.fmt_f(v, 1)) + ")")
w = b.pivot_table(index=["variavel", "categoria"], columns="raca", values="valor", aggfunc="first", sort=False)
c = b.drop_duplicates(["variavel", "raca"]).pivot_table(index="variavel", columns="raca", values="pct_completude", sort=False)
c = c.map(lambda v: E.fmt_f(v, 1) + "% completo")
c.index = pd.MultiIndex.from_arrays([c.index, ["completude"] * len(c)])
w = pd.concat([w, c]).sort_index(level=0, sort_remaining=False)
order = list(V)
w = w.reindex(sorted(w.index, key=lambda i: (order.index(i[0]), i[1] == "completude")))
nrow = pd.DataFrame([{g: E.fmt_n(int((d.raca == g).sum()) if g != "Total" else len(d)) for g in ["Total"] + E.L.RACA_ORDER}],
                    index=pd.MultiIndex.from_tuples([("N", "")]))
w = pd.concat([nrow, w[["Total"] + E.L.RACA_ORDER]])
w.to_csv(E.L.TAB / f"tab_e1_03_tabela1_brasil_v1_{E.L.STAMP}.csv")
log("tabela 1 Brasil formatada gravada")
