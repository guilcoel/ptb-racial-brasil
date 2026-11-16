"""
Auditoria própria da Etapa 0 (pandas/pyarrow).

  1. totais por ano: metadado do bruto = metadado da partição = linhas lidas da partição
  2. UF × ano: base processada = inventário do bruto (tab00_inventario_uf_ano)
  3. duplicatas: linhas idênticas em TODAS as colunas do bruto (por ano) e em todas as colunas da base
  4. fechamento: fluxograma (fonte − Σ excluídos = final), regiões somam Brasil, raças somam total,
     final do fluxograma = n de incluídos da tab08 = Σ tab09; prematuros da tab12 = n_ptb da tab09
Saída: tab14_auditoria_propria (verificação, valor, ok).
"""
import pandas as pd
import pyarrow.parquet as pq

import etapa0_lib as L

log = L.Logger("07_auditoria")
chk = []


def check(nome, valor, ok):
    chk.append(dict(verificacao=nome, valor=str(valor), ok=bool(ok)))
    log(f"{'OK ' if ok else 'FALHA'} {nome}: {valor}")


# 1 e 3 (bruto)
dup_rows = []
for y in L.YEARS:
    n_raw = pq.ParquetFile(L.RAW / f"sinasc_{y}.parquet").metadata.num_rows
    part = L.BASE_DIR / f"ano={y}" / "part-0.parquet"
    n_meta = pq.ParquetFile(part).metadata.num_rows
    n_read = len(pd.read_parquet(part, columns=["CODMUNRES"]))
    check(f"n {y} bruto=partição(meta)=partição(lida)", f"{n_raw:,}/{n_meta:,}/{n_read:,}", n_raw == n_meta == n_read)
    raw = pd.read_parquet(L.RAW / f"sinasc_{y}.parquet", dtype_backend="pyarrow")
    # contador/CONTADOR (só 2023–2024) é único por linha e esconderia duplicatas: fica de fora
    raw = raw.drop(columns=[c for c in raw.columns if c.lower() == "contador"])
    h = pd.util.hash_pandas_object(raw.astype("string"), index=False)
    dmask = h.duplicated(keep=False).to_numpy()
    dup = int(h.duplicated().sum())
    gem = int((pd.to_numeric(raw["GRAVIDEZ"].astype("string"), errors="coerce")[dmask] > 1).sum())
    dup_rows.append(dict(ano=y, n_colunas=raw.shape[1], linhas_em_excesso=dup,
                         linhas_envolvidas=int(dmask.sum()), envolvidas_gemelares=gem))
    # informativo: duplicata exata não é removida na Etapa 0 (ver resumo)
    check(f"duplicatas exatas {y} ({raw.shape[1]} colunas, sem contador) — informativo",
          f"excesso={dup}; envolvidas={int(dmask.sum())}; gemelares={gem}", True)
    del raw, h

base = pd.read_parquet(L.BASE_DIR)
base["ano"] = base["ano"].astype(int)
tot = pd.read_csv(L.out_name("tab00_inventario_ano")).n_registros.sum()
check("n total base = Σ inventário bruto", f"{len(base):,} vs {tot:,}", len(base) == tot)
hb = pd.util.hash_pandas_object(base.drop(columns=["_ano_arquivo"]), index=False)
pd.DataFrame(dup_rows).to_csv(L.out_name("tab15_duplicatas_bruto"), index=False)
# esperado: com só 18 variáveis, registros distintos colidem; informativo
check("linhas iguais na base enxuta (18 variáveis + derivadas) — informativo", int(hb.duplicated().sum()), True)
del hb

# 2
inv = pd.read_csv(L.out_name("tab00_inventario_uf_ano")).set_index(["uf", "ano"]).n
bas = base.groupby(["uf", "ano"]).size()
diff = (inv.sort_index() - bas.sort_index()).abs().sum()
check("UF×ano base = bruto (Σ|dif| em 270 células)", int(diff), diff == 0 and len(bas) == 270)

# 4
fx = pd.read_csv(L.out_name("tab06_fluxograma_regiao"))
for reg, d in fx.groupby("regiao"):
    fonte, final = d.restante.iloc[0], d.restante.iloc[-1]
    check(f"fluxo {reg}: fonte − Σexcl = final", f"{fonte:,} − {d.excluidos.sum():,} = {final:,}",
          fonte - d.excluidos.sum() == final)
br = fx[fx.regiao == "Brasil"].set_index("passo")
rg = fx[fx.regiao != "Brasil"].groupby("passo")[["excluidos", "restante"]].sum()
check("fluxo: Σ regiões = Brasil em todos os passos", "", (br[["excluidos", "restante"]] == rg).all().all())
nr = pd.read_csv(L.out_name("tab09_n_final_raca"))
for reg, d in nr.groupby("regiao"):
    t = d[d.raca == "Total"].n.iloc[0]
    s = d[d.raca != "Total"].n.sum()
    f = fx[(fx.regiao == reg)].restante.iloc[-1]
    check(f"{reg}: Σ raças = total = final do fluxograma", f"{s:,}/{t:,}/{f:,}", s == t == f)
pr = pd.read_csv(L.out_name("tab08_ptb_incluidos_excluidos"))
b = pr[pr.regiao == "Brasil"].set_index("grupo")
check("tab08 incluídos+excluídos = fonte", f"{b.n['incluidos'] + b.n['excluidos']:,}",
      b.n["incluidos"] + b.n["excluidos"] == br.restante["0_fonte"])
fe = pd.read_csv(L.out_name("tab12_fenotipo_regiao_ano"))
npt = fe[(fe.regiao == "Brasil") & (fe.ano == "2015-2024")].n.sum()
nptb9 = nr[(nr.regiao == "Brasil") & (nr.raca == "Total")].n_ptb.iloc[0]
check("prematuros 0.6 = n_ptb da amostra (tab09)", f"{npt:,} vs {nptb9:,}", npt == nptb9)
fy = fe[(fe.regiao == "Brasil") & (fe.ano != "2015-2024")].n.sum()
check("prematuros 0.6: Σ anos = 2015-2024", f"{fy:,}", fy == npt)
val = pd.read_csv(L.out_name("tab10_validacao_co"))
check("validação CO: todos os itens batem", f"{int(val.bate.sum())}/{len(val)}", val.bate.all())

pd.DataFrame(chk).to_csv(L.out_name("tab14_auditoria_propria"), index=False)
log(f"auditoria própria: {sum(c['ok'] for c in chk)}/{len(chk)} OK")
