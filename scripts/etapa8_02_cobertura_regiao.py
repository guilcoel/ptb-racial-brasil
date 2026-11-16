"""
8.2 Cobertura da Atenção Básica por região de saúde × ano (2014–2020), a partir do bruto municipal mensal do etapa8_01.
cobertura(r, a) = Σ pcCoberturaAb_im · qtPopulacao_im / Σ qtPopulacao_im, somando os municípios i da região r e os 12 meses m
  do ano a: média do percentual oficial ponderada pela população que o próprio relatório usa (decisão da Etapa 8: média dos 12
  meses). Não usa a qtCoberturaAb: no teste com o AC, Rio Branco 03/2014 veio com 2.670 cobertos e 74,75%.
Mapa município → região: o mesmo do índice de pré-natal (data/processed/municipio_regsaude_dez24, base territorial dez/2024).
Controles (contados, nada é corrigido): registros por município (84 competências); municípios do mapa sem registro e registros
  sem região; pcCoberturaAb fora de 0–100 ou nulo; população nula ou zero; divergência |pc − 100·qtCoberturaAb/qtPopulacao| >
  0,5 p.p.; população diferente entre os meses do mesmo ano.
Saídas: data/processed/cobertura_ab_regsaude_ano_v1 (região × ano, agregado), tab_e8_02_qualidade (por UF),
  tab_e8_02_cobertura_distribuicao_macro_ano (regiões ponderadas pela população).
Rodar da raiz: python3 scripts/etapa8_02_cobertura_regiao.py
"""
import json

import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("8_02_cobertura_regiao", etapa="etapa8")
RAW = L.PROJ / "data" / "raw" / "aps_cobertura_ab"
man = pd.read_csv(RAW / "manifesto_cobertura_ab_v1_20261013.csv", dtype=str)
assert len(man) == 27
num = lambda s: pd.to_numeric(s.astype("string").str.replace(",", "", regex=False).str.strip(), errors="coerce")
partes = []
for r in man.itertuples():
    x = pd.DataFrame(json.loads((RAW / r.arquivo).read_bytes()))
    partes.append(x[["nuComp", "coUfIbge", "coMunicipioIbge", "qtPopulacao", "pcCoberturaAb", "qtCoberturaAb",
                     "nuAnoPopulacaoConsiderada"]])
D = pd.concat(partes, ignore_index=True)
D = D.assign(ano=D.nuComp.str[:4].astype(int), popu=num(D.qtPopulacao), pc=num(D.pcCoberturaAb), qcob=num(D.qtCoberturaAb),
             cod=D.coMunicipioIbge.astype(str).str.strip())
assert D.cod.str.fullmatch(r"\d{6}").all()
assert not D.duplicated(["cod", "nuComp"]).any()
log(f"registros: {len(D):,}; municípios: {D.cod.nunique():,}; competências: {D.nuComp.nunique()}")

mp = pd.read_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", dtype=str)
mp = mp[~mp.CODMUNRES.str.endswith("0000")]                    # 530000 (município ignorado do DF) não é município
D["CO_REGSAUD"] = D.cod.map(dict(zip(mp.CODMUNRES, mp.CO_REGSAUD)))
sem_reg = sorted(D.cod[D.CO_REGSAUD.isna()].unique())
sem_dado = sorted(set(mp.CODMUNRES) - set(D.cod))
n_reg = D.groupby("cod").nuComp.nunique()
div = (D.pc - 100 * D.qcob / D.popu).abs() > 0.5
pop_var = D.groupby(["cod", "ano"]).popu.nunique() > 1

Q = (D.assign(div=div, pc_ruim=~D.pc.between(0, 100), pop_ruim=~(D.popu > 0), uf=D.coUfIbge)
     .groupby("uf").agg(registros=("cod", "size"), municipios=("cod", "nunique"), pc_fora_0_100_ou_nulo=("pc_ruim", "sum"),
                        pop_nula_ou_zero=("pop_ruim", "sum"), divergencia_pc_qt_gt_0_5pp=("div", "sum")).reset_index())
Q["municipios_com_menos_de_84_competencias"] = Q.uf.map(n_reg[n_reg < 84].groupby(lambda c: c[:2]).size()).fillna(0).astype(int)
Q["municipio_ano_com_populacao_variando"] = Q.uf.map(pop_var[pop_var].reset_index().cod.str[:2].value_counts()).fillna(0).astype(int)
Q["municipios_do_mapa_sem_registro"] = Q.uf.map(pd.Series(sem_dado, dtype=str).str[:2].value_counts()).fillna(0).astype(int)
Q["registros_sem_regiao_de_saude"] = Q.uf.map(D[D.CO_REGSAUD.isna()].coUfIbge.value_counts()).fillna(0).astype(int)
Q.insert(1, "sigla", Q.uf.map(L.UF_SIGLA))
Q.to_csv(L.out_name("tab_e8_02_qualidade"), index=False)
tot = Q.drop(columns=["uf", "sigla"]).sum()
log(f"qualidade: {tot.to_dict()}")
log(f"municípios do mapa sem registro: {sem_dado}; registros sem região: {sem_reg}")
dv = D[div][["nuComp", "cod", "pc"]].assign(qcob_sobre_pop=lambda z: (100 * D.qcob / D.popu)[div].round(2))
log(f"divergências pc × qtCoberturaAb/qtPopulacao > 0,5 p.p. ({int(div.sum())}): {dv.to_dict('records')[:10]}")
assert D.pc.between(0, 100).all() and (D.popu > 0).all()

ok = D[D.CO_REGSAUD.notna()]
A = (ok.assign(pw=ok.pc * ok.popu).groupby(["CO_REGSAUD", "ano"])
     .agg(pw=("pw", "sum"), pop_meses=("popu", "sum"), n_municipios=("cod", "nunique"), n_registros=("cod", "size")).reset_index())
A["cobertura_ab"] = A.pw / A.pop_meses
A["pop_media"] = A.set_index(["CO_REGSAUD", "ano"]).index.map(   # média, nos meses do ano, da população somada da região
    ok.groupby(["CO_REGSAUD", "ano", "nuComp"]).popu.sum().groupby(["CO_REGSAUD", "ano"]).mean())
mun_reg = mp.groupby("CO_REGSAUD").CODMUNRES.nunique()
A["municipios_no_mapa"] = A.CO_REGSAUD.map(mun_reg)
A["completa"] = (A.n_municipios == A.municipios_no_mapa) & (A.n_registros == 12 * A.municipios_no_mapa)
A = A[["CO_REGSAUD", "ano", "cobertura_ab", "pop_media", "n_municipios", "municipios_no_mapa", "n_registros", "completa"]]
assert len(A) == A.CO_REGSAUD.nunique() * 7 and A.CO_REGSAUD.nunique() == mp.CO_REGSAUD.nunique()
A.to_csv(L.PROC / f"cobertura_ab_regsaude_ano_v1_{L.STAMP}.csv", index=False)
log(f"cobertura por região × ano: {len(A):,} pares; {A.CO_REGSAUD.nunique()} regiões; incompletos {int((~A.completa).sum())}; "
    f"min/max = {A.cobertura_ab.min():.1f}/{A.cobertura_ab.max():.1f}")

A["macro"] = A.CO_REGSAUD.str[0].map(L.REGIAO)


def wq(x, w, q):
    o = np.argsort(x.to_numpy())
    xs, ws = x.to_numpy()[o], w.to_numpy()[o]
    return xs[np.searchsorted(np.cumsum(ws) / ws.sum(), q)]


dist = [dict(macro=m, ano=a, n_regioes=len(g), media_pond=np.average(g.cobertura_ab, weights=g.pop_media),
             p25=wq(g.cobertura_ab, g.pop_media, 0.25), mediana=wq(g.cobertura_ab, g.pop_media, 0.5),
             p75=wq(g.cobertura_ab, g.pop_media, 0.75), minimo=g.cobertura_ab.min(), maximo=g.cobertura_ab.max())
        for (m, a), g in A.groupby(["macro", "ano"])]
dist += [dict(macro="Brasil", ano=a, n_regioes=len(g), media_pond=np.average(g.cobertura_ab, weights=g.pop_media),
              p25=wq(g.cobertura_ab, g.pop_media, 0.25), mediana=wq(g.cobertura_ab, g.pop_media, 0.5),
              p75=wq(g.cobertura_ab, g.pop_media, 0.75), minimo=g.cobertura_ab.min(), maximo=g.cobertura_ab.max())
         for a, g in A.groupby("ano")]
Dd = pd.DataFrame(dist).round(2)
Dd.to_csv(L.out_name("tab_e8_02_cobertura_distribuicao_macro_ano"), index=False)
log("cobertura média ponderada pela população, Brasil por ano: "
    + ", ".join(f"{int(r.ano)} {r.media_pond:.1f}" for r in Dd[Dd.macro == "Brasil"].itertuples()))
