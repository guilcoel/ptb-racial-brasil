"""Bloco A — git e árvore: HEAD, refs, stash, remoto; mudanças desde cdddf8f arquivo a arquivo; v13 arquivada = bytes de cdddf8f; ._*; docs/referencias."""
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *

B = Bloco("a")
head = git("rev-parse", "HEAD").strip()
B.ok("A1.01", "HEAD = cdddf8f (Etapa 8)", head.startswith("cdddf8f") and git("log", "-1", "--format=%s").strip().startswith("Etapa 8: sensibilidade"), head)
refs = git("show-ref").split("\n")
refs = [r for r in refs if r]
B.ok("A1.02", "refs: só refs/heads/main (nenhuma tag nova, nenhum outro ramo)", len(refs) == 1 and refs[0].endswith("refs/heads/main"), refs)
B.ok("A1.03", "stash vazio", git("stash", "list").strip() == "", git("stash", "list")[:200])
B.ok("A1.04", "sem remoto", git("remote", "-v").strip() == "", git("remote", "-v"))
TCOMMIT = int(git("log", "-1", "--format=%ct", BASE).strip())

# ---- status completo
st = git("status", "--porcelain=v1", "-uall", "-z").split("\0")
ent = []
i = 0
while i < len(st):
    e = st[i]
    if not e:
        i += 1; continue
    x, y, p = e[0], e[1], e[3:]
    if x == "R":
        ent.append(("R", st[i + 1], p)); i += 2
    else:
        ent.append((x + y, p, None)); i += 1
naor = [p for s, p, _ in ent if s == "??"]
naor_ref = [p for p in naor if p.startswith("docs/referencias/")]
naor_out = [p for p in naor if not p.startswith("docs/referencias/")]
mod = sorted(p for s, p, _ in ent if s.strip() == "M")
ren = sorted((a, b) for s, a, b in ent if s == "R")
outros = [(s, p) for s, p, _ in ent if s not in ("??", "R") and s.strip() != "M"]
B.ok("A2.01", "nenhum estado inesperado (D, A, UU, T) no status", not outros, outros)
MOD_ESP = sorted(["Submissao/ESM_1.xlsx", "Submissao/ESM_2.pdf", "Submissao/ESM_3.pdf", "Submissao/ESM_4.pdf", "outputs/manuscrito/MANIFEST.md",
                  "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "scripts/etapa7b_01_tabelas.py",
                  "scripts/etapa7b_02_suplementar.py", "scripts/etapa7b_04_submissao.py", "scripts/etapa7b_checa.py", "scripts/etapa7b_lib.py"])
B.ok("A2.02", "modificados rastreados = os 12 previstos (4 ESM de Submissao/, MANIFEST, disponibilidade, legendas, 5 scripts do pacote)", mod == MOD_ESP,
     f"a mais {sorted(set(mod) - set(MOD_ESP))}; faltam {sorted(set(MOD_ESP) - set(mod))}")
# Fig1-4 de Submissao/ não mudaram em bytes (pixels iguais e tif regravado igual)
figs_sub = [git("hash-object", f"Submissao/Fig{k}.tif").strip() == git("rev-parse", f"{BASE}:Submissao/Fig{k}.tif").strip() for k in range(1, 5)]
B.ok("A2.03", "Submissao/Fig1–4.tif com os mesmos bytes de cdddf8f (por isso fora do status)", all(figs_sub), figs_sub)
v13_base = sorted(p for p in git("ls-tree", "-r", "--name-only", BASE, "outputs/manuscrito").split("\n") if V13 in p and "/_arquivo_" not in p)
ren_esp = sorted((p, str(Path(p).parent).replace("outputs/manuscrito", "outputs/manuscrito/_arquivo_v13") + "/" + Path(p).name) for p in v13_base)
B.ok("A2.04", "renomeações (staged, git mv) = todos os arquivos com v13 no nome em cdddf8f → _arquivo_v13/, com a mesma subpasta", ren == ren_esp,
     f"{len(ren)} renomeações; esperado {len(ren_esp)}; diferença {sorted(set(ren) ^ set(ren_esp))[:3]}")
idx = git("diff", "--cached", "--name-status", BASE).split("\n")
idx = [l for l in idx if l]
B.ok("A2.05", "no índice só as renomeações (R100, sem conteúdo alterado); nada mais staged", all(l.startswith("R100") for l in idx) and len(idx) == len(ren_esp),
     f"{len(idx)} linhas; não R100 {[l for l in idx if not l.startswith('R100')][:3]}")
v14_esp = sorted(p.replace(V13, V14) for p in v13_base)
ARQ_NOVO = sorted([f"outputs/manuscrito/_arquivo_v13/MANIFEST_{V13}.md", f"outputs/manuscrito/_arquivo_v13/data_code_availability_{V13}.md",
                   f"outputs/manuscrito/_arquivo_v13/legendas_figuras_{V13}.md"] +
                  [f"outputs/manuscrito/_arquivo_v13/Submissao/{n}" for n in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]])
ETAPA = sorted(["outputs/RESUMO_ETAPA8b_v1_20261026.md", "outputs/manuscrito/_resumo8b_texto_v1_20261026.md", "outputs/manuscrito/audita_8b_v1_20261026.csv",
                "scripts/etapa8b_01_audita.py", "scripts/resumos/etapa8b_01_resumo.py"])
naor_esp = sorted(v14_esp + ARQ_NOVO + ETAPA)
naor_out_sem_aud = [p for p in naor_out if not p.startswith("audit_independente/etapa8b/")]
B.ok("A2.06", "não rastreados fora de docs/referencias = v14 (mesmos nomes da v13) + 11 cópias de arquivo da v13 + 5 arquivos da etapa (fora a pasta do auditor)",
     sorted(naor_out_sem_aud) == naor_esp, f"{len(naor_out_sem_aud)} vs {len(naor_esp)}; a mais {sorted(set(naor_out_sem_aud) - set(naor_esp))[:4]}; faltam {sorted(set(naor_esp) - set(naor_out_sem_aud))[:4]}")
B.ok("A2.07", "v14: mesmo conjunto de arquivos da v13 (38), checa_7b_v14 incluído", len(v14_esp) == len(v13_base) and all((PROJ / p).exists() for p in v14_esp), len(v14_esp))

# ---- v13 arquivada = bytes de cdddf8f
dif = []
for a, b in ren_esp:
    if git("hash-object", b).strip() != git("rev-parse", f"{BASE}:{a}").strip():
        dif.append(b)
MAPA = {f"outputs/manuscrito/_arquivo_v13/MANIFEST_{V13}.md": "outputs/manuscrito/MANIFEST.md",
        f"outputs/manuscrito/_arquivo_v13/data_code_availability_{V13}.md": "outputs/manuscrito/data_code_availability.md",
        f"outputs/manuscrito/_arquivo_v13/legendas_figuras_{V13}.md": "outputs/manuscrito/legendas_figuras.md"}
MAPA.update({f"outputs/manuscrito/_arquivo_v13/Submissao/{n}": f"Submissao/{n}" for n in ["ESM_1.xlsx", "ESM_2.pdf", "ESM_3.pdf", "ESM_4.pdf", "Fig1.tif", "Fig2.tif", "Fig3.tif", "Fig4.tif"]})
for b, a in MAPA.items():
    if git("hash-object", b).strip() != git("rev-parse", f"{BASE}:{a}").strip():
        dif.append(b)
B.ok("A3.01", "v13 arquivada: os 49 arquivos (38 renomeados + MANIFEST, disponibilidade, legendas, 8 de Submissao/) com os bytes de cdddf8f",
     not dif and len(ren_esp) + len(MAPA) == 49, f"divergentes {dif[:4]}")
arq = sorted(str(p.relative_to(PROJ)) for p in A13.rglob("*") if p.is_file())
B.ok("A3.02", "_arquivo_v13 contém só esses 49 arquivos (nenhum ._*, nenhum extra)", sorted(arq) == sorted([b for _, b in ren_esp] + list(MAPA)),
     f"{len(arq)}; extras {sorted(set(arq) - set([b for _, b in ren_esp] + list(MAPA)))[:3]}")
a12 = sorted(str(p.relative_to(MS / "_arquivo_v12")).replace("v12_20261013", "VX") for p in (MS / "_arquivo_v12").rglob("*") if p.is_file() and not p.name.startswith("._"))
a13 = sorted(str(p.relative_to(A13)).replace(V13, "VX") for p in A13.rglob("*") if p.is_file())
B.ok("A3.03", "mesmo padrão do _arquivo_v12 (mesma estrutura de nomes e subpastas)", a12 == a13, f"v12 {len(a12)}; v13 {len(a13)}; dif {sorted(set(a12) ^ set(a13))[:4]}")

# ---- ._* e .DS_Store
lixo = []
for raiz in ["outputs", "scripts", "Submissao", "audit_independente", "docs", "data"]:
    for dp, dn, fn in os.walk(PROJ / raiz):
        for f in fn:
            if f.startswith("._") or f == ".DS_Store":
                p = Path(dp) / f
                lixo.append((str(p.relative_to(PROJ)), p.lstat().st_mtime))
novos = [p for p, t in lixo if t >= TCOMMIT - 3600]
B.ok("A4.01", "nenhum ._*/.DS_Store novo (mtime depois de 1 h antes de cdddf8f) em outputs, scripts, Submissao, audit_independente, docs, data",
     not novos, f"total {len(lixo)} (antigos: {[p for p, _ in lixo][:3]}); novos {novos[:3]}")

# ---- docs/referencias
mt_ref = [p for p in naor_ref if (PROJ / p).lstat().st_mtime >= TCOMMIT]
B.ok("A5.01", "93 não rastreados em docs/referencias, todos com mtime anterior a cdddf8f (já existiam)", len(naor_ref) == 93 and not mt_ref,
     f"{len(naor_ref)}; recentes {mt_ref[:3]}")
B.ok("A5.02", ".gitignore igual ao de cdddf8f", (PROJ / ".gitignore").read_bytes() == git("show", f"{BASE}:.gitignore", binary=True))
# nenhum rastreado fora do previsto mudou (stat-dirty): git diff sem renomeações
wt = sorted(l for l in git("diff", "--name-only").split("\n") if l)
B.ok("A2.08", "diff da árvore de trabalho = os 12 modificados", wt == MOD_ESP, sorted(set(wt) ^ set(MOD_ESP)))
# ---- diffs dos scripts: só as trocas da 8b (lidas linha a linha pelo auditor; aqui, a forma)
ns = {l.split("\t")[2]: tuple(map(int, l.split("\t")[:2])) for l in git("diff", "--numstat", "--", "scripts/").splitlines() if l}
B.ok("A6.01", "numstat dos scripts: 01 +6/−0 (6 Wald6_*), 02 +6/−5 (coluna, rodapé, ETAPA), 04 +5/−3 (docstring, título, histórico), lib +2/−2 (V, título do MD), checa +108/−35",
     ns == {"scripts/etapa7b_01_tabelas.py": (6, 0), "scripts/etapa7b_02_suplementar.py": (6, 5), "scripts/etapa7b_04_submissao.py": (5, 3),
            "scripts/etapa7b_lib.py": (2, 2), "scripts/etapa7b_checa.py": (108, 35)}, ns)
d02 = [l for l in git("diff", "-U0", "scripts/etapa7b_02_suplementar.py").splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
B.ok("A6.02", "02: única linha nova de dado = a coluna 'Wald p, 6 race×tertile terms' com B.pval(w.p_6gl), com w = e8w.loc[(ex_, d_)] da mesma exposição",
     sum("p_6gl" in l for l in d02 if l.startswith("+")) == 1 and 'rows[-1][f"{col_}: Wald p, 6 race\\u00d7tertile terms"] = B.pval(w.p_6gl)' in "\n".join(d02), len(d02))
s_chk = git("diff", "-U0", "scripts/etapa7b_checa.py")
B.ok("A6.03", "[ressalva] checa: o 9i foi reescrito para comparar v12 × v13 arquivadas (Jcur→J13, B.TABD→A13…); o 9j novo compara v13 × v14. "
     "O 9j compara xlsx só por título e rodapé (abas()) e não olha S9 (suplementar/) nem os arquivos copiados para _arquivo_v13 (ver E4)", True,
     f"{s_chk.count(chr(10))} linhas de diff")
B.grava()
