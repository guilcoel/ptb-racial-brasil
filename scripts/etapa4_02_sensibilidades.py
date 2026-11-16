"""
4.2–4.5 Sensibilidades simples da análise 3.2 (mesmo estimador, etapa3_lib.knol via etapa4_lib.roda_32).
  4.2 só gestações únicas (unica = 1): ptb, ptb_esp, ptb_ind
  4.3 sem CE e DF: ptb, ptb_esp, ptb_ind, pig, lbw_termo
  4.4 sem 2024: idem
  4.5 PIG com IG em dias = semanas×7 + 0 e + 6 (pig_k0, pig_k6)
Os tercis de acesso são os da Etapa 3 (cortes calculados na amostra completa), não recalculados na subamostra.
Saídas: tab_e4_02_{conjunto,dentro,interacao,wald}.
"""
import time

import pandas as pd

import etapa4_lib as S4
import etapa0_lib as L

log = S4.logger("02_sensibilidades")
d = S4.carrega()
t0 = time.time()
OUT5 = ["ptb", "ptb_esp", "ptb_ind", "pig", "lbw_termo"]
JOBS = [("4.2_unicas", d[d.unica == 1], ["ptb", "ptb_esp", "ptb_ind"]),
        ("4.3_sem_CE_DF", d[~d.uf.isin(["CE", "DF"])], OUT5),
        ("4.4_sem_2024", d[d.ano != 2024], OUT5),
        ("4.5_pig_k0", d, ["pig_k0"]),
        ("4.5_pig_k6", d, ["pig_k6"])]
res = {k: [] for k in ("conjunto", "dentro", "interacao", "wald")}
for rot, sub, outs in JOBS:
    for desf in outs:
        r = S4.roda_32(sub, desf, rot)
        for k in res:
            res[k].append(r[k])
    log(f"{rot}: n = {len(sub):,}; desfechos {outs} ({(time.time() - t0) / 60:.1f} min)")
for k, v in res.items():
    pd.concat(v).to_csv(L.TAB / f"tab_e4_02_{k}_v1_{L.STAMP}.csv", index=False)
log("4.2–4.5 concluídos")
