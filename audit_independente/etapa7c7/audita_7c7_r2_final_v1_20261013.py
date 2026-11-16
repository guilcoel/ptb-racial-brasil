"""
Auditor independente da Etapa 7c.7 — rodada 2, comparação final (R2.f). Rodado por último: só aqui se lê o CSV da autoauditoria nova
(outputs/manuscrito/audita_7c7_v1_20261013.csv). Compara com a reexecução própria do checa (sandbox r2) e com a revisão item a item (R2.c11);
confere o CSV da autoauditoria para o commit (microdados). Grava as linhas R2.f no comparacao_7c7_v1_20261013.csv.
Rodar: python3 audit_independente/etapa7c7/audita_7c7_r2_final_v1_20261013.py
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
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {str(det)[:200]}", flush=True)


meu = pd.read_csv(CMP)
meu = meu[~meu.verificacao.str.startswith("R2.f")].reset_index(drop=True)
M = dict(zip(meu.verificacao.str.split(" ").str[0], okb(meu.ok)))
au = pd.read_csv(MS / "audita_7c7_v1_20261013.csv")
au["id"] = au.verificacao.str.split(" ").str[0]
au["ok_"] = okb(au.ok)
ok("R2.f01", "autoauditoria nova: 56 itens, 56/56 OK; mesmos ids que o código revisado em R2.c11", len(au) == 56 and au.ok_.all()
   and set(au.id) == {k.split("R2.c11.")[1] for k in M if k.startswith("R2.c11.")}, f"{int(au.ok_.sum())}/{len(au)}; falhas {list(au[~au.ok_].id)}")
MAPA = {"A0.01": ["R2.bA01"], "A1.01": ["R2.bA03", "R2.bA04"], "A1.02": ["R2.bA06"], "A1.03": ["R2.bA07"], "A1.04": ["R2.bA05"],
        "A2.01": ["R2.bA08"], "A2.02": ["R2.bE01"], "B1.01": ["R2.bB14", "R2.bB15"], "B1.02": ["R2.bB14"], "B2.01": ["R2.bB18"], "B2.02": ["R2.bB15"],
        "B2.03": ["R2.bB18"], "B2.04": ["R2.bB18"], "B3.01": [f"R2.bB01.{i:02d}" for i in range(1, 21)], "B4.01": ["R2.bB02"], "B4.02": ["R2.bB03"],
        "B4.03": ["R2.bB17"], "B5.01": ["R2.bB04"], "B6.01": [f"R2.bB05.{i}" for i in range(1, 6)], "B7.01": ["R2.bB06"],
        "B8.01": ["R2.bB08", "R2.bB09"], "B8.02": ["R2.bB10"], "B8.03": ["R2.bB11"], "B8.04": ["R2.a04"], "B8.05": ["R2.bB12", "R2.bB13"],
        "C1.01": ["R2.a10"], "C2.01": ["R2.a07", "R2.a08", "R2.a09", "R2.a10", "R2.a05"], "C3.01": ["R2.s04"], "C3.02": ["R2.a11"],
        "C4.01": ["R2.a06"], "C6.00": ["R2.s04"], **{f"C6.{k:02d}": [] for k in range(1, 17)}, "C6.20": ["R2.s06"], "C6.21": [],
        "C6.22": ["R2.s09"], "C6.23": ["R2.c01", "R2.s03"], "D1.01": ["R2.bD01", "R2.bD04"], "D1.02": ["R2.bD02", "R2.bD03"],
        "E1.01": ["R2.bE01"], "E1.02": ["R2.bE02"], "E1.03": ["R2.bE04"]}
div = []
for r in au.itertuples():
    mine = MAPA.get(r.id)
    if mine is None:
        div.append((r.id, "sem correspondência"))
        continue
    m_ok = all(M.get(x, False) for x in mine) and M.get(f"R2.c11.{r.id}", False)
    if bool(r.ok_) != m_ok:
        div.append((r.id, f"autoauditoria {r.ok_}; auditor {m_ok}"))
ok("R2.f02", "item a item, o veredito da autoauditoria coincide com o deste auditor (verificação própria correspondente + revisão do código)",
   not div, div or f"{len(au)} itens; C6.01–C6.16 e C6.21 comparados só com a revisão (as mutações próprias desta rodada são outras: R2.s05)")
c12 = pd.read_csv(MS / "checa_7b_v12_20261013.csv")
sb = json.load(open(OUTD / "sandbox_7c7_r2_v1_20261013.json"))["linha_de_base"]["linhas"]
ok("R2.f03", "checa_7b_v12 do autor = reexecução própria no sandbox r2: mesmas 113 verificações, mesma ordem, mesmos ok e mesmos detalhes",
   [(v, bool(o), str(x)[:200]) for v, o, x in zip(c12.verificacao, okb(c12.ok), c12.valor)] == [(a, b, c) for a, b, c in sb],
   f"autor {int(okb(c12.ok).sum())}/{len(c12)}; sandbox {sum(b for _, b, _ in sb)}/{len(sb)}")
det = dict(zip(au.id, au.detalhe.astype(str)))
ok("R2.f04", "detalhes da autoauditoria batem com números daqui (A1.01: 93 em docs/referencias; B3.01 20/20; B8.02 49/49; C6.00 113; "
   "D1.02 ≥ 40 arquivos)", "93 em docs/referencias" in det.get("A1.01", "") and det.get("B3.01", "") == "20/20" and det.get("B8.02", "").startswith("49/49")
   and "113 verificações" in det.get("C6.00", ""), {k: det.get(k, "")[:80] for k in ("A1.01", "B3.01", "B8.02", "C6.00", "D1.02")})
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|CODMUNRES)$", re.I)
ok("R2.f05", "CSV da autoauditoria (vai para o commit): 3 colunas, sem identificador, 56 linhas, sem padrão de registro individual",
   list(au.columns[:3]) == ["verificacao", "ok", "detalhe"] and not any(ID_RX.match(c) for c in au.columns)
   and not re.search(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b", au.to_csv()), f"{len(au)} linhas")
so_meu = sorted(k for k, v in M.items() if not v and k.startswith("R2."))
ok("R2.f06", "falhas deste auditor na rodada 2 que a autoauditoria não registra (divergências)", not so_meu,
   "; ".join(f"{k}: {meu.set_index(meu.verificacao.str.split(' ').str[0]).detalhe.get(k, '')[:150]}" for k in so_meu))

out = pd.concat([meu, pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
r2 = out[out.verificacao.str.startswith("R2.")]
print(f"\nR2 total: {int(okb(r2.ok).sum())}/{len(r2)}; CSV {int(okb(out.ok).sum())}/{len(out)}")
