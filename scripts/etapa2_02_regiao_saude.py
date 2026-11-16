"""
2.2 Região de saúde (CIR) — tabela OFICIAL do DATASUS, versão fixa de dezembro/2024 para todo o período.

Fonte: ftp://ftp.datasus.gov.br/territorio/tabelas/2024/12-base territorial_dez24.zip
  (base territorial do TabNet; arquivo datado de 19/12/2024 no FTP; baixado em 2026-10-08;
   URL, data e MD5 em docs/referencias/territorio_dez24/ACESSO.txt)
  rl_municip_regsaud.csv  CO_MUNICIP (6 díg.) -> CO_REGSAUD (5 díg.)
  tb_regsaud.csv          CO_REGSAUD, status, nome
  tb_municip.csv          CO_MUNICIP, status, DT_INSTAL, DT_EXTIN, CO_SUCESS
Casamento com CODMUNRES de TODOS os nascidos vivos residentes 2014–2024 (2014 = índice t−1 de 2015).
Códigos UF+0000 (município ignorado) ficam sem região por desenho.
Saídas: data/processed/municipio_regsaude_dez24_v1 (mapa), tab_e2_02_regsaude_* (resumo e exceções).
"""
import pandas as pd

import etapa0_lib as L

log = L.Logger("02_regsaude", etapa="etapa2")
TER = L.PROJ / "docs/referencias/territorio_dez24"
rl = pd.read_csv(TER / "rl_municip_regsaud.csv", dtype=str)
rg = pd.read_csv(TER / "tb_regsaud.csv", dtype=str, encoding="utf-8")
mu = pd.read_csv(TER / "tb_municip.csv", dtype=str, sep=";", encoding="latin-1")
rg.columns = [c.strip() for c in rg.columns]
log(f"rl_municip_regsaud: {len(rl):,} municípios, {rl.CO_REGSAUD.nunique()} regiões; "
    f"tb_regsaud: {len(rg)} ({rg.CO_STATUS.value_counts().to_dict()}); tb_municip: {len(mu):,}")
assert rl.CO_MUNICIP.is_unique

# nascidos por município de residência, 2014–2024 (todos os residentes)
rows = []
for y in range(2014, 2025):
    s = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", columns=["CODMUNRES"]).CODMUNRES.astype("string").str.strip()
    vc = s.value_counts()
    rows.append(pd.DataFrame({"CODMUNRES": vc.index, "ano": y, "n": vc.values}))
nv = pd.concat(rows)
log("nascidos vivos residentes 2014–2024", int(nv.n.sum()))

m = nv.merge(rl, left_on="CODMUNRES", right_on="CO_MUNICIP", how="left")
m["ignorado"] = m.CODMUNRES.str.endswith("0000")
sem = m[m.CO_REGSAUD.isna()]
info = mu[["CO_MUNICIP", "CO_STATUS", "DS_NOME", "SG_UF", "DT_INSTAL", "DT_EXTIN", "CO_SUCESS"]]
exc = (sem.groupby(["CODMUNRES", "ignorado"]).agg(n=("n", "sum"), anos=("ano", lambda a: f"{min(a)}–{max(a)}"))
       .reset_index().merge(info, left_on="CODMUNRES", right_on="CO_MUNICIP", how="left").drop(columns="CO_MUNICIP"))
exc.to_csv(L.TAB / f"tab_e2_02_regsaude_sem_correspondencia_v1_{L.STAMP}.csv", index=False)
log(f"sem correspondência: {len(exc)} códigos; ignorados (UF0000) = {int(exc.ignorado.sum())} "
    f"({int(exc[exc.ignorado].n.sum()):,} nasc.); outros = {int((~exc.ignorado).sum())} ({int(exc[~exc.ignorado].n.sum()):,} nasc.)")

# municípios instalados ou extintos no período (pela tabela oficial) e presença no SINASC
inst = pd.to_numeric(info.DT_INSTAL, errors="coerce")
ext = pd.to_numeric(info.DT_EXTIN, errors="coerce")
mud = info[(inst >= 2013) | ext.notna()].copy()
pres = nv.groupby("CODMUNRES").agg(primeiro_ano_sinasc=("ano", "min"), ultimo_ano_sinasc=("ano", "max"), n_2014_2024=("n", "sum"))
mud = mud.merge(pres, left_on="CO_MUNICIP", right_index=True, how="left").merge(rl, on="CO_MUNICIP", how="left")
mud.to_csv(L.TAB / f"tab_e2_02_regsaude_municipios_criados_extintos_v1_{L.STAMP}.csv", index=False)
log(f"municípios com instalação ≥ 2013 ou extinção registrada: {len(mud)}")

# códigos que aparecem/somem no SINASC dentro de 2015–2024
p = nv[nv.ano >= 2015].groupby("CODMUNRES").ano.agg(["min", "max", "nunique"])
irreg = p[(p["min"] > 2015) | (p["max"] < 2024) | (p["nunique"] < 10)]
irreg = irreg[~irreg.index.str.endswith("0000")]
irreg.to_csv(L.TAB / f"tab_e2_02_regsaude_codigos_irregulares_v1_{L.STAMP}.csv")
log(f"CODMUNRES (exc. ignorados) ausentes em algum ano de 2015–2024: {len(irreg)}")

mapa = rl.rename(columns={"CO_MUNICIP": "CODMUNRES"}).merge(
    rg[["REGSAUD", "DS_NOME"]].rename(columns={"REGSAUD": "CO_REGSAUD", "DS_NOME": "nome_regsaud"}), on="CO_REGSAUD", how="left")
assert mapa.nome_regsaud.notna().all()
mapa.to_csv(L.PROC / f"municipio_regsaude_dez24_v1_{L.STAMP}.csv", index=False)
res = dict(fonte="DATASUS base territorial dez/2024", n_municipios_tabela=len(rl), n_regioes=rl.CO_REGSAUD.nunique(),
           n_codmunres_sinasc_2014_2024=nv.CODMUNRES.nunique(),
           n_codigos_sem_regiao=len(exc), n_nasc_sem_regiao=int(exc.n.sum()),
           n_nasc_sem_regiao_nao_ignorado=int(exc[~exc.ignorado].n.sum()))
pd.DataFrame([res]).to_csv(L.TAB / f"tab_e2_02_regsaude_resumo_v1_{L.STAMP}.csv", index=False)
log(str(res))
