"""
7c.7 Regiões de saúde e municípios por UF na base territorial usada (DATASUS, dez/2024: rl_municip_regsaud.csv, o mesmo arquivo
que o etapa2_02 lê). Contagem descritiva da tabela de referência, sem microdados e sem análise nova: dá base ao segundo motivo da
sensibilidade sem CE/DF ("índice calculado sobre poucas regiões de saúde, grandes"), decisão da Etapa 7c.6b (redação, item 8).
Municípios: códigos que não terminam em 0000. A tabela traz também 530000 (município ignorado do DF) ligado à região 53001, que
conta só como região (a 53001 tem Brasília). As regiões contadas são as do mapa município → região, que é o que o índice usa: a
tb_regsaud.csv da mesma base lista mais regiões, todas ATIVO (CE 25, DF 8), mas 20 do CE e 7 do DF não têm município no mapa.
Saída: outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv (27 UFs + Brasil).
Rodar da raiz: python3 scripts/etapa7c7_01_regsaude_uf.py
"""
import pandas as pd

import etapa0_lib as L

log = L.Logger("7c7_01_regsaude_uf", etapa="etapa7c7")
rl = pd.read_csv(L.PROJ / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv", dtype=str)
assert rl.CO_MUNICIP.is_unique and rl.CO_REGSAUD.notna().all()
rl["cod_uf"] = rl.CO_MUNICIP.str[:2]
ign = rl.CO_MUNICIP.str.endswith("0000")
log(f"códigos UF0000 na tabela: {sorted(rl.CO_MUNICIP[ign])}")
assert (rl.CO_REGSAUD.str[:2] == rl.cod_uf).all()   # toda região de saúde fica dentro de uma UF
uf = (rl.assign(mun=~ign).groupby("cod_uf").agg(n_regioes_saude=("CO_REGSAUD", "nunique"), n_municipios=("mun", "sum")).reset_index()
      .assign(uf=lambda d: d.cod_uf.map(L.UF_SIGLA)))
assert uf.uf.notna().all() and len(uf) == 27
br = pd.DataFrame([dict(cod_uf="", uf="Brasil", n_regioes_saude=rl.CO_REGSAUD.nunique(), n_municipios=int((~ign).sum()))])
out = pd.concat([uf, br], ignore_index=True).assign(municipios_por_regiao=lambda d: (d.n_municipios / d.n_regioes_saude).round(1))
out = out[["cod_uf", "uf", "n_regioes_saude", "n_municipios", "municipios_por_regiao"]]
assert out.n_regioes_saude.iloc[:-1].sum() == out.n_regioes_saude.iloc[-1]
out.to_csv(L.out_name("tab_e7c7_01_regsaude_uf"), index=False)
x = out.set_index("uf")
log(f"regiões de saúde: Brasil {x.n_regioes_saude['Brasil']} ({x.n_municipios['Brasil']:,} municípios); CE {x.n_regioes_saude['CE']} "
    f"({x.n_municipios['CE']} municípios); DF {x.n_regioes_saude['DF']} ({x.n_municipios['DF']} município)")
