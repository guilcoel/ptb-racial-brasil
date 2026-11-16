"""
0.3 Completude — % ausente (nulo/vazio) e % ignorado por variável, por ano, UF×ano, região×ano.

Código de "ignorado" de cada variável, confirmado na distribuição real (tab00_distribuicao_codigos)
e no dicionário oficial (Estrutura_SINASC_para_CD.pdf):
  RACACORMAE, SEMAGESTAC: não há código de ignorado no dado (só nulo) -> ignorado = 0
  9: GESTACAO, ESCMAE, ESCMAE2010, GRAVIDEZ, PARTO, CONSULTAS, ESTCIVMAE, STTRABPART, STCESPARTO
  99: IDADEMAE, MESPRENAT, QTDFILVIVO
  11: TPROBSON ("nascimento não classificado por ausência de resposta")
  9999: PESO
"""
import pandas as pd

import etapa0_lib as L

log = L.Logger("03_completude")
IGN = {"RACACORMAE": None, "SEMAGESTAC": None, "GESTACAO": 9, "IDADEMAE": 99, "ESCMAE": 9,
       "ESCMAE2010": 9, "GRAVIDEZ": 9, "PARTO": 9, "CONSULTAS": 9, "MESPRENAT": 99,
       "QTDFILVIVO": 99, "ESTCIVMAE": 9, "STTRABPART": 9, "STCESPARTO": 9, "TPROBSON": 11, "PESO": 9999}
VARS = ["CODMUNRES", "DTNASC"] + list(IGN)
DESTAQUE = ["RACACORMAE", "SEMAGESTAC", "ESCMAE", "STTRABPART", "STCESPARTO"]

df = pd.read_parquet(L.BASE_DIR)
df["ano"] = df["ano"].astype(int)
log("base lida", len(df))

flags = {}
for v in VARS:
    flags[f"aus__{v}"] = df[v].isna()
    code = IGN.get(v)
    flags[f"ign__{v}"] = (df[v] == code).fillna(False) if code is not None else pd.Series(False, index=df.index)
F = pd.DataFrame(flags)
F["ano"], F["uf"], F["regiao"] = df["ano"].values, df["uf"].values, df["regiao"].values


def tabula(keys):
    g = F.groupby(keys, observed=True)
    n = g.size().rename("n")
    s = g[[c for c in F.columns if "__" in c]].sum()
    long = []
    for v in VARS:
        t = pd.concat([n, s[f"aus__{v}"].rename("n_ausente"), s[f"ign__{v}"].rename("n_ignorado")], axis=1)
        t.insert(0, "variavel", v)
        long.append(t.reset_index())
    out = pd.concat(long, ignore_index=True)
    out["pct_ausente"] = (100 * out.n_ausente / out.n).round(3)
    out["pct_ignorado"] = (100 * out.n_ignorado / out.n).round(3)
    out["pct_incompleto"] = (out.pct_ausente + out.pct_ignorado).round(3)
    out["codigo_ignorado"] = out.variavel.map(lambda v: "" if IGN.get(v) is None else str(IGN[v]))
    out["destaque"] = out.variavel.isin(DESTAQUE)
    return out


t_ano = tabula(["ano"])
t_ufano = tabula(["uf", "ano"])
t_regano = tabula(["regiao", "ano"])
t_ano.to_csv(L.out_name("tab01_completude_ano"), index=False)
t_ufano.to_csv(L.out_name("tab02_completude_uf_ano"), index=False)
t_regano.to_csv(L.out_name("tab03_completude_regiao_ano"), index=False)
log("tabelas por ano / UF×ano / região×ano gravadas", len(df))

# resumo 2015–2024: média simples das 10 proporções anuais (cada ano pesa igual) por região × variável
res = (t_regano.groupby(["regiao", "variavel"])[["pct_ausente", "pct_ignorado", "pct_incompleto"]]
       .mean().round(2).reset_index())
res.to_csv(L.out_name("tab04_completude_regiao_media_2015_2024"), index=False)
uf_rc = (t_ufano[t_ufano.variavel == "RACACORMAE"].groupby("uf")["pct_incompleto"].mean()
         .round(2).sort_values(ascending=False).reset_index())
uf_rc.columns = ["uf", "pct_racacormae_incompleto_media_2015_2024"]
uf_rc.to_csv(L.out_name("tab05_racacormae_uf_ranking"), index=False)
log("resumos gravados")
