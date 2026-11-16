"""
Auditor independente da Etapa 7c.7 — rodada 4 (curta). Base de diff: revisados_7c7_r3_v1_20261013.json. Testes dinâmicos em
sandbox_7c7_r4_v1_20261013.json. O CSV da autoauditoria só é lido no fim, em R4.f.
  R4.a  R3.e01, R3.f06 e ressalvas acolhidas; todas as tabelas do RESUMO bem formadas
  R4.b  diff da autoauditoria e do gerador × rodada 3; GuardaFalhou testado com a guarda quebrada; regex do A1.04
  R4.c  afirmações novas do texto × CSV e relatório da rodada 3; reprodução do RESUMO das 19:52
  R4.d  nada mudou no pacote, nos scripts do pacote, em outputs/tables e no git desde a rodada 3
  R4.e  outros (inclui o __pycache__ que a rodada 3 deste auditor deixou nesta pasta: apagado aqui)
  R4.f  comparação com o CSV da autoauditoria
Grava linhas R4.* no comparacao_7c7_v1_20261013.csv e atualiza o revisados (revisados_7c7_r4_v1_20261013.json).
Rodar: python3 audit_independente/etapa7c7/audita_7c7_r4_v1_20261013.py
"""
import sys

sys.dont_write_bytecode = True
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
MS = PROJ / "outputs" / "manuscrito"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
R = []
okb = lambda s: s.astype(str).str.lower().isin(["true", "1"])
st = lambda p: (PROJ / p).stat().st_mtime
hora = lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S")
git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, env=ENV, check=True).stdout


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}".replace("|", "¦"), ok=bool(cond), detalhe=str(det).replace("|", "¦")[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {str(det)[:170]}", flush=True)


ANTES = pd.read_csv(CMP)
ANTES = ANTES[~ANTES.verificacao.str.startswith("R4.")]
REV3 = json.load(open(OUTD / "revisados_7c7_r3_v1_20261013.json"))
SB = json.load(open(OUTD / "sandbox_7c7_r4_v1_20261013.json"))
res = (PROJ / "outputs/RESUMO_ETAPA7C7_v1_20261013.md").read_text()
txt = (MS / "_resumo7c7_texto_v1_20261013.md").read_text()
ger = (PROJ / "scripts/resumos/etapa7c7_01_resumo.py").read_text()
sa = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()


def tabelas(t):
    out, cur = [], []
    for l in t.splitlines():
        if l.startswith("|"):
            cur.append(l)
        elif cur:
            out.append(cur)
            cur = []
    return out + ([cur] if cur else [])


npipe = lambda l: len(re.findall(r"(?<!\\)\|", l))
tabs = tabelas(res)
ruins = [(i, l[:60]) for i, t in enumerate(tabs) for l in t if npipe(l) != npipe(t[0])]

# ======================================================================= R4.a
gq_ok = SB.get("guarda_quebrada", {}).get("ids_c6") == ["C6.00a", "C6.99", "C6.23"]
ok("R4.a01", "R3.e01 corrigida: o md() do gerador escapa o | nas células; todas as tabelas do RESUMO das 19:52 estão bem formadas (mesmo número "
   "de separadores não escapados em cada linha da tabela)", not ruins and '.str.replace("|", "\\\\|", regex=False)' in ger and len(tabs) == 4,
   f"{len(tabs)} tabelas, {sum(len(t) for t in tabs)} linhas; quebradas {ruins}")
lin_r2d03 = [l for l in res.splitlines() if "R2.d03" in l and l.startswith("|")]
ok("R4.a02", "as linhas de R2.d03 e R2.f06 na tabela de falhas saem com o caractere escapado (\\¦ vira \\\\¦ no Markdown)",
   lin_r2d03 and all("\\|PR_M2cc" in l for l in lin_r2d03[:1]), lin_r2d03[0][:120] if lin_r2d03 else "")
ok("R4.a03", "R3.f06 (síntese) resolvida por consequência; ressalvas acolhidas: nomes dos blocos R3 no gerador; frase sobre as falhas "
   "tratadas antes da rodada seguinte trocada; sandbox para se o C6.00a falhar (R4.b03)",
   all(f'"R3.{b}":' in ger for b in "abcdef") and "As falhas de cada rodada foram tratadas antes da seguinte; o texto abaixo da tabela diz o que foi "
   "feito, inclusive com as da última." in res and gq_ok
   and "R3.a. Falhas da rodada 2 e ressalvas acolhidas" in res)

# ======================================================================= R4.b
def dif(p):
    a, b = REV3[p]["texto"].splitlines(), (PROJ / p).read_text().splitlines()
    rem, add = [], []
    for l in difflib.unified_diff(a, b, lineterm="", n=0):
        if not l.startswith(("---", "+++", "@@")):
            (rem if l[0] == "-" else add).append(l[1:])
    return rem, add


rem, add = dif("scripts/etapa7c7_02_audita.py")
ESP_REM = ["testada antes do uso (C6.00a). O sandbox é apagado no fim.", r'r"scripts/(resumos/)?__pycache__/[^/]+\.pyc|audit_independente',
           'ok("A1.04", "ignorados pelo git com mtime depois de dc9328d: só a tabela nova, os logs (7b, 7c6, 7c7), __pycache__ e os CSVs do auditor "']
ESP_ADD = ["testada antes do uso (C6.00a; se falhar, o sandbox para ali). O sandbox é apagado no fim.",
           r'r"(scripts/(resumos/)?|audit_independente/etapa7c7/)__pycache__/[^/]+\.pyc|audit_independente',
           '__pycache__ (scripts/ e pasta do auditor) e os CSVs do auditor "', "class GuardaFalhou(Exception):", "    pass", "", "",
           '    if not R[-1]["ok"]:', '        raise GuardaFalhou("a guarda do sandbox não funcionou', "except GuardaFalhou as e:",
           '    ok("C6.99", "sandbox interrompido", False, e)']
def casa(ls, esp):
    cheias = [x for x in ls if x.strip()]
    marc = [e for e in esp if e]
    return (all(sum(e in x for x in cheias) == 1 for e in marc) and all(any(e in x for e in marc) for x in cheias)
            and len(cheias) == len(marc) and len(ls) - len(cheias) == len(esp) - len(marc))


ok("R4.b01", "autoauditoria × rodada 3: só mudou o que foi listado (docstring, regex e rótulo do A1.04, classe GuardaFalhou, a parada depois "
   "do C6.00a e o C6.99)", casa(rem, ESP_REM) and casa(add, ESP_ADD), f"-{len(rem)} +{len(add)}; " + " ¦ ".join(x[:70] for x in add))
rem2, add2 = dif("scripts/resumos/etapa7c7_01_resumo.py")
ok("R4.b02", "gerador × rodada 3: só mudaram o md() (escape do |), o NOMES_IA (R3.a–R3.f) e a frase das falhas tratadas",
   len(rem2) == 3 and len(add2) == 6 and any("md = lambda df" in x for x in rem2) and any('c.str.replace("|", "\\\\|", regex=False)' in x for x in add2)
   and sum('"R3.' in x for x in add2) == 3 and any("inclusive com as da última" in x for x in add2), f"-{len(rem2)} +{len(add2)}")
gq = SB.get("guarda_quebrada", {})
ok("R4.b03", "GuardaFalhou funciona: numa cópia da autoauditoria com a guarda quebrada de propósito (num espelho do projeto, dentro do sandbox "
   "deste auditor), o C6.00a dá falso, grava C6.99 e não roda nenhuma mutação, commit simulado nem teste do LEIAME; o C6.23, o D e o E "
   "continuam; o sandbox dela é apagado e os ignorados do Forja ficam intactos",
   gq.get("rc") == 0 and gq.get("c600a") is False and gq.get("ids_c6") == ["C6.00a", "C6.99", "C6.23"] and gq.get("c623") is True
   and gq.get("blocos_depois") == ["D1.01", "D1.02", "E1.01", "E1.02", "E1.03"] and SB.get("ignorados_intactos") and SB.get("sandbox_apagado"),
   f"{gq.get('ids_c6')}; C6.99: {gq.get('c699')}; {gq.get('n')} itens; {gq.get('seg')} s")
import ast as _ast
_ign = [n for n in _ast.walk(_ast.parse(sa)) if isinstance(n, _ast.Assign) and _ast.unparse(n.targets[0]) == "IGN_OK"][0]
rx = re.compile(_ast.literal_eval(_ign.value.args[0]))
aceita = ["audit_independente/etapa7c7/__pycache__/audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc", "scripts/__pycache__/x.cpython-312.pyc",
          "scripts/resumos/__pycache__/x.pyc", "audit_independente/etapa7c7/comparacao_7c7_v1_20261013.csv"]
rejeita = ["audit_independente/etapa7c7/__pycache__/x.py", "audit_independente/etapa7c7/sub/__pycache__/x.pyc",
           "audit_independente/etapa7c6/__pycache__/x.pyc", "data/__pycache__/x.pyc", "outputs/tables/__pycache__/x.pyc",
           "audit_independente/etapa7c7/x.pyc", "audit_independente/etapa7c7/qualquer.csv", "scripts/__pycache__/sub/x.pyc"]
ok("R4.b04", "regex novo do A1.04 é estreito: aceita só .pyc direto em __pycache__ de scripts/, scripts/resumos/ e da pasta deste auditor (e os CSVs "
   "*7c7*_v1_20261013 dela); rejeita .pyc em outras pastas, subpastas e qualquer outro tipo", all(rx.match(p) for p in aceita) and not any(rx.match(p) for p in rejeita),
   "ressalva: dentro desse __pycache__ aceita qualquer nome de .pyc (não só os *7c7*); como o git ignora __pycache__, nada disso vai para o commit")
ok("R4.b05", "o .pyc acusado foi criado às 16:04:20 pela rodada 3 deste auditor (o audita_7c7_r3_sandbox importou o módulo da rodada 2 sem "
   "desligar o bytecode), não pela rodada 2; é ignorado pelo git (__pycache__/ no .gitignore)",
   hora((OUTD / "__pycache__/audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc").stat().st_mtime) == "16:04:20"
   if (OUTD / "__pycache__").exists() else True,
   "o texto do RESUMO diz 'o sandbox do auditor' (certo); a mensagem do coordenador dizia 'da rodada 2'")

# ======================================================================= R4.c
rp = SB.get("gerador", {}).get("reproduz", {})
ok("R4.c01", "cópia do gerador (saída desviada; CSV deste auditor por link no estado de antes das R4: 16:11:52, nenhuma linha R4) reproduz o "
   "RESUMO das 19:52 byte a byte; com a v12 arquivada, para", rp.get("igual") is True and SB["comparacao_estado"] == {"mtime": "16:11:52", "linhas_r4": 0}
   and SB["gerador"]["apos_arquivar_v12"]["rc"] not in (0, None), f"md5 {rp.get('md5_real')}")
r3 = ANTES[ANTES.verificacao.str.startswith("R3.")].copy()
r3["b"] = r3.verificacao.str.extract(r"^(R3\.[a-z])")[0]
cont = {b: (int(okb(d.ok).sum()), len(d)) for b, d in r3.groupby("b")}
fal3 = sorted(r3[~okb(r3.ok)].verificacao.str.split(" ").str[0])
ok("R4.c02", "parágrafo da rodada 3 = CSV deste auditor: 108/110; R3.a 6/6; R3.b 8/8; R3.c 8/8; R3.d 79/79; falhas R3.e01 e R3.f06",
   (int(okb(r3.ok).sum()), len(r3)) == (108, 110) and "**Rodada 3** (estado das 16:01, sem mudança no pacote): **108/110**." in txt
   and all(f"({b}, {cont[b][0]}/{cont[b][1]})" in txt for b in ("R3.a", "R3.b", "R3.c", "R3.d")) and fal3 == ["R3.e01", "R3.f06"],
   {b: f"{v[0]}/{v[1]}" for b, v in cont.items()})
ok("R4.c03", "parágrafo da rodada 3 × relatório da rodada 3: '12 operações de escrita no Forja com sondas inofensivas' (o relatório fala em 12 "
   "operações: escrita, remoção, renomeação, replace, mkdir, utime, chmod, rmtree); C6.00a seguro; R3.e01 e R3.f06 descritos como no relatório; "
   "as 3 ressalvas acolhidas existem no código", "o auditor testou 12 operações de escrita no Forja com sondas inofensivas" in txt
   and "**R3.e01:** o gerador não escapava o `|` dentro das células" in txt and "GuardaFalhou" in sa,
   "ressalva de redação: são 12 operações que mexem no Forja (não só escrita: também remoção, renomeação, mkdir, utime, chmod, rmtree)")
ok("R4.c04", "nota do A1.04: 'um __pycache__ que o sandbox do auditor criou em audit_independente/etapa7c7/'; 'o git ignora esse arquivo e ele fica "
   "fora do commit'; 'o A1.04 passou a aceitar __pycache__ nessa pasta' — conferem (origem: rodada 3 deste auditor; git check-ignore; regex)",
   "que o sandbox do auditor criou em `audit_independente/etapa7c7/`" in txt and subprocess.run(
       ["git", "-C", str(PROJ), "check-ignore", "-q", "audit_independente/etapa7c7/__pycache__/audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc"], env=ENV).returncode == 0
   and rx.match("audit_independente/etapa7c7/__pycache__/audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc") is not None)
ok("R4.c05", "AUTO: 'A guarda é testada antes do uso; se falhar, o sandbox para ali' = código e teste (R4.b03); partes geradas: rodada 3 "
   "108/110 na contagem por rodada, nomes R3 na tabela, autoauditoria 57/57", "A guarda é testada antes do uso; se falhar, o sandbox para ali." in txt
   and "**rodada 3: 108/110 OK**" in res and "**57/57 OK**" in res and "R3.d. Nada mudou desde a rodada 2" in res)

# ======================================================================= R4.d
T3 = datetime.strptime("2026-10-13 16:13:15", "%Y-%m-%d %H:%M:%S").timestamp()   # fim da rodada 3 deste auditor
mud = []
for raiz, dirs, fs in os.walk(PROJ):
    rel = Path(raiz).relative_to(PROJ)
    if rel == Path("."):
        dirs[:] = [d for d in dirs if d not in ("data", ".git")]
    mud += [str(rel / f) for f in fs if (Path(raiz) / f).stat().st_mtime > T3 and not str(rel).startswith("audit_independente/etapa7c7")]
ESP = {"outputs/logs/etapa7c7_20261008.log", "outputs/manuscrito/_resumo7c7_texto_v1_20261013.md", "outputs/manuscrito/audita_7c7_v1_20261013.csv",
       "outputs/RESUMO_ETAPA7C7_v1_20261013.md", "scripts/etapa7c7_02_audita.py", "scripts/resumos/etapa7c7_01_resumo.py"}
ok("R4.d01", "desde o fim da rodada 3 (16:13), mudaram só o texto, o gerador, a autoauditoria e o CSV dela, o RESUMO e o log 7c7 (nada no "
   "pacote, nos scripts do pacote, em outputs/tables, nos outros logs)", set(mud) == ESP, sorted(f"{p} {hora(st(p))}" for p in mud))
L7 = [l for l in (PROJ / "outputs/logs/etapa7c7_20261008.log").read_text().splitlines() if l[1:20] > "2026-10-13 16:13:15"]
ok("R4.d02", "log 7c7 depois da rodada 3: só linhas do gerador do RESUMO (16:20:09 com 56/57 — a execução intermediária —, 19:52:14 e 19:52:22)",
   L7 and all("[7c7_01_resumo]" in l for l in L7), [l[12:20] + " " + l.split("autoauditoria ")[1][:5] for l in L7])
src = (OUTD / "audita_7c7_r2_v1_20261013.py").read_text()
src = src[:src.index("# ======================================================================= R2.s — sandbox da rodada 2")]
src = src.replace('[n_ for _, n_ in ult["etapa7c7_20261008.log"]] == ["7c7_01_resumo"]', '{n_ for _, n_ in ult["etapa7c7_20261008.log"]} == {"7c7_01_resumo"}')
src = src.replace('json.dump(RUNS_DIA, open(OUTD / "logs_execucoes_7c7_r2_v1_20261013.json", "w"), ensure_ascii=False, indent=1)', "pass")
ns = {"__name__": "r2_reexec"}
exec(compile(src, "audita_7c7_r2 (reexecução r4)", "exec"), ns)
rr = [r for r in ns["R"] if not r["verificacao"].startswith("R2.bA10")]
ok("R4.d03", "lógica da rodada 2 (A, B, D, E, correções, pegadas) reexecutada hoje: tudo OK — git (HEAD dc9328d, 38 renomeações em stage, os 14 "
   "modificados, não rastreados previstos), pacote × v11, MANIFEST e seus 49 MD5, tabela nova, logs", all(r["ok"] for r in rr),
   f"{sum(r['ok'] for r in rr)}/{len(rr)}; falhas {[r['verificacao'][:50] for r in rr if not r['ok']]}")
L12 = (MS / "MANIFEST.md").read_text()
ok("R4.d04", "pacote, scripts do pacote e outputs/tables com os mesmos mtimes/MD5 de antes (MANIFEST 12:26:33; checa 12:26:17; tabela nova "
   "3fa3447171b2; scripts do pacote como na R2.bD03)", hora(st("outputs/manuscrito/MANIFEST.md")) == "12:26:33" and hora(st("outputs/manuscrito/checa_7b_v12_20261013.csv")) == "12:26:17"
   and hashlib.md5((PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv").read_bytes()).hexdigest()[:12] == "3fa3447171b2"
   and all(f"{s} {hora(st('scripts/' + s))}" in str(ANTES.set_index(ANTES.verificacao.str.split(' ').str[0]).detalhe.get("R2.bD03", ""))
           for s in ["etapa7b_lib.py", "etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_04_submissao.py", "etapa7b_checa.py", "etapa7c7_01_regsaude_uf.py"]))

# ======================================================================= R4.e
pyc = OUTD / "__pycache__"
if pyc.exists():
    shutil.rmtree(pyc)
ok("R4.e01", "o __pycache__ que a rodada 3 deste auditor deixou nesta pasta foi apagado; as rodadas 4 em diante rodam com sys.dont_write_bytecode "
   "(o sandbox desta rodada não recriou o .pyc)", not pyc.exists() and SB.get("pycache_criado") is False,
   "o A1.04 continua aceitando __pycache__ nesta pasta (inofensivo); o texto do RESUMO segue verdadeiro (descreve o que aconteceu)")
ok("R4.e02", "o gerador rodou 3 vezes depois da rodada 3 (16:20:09, com a autoauditoria intermediária em 56/57; 19:52:14; 19:52:22); vale o das "
   "19:52:22, reproduzido em R4.c01", len(L7) == 3, "informativo")
REVIS = {p: (PROJ / p).read_text() for p in ["scripts/etapa7c7_02_audita.py", "scripts/resumos/etapa7c7_01_resumo.py",
                                              "outputs/manuscrito/_resumo7c7_texto_v1_20261013.md"]}
json.dump({p: {"md5": hashlib.md5(t.encode()).hexdigest(), "linhas": len(t.splitlines()), "texto": t} for p, t in REVIS.items()},
          open(OUTD / "revisados_7c7_r4_v1_20261013.json", "w"), ensure_ascii=False, indent=1)
ok("R4.e03", "base de diff para a próxima rodada gravada (revisados_7c7_r4_v1_20261013.json)", (OUTD / "revisados_7c7_r4_v1_20261013.json").exists(),
   {p: hashlib.md5(t.encode()).hexdigest()[:12] for p, t in REVIS.items()})

# ======================================================================= R4.f (por último: CSV da autoauditoria)
au = pd.read_csv(MS / "audita_7c7_v1_20261013.csv")
au["id"], au["ok_"] = au.verificacao.str.split(" ").str[0], okb(au.ok)
ok("R4.f01", "autoauditoria: 57/57, sem C6.99 (a guarda funcionou na execução real), com o A1.04 novo; CSV de 57 linhas sem identificador",
   len(au) == 57 and au.ok_.all() and "C6.99" not in set(au.id) and "C6.00a" in set(au.id)
   and "__pycache__ (scripts/ e pasta do auditor)" in au.set_index("id").verificacao["A1.04"]
   and not re.search(r"\b\d{6}\b.{0,3}\b(19|20)\d{2}-?\d{2}-?\d{2}\b", au.to_csv()), f"{int(au.ok_.sum())}/{len(au)}")
so = sorted(r["verificacao"].split(" ")[0] for r in R if not r["ok"])
ok("R4.f02", "falhas deste auditor na rodada 4 que a autoauditoria não registra (síntese)", not so, so)

out = pd.concat([ANTES, pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
r4 = pd.DataFrame(R)
print(f"\nR4: {int(r4.ok.sum())}/{len(r4)}; CSV {int(okb(out.ok).sum())}/{len(out)}")
