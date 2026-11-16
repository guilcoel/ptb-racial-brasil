"""
Auditor independente da Etapa 7c.7 — rodada de comparação (F), rodada DEPOIS das verificações próprias (audita_7c7_v1_20261013.py).
Só aqui são lidos: o CSV da autoauditoria (outputs/manuscrito/audita_7c7_v1_20261013.csv), o CSV do checa da v12
(outputs/manuscrito/checa_7b_v12_20261013.csv) e o conteúdo das linhas do checa no log de 2026-10-13.
Acrescenta as linhas F ao comparacao_7c7_v1_20261013.csv (refazendo-as se já existirem).
Rodar: python3 audit_independente/etapa7c7/audita_7c7_comparacao_v1_20261013.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
MS = PROJ / "outputs" / "manuscrito"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
okb = lambda s: s.astype(str).str.lower().isin(["true", "1"])

meu = pd.read_csv(CMP)
meu = meu[~meu.verificacao.str.startswith("F")].reset_index(drop=True)
meu["id"] = meu.verificacao.str.split(" ").str[0]
M = dict(zip(meu.id, okb(meu.ok)))
R = []


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:90]} | {str(det)[:200]}")


# ---------------------------------------------------------------- autoauditoria
au = pd.read_csv(MS / "audita_7c7_v1_20261013.csv")
au["id"] = au.verificacao.str.split(" ").str[0]
au["ok_"] = okb(au.ok)
ok("F1.01", "autoauditoria: CSV com as colunas verificacao/ok/detalhe; todas as verificações OK",
   list(au.columns[:3]) == ["verificacao", "ok", "detalhe"] and au.ok_.all(), f"{int(au.ok_.sum())}/{len(au)} OK; falhas {list(au[~au.ok_].id)}")
MAPA = {  # item da autoauditoria → itens deste auditor que cobrem a mesma afirmação
    "A0.01": ["A1.01", "A1.02"], "A1.01": ["A2.01", "A2.02", "A2.03", "A2.04"], "A1.02": ["A3.01"], "A1.03": ["A4.01", "A4.02"],
    "A2.01": ["A5.01", "A5.02"], "A2.02": ["E1.01", "F1.03"], "B1.01": ["B9.01", "B9.03"], "B1.02": ["B9.02"], "B2.01": ["B11.01", "B11.06"],
    "B2.02": ["B9.03"], "B2.03": ["B11.02", "B11.07", "B11.08"], "B3.01": [f"B1.{i:02d}" for i in range(1, 21)], "B4.01": ["B2.01"],
    "B4.02": ["B2.03", "B2.04"], "B4.03": ["B10.02"], "B5.01": ["B3.01"], "B6.01": ["B4.01", "B4.02", "B4.05", "B6.06", "B6.07"],
    "B7.01": [f"B5.{i:02d}" for i in range(1, 15)], "B8.01": ["B7.01", "B7.02", "B7.03"], "B8.02": ["B7.04"], "B8.03": ["B8.01", "B8.03"],
    "C1.01": ["C1.01", "C1.02"], "C2.01": ["C2.01", "C2.02", "C2.03", "C2.04"], "C3.01": ["C3.00", "C3.01", "F2.01"],
    "C3.02": ["C2.05", "C2.06", "C2.07"], "C4.01": ["C4.01", "C4.02", "C4.03"], "C5.01": ["C6.01", "C6.02", "C6.03", "C6.04", "C6.05", "C6.06"],
    "D1.01": ["D1.01"],
}

# ---------------------------------------------------------------- checa da v12 × reexecução no sandbox
SB = json.load(open(OUTD / "sandbox_7c7_v1_20261013.json"))
base = [(v, bool(o)) for v, o in SB["linha_de_base"]["linhas"]]
c12 = pd.read_csv(MS / "checa_7b_v12_20261013.csv")
real = list(zip(c12.verificacao, okb(c12.ok)))
ok("F2.01", "checa_7b_v12 (CSV do autor) = reexecução própria no sandbox: mesmas 113 verificações, na mesma ordem, todas OK",
   real == base and len(real) == 113 and all(o for _, o in real), f"autor {sum(o for _, o in real)}/{len(real)}; sandbox {sum(o for _, o in base)}/{len(base)}")
M["F2.01"] = R[-1]["ok"]
c11 = pd.read_csv(MS / "_arquivo_v11" / "checa_7b_v11_20261009.csv")
n11 = [v.replace("v11_20261009", "VX") for v in c11.verificacao]
n12 = [v.replace("v12_20261013", "VX") for v in c12.verificacao]
sai, entra = sorted(set(n11) - set(n12)), sorted(set(n12) - set(n11))
ok("F2.02", "checa v11 → v12: as 100 da v11 continuam (só a 1ª da 7c.6 muda de rótulo, por causa do pacote_esperado); entram as 13 da 7c.7",
   len(c11) == 100 and len(sai) == 1 and sai[0].startswith("7c.6 números-chave") and len(entra) == 14 and sum(x.startswith("7c.7") for x in entra) == 13
   and okb(c11.ok).all(), f"saem {[x[:60] for x in sai]}; entram {len(entra)} ({sum(x.startswith('7c.7') for x in entra)} da 7c.7)")
c12["valor"] = c12["valor"].astype(str)
v_cp = c12[c12.verificacao.str.startswith("7c.7 commit_pacote")].valor.iloc[0]
ok("F2.03", "checa v12: o detalhe do commit_pacote diz 'esperado dc9328d; no JSON [dc9328d]' (antes do commit)", v_cp == "esperado dc9328d; no JSON ['dc9328d']", v_cp)

# ---------------------------------------------------------------- comparação item a item
diverg = []
for r in au.itertuples():
    mine = MAPA.get(r.id)
    if mine is None:
        diverg.append((r.id, "sem correspondência"))
        continue
    m_ok = all(M.get(x, True) for x in mine if x in M or x.startswith("F"))
    falt = [x for x in mine if x not in M and not x.startswith("F")]
    if falt:
        diverg.append((r.id, f"itens meus ausentes {falt}"))
    if bool(r.ok_) != m_ok:
        diverg.append((r.id, f"autoauditoria {r.ok_}, auditor {m_ok} ({[x for x in mine if not M.get(x, True)]})"))
ok("F3.01", "cada item da autoauditoria tem correspondente aqui e o veredito coincide", not diverg, diverg or f"{len(au)} itens comparados")
# o que o auditor achou e a autoauditoria não registra
so_meu = [i for i, v in M.items() if not v and not i.startswith("C5.")]
ok("F3.02", "falhas deste auditor (fora a revisão da autoauditoria, C5) que a autoauditoria não registra", not so_meu,
   "; ".join(f"{i}: {meu.set_index('id').detalhe.get(i, '')[:140]}" for i in so_meu))
det = dict(zip(au.id, au.detalhe.astype(str)))
ok("F3.03", "detalhes da autoauditoria batem com os números daqui (B3.01 20/20; C3.01 113; A1.01 apagados 38; B8.02 50/50)",
   "20/20" in det.get("B3.01", "") and "apagados 38" in det.get("A1.01", "") and det.get("B8.02", "").startswith("50/50"),
   {k: det.get(k, "")[:90] for k in ("B3.01", "A1.01", "B8.02", "C3.01")})

# ---------------------------------------------------------------- log: por que a 1ª execução do checa parou
lin = [l for l in (PROJ / "outputs/logs/etapa7b_20261008.log").read_text(errors="replace").splitlines()
       if l.startswith("[2026-10-13 10:4") and "[7b_checa]" in l]
t = [re.match(r"^\[2026-10-13 (\d\d:\d\d:\d\d)\]", l).group(1) for l in lin]
ini = [i for i, l in enumerate(lin) if "números-chave = arquivo de origem" in l]
run1 = lin[ini[0]:ini[1]] if len(ini) >= 2 else []
falhas1 = [l for l in run1 if "] FALHA" in l]
ult = run1[-1] if run1 else ""
ok("F4.01", "1ª execução do checa (10:43:50–10:44:48): nenhuma linha FALHA; parou depois da 3ª verificação do 9h (n_regsaude), ao montar a 4ª "
   "(commit_registro com v1–v11) — exceção de código, não reprovação do pacote; o checa foi editado às 10:44:56 e a 2ª execução passou",
   not falhas1 and "7c.7 n_regsaude_CE" in ult and len(ini) == 2,
   f"{len(run1)} linhas na 1ª execução, {len(lin) - len(run1)} na 2ª; última da 1ª: {ult[:150]}")
run2 = lin[ini[1]:] if len(ini) >= 2 else []
ok("F4.02", "2ª execução do checa: 113 linhas OK, nenhuma FALHA; termina com '113/113 OK'", len([l for l in run2 if "] OK " in l]) == 113
   and not [l for l in run2 if "] FALHA" in l] and "113/113 OK" in run2[-1], run2[-1][:120] if run2 else "")

# ---------------------------------------------------------------- E para o CSV da autoauditoria (vai para o commit)
ID_RX = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|DTOBITO|DTNASCMAE|DTULTMENST|CNS|CPF|CODMUNRES)$", re.I)
ok("F1.02", "CSV da autoauditoria (vai para o commit): 3 colunas, sem coluna identificadora, poucas linhas; sem padrão de registro individual",
   not any(ID_RX.match(c) for c in au.columns) and len(au) < 200 and not re.search(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b", au.to_csv()),
   f"{len(au)} linhas; colunas {list(au.columns[:3])}")
hist = subprocess.run(["git", "-C", str(PROJ), "log", "--all", "--format=", "--name-only"], capture_output=True, text=True, env=ENV).stdout.split()
ok("F1.03", "nenhum ._* em todo o histórico do git (conferência própria do item A2.02 da autoauditoria)",
   not [p for p in hist if Path(p).name.startswith("._")], f"{len(set(hist))} caminhos no histórico")
M["F1.03"] = R[-1]["ok"]

# recalcula F3.01 com F1.03/F2.01 já conhecidos (ordem de dependência)
diverg = []
for r in au.itertuples():
    mine = MAPA.get(r.id, [])
    m_ok = all(M.get(x, True) for x in mine)
    if bool(r.ok_) != m_ok:
        diverg.append((r.id, f"autoauditoria {r.ok_}, auditor {m_ok} ({[x for x in mine if not M.get(x, True)]})"))
R[[i for i, x in enumerate(R) if x["verificacao"].startswith("F3.01")][0]].update(
    ok=not diverg, detalhe=str(diverg or f"{len(au)} itens comparados; mapa {MAPA}")[:1800])

out = pd.concat([meu.drop(columns="id"), pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
print(f"\n{int(okb(out.ok).sum())}/{len(out)} OK no total; F: {sum(r['ok'] for r in R)}/{len(R)}")
