"""
0.5 Validação contra o artigo publicado (Rev Saude Publica 2026;60:e44) — Centro-Oeste (MS, MT, GO, DF).

Reaplica a mesma cascata (etapa0_lib.cascade_flags) ao recorte CO da base nacional e compara
com os números publicados. Saída: tab10_validacao_co (valor obtido, publicado, diferença).
"""
import pandas as pd

import etapa0_lib as L

log = L.Logger("05_validacao_co")
PUB = {"fonte": 2338990, "amostra": 2156674,
       "n_Branca": 610353, "n_Parda": 1392713, "n_Preta": 115766, "n_Indigena": 37842,
       "ptb_Branca": 11.1, "ptb_Parda": 11.0, "ptb_Preta": 11.7, "ptb_Indigena": 17.6}
# passos intermediários do log da RSP (outputs/centro_oeste/logs/build_baseB_20260627.log)
LOG_RSP = {"1_raca": 2179783, "2_ig": 2166187, "3_esc": 2156705, "4_idade": 2156674}

df = pd.read_parquet(L.BASE_DIR, columns=["RACACORMAE", "SEMAGESTAC", "ESCMAE", "IDADEMAE", "uf", "regiao"],
                     filters=[("regiao", "==", "CO")])
assert set(df.uf.unique()) == {"MS", "MT", "GO", "DF"}
log("CO lido", len(df))
ok = L.cascade_flags(df)
inc = df[ok.incluido.values].copy()
inc["raca"] = inc.RACACORMAE.map(L.RACA_LABEL)
inc["ptb"] = (inc.SEMAGESTAC < 37)

got = {"fonte": len(df), "amostra": len(inc)}
for g in L.RACA_ORDER:
    s = inc[inc.raca == g]
    got[f"n_{g}"] = len(s)
    got[f"ptb_{g}"] = 100 * s.ptb.mean()
rows = []
for k, pub in PUB.items():
    v = got[k]
    if k.startswith("ptb"):
        rows.append(dict(item=k, obtido=round(v, 4), obtido_1casa=round(v, 1), publicado=pub,
                         diferenca=round(round(v, 1) - pub, 1), bate=round(v, 1) == pub))
    else:
        rows.append(dict(item=k, obtido=v, obtido_1casa="", publicado=pub, diferenca=v - pub, bate=v == pub))
n = len(df)
for k, desc in L.CASCADE:
    n -= int((ok.etapa_exclusao == k).sum())
    rows.append(dict(item=f"cascata_{k}", obtido=n, obtido_1casa="", publicado=LOG_RSP[k],
                     diferenca=n - LOG_RSP[k], bate=n == LOG_RSP[k]))
t = pd.DataFrame(rows)
t.to_csv(L.out_name("tab10_validacao_co"), index=False)
for r in rows:
    log(f"{r['item']}: obtido={r['obtido']} publicado={r['publicado']} bate={r['bate']}")
log(f"TUDO BATE = {bool(t.bate.all())}")
