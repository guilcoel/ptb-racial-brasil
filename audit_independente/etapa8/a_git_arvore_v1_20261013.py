"""Bloco A — git e árvore (somente leitura; GIT_OPTIONAL_LOCKS=0)."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import os
import re
import subprocess
from datetime import datetime

from comum_v1_20261013 import PROJ, HEAD, V12, V13, Res, blob_sha

os.environ["GIT_OPTIONAL_LOCKS"] = "0"
R = Res("A")
git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, check=True).stdout
T0 = datetime(2026, 10, 13, 21, 26, 33).timestamp()

# A1 HEAD, refs, stash, tags, remoto
head = git("rev-parse", "HEAD").strip()
refs = git("for-each-ref", "--format=%(refname) %(objectname)").split("\n")
R.ok("A1.01 HEAD = dc54fb9 e branch main", head == HEAD and git("branch", "--show-current").strip() == "main", head[:7])
R.ok("A1.02 sem stash, sem remoto; tags e refs sem nada posterior a dc54fb9",
     git("stash", "list").strip() == "" and git("remote").strip() == ""
     and all(HEAD in l or "refs/tags" in l for l in refs if l), f"refs: {[l.split()[0] for l in refs if l]}")
tags = git("tag", "--points-at", "HEAD").split()
R.ok("A1.03 nenhuma tag em HEAD (a tag é decisão posterior)", not tags, tags)

# A2 o que mudou
st = git("status", "--porcelain=v1", "-uall", "--ignored", "-z").split("\0")
ents, i = [], 0
while i < len(st):
    e = st[i]
    if not e:
        i += 1
        continue
    xy, p = e[:2], e[3:]
    if xy[0] == "R":
        ents.append((xy, p, st[i + 1]))
        i += 2
    else:
        ents.append((xy, p, None))
        i += 1
mod = sorted(p for xy, p, _ in ents if xy.strip() == "M")
ren = sorted((o, p) for xy, p, o in ents if xy[0] == "R")
unt = sorted(p for xy, p, _ in ents if xy == "??")
ign = sorted(p for xy, p, _ in ents if xy == "!!")
outros = [(xy, p) for xy, p, _ in ents if xy.strip() not in ("M", "??", "!!") and xy[0] != "R"]
MOD_ESP = sorted(["Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf",
                  "outputs/manuscrito/MANIFEST.md", "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md",
                  "scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py",
                  "scripts/etapa7b_checa.py", "scripts/etapa7b_lib.py", "scripts/resumos/LEIAME.md"])
R.ok("A2.01 rastreados modificados = exatamente os 13 previstos (Submissao ESM_1–4, MANIFEST, disponibilidade, legendas, lib/01/02/04/checa, LEIAME)",
     mod == MOD_ESP, f"{len(mod)} modificados; fora do previsto {sorted(set(mod) ^ set(MOD_ESP))}")
v12_head = sorted(l.split("\t")[1] for l in git("ls-tree", "-r", "HEAD", "outputs/manuscrito").splitlines() if V12 in l)
ren_ok = all(n == o.replace("outputs/manuscrito/", "outputs/manuscrito/_arquivo_v12/") for o, n in ren)
R.ok("A2.02 renomeações (staged) = todos os 38 arquivos v12 rastreados → _arquivo_v12/, mesma subpasta; nenhuma outra",
     ren_ok and sorted(o for o, _ in ren) == v12_head, f"{len(ren)} renomeados; v12 em HEAD {len(v12_head)}")
R.ok("A2.03 nenhuma outra situação no git (D, A, U, MM etc.)", not outros, outros[:5])
dr = [p for p in unt if p.startswith("docs/referencias/")]
dr_novos = [p for p in dr if os.stat(PROJ / p).st_mtime > T0]
R.ok("A2.04 não rastreados em docs/referencias: 94, dos quais só o aps_cobertura_ab/ACESSO.txt é posterior a dc54fb9",
     len(dr) == 94 and dr_novos == ["docs/referencias/aps_cobertura_ab/ACESSO.txt"], f"{len(dr)}; novos {dr_novos}")
UNT_ESP = {"outputs/RESUMO_ETAPA8_v1_20261013.md", "outputs/manuscrito/_resumo8_texto_v1_20261013.md",
           "outputs/manuscrito/audita_8_v1_20261013.csv", f"outputs/manuscrito/checa_7b_{V13}.csv",
           f"outputs/manuscrito/numeros_chave_{V13}.json", f"outputs/manuscrito/numeros_chave_{V13}.md",
           "outputs/manuscrito/_arquivo_v12/MANIFEST_v12_20261013.md", "outputs/manuscrito/_arquivo_v12/data_code_availability_v12_20261013.md",
           "outputs/manuscrito/_arquivo_v12/legendas_figuras_v12_20261013.md",
           *[f"outputs/manuscrito/_arquivo_v12/Submissao/{f}" for f in ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf",
                                                                       "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif")],
           *[f"scripts/etapa8_0{k}" for k in ()], "scripts/resumos/etapa8_01_resumo.py",
           "scripts/etapa8_01_baixa_cobertura_ab.py", "scripts/etapa8_02_cobertura_regiao.py", "scripts/etapa8_03_tercis.py",
           "scripts/etapa8_04_modelos.py", "scripts/etapa8_05_audita.py"}
v13_esp = {n.replace("_arquivo_v12/", "").replace(V12, V13) for _, n in ren if "checa_7b" not in n and "numeros_chave" not in n}
UNT_ESP |= v13_esp
fora = [p for p in unt if not p.startswith(("docs/referencias/", "audit_independente/etapa8/")) and p not in UNT_ESP]
falta = sorted(UNT_ESP - set(unt))
R.ok("A2.05 não rastreados fora de docs/referencias = pacote v13 (mesmos nomes da v12 com v13), extras do _arquivo_v12, scripts e textos da Etapa 8",
     not fora and not falta, f"{len(unt) - len(dr)} arquivos; inesperados {fora[:6]}; faltando {falta[:6]}")
ign_novos = sorted(p for p in ign if (PROJ / p).is_file() and os.stat(PROJ / p).st_mtime > T0)
ign_dirs = sorted(p for p in ign if (PROJ / p).is_dir())
esp_ign = re.compile(r"^(data/raw/aps_cobertura_ab/(cobertura_ab_uf\d\d_201401_202012\.json|manifesto_cobertura_ab_v1_20261013\.csv)"
                     r"|data/processed/(cobertura_ab_regsaude_ano|tercil_aps_regsaude_ano)_v1_20261008\.csv"
                     r"|outputs/tables/tab_e8_0[234]_\w+_v1_20261008\.csv|outputs/logs/etapa(8|7b)_20261008\.log"
                     r"|scripts/__pycache__/etapa7b_lib\.cpython-312\.pyc|audit_independente/etapa8/.*)$")
ign_fora = [p for p in ign_novos if not esp_ign.match(p)]
R.ok("A2.06 ignorados novos (mtime > dc54fb9): só bruto da cobertura (27 JSON + manifesto), 2 CSV de data/processed, tab_e8_02–04, 2 logs e o .pyc da lib",
     not ign_fora, f"{len(ign_novos)} arquivos; fora do padrão {ign_fora[:5]}; diretórios ignorados inteiros {ign_dirs[:8]}")
pyc = [p for p in ign_novos if p.endswith(".pyc")]
R.ok("A2.07 [ressalva] __pycache__ regravado (gitignored) — efeito colateral de import, sem dado", True, pyc)
# arquivos novos em diretórios ignorados por inteiro (git status mostra só o diretório)
novos_dir = []
for d in ign_dirs:
    for root, _, fs in os.walk(PROJ / d):
        for f in fs:
            q = os.path.join(root, f)
            if os.stat(q).st_mtime > T0 and "audit_independente/etapa8" not in q:
                novos_dir.append(os.path.relpath(q, PROJ))
R.ok("A2.08 dentro dos diretórios ignorados por inteiro: nada novo além do previsto", all(esp_ign.match(p) for p in novos_dir),
     f"{len(novos_dir)} arquivos: {sorted(set(os.path.dirname(p) for p in novos_dir))}")
dados = sorted(p for p in ign_novos + novos_dir if p.startswith("data/"))
R.ok("A2.09 data/: nomes e mtimes dos novos (só leitura de metadado)", len(dados) == 30,
     "; ".join(f"{os.path.basename(p)}@{datetime.fromtimestamp(os.stat(PROJ / p).st_mtime):%H:%M:%S}" for p in dados if 'uf' not in p)
     + f"; + {sum('uf' in p for p in dados)} JSON por UF entre 21:44:15 e 21:46:09")

# A3 v12 arquivada = dc54fb9
lst = {l.split("\t")[1]: l.split()[2] for l in git("ls-tree", "-r", "HEAD").splitlines()}
dif = []
for o, n in ren:
    if blob_sha((PROJ / n).read_bytes()) != lst[o]:
        dif.append(n)
extra = {"outputs/manuscrito/_arquivo_v12/MANIFEST_v12_20261013.md": "outputs/manuscrito/MANIFEST.md",
         "outputs/manuscrito/_arquivo_v12/data_code_availability_v12_20261013.md": "outputs/manuscrito/data_code_availability.md",
         "outputs/manuscrito/_arquivo_v12/legendas_figuras_v12_20261013.md": "outputs/manuscrito/legendas_figuras.md",
         **{f"outputs/manuscrito/_arquivo_v12/Submissao/{f}": f"Submissao/{f}" for f in
            ("ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif")}}
for n, o in extra.items():
    if blob_sha((PROJ / n).read_bytes()) != lst[o]:
        dif.append(n)
R.ok("A3.01 v12 arquivada byte a byte = dc54fb9 (38 renomeados + 11 cópias: MANIFEST, disponibilidade, legendas, Submissao/ 8)",
     not dif and len(ren) + len(extra) == 49, f"{len(ren) + len(extra)} arquivos; divergentes {dif}")
arq = sorted(os.path.relpath(os.path.join(r, f), PROJ) for r, _, fs in os.walk(PROJ / "outputs/manuscrito/_arquivo_v12") for f in fs)
R.ok("A3.02 _arquivo_v12 contém só esses 49 arquivos", sorted(arq) == sorted([n for _, n in ren] + list(extra)), f"{len(arq)} arquivos")
sub_igual = [f for f in ("Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif") if blob_sha((PROJ / "Submissao" / f).read_bytes()) == lst[f"Submissao/{f}"]]
R.ok("A3.03 Submissao/Fig1–4 da v13 byte a byte iguais a dc54fb9 (regravados com o mesmo conteúdo)", len(sub_igual) == 4, sub_igual)

# A4 ._*
dot = []
for root, dirs, fs in os.walk(PROJ):
    if "/.git" in root:
        continue
    for f in fs:
        if f.startswith("._"):
            q = os.path.join(root, f)
            dot.append((os.path.relpath(q, PROJ), datetime.fromtimestamp(os.lstat(q).st_mtime).strftime("%Y-%m-%d")))
dot_novos = [p for p, d in dot if d >= "2026-10-13"]
R.ok("A4.01 nenhum ._* novo (mtime ≥ 13/10) no projeto", not dot_novos, f"novos {dot_novos}; antigos {dot}")
R.ok("A4.02 [ressalva] ._* antigo em data/processed (08/10, anterior à etapa, ignorado pelo git)", True, [p for p, _ in dot])
R.grava()
