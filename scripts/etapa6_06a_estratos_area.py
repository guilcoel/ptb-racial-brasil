"""
6.6 (dados) MAIHDA do PIG com nível de área: células estrato (540, definição da Etapa 5) × região de saúde de residência.
Mesma amostra da Etapa 5 (PIG elegível com tercil; 25,028,320). Saída: data/processed/maihda_estratos_regsaude_v1 (agregado).
"""
import pandas as pd

import etapa3_lib as T
import etapa6_lib as E6
import etapa0_lib as L

log = E6.logger("06a_estratos_area")
d = T.anexa_acesso(T.load(["raca", "idade_cat", "esc_cat", "regiao", "CO_REGSAUD", "pig"]))
d = d[d.pig.notna() & d.tercil_reg.notna()].copy()
ESC = {"1_nenhuma": "le7", "2_1a3anos": "le7", "3_4a7anos": "le7", "4_8a11anos": "8a11", "5_12mais": "ge12"}
IDA = {"<20": "lt20", "20-34": "20a34", ">=35": "ge35"}
d["estrato"] = (d.raca.astype(str) + "|" + d.esc_cat.astype(str).map(ESC) + "|" + d.idade_cat.astype(str).map(IDA) + "|" +
                d.regiao.astype(str) + "|" + d.tercil_reg.astype(str))
a = d.groupby(["estrato", "CO_REGSAUD"], observed=True).pig.agg(n="size", casos="sum").reset_index()
a[["raca", "esc3", "idade3", "regiao", "tercil"]] = a.estrato.str.split("|", expand=True)
e5 = pd.read_csv(L.PROC / f"maihda_estratos_v1_{L.STAMP}.csv")
chk = a.groupby("estrato")[["n", "casos"]].sum().reindex(e5.estrato)
assert len(d) == 25028320 and (chk.n.to_numpy() == e5.n.to_numpy()).all() and (chk.casos.to_numpy() == e5.casos.to_numpy()).all()
a.to_csv(L.PROC / f"maihda_estratos_regsaude_v1_{L.STAMP}.csv", index=False)
log(f"células estrato × região de saúde: {len(a):,}; estratos {a.estrato.nunique()}; regiões {a.CO_REGSAUD.nunique()}; "
    f"N {int(a.n.sum()):,}; casos {int(a.casos.sum()):,}; Σ por estrato = Etapa 5")
