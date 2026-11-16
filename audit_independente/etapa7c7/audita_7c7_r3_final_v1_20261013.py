"""
Auditor independente da Etapa 7c.7 — rodada 3, comparação final (R3.f). Rodado por último: só aqui se lê o CSV da autoauditoria nova
(57 itens). Compara com as verificações próprias (R3.d reexecutadas, R3.b) e com a reexecução do checa (sandbox r2); confere o CSV dela
para o commit. Grava as linhas R3.f. Rodar: python3 audit_independente/etapa7c7/audita_7c7_r3_final_v1_20261013.py
"""
import json
import re
from pathlib import Path

import pandas as pd

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
MS = PROJ / "outputs" / "manuscrito"
okb = lambda s: s.astype(str).str.lower().isin(["true", "1"])
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}".replace("|", "¦"), ok=bool(cond), detalhe=str(det).replace("|", "¦")[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {str(det)[:200]}", flush=True)


meu = pd.read_csv(CMP)
meu = meu[~meu.verificacao.str.startswith("R3.f")].reset_index(drop=True)
M = dict(zip(meu.verificacao.str.split(" ").str[0], okb(meu.ok)))
au = pd.read_csv(MS / "audita_7c7_v1_20261013.csv")
au["id"], au["ok_"] = au.verificacao.str.split(" ").str[0], okb(au.ok)
sa = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()
ids_cod = sorted(set(re.findall(r'^\s*ok\(f?"([A-E]\d\.\d\d[a-z]?)"', sa, re.M)) | {f"C6.{k:02d}" for k in range(1, 17)})
ok("R3.f01", "autoauditoria: 57 itens, 57/57 OK, mesmos ids do código revisado (56 da rodada 2 + C6.00a)",
   len(au) == 57 and au.ok_.all() and sorted(au.id) == ids_cod, f"{int(au.ok_.sum())}/{len(au)}; falhas {list(au[~au.ok_].id)}")
det = dict(zip(au.id, au.detalhe.astype(str)))
neg = [i for i in (f"C6.{k:02d}" for k in range(1, 16)) if "o bloco 9g (7c.6) não se mexe" not in au.set_index("id").verificacao[i]]
ok("R3.f02", "C6.00a, C6.01–C6.15 (com o controle negativo no rótulo e na condição) e C6.22 (com o gerador 7c7_01) OK; coerentes com as "
   "sondas e a reprodução deste auditor (R3.b01, R3.c01)", all(au.set_index("id").ok_[i] for i in ["C6.00a", "C6.22"] + [f"C6.{k:02d}" for k in range(1, 17)])
   and not neg and M.get("R3.b01") and M.get("R3.c01"), {k: det.get(k, "")[:90] for k in ("C6.00a", "C6.22")})
c12 = pd.read_csv(MS / "checa_7b_v12_20261013.csv")
sb = json.load(open(OUTD / "sandbox_7c7_r2_v1_20261013.json"))["linha_de_base"]["linhas"]
ok("R3.f03", "checa_7b_v12 continua igual à reexecução própria da rodada 2 (113 verificações, ok e detalhes)",
   [(v, bool(o), str(x)[:200]) for v, o, x in zip(c12.verificacao, okb(c12.ok), c12.valor)] == [(a, b, c) for a, b, c in sb])
MAPA = {"A0.01": ["bA01"], "A1.01": ["bA03", "bA04"], "A1.02": ["bA06"], "A1.03": ["bA07"], "A1.04": ["bA05"], "A2.01": ["bA08"], "A2.02": ["bE01"],
        "B1.01": ["bB14", "bB15"], "B1.02": ["bB14"], "B2.01": ["bB18"], "B2.02": ["bB15"], "B2.03": ["bB18"], "B2.04": ["bB18"],
        "B3.01": [f"bB01.{i:02d}" for i in range(1, 21)], "B4.01": ["bB02"], "B4.02": ["bB03"], "B4.03": ["bB17"], "B5.01": ["bB04"],
        "B6.01": [f"bB05.{i}" for i in range(1, 6)], "B7.01": ["bB06"], "B8.01": ["bB08", "bB09"], "B8.02": ["bB10"], "B8.03": ["bB11"],
        "B8.04": ["a04"], "B8.05": ["bB12", "bB13"], "C1.01": ["a10"], "C2.01": ["a07", "a08", "a09", "a10", "a05"], "C3.01": ["a11"],
        "C3.02": ["a11"], "C4.01": ["a06"], "D1.01": ["bD01", "bD04"], "D1.02": ["bD02", "bD03"], "E1.01": ["bE01"], "E1.02": ["bE02"], "E1.03": ["bE04"]}
EXTRA = {"C6.00a": ["R3.b01", "R3.b04"], "C6.22": ["R3.b06", "R3.c01"], "C6.23": ["R3.d.c01"]}
div = []
for r in au.itertuples():
    mine = [f"R3.d.{x}" for x in MAPA.get(r.id, [])] + EXTRA.get(r.id, [])
    if not mine:
        continue
    m_ok = all(M.get(x, False) for x in mine)
    if bool(r.ok_) != m_ok:
        div.append((r.id, f"autoauditoria {r.ok_}; auditor {m_ok}; {[x for x in mine if not M.get(x, False)]}"))
ok("R3.f04", "item a item, onde há verificação própria correspondente (reexecução da rodada 2 no estado de hoje, sondas, gerador), o veredito "
   "coincide", not div, div or f"{sum(1 for r in au.itertuples() if MAPA.get(r.id) or EXTRA.get(r.id))} itens comparados")
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|CODMUNRES)$", re.I)
ok("R3.f05", "CSV da autoauditoria (vai para o commit): 3 colunas, 57 linhas, sem identificador nem padrão de registro individual",
   list(au.columns[:3]) == ["verificacao", "ok", "detalhe"] and not any(ID_RX.match(c) for c in au.columns)
   and not re.search(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b", au.drop(columns=["id", "ok_"]).to_csv()))
so_meu = sorted(k for k, v in M.items() if not v and k.startswith("R3."))
ok("R3.f06", "falhas deste auditor na rodada 3 que a autoauditoria não registra (síntese; ela não confere o RESUMO)", not so_meu, so_meu)

out = pd.concat([meu, pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
r3 = out[out.verificacao.str.startswith("R3.")]
print(f"\nR3 total: {int(okb(r3.ok).sum())}/{len(r3)}; CSV {int(okb(out.ok).sum())}/{len(out)}")
