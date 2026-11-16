"""
Auditor independente da Etapa 7c.7, rodada 2 — testes dinâmicos em sandbox.

O que o sandbox faz (regra nova da rodada 2: nada ignorado pelo git copiado para fora do Forja):
  - fica no scratch do sistema (/private/tmp/.../scratchpad/aud7c7r2_*), e é apagado no fim;
  - git: `git clone --no-checkout` do repositório (só objetos versionados) + cópia do índice real;
  - copia só arquivos rastreados e não rastreados NÃO ignorados (git ls-files; nada de data/);
  - arquivos ignorados que os scripts leem (outputs/tables/*, audit_independente/*/comparacao_*.csv) entram como LINKS SIMBÓLICOS
    para o Forja, um por arquivo, dentro de pastas reais do sandbox — nada é copiado;
  - toda execução de Python no sandbox carrega uma guarda (sitecustomize.py no PYTHONPATH, com sys.addaudithook) que levanta
    PermissionError em qualquer escrita, remoção, renomeação, chmod/utime ou criação de pasta em caminho cujo realpath esteja em
    /Volumes/Forja, e em qualquer cópia (shutil) de arquivo ignorado do Forja para fora dele. Assim os links só são lidos;
  - antes e depois: MD5 e mtime de outputs/tables/* e dos CSVs de audit_independente/ no Forja (intactos).
Roda: o checa (cópia com assert desligado) na linha de base, depois de 2 mutações nas verificações que mudaram na rodada 2 e depois
de commits simulados (grep ancorado); o gerador do RESUMO (cópia, saída desviada) contra o RESUMO real, byte a byte, e depois de
arquivar a v12; o 01 e o 03 (reprodução). Saída: audit_independente/etapa7c7/sandbox_7c7_r2_v1_20261013.json.
Rodar: python3 audit_independente/etapa7c7/audita_7c7_r2_sandbox_v1_20261013.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
SCRATCH = Path("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad")
V11, V12 = "v11_20261009", "v12_20261013"
ENV0 = dict(os.environ, GIT_OPTIONAL_LOCKS="0", PYTHONDONTWRITEBYTECODE="1")
PY = sys.executable
RES = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S")}

GUARDA = r'''
import os, sys
_F = "/Volumes/Forja"
_W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_SENS = ("/Volumes/Forja/ptb-racial-brasil/outputs/tables/", "/Volumes/Forja/ptb-racial-brasil/data/",
         "/Volumes/Forja/ptb-racial-brasil/outputs/logs/")
def _r(p):
    try:
        return os.path.realpath(os.fsdecode(p))
    except Exception:
        return ""
def _sens(p):
    r = _r(p)
    return r.startswith(_SENS) or (r.startswith("/Volumes/Forja/ptb-racial-brasil/audit_independente/") and r.endswith(".csv"))
def _h(ev, args):
    if ev == "open":
        p, mode, flags = (list(args) + [None, None, None])[:3]
        if isinstance(p, int):
            return
        w = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (mode is None and isinstance(flags, int) and flags & _W)
        if w and _r(p).startswith(_F):
            raise PermissionError("[guarda do auditor 7c.7] escrita no Forja bloqueada: " + str(p))
    elif ev in ("os.remove", "os.rename", "os.replace", "os.rmdir", "os.truncate", "os.chmod", "os.utime", "os.mkdir", "shutil.rmtree",
                "os.link", "os.chown", "shutil.move"):
        for a in args[:2]:
            if isinstance(a, (str, bytes, os.PathLike)) and _r(a).startswith(_F):
                raise PermissionError("[guarda do auditor 7c.7] " + ev + " no Forja bloqueado: " + str(a))
    elif ev == "os.symlink":
        if len(args) > 1 and _r(args[1]).startswith(_F):
            raise PermissionError("[guarda do auditor 7c.7] link criado dentro do Forja bloqueado")
    elif ev in ("shutil.copyfile", "shutil.copymode", "shutil.copystat"):
        src, dst = args[0], args[1]
        if _r(dst).startswith(_F) or (_sens(src) and not _r(dst).startswith(_F)):
            raise PermissionError("[guarda do auditor 7c.7] cópia bloqueada: " + str(src) + " -> " + str(dst))
sys.addaudithook(_h)
'''


def sh(cmd, cwd=None, check=True, env=None, timeout=3600, inp=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=env or ENV0, timeout=timeout, input=inp)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.returncode}\n{r.stderr[-2000:]}")
    return r


git_real = lambda *a: sh(["git", "-C", PROJ, *a]).stdout
gitc = lambda d, *a, check=True: sh(["git", "-C", d, "-c", "user.name=auditor7c7", "-c", "user.email=auditor@example.invalid", *a], check=check).stdout
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()


def foto_ignorados():
    """MD5 e mtime, no Forja, dos ignorados que o sandbox liga por link (outputs/tables e CSVs de audit_independente)."""
    fs = sorted([f for f in (PROJ / "outputs/tables").iterdir() if f.is_file()] + list((PROJ / "audit_independente").rglob("*.csv")))
    return {str(f.relative_to(PROJ)): (md5(f), f.stat().st_mtime) for f in fs if not f.name.startswith("._")}


def env_sbx(d, root):
    return dict(ENV0, PYTHONPATH=f"{root / '_guarda'}{os.pathsep}{d / 'scripts'}", MPLBACKEND="Agg")


def monta_base(root):
    (root / "_guarda").mkdir()
    (root / "_guarda" / "sitecustomize.py").write_text(GUARDA)
    base = root / "base"
    sh(["git", "clone", "--quiet", "--no-checkout", PROJ, base])
    gitc(base, "remote", "remove", "origin")
    shutil.copy2(PROJ / ".git" / "index", base / ".git" / "index")
    tracked = [p for p in git_real("ls-files", "-z").split("\0") if p]
    untracked = [p for p in git_real("ls-files", "-o", "--exclude-standard", "-z").split("\0") if p]
    pula = {"outputs/manuscrito/checa_7b_v12_20261013.csv"}
    nc = 0
    for p in tracked + untracked:                       # rastreados e não rastreados não ignorados: cópia
        if p.startswith(("data/", "audit_independente/etapa7c7/")) or p in pula:
            continue
        if (PROJ / p).is_file():
            (base / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJ / p, base / p)
            nc += 1
    ign = [f for f in sorted((PROJ / "outputs/tables").iterdir()) if f.is_file() and not f.name.startswith("._")]
    ign += sorted(PROJ.glob("audit_independente/*/comparacao_*.csv"))
    for f in ign:                                       # ignorados: link simbólico, nada copiado
        dst = base / f.relative_to(PROJ)
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(f, dst)
    (base / "outputs/logs").mkdir(parents=True, exist_ok=True)
    ck = base / "scripts/etapa7b_checa.py"
    t = ck.read_text()
    assert t.count("    assert cond, nome\n") == 1
    ck.write_text(t.replace("    assert cond, nome\n", "    pass  # [auditor 7c.7 r2] assert desligado nesta cópia\n"))
    ign_git = [p for p in git_real("ls-files", "-o", "-i", "--exclude-standard", "-z", "--", "outputs", "audit_independente", "docs",
                                     "scripts", "Submissao").split("\0") if p]
    copiados_ign = [p for p in ign_git if (base / p).exists() and not (base / p).is_symlink()]
    RES["base"] = dict(copiados=nc, links=len(ign), indice_igual=gitc(base, "ls-files", "-s") == git_real("ls-files", "-s"),
                       head=gitc(base, "rev-parse", "--short", "HEAD").strip(), ignorados_copiados=copiados_ign,
                       links_para_forja=all(os.readlink(base / f.relative_to(PROJ)).startswith(str(PROJ)) for f in ign),
                       data_no_sandbox=(base / "data").exists())
    return base


def clona(base, nome):
    d = base.parent / nome
    sh(["cp", "-cpR", base, d])                         # -R sem -L: links continuam links
    return d


def roda(d, root, script, timeout=3600):
    return sh([PY, script], cwd=d, check=False, env=env_sbx(d, root), timeout=timeout)


def roda_checa(d, root, rot):
    t0 = time.time()
    r = roda(d, root, "scripts/etapa7b_checa.py")
    csv = d / "outputs/manuscrito/checa_7b_v12_20261013.csv"
    linhas = []
    if csv.exists():
        import pandas as pd
        x = pd.read_csv(csv)
        linhas = [(v, bool(o), str(val)[:200]) for v, o, val in zip(x.verificacao, x.ok, x.valor)]
    return dict(rotulo=rot, rc=r.returncode, seg=round(time.time() - t0, 1), linhas=linhas, erro=r.stderr[-1500:] if r.returncode else "",
                guarda=[l for l in r.stderr.splitlines() if "guarda do auditor" in l][:3])


def teste_guarda(base, root):
    alvo = sorted((base / "outputs/tables").iterdir())[0]
    # 1º teste inofensivo mesmo se a guarda falhar (abrir em 'a' e fechar sem escrever não muda o arquivo); o 2º só roda se o 1º
    # provar que a guarda está carregada
    prog = (f"import os, shutil, sys\ntry:\n    open({str(alvo)!r}, 'a').close()\n    print('ESCREVEU'); sys.exit(0)\n"
            f"except PermissionError:\n    print('BLOQUEOU')\n"
            f"try:\n    shutil.copyfile({str(alvo)!r}, {str(root / 'x.csv')!r})\n    print('COPIOU')\nexcept PermissionError:\n    print('BLOQUEOU')\n")
    r = sh([PY, "-c", prog], cwd=base, check=False, env=env_sbx(base, root))
    return dict(saida=r.stdout.split(), alvo=str(alvo.relative_to(base)), link=alvo.is_symlink(), sem_copia=not (root / "x.csv").exists())


def mut_desc(d):
    p = d / f"outputs/manuscrito/numeros_chave_{V12}.json"
    J = json.load(open(p))
    for i in J:
        if i["id"] == "n_regsaude_CE":
            i["descricao"] = "Health regions in Ceará (DATASUS territorial base, December 2024)"
    json.dump(J, open(p, "w"), ensure_ascii=False, indent=1)


def mut_grep(d):
    p = d / "outputs/manuscrito/data_code_availability.md"
    t = p.read_text()
    assert t.count('"^Etapa 7c.7:"') == 1
    p.write_text(t.replace('"^Etapa 7c.7:"', '"Etapa 7c.7"'))


def mutacao(base, root, nome, fn, alvo):
    d = clona(base, f"mut_{nome}")
    try:
        fn(d)
        r = roda_checa(d, root, nome)
    except Exception:
        r = dict(rotulo=nome, rc=-1, linhas=[], erro=traceback.format_exc()[-1500:])
    r["alvo"] = alvo
    shutil.rmtree(d, ignore_errors=True)
    return r


def commits(base, root):
    d = clona(base, "commit_S1")
    gitc(d, "add", "-A")
    ign_no_index = [p for p in gitc(d, "ls-files").splitlines() if p.startswith("outputs/tables/") or (p.startswith("audit_independente/") and p.endswith(".csv"))]
    gitc(d, "commit", "-q", "-m", "Etapa 7c.7: pacote v12 com as decisões da 7c.6b (SIMULADO pelo auditor)")
    h1 = gitc(d, "rev-parse", "--short", "HEAD").strip()
    g = lambda pat: gitc(d, "log", "--grep", pat, "--format=%h").split()
    out = dict(head=h1, pai=gitc(d, "rev-parse", "--short", "HEAD^").strip(), ignorados_no_commit=ign_no_index,
               grep_ancorado=g("^Etapa 7c.7:"), grep_76_ancorado=g("^Etapa 7c.6:"), grep_76_solto=g("Etapa 7c.6"))
    out["checa"] = roda_checa(d, root, "S1")
    gitc(d, "commit", "-q", "--allow-empty", "-m", "Etapa 7c.7b: commit seguinte (SIMULADO)")
    out["grep_ancorado_apos_7c7b"] = g("^Etapa 7c.7:")
    out["grep_solto_apos_7c7b"] = g("Etapa 7c.7")
    shutil.rmtree(d, ignore_errors=True)
    return out


def gerador(base, root):
    out = {}
    d = clona(base, "resumo")
    shutil.copy2(PROJ / "outputs/manuscrito/checa_7b_v12_20261013.csv", d / "outputs/manuscrito/checa_7b_v12_20261013.csv")  # rastreável, não ignorado
    p = d / "scripts/resumos/etapa7c7_01_resumo.py"
    t = p.read_text()
    alvo = '(PROJ / "outputs" / "RESUMO_ETAPA7C7_v1_20261013.md").write_text(out)'
    assert t.count(alvo) == 1
    p.write_text(t.replace(alvo, '(PROJ / "_saida_auditor" / "RESUMO.md").write_text(out)'))
    (d / "_saida_auditor").mkdir()
    r = roda(d, root, "scripts/resumos/etapa7c7_01_resumo.py")
    s = d / "_saida_auditor" / "RESUMO.md"
    real = (PROJ / "outputs/RESUMO_ETAPA7C7_v1_20261013.md").read_bytes()
    out["reproduz"] = dict(rc=r.returncode, igual=s.exists() and s.read_bytes() == real, md5_real=hashlib.md5(real).hexdigest(),
                           md5_sbx=md5(s) if s.exists() else "", erro=r.stderr[-600:],
                           comparacao_lida_mtime=time.strftime("%H:%M:%S", time.localtime((PROJ / "audit_independente/etapa7c7/comparacao_7c7_v1_20261013.csv").stat().st_mtime)))
    # v12 arquivada: o gerador tem de parar (LEIAME: "fixa a v12 do mesmo jeito")
    a12 = d / "outputs/manuscrito/_arquivo_v12"
    a12.mkdir()
    for f in [f"checa_7b_{V12}.csv", f"numeros_chave_{V12}.json", f"numeros_chave_{V12}.md"]:
        shutil.move(str(d / "outputs/manuscrito" / f), str(a12 / f))
    s.unlink(missing_ok=True)
    r2 = roda(d, root, "scripts/resumos/etapa7c7_01_resumo.py")
    tb = r2.stderr.strip().splitlines()
    out["apos_arquivar_v12"] = dict(rc=r2.returncode, ultima=tb[-1] if tb else "", linha=[l.strip() for l in tb if "etapa7c7_01_resumo.py" in l][-1:],
                                    gravou=s.exists())
    shutil.rmtree(d, ignore_errors=True)
    return out


def reproduz(base, root):
    d = clona(base, "repro")
    ex = {}
    for s in ("scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_03_figuras.py"):
        r = roda(d, root, s)
        ex[s] = dict(rc=r.returncode, err=r.stderr[-500:])
    from PIL import Image
    MSr, MSs = PROJ / "outputs/manuscrito", d / "outputs/manuscrito"
    comp = {}
    for rel in [f"numeros_chave_{V12}.json", f"numeros_chave_{V12}.md", "legendas_figuras.md"] + [f"tabelas/{x.name}" for x in sorted((MSr / "tabelas").glob("*.csv"))]:
        comp[rel] = (MSs / rel).exists() and md5(MSs / rel) == md5(MSr / rel)
    import openpyxl
    import docx
    cel = lambda f: [[(c.coordinate, c.value) for row in ws.iter_rows() for c in row if c.value is not None] for ws in openpyxl.load_workbook(f).worksheets]
    comp["tabelas_principais.xlsx (células)"] = cel(MSs / f"tabelas/tabelas_principais_{V12}.xlsx") == cel(MSr / f"tabelas/tabelas_principais_{V12}.xlsx")
    dx = lambda f: ([p.text for p in docx.Document(f).paragraphs], [[c.text for r in t.rows for c in r.cells] for t in docx.Document(f).tables])
    comp["tabelas_principais.docx (texto)"] = dx(MSs / f"tabelas/tabelas_principais_{V12}.docx") == dx(MSr / f"tabelas/tabelas_principais_{V12}.docx")
    px = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), hashlib.md5(im.tobytes()).hexdigest()))(Image.open(f))
    for x in sorted((MSr / "figuras").iterdir()):
        comp[f"figuras/{x.name}"] = px(MSs / "figuras" / x.name) == px(x)
    shutil.rmtree(d, ignore_errors=True)
    return dict(execucoes=ex, comparacoes=comp)


def main():
    foto0 = foto_ignorados()
    root = Path(tempfile.mkdtemp(prefix="aud7c7r2_", dir=SCRATCH))
    RES["sandbox"] = str(root)
    try:
        base = monta_base(root)
        RES["guarda"] = teste_guarda(base, root)
        if RES["guarda"]["saida"] != ["BLOQUEOU", "BLOQUEOU"]:          # sem guarda comprovada, nada roda
            raise RuntimeError(f"guarda não carregou: {RES['guarda']}")
        RES["linha_de_base"] = roda_checa(clona(base, "linha_base"), root, "linha_de_base")
        with ThreadPoolExecutor(max_workers=5) as ex:
            f1 = ex.submit(mutacao, base, root, "desc", mut_desc, "7c.7 n_regsaude_CE e n_regsaude_DF")
            f2 = ex.submit(mutacao, base, root, "grep", mut_grep, "7c.7 data_code_availability")
            f3 = ex.submit(commits, base, root)
            f4 = ex.submit(gerador, base, root)
            f5 = ex.submit(reproduz, base, root)
            for k, f in (("mut_desc", f1), ("mut_grep", f2), ("commits", f3), ("gerador", f4), ("reproducao", f5)):
                try:
                    RES[k] = f.result()
                except Exception:
                    RES[k] = {"erro": traceback.format_exc()[-2000:]}
    finally:
        shutil.rmtree(root, ignore_errors=True)
        RES["sandbox_apagado"] = not root.exists()
        foto1 = foto_ignorados()
        RES["ignorados_intactos"] = foto0 == foto1
        RES["ignorados_mudaram"] = sorted(k for k in set(foto0) | set(foto1) if foto0.get(k) != foto1.get(k))
        RES["n_ignorados_conferidos"] = len(foto0)
        RES["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
        json.dump(RES, open(OUTD / "sandbox_7c7_r2_v1_20261013.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
