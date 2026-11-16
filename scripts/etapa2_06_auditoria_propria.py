"""
Auditoria própria da Etapa 2 (+ confronto com a auditoria independente, se presente).

  1. índice de acesso recalculado em DuckDB SQL direto dos brutos = índice pandas (4,763 região-anos)
  2. todo incluído tem região de saúde, exceto os 533 de município ignorado
  3. tercis com ~1/3 dos nascimentos; atribuição t−1 conferida
  4. Σ células = n individual nos modelos (recontagem por desfecho e modelo)
  5. M1 reproduz as RP brutas da Etapa 1 (ptb e pig; lbw_termo mudou de definição na v3)
  6. tb_regsaud: códigos sem município na relação (informativo)
  7. auditoria independente (audit_independente/etapa2): índice nos 10 sorteios, cortes, RP M2 de ptb e ptb_esp
Saída: tab_e2_06_auditoria_propria.
"""
import duckdb
import numpy as np
import pandas as pd

import etapa0_lib as L

log = L.Logger("06_auditoria", etapa="etapa2")
T, S = L.TAB, L.STAMP
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


# 1 índice em SQL
A = pd.read_csv(L.PROC / f"indice_acesso_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})
fs = [str(L.RAW / f"sinasc_{y}.parquet") for y in range(2014, 2025)]
rl = str(L.PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv")
q = f"""
WITH b AS (SELECT CAST(regexp_extract(filename, 'sinasc_([0-9]+)', 1) AS INT) ano, trim(CAST(CODMUNRES AS VARCHAR)) mun,
              TRY_CAST(trim(CAST(MESPRENAT AS VARCHAR)) AS DOUBLE) mes
           FROM read_parquet($fs, filename=true, union_by_name=true))
SELECT r.CO_REGSAUD, b.ano, sum(CASE WHEN mes BETWEEN 1 AND 9 THEN 1 ELSE 0 END) val,
       sum(CASE WHEN mes BETWEEN 1 AND 3 THEN 1 ELSE 0 END) tri1, count(*) n
FROM b JOIN read_csv('{rl}', all_varchar=true) r ON b.mun = r.CO_MUNICIP GROUP BY ALL"""
Q = duckdb.execute(q, {"fs": fs}).df()
Q["indice_sql"] = 100 * Q.tri1 / Q.val
m = A.merge(Q, on=["CO_REGSAUD", "ano"], how="outer", indicator=True)
dif = (m.indice - m.indice_sql).abs().max()
check("índice pandas = SQL (região-anos; máx |dif|)", f"{len(m):,} pares; só um lado={int((m._merge != 'both').sum())}; máx={dif:.2e}",
      (m._merge == "both").all() and dif < 1e-9 and (m.n_nasc == m.n).all())

# 2 e 3
d = pd.read_parquet(L.PROC / f"sinasc_brasil_2015_2024_v3_{S}", columns=["incl", "ano", "CO_REGSAUD", "CODMUNRES"],
                    filters=[("incl", "==", True)])
d["ano"] = d.ano.astype(int)
sem = d.CO_REGSAUD.isna()
check("incluídos sem região de saúde = 533, todos UF+0000", f"{int(sem.sum())}; UF0000={int(d[sem].CODMUNRES.str.endswith('0000').sum())}",
      int(sem.sum()) == 533 and d[sem].CODMUNRES.str.endswith("0000").all())
cut = pd.read_csv(T / f"tab_e2_03_tercis_cortes_v1_{S}.csv").iloc[0]
pct = [cut.pct_nasc_T1_pior, cut.pct_nasc_T2, cut.pct_nasc_T3_melhor]
check("tercis com ~1/3 dos nascimentos (|pct − 33.33| < 1)", [round(x, 2) for x in pct], all(abs(x - 100 / 3) < 1 for x in pct))
ter = pd.read_csv(L.PROC / f"tercil_regsaude_ano_v1_{S}.csv", dtype={"CO_REGSAUD": str})
chk_t1 = ter.merge(A.assign(ano=A.ano + 1)[["CO_REGSAUD", "ano", "indice"]], on=["CO_REGSAUD", "ano"])
check("índice atribuído = índice de t−1 da mesma região", f"{len(chk_t1):,} pares; máx |dif| = {(chk_t1.indice_t1 - chk_t1.indice).abs().max():.1e}",
      (chk_t1.indice_t1 - chk_t1.indice).abs().max() < 1e-9 and len(chk_t1) == len(ter.dropna()))
recalc = pd.cut(ter.indice_t1, [-np.inf, cut.corte_T1_T2, cut.corte_T2_T3, np.inf], labels=["T1_pior", "T2", "T3_melhor"])
check("tercil reclassificado pelos cortes = tercil gravado", int((recalc.astype(str) != ter.tercil.astype(str)).sum()),
      (recalc.astype(str) == ter.tercil.astype(str)).all())

# 4 Σ células = n (refaz as contagens do modelo)
t = pd.read_csv(T / f"tab_e2_04_modelos_long_v1_{S}.csv")
v = pd.read_parquet(L.PROC / f"sinasc_brasil_2015_2024_v3_{S}",
                    columns=["incl", "regiao", "estciv_cat", "ptb", "ptb_esp", "ptb_ind", "lbw_termo", "pig"], filters=[("incl", "==", True)])
bad = 0
for desf in ["ptb", "ptb_esp", "ptb_ind", "lbw_termo", "pig"]:
    s = v[v[desf].notna()]
    exp = {"M1": len(s), "M2": len(s), "M2s": len(s), "M2cc": int(s.estciv_cat.notna().sum()), "M3": int(s.estciv_cat.notna().sum())}
    for mo, n in exp.items():
        bad += int((t[(t.desfecho == desf) & (t.modelo == mo) & (t.regiao == "Brasil")].N != n).any())
    for reg in L.REGIOES:
        bad += int((t[(t.desfecho == desf) & (t.modelo == "M2") & (t.regiao == reg)].N != int((s.regiao == reg).sum())).any())
check("N de cada modelo (Σ células) = n individual (5 desfechos × 5 modelos + 5 regiões)", f"{bad} divergências", bad == 0)

# 5 M1 = RP bruta da Etapa 1
e1 = pd.read_csv(T / f"tab_e1_05c_rp_or_da_brutas_v1_{S}.csv")
e1 = e1[(e1.medida == "RP") & (e1.regiao == "Brasil") & e1.desfecho.isin(["ptb", "pig"])]
m1 = t[(t.modelo == "M1") & (t.regiao == "Brasil")].merge(e1, on=["desfecho", "raca"])
dm = (m1.RP - m1.est).abs().max()
dl = np.maximum((m1.RP_lo - m1.lo).abs(), (m1.RP_hi - m1.hi).abs()).max()
check("M1 = RP bruta Etapa 1 (ptb, pig; ponto e IC)", f"{len(m1)} RP; máx |dif| ponto {dm:.1e}, IC {dl:.1e}", dm < 1e-9 and dl < 1e-9)

# 6 tb_regsaud
rg = pd.read_csv(L.PROJ / "docs/referencias/territorio_dez24/tb_regsaud.csv", dtype=str, encoding="utf-8")
rlx = pd.read_csv(rl, dtype=str)
extra = rg[~rg.REGSAUD.isin(rlx.CO_REGSAUD)]
extra.to_csv(T / f"tab_e2_06_regsaud_sem_municipio_v1_{S}.csv", index=False)
check("tb_regsaud: códigos sem município na relação — informativo", f"{len(extra)} de {len(rg)}; UFs {sorted(extra.REGSAUD.str[:2].unique())}", True)

# 7 independente
AUD = L.PROJ / "audit_independente" / "etapa2"
if AUD.exists():
    s10 = pd.read_csv(AUD / "sorteio_10_pares_seed42.csv", dtype={"CO_REGSAUD": str})
    x = s10.merge(A, on=["CO_REGSAUD", "ano"], suffixes=("_ind", ""))
    ok10 = (len(x) == 10 and (x.n_res == x.n_nasc).all() and (x.n_mesprenat_valido == x.mes_valido).all()
            and (x.n_1tri == x.tri1).all() and ((x.indice_ind - x.indice.round(4)).abs() < 1e-9).all())
    check("independente: índice nos 10 região-anos sorteados (n, válidos, 1º tri, índice 4 casas)", f"{len(x)}/10", ok10)
    tc = pd.read_csv(AUD / "tercis_cortes_e_distribuicao.csv")
    okc = (round(cut.corte_T1_T2, 4) == tc.corte1.iloc[0] and round(cut.corte_T2_T3, 4) == tc.corte2.iloc[0]
           and np.allclose(tc.pct_nasc.to_numpy(), np.round(pct, 4)))
    check("independente: cortes dos tercis (4 casas) e % por tercil", f"{tc.corte1.iloc[0]}/{tc.corte2.iloc[0]}", okc)
    rp = pd.read_csv(AUD / "m2_rp_brasil.csv")
    y = rp.merge(t[(t.modelo == "M2") & (t.regiao == "Brasil")], on=["desfecho", "raca"])
    dmax = np.max(np.abs(np.r_[y.RP_x - y.RP_y, y.IC_inf - y.RP_lo, y.IC_sup - y.RP_hi]))
    check("independente: RP M2 Brasil (ptb, ptb_esp; ponto e IC)", f"{len(y)}/6; máx |dif| = {dmax:.1e}", len(y) == 6 and dmax < 5e-6)
pd.DataFrame(chk).to_csv(T / f"tab_e2_06_auditoria_propria_v1_{S}.csv", index=False)
log(f"auditoria Etapa 2: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
