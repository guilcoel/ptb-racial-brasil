"""Bloco E/G — sandbox no diretório temporário do sistema: clone -s de dc54fb9 + estado não commitado (cópias de rastreados modificados e
não rastreados; renomeações refeitas no git do sandbox) + links simbólicos para os ignorados necessários (outputs/tables,
data/raw/aps_cobertura_ab, comparacao_*.csv). Nada de data/processed. Todo Python do sandbox carrega a guarda (sitecustomize com
sys.addaudithook) que bloqueia escrita/remoção/renomeação/mkdir/utime/chmod/rmtree em caminhos cujo realpath esteja sob /Volumes/Forja,
e subprocessos (exceto git de leitura) com argumentos sob o Forja. A guarda é testada antes do uso. O sandbox é apagado no fim."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8")
import csv
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from comum_v1_20261013 import PROJ, MS, Res, md5

R = Res("E")
os.environ["GIT_OPTIONAL_LOCKS"] = "0"
SB = Path(tempfile.mkdtemp(prefix="aud8_sb_"))
assert not str(SB.resolve()).startswith("/Volumes/Forja")
REPO, GUARD = SB / "repo", SB / "guarda"
GUARD.mkdir()
(GUARD / "sitecustomize.py").write_text(r'''
import os, sys
sys.dont_write_bytecode = True
_F = "/Volumes/Forja"
_W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
def _bad(p):
    try:
        p = os.fsdecode(p)
    except Exception:
        return False
    if not isinstance(p, str):
        return False
    r = os.path.realpath(os.path.abspath(p))
    return r == _F or r.startswith(_F + "/")
_EV = {"os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.utime", "os.chmod", "os.chown", "os.truncate", "os.symlink", "os.link",
       "shutil.rmtree", "os.chflags", "os.lchflags", "os.setxattr", "os.removexattr", "shutil.copyfile", "shutil.copytree", "shutil.move",
       "shutil.chown", "os.replace"}
_GIT_OK = {"log", "rev-parse", "show", "ls-files", "cat-file", "merge-base", "rev-list", "diff", "status", "ls-tree", "for-each-ref", "branch"}
def _h(ev, a):
    if ev == "open":
        path, mode, flags = a
        if isinstance(path, int):
            return
        w = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & _W)
        if w and _bad(path):
            raise PermissionError(f"GUARDA_FORJA: escrita bloqueada em {path}")
    elif ev in _EV:
        for x in a:
            if isinstance(x, (str, bytes, os.PathLike)) and _bad(x):
                raise PermissionError(f"GUARDA_FORJA: {ev} bloqueado em {x}")
    elif ev == "subprocess.Popen":
        exe, argv, cwd, env = a
        argv = [os.fsdecode(x) for x in (argv if isinstance(argv, (list, tuple)) else [argv])]
        if os.path.basename(argv[0]) == "git":
            sub = [x for i, x in enumerate(argv[1:]) if not x.startswith("-") and (i == 0 or argv[i] not in ("-C", "-c"))]
            if sub and sub[0] not in _GIT_OK:
                raise PermissionError(f"GUARDA_FORJA: git {sub[0]} bloqueado no sandbox")
            return
        if any(_bad(x) for x in argv if "/" in x) or (cwd and _bad(cwd)):
            raise PermissionError(f"GUARDA_FORJA: subprocesso com caminho do Forja: {argv[:3]}")
sys.addaudithook(_h)
''')
ENV = dict(os.environ, PYTHONPATH=f"{GUARD}:{REPO}/scripts", PYTHONDONTWRITEBYTECODE="1")
py = lambda code, cwd=SB: subprocess.run([sys.executable, "-c", code], cwd=cwd, env=ENV, capture_output=True, text=True)
AUDDIR = "/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa8"
testes = {
    "open w": f"open('{AUDDIR}/guarda_teste_inexistente.txt', 'w')",
    "open a": f"open('{PROJ}/outputs/tables/guarda_teste.csv', 'a')",
    "os.open O_CREAT": f"import os; os.open('{AUDDIR}/guarda_teste2', os.O_CREAT | os.O_WRONLY)",
    "pandas to_csv": f"import pandas as pd; pd.DataFrame({{'a': [1]}}).to_csv('{AUDDIR}/guarda_teste3.csv')",
    "remove": f"import os; os.remove('{AUDDIR}/guarda_inexistente')",
    "rename": f"import os; os.rename('{AUDDIR}/guarda_inexistente', '{AUDDIR}/guarda_inexistente2')",
    "mkdir": f"import os; os.mkdir('{AUDDIR}/guarda_dir')",
    "utime": f"import os; os.utime('{AUDDIR}/comum_v1_20261013.py')",
    "chmod": f"import os; os.chmod('{AUDDIR}/comum_v1_20261013.py', 0o644)",
    "rmtree": f"import shutil; shutil.rmtree('{AUDDIR}/guarda_inexistente_dir')",
    "via symlink": f"open('{SB}/lnk/guarda_teste4.txt', 'w')",
    "subprocess touch": f"import subprocess; subprocess.run(['touch', '{AUDDIR}/guarda_teste5'])",
    "git commit": "import subprocess; subprocess.run(['git', '-C', '.', 'commit', '-m', 'x'])",
}
os.symlink(AUDDIR, SB / "lnk")
blk = {k: "GUARDA_FORJA" in py(c).stderr for k, c in testes.items()}
leit = py(f"print(len(open('{PROJ}/outputs/RESUMO_ETAPA8_v1_20261013.md').read()) > 0); open('{SB}/livre.txt', 'w').write('x')")
criados = [p.name for p in Path(AUDDIR).iterdir() if p.name.startswith("guarda_")]
R.ok("E1.01 guarda testada antes do uso: bloqueia open w/a, os.open, pandas, remove, rename, mkdir, utime, chmod, rmtree, escrita via symlink, "
     "subprocesso no Forja e git de escrita; leitura no Forja e escrita no sandbox liberadas; nenhum arquivo criado",
     all(blk.values()) and leit.stdout.strip() == "True" and (SB / "livre.txt").exists() and not criados,
     f"bloqueados {sum(blk.values())}/{len(blk)}; não bloqueados {[k for k, v in blk.items() if not v]}; criados {criados}")
if not all(blk.values()) or criados:
    shutil.rmtree(SB)
    R.grava()
    raise SystemExit("guarda falhou")
(SB / "lnk").unlink()

# monta o sandbox
git = lambda *a, cwd=PROJ: subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout
subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(REPO)], check=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
st = git("status", "--porcelain=v1", "-uall", "-z").split("\0")
i = 0
mods, unt, ren = [], [], []
while i < len(st):
    e = st[i]
    if not e:
        i += 1
        continue
    xy, p = e[:2], e[3:]
    if xy[0] == "R":
        ren.append((st[i + 1], p))
        i += 2
        continue
    (mods if xy.strip() == "M" else unt if xy == "??" else []).append(p)
    i += 1
for o, n in ren:
    (REPO / n).parent.mkdir(parents=True, exist_ok=True)
    git("mv", o, n, cwd=REPO)
for p in mods + [u for u in unt if not u.startswith("audit_independente/etapa8/")]:
    (REPO / p).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJ / p, REPO / p)
for d in ("outputs/tables",):
    os.symlink(PROJ / d, REPO / d)
(REPO / "data/raw").mkdir(parents=True)
os.symlink(PROJ / "data/raw/aps_cobertura_ab", REPO / "data/raw/aps_cobertura_ab")
for f in PROJ.glob("audit_independente/*/comparacao_*.csv"):
    if "etapa8" in str(f):
        continue
    (REPO / f.parent.relative_to(PROJ)).mkdir(parents=True, exist_ok=True)
    os.symlink(f, REPO / f.relative_to(PROJ))
(REPO / "outputs/logs").mkdir(parents=True, exist_ok=True)
dif_arv = [p for p in mods + [u for u in unt if not u.startswith("audit_independente/etapa8/")] + [n for _, n in ren]
           if md5(REPO / p) != md5(PROJ / p)]
R.ok("E1.02 sandbox = árvore de trabalho do projeto (rastreados modificados, não rastreados e renomeações; HEAD dc54fb9); sem data/processed",
     not dif_arv and git("rev-parse", "HEAD", cwd=REPO).strip().startswith("dc54fb9") and not (REPO / "data/processed").exists(),
     f"{len(mods)} mod; {len(unt)} não rastr.; {len(ren)} renomeados; divergentes {dif_arv[:3]}")

CHECA = f"{REPO}/scripts/etapa7b_checa.py"


def roda_checa():
    r = subprocess.run([sys.executable, "-B", CHECA], cwd=REPO, env=ENV, capture_output=True, text=True, timeout=3600)
    falha = ""
    for l in (r.stdout + r.stderr).splitlines():
        if "AssertionError" in l:
            falha = l.split("AssertionError:", 1)[-1].strip()
    return r.returncode, falha, r


rc, falha, r = roda_checa()
out = REPO / "outputs/manuscrito/checa_7b_v13_20261013.csv"
meu = list(csv.DictReader(open(out))) if out.exists() else []
proj = list(csv.DictReader(open(MS / "checa_7b_v13_20261013.csv")))
igual = [(a["verificacao"], a["ok"]) for a in meu] == [(b["verificacao"], b["ok"]) for b in proj]
dif_val = [a["verificacao"][:50] for a, b in zip(meu, proj) if a["valor"] != b["valor"]]
n9i = [a for a in meu if a["verificacao"].startswith("8 ")]
R.ok("E2.01 checa rodado no sandbox com a guarda: 128/128 OK; mesmas verificações e resultados do checa_7b_v13 do projeto; 15 do bloco 9i",
     rc == 0 and len(meu) == 128 and all(a["ok"] == "True" for a in meu) and igual and len(n9i) == 15,
     f"rc {rc}; {sum(a['ok'] == 'True' for a in meu)}/{len(meu)}; 9i {len(n9i)}; valores diferentes {dif_val[:4]}; erro {r.stderr[-300:] if rc else ''}")
R.ok("E2.02 [contagem] o RESUMO diz '15/15 são as novas da Etapa 8 (bloco 9i)'; o gerador conta as linhas que começam com '8 '", len(n9i) == 15, len(n9i))


# mutações no bloco 9i (cada uma restaurada depois); o checa para no 1º assert, que tem de ser o esperado
def muta(rel, f):
    p = REPO / rel
    orig = p.read_bytes()
    p.write_bytes(f(orig))
    try:
        return roda_checa()[1]
    finally:
        p.write_bytes(orig)


MUT = [
    ("S2b (d) PIG alterada", "outputs/manuscrito/suplementar/S2b_access_specifications_v13_20261013.csv",
     lambda b: b.replace("1.35 (−1.94 to 4.65)".encode(), "1.36 (−1.94 to 4.65)".encode(), 1), "8 S2b"),
    ("nota n.a. removida? (Tabela 4 CSV com um n.a. novo sem explicação)", "outputs/manuscrito/tabelas/tab04_sensitivity_v13_20261013.csv",
     lambda b: b.replace("1.61 (1.43–1.81)".encode(), "n.a.".encode(), 1), "8 "),
    ("MD5 do ACESSO.txt alterado", "docs/referencias/aps_cobertura_ab/ACESSO.txt",
     lambda b: b.replace(b"dcdccf7a53ff7d3e3210bd39d596eb66", b"dcdccf7a53ff7d3e3210bd39d596eb67"), "8 bruto"),
    ("legendas com um caractere a mais", "outputs/manuscrito/legendas_figuras.md", lambda b: b + b" ", "8 legendas"),
    ("número-chave novo com valor formatado errado", "outputs/manuscrito/numeros_chave_v13_20261013.json",
     lambda b: b.replace(b'"valor_formatado": "0.507"', b'"valor_formatado": "0.508"', 1), ""),
]
for k, (nome, rel, f, esp) in enumerate(MUT, 1):
    fa = muta(rel, f)
    R.ok(f"E3.{k:02d} mutação '{nome}' derruba o checa{' em ' + repr(esp) if esp else ''}", bool(fa) and fa.startswith(esp), f"1ª falha: {fa[:140]}")
rc2, falha2, _ = roda_checa()
R.ok("E3.99 controle: depois das mutações restauradas, o checa volta a 128/128", rc2 == 0 and not falha2, falha2)

# G: gerador do RESUMO com saída desviada (o sandbox), comparado ao RESUMO do projeto
g = subprocess.run([sys.executable, "-B", f"{REPO}/scripts/resumos/etapa8_01_resumo.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
gerado = REPO / "outputs/RESUMO_ETAPA8_v1_20261013.md"
R.ok("G1.01 o gerador (cópia no sandbox, sem o CSV do auditor) reproduz o RESUMO_ETAPA8 do projeto byte a byte",
     g.returncode == 0 and gerado.read_bytes() == (PROJ / "outputs/RESUMO_ETAPA8_v1_20261013.md").read_bytes(), g.stderr[-300:])
g7 = subprocess.run([sys.executable, "-B", f"{REPO}/scripts/resumos/etapa7c7_01_resumo.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
R.ok("E4.01 LEIAME: o gerador da 7c.7 para depois do arquivamento da v12 (procura a v12 na raiz)", g7.returncode != 0
     and "v12_20261013" in g7.stderr and "GUARDA_FORJA" not in g7.stderr, g7.stderr.strip().splitlines()[-1][:200] if g7.stderr else "")
# o gerador da Etapa 8 com um CSV de auditor falso (só no sandbox) de 2 rodadas: blocos agrupados certos?
fake = REPO / "audit_independente/etapa8/comparacao_8_v1_20261013.csv"
fake.parent.mkdir(parents=True, exist_ok=True)
fake.write_text("verificacao,ok,detalhe\nA1.01 x,True,a\nB1.01 y,False,b\nR2.B1.01 z,True,c\nR2.C1.01 w,True,d\n")
g2 = subprocess.run([sys.executable, "-B", f"{REPO}/scripts/resumos/etapa8_01_resumo.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
txt = gerado.read_text() if g2.returncode == 0 else ""
sec2 = txt.split("## 2. Auditoria independente")[1].split("## 3.")[0] if txt else ""
R.ok("G1.02 gerador com CSV de 2 rodadas (teste sintético no sandbox): a rodada 2 aparece agrupada pelos blocos (B, C), não num bloco 'R'",
     bool(__import__("re").search(r"\|\s*2\s*\|\s*B\.", sec2)) and bool(__import__("re").search(r"\|\s*2\s*\|\s*C\.", sec2))
     and not __import__("re").search(r"\|\s*2\s*\|\s*R\.", sec2), [l for l in sec2.splitlines() if l.startswith("| 2 ")][:3])
fake.unlink()
# limpeza
shutil.rmtree(SB)
R.ok("E5.01 sandbox apagado; nada criado no projeto pelos testes", not SB.exists() and not [p for p in Path(AUDDIR).iterdir() if p.name.startswith("guarda_")],
     str(SB))
R.grava()
