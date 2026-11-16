"""Bloco E — sandbox fora do Forja (tempfile.mkdtemp em /var/folders): clone -s + estado de trabalho; ignorados só por link simbólico;
guarda própria (audit hook em sitecustomize) que bloqueia escrita/remoção/renomeação no Forja; checa de controle (137/137), mutações
dirigidas ao bloco 9j (e alguns pontos cegos), commit simulado com o checa de verdade, e o gerador do RESUMO (byte a byte). Sandbox apagado no fim."""
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comum_v1_20261026 import *
import csv
import openpyxl

B = Bloco("e")
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "PYTHONDONTWRITEBYTECODE": "1"}
TMP = Path(tempfile.mkdtemp(prefix="aud8b_ind_"))
B.ok("E0.01", "sandbox criado por tempfile.mkdtemp fora do Forja e fora de /private/tmp", str(TMP).startswith("/var/folders/") and "Forja" not in str(TMP), str(TMP))
BASE_S = TMP / "base"
GD = TMP / "guarda"
GUARDA = r'''
import os, sys
_F = "/Volumes/Forja"
def _no_forja(p):
    try:
        if isinstance(p, int) or p is None:
            return False
        r = os.path.realpath(os.fsdecode(p))
        return r == _F or r.startswith(_F + "/")
    except Exception:
        return False
def _h(ev, a):
    alvos = []
    if ev == "open":
        modo, flags = a[1], a[2]
        esc = (isinstance(modo, str) and any(c in modo for c in "wax+")) or (isinstance(flags, int) and (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        if esc:
            alvos = [a[0]]
    elif ev in ("os.remove", "os.unlink", "os.rmdir", "os.mkdir", "os.truncate", "os.chmod", "os.chown", "os.utime", "shutil.rmtree", "os.chflags"):
        alvos = [a[0]]
    elif ev in ("os.rename", "os.replace", "shutil.move", "shutil.copyfile", "shutil.copytree", "os.symlink", "os.link"):
        alvos = list(a[:2])
    if any(_no_forja(x) for x in alvos):
        raise PermissionError("guarda-auditor-8b: escrita no Forja bloqueada: %r %r" % (ev, alvos))
sys.addaudithook(_h)
'''


def py(d, code=None, script=None, timeout=1800):
    e = {**ENV, "PYTHONPATH": str(GD)}
    cmd = [sys.executable, "-c", code] if code else [sys.executable, script]
    return subprocess.run(cmd, cwd=d, capture_output=True, text=True, env=e, timeout=timeout)


def g(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=ENV, check=True).stdout


# estado de trabalho (status do projeto)
st = git("status", "--porcelain=v1", "-uall", "-z").split("\0")
mods, rens, novos = [], [], []
i = 0
while i < len(st):
    e = st[i]
    if not e:
        i += 1; continue
    if e[0] == "R":
        rens.append((st[i + 1], e[3:])); i += 2; continue
    if e.startswith("??"):
        novos.append(e[3:])
    elif e[:2].strip() == "M":
        mods.append(e[3:])
    i += 1
novos = [p for p in novos if not p.startswith("audit_independente/etapa8b/")]
VAI = sorted(mods + [b for _, b in rens] + [p for p in novos if not p.startswith("docs/referencias/")])


def monta():
    GD.mkdir()
    (GD / "sitecustomize.py").write_text(GUARDA)
    subprocess.run(["git", "clone", "-q", "-s", str(PROJ), str(BASE_S)], check=True, env=ENV)
    for a, b in rens:
        (BASE_S / a).unlink()
    for p in mods + [b for _, b in rens] + [p for p in novos if not p.startswith("docs/referencias/")]:
        (BASE_S / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJ / p, BASE_S / p)
    for p in novos:                                   # docs/referencias não versionados: só links (leitura)
        if p.startswith("docs/referencias/"):
            (BASE_S / p).parent.mkdir(parents=True, exist_ok=True)
            (BASE_S / p).symlink_to(PROJ / p)
    (BASE_S / "outputs/tables").mkdir(parents=True, exist_ok=True)
    for f in TB.iterdir():
        (BASE_S / "outputs/tables" / f.name).symlink_to(f)
    for f in (PROJ / "audit_independente").rglob("comparacao_*.csv"):
        if "etapa8b" in f.parts or f.name.startswith("._"):
            continue
        q = BASE_S / f.relative_to(PROJ)
        if not q.exists():
            q.parent.mkdir(parents=True, exist_ok=True); q.symlink_to(f)
    (BASE_S / "data/raw/aps_cobertura_ab").mkdir(parents=True)
    for f in (PROJ / "data/raw/aps_cobertura_ab").iterdir():
        if not f.name.startswith("._"):
            (BASE_S / "data/raw/aps_cobertura_ab" / f.name).symlink_to(f)
    (BASE_S / "outputs/logs").mkdir(parents=True, exist_ok=True)


SEM_ASSERT = ("import sys, re; sys.path.insert(0, 'scripts'); s = open('scripts/etapa7b_checa.py').read(); "
              "n = s.count('    assert cond, nome\\n'); assert n == 1, n; "
              "exec(compile(s.replace('    assert cond, nome\\n', '    pass\\n'), 'scripts/etapa7b_checa.py', 'exec'), {'__name__': '__main__'})")


def le_checa(d):
    p = d / f"outputs/manuscrito/checa_7b_{V14}.csv"
    if not p.exists():
        return None
    with open(p, newline="") as f:
        R = list(csv.DictReader(f))
    return R


def caso(nome, mut=None, real=False, commit=False):
    d = TMP / f"c_{abs(hash(nome)) % 10**8}"
    subprocess.run(["cp", "-cR", str(BASE_S), str(d)], check=True)
    try:
        if commit:
            gi = ["-c", "user.name=auditor8b", "-c", "user.email=auditor8b@local"]
            subprocess.run(["git", "-C", str(d), "add", "-A", "--", *VAI, *[a for a, _ in rens]], check=True, env=ENV, capture_output=True)
            subprocess.run(["git", "-C", str(d), *gi, "commit", "-q", "-m", "Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)"], check=True, env=ENV, capture_output=True)
            res_c = g(d, "show", "--stat", "--format=", "HEAD").strip().splitlines()[-1]
        if mut:
            mut(d)
        (d / f"outputs/manuscrito/checa_7b_{V14}.csv").unlink()
        r = py(d, script="scripts/etapa7b_checa.py") if real else py(d, code=SEM_ASSERT)
        R = le_checa(d)
        out = {"rc": r.returncode, "n": len(R) if R else 0, "falhas": [x["verificacao"] for x in R if x["ok"] != "True"] if R else None,
               "err": r.stderr[-400:], "rot": [x["verificacao"] for x in R] if R else []}
        if commit:
            out["pai"] = g(d, "rev-parse", "--short", "HEAD^").strip(); out["stat"] = res_c
            out["status"] = g(d, "status", "--porcelain", "-uno").strip()
        return out
    finally:
        shutil.rmtree(d, ignore_errors=True)


S2B = f"outputs/manuscrito/suplementar/S2b_access_specifications_{V14}.csv"
ESM = f"outputs/manuscrito/suplementar/ESM_1_tables_S1_S6_{V14}.xlsx"
JS = f"outputs/manuscrito/numeros_chave_{V14}.json"


def txt_troca(rel, a, b, n=1):
    def f(d):
        p = d / rel; s = p.read_text(encoding="utf-8")
        assert s.count(a) >= 1, (rel, a)
        p.write_text(s.replace(a, b, n), encoding="utf-8")
    return f


def troca_6gl_csv(d):                    # p de 6 gl da PTB total trocado entre (d) e (e)
    p = d / S2B
    with open(p, newline="", encoding="utf-8") as f:
        R = list(csv.reader(f))
    h = R[0]; i, j = h.index(h[7]), h.index(h[10])
    R[1][i], R[1][j] = R[1][j], R[1][i]
    with open(p, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(R)


def xl_set(rel, aba, linha, col, novo=None, troca_com=None):
    def f(d):
        p = d / rel
        wb = openpyxl.load_workbook(p)
        ws = wb[aba]
        if troca_com:
            a, b = ws.cell(linha, col).value, ws.cell(*troca_com).value
            ws.cell(linha, col).value, ws.cell(*troca_com).value = b, a
        else:
            ws.cell(linha, col).value = novo
        wb.save(p)
    return f


def js(fun):
    def f(d):
        p = d / JS
        J = json.load(open(p)); fun(J)
        json.dump(J, open(p, "w"), ensure_ascii=False, indent=1, default=float)
    return f


def px_s9(d):
    from PIL import Image
    p = d / f"outputs/manuscrito/suplementar/S9_maihda_caterpillar_{V14}.png"
    im = Image.open(p); dpi = im.info.get("dpi"); im = im.convert(im.mode)
    x = im.getpixel((10, 10)); im.putpixel((10, 10), tuple(255 - v for v in x) if isinstance(x, tuple) else 255 - x)
    im.save(p, dpi=dpi)


def docx_par(d):
    p = d / f"outputs/manuscrito/tabelas/tabelas_principais_{V14}.docx"
    z = zipfile.ZipFile(p); parts = {n: z.read(n) for n in z.namelist()}; z.close()
    s = parts["word/document.xml"].decode()
    k = s.index("Sources:")
    parts["word/document.xml"] = (s[:k] + "Fontes:" + s[k + 8:]).encode()
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)


def json_extra(J):
    x = dict(J[-1]); x["id"] = "Wald6_extra"; J.append(x)


MUT = [
    ("M01", "p de 6 gl da PTB total trocado entre (d) e (e) no CSV da S2b", troca_6gl_csv, "8b S2b: colunas novas"),
    ("M02", "p de 6 gl da PTB total trocado entre (d) e (e) só no ESM_1 do pacote (CSV e JSON certos)", xl_set(ESM, "S2b_access_specifications", 4, 8, troca_com=(4, 11)), None),
    ("M03", "número-chave a mais no JSON (cópia de Wald6 com id novo)", js(json_extra), "8b números-chave"),
    ("M04", "valor_formatado de Wald6_aps_ptb e Wald6_indice_2015_2021_ptb trocados no JSON e na S2b (troca coerente d↔e)",
     lambda d: (js(lambda J: [i.update(valor_formatado={"Wald6_aps_ptb": "0.00284", "Wald6_indice_2015_2021_ptb": "0.00369"}[i["id"]]) for i in J if i["id"] in ("Wald6_aps_ptb", "Wald6_indice_2015_2021_ptb")])(d), troca_6gl_csv(d)), "8b commit_registro recalculado"),
    ("M05", "um dígito de um CSV da v14 fora da S2b (S3_multinomial)", txt_troca(f"outputs/manuscrito/suplementar/S3_multinomial_{V14}.csv", "0.", "1."), "8b v13 × v14 célula a célula"),
    ("M06", "rótulo '(6 df)' trocado por '(4 df)' no rodapé da S2b (ESM_1 do pacote e de Submissao/)",
     lambda d: _rodape(d), "8b ESM_1"),
    ("M07", "legendas_figuras.md com uma palavra trocada", txt_troca("outputs/manuscrito/legendas_figuras.md", "Open circles", "Open squares"), "8b data_code_availability"),
    ("M08", "parágrafo do docx v14 alterado ('Sources:' → 'Fontes:')", docx_par, "8b tabelas principais"),
    ("M09", "célula de dados de outra aba do ESM_1 v14 (S3, linha 4, col 2) alterada", xl_set(ESM, "S3_multinomial", 4, 2, "9.99 (9.99–9.99)"), None),
    ("M10", "célula de dados da Tabela 2 no tabelas_principais.xlsx v14 alterada", xl_set(f"outputs/manuscrito/tabelas/tabelas_principais_{V14}.xlsx", "tab02_models_m1m3", 4, 2, "9.99 (9.99–9.99)"), None),
    ("M11", "um pixel da S9 (png, em suplementar/) da v14", px_s9, None),
    ("M12", "MANIFEST arquivado da v13 alterado (uma palavra)", txt_troca(f"outputs/manuscrito/_arquivo_v13/MANIFEST_{V13}.md", "Gerado em", "Gerada em"), None),
    ("M13", "numeros_chave_v13.md arquivado alterado (um valor)", txt_troca(f"outputs/manuscrito/_arquivo_v13/numeros_chave_{V13}.md", "| 0.107 |", "| 0.108 |"), None),
    ("M14", "valor_bruto de Wald6_aps_ptb alterado no JSON (formatado igual)", js(lambda J: [i.update(valor_bruto=0.0037) for i in J if i["id"] == "Wald6_aps_ptb"]), None),
    ("M15", "data_code_availability com o título do commit da Etapa 8 (v13) no lugar do da 8b", txt_troca("outputs/manuscrito/data_code_availability.md", "Etapa 8b: Wald de 6 gl da cobertura na S2b (pacote v14)", "Etapa 8: sensibilidade com a cobertura da Atenção Básica (pacote v13)"), "8b data_code_availability"),
]


def _rodape(d):
    for rel in (ESM, "Submissao/ESM_1.xlsx"):
        p = d / rel
        wb = openpyxl.load_workbook(p); ws = wb["S2b_access_specifications"]
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and "as in (b) (6 df)" in c.value:
                    c.value = c.value.replace("as in (b) (6 df)", "as in (b) (4 df)")
        wb.save(p)


try:
    monta()
    # guarda
    alvo = sorted(f.name for f in (BASE_S / "outputs/tables").iterdir())[0]
    g1 = py(BASE_S, code=f"open('outputs/tables/{alvo}', 'a')")
    g2 = py(BASE_S, code=f"import os; os.remove('outputs/tables/{alvo}')")
    g3 = py(BASE_S, code="open('/Volumes/Forja/ptb-racial-brasil/outputs/logs/x_guarda_auditor.txt', 'w')")
    g4 = py(BASE_S, code="open('outputs/logs/x.txt', 'w').write('x')")
    g5 = py(BASE_S, code="import os; os.rename('docs/referencias/' + os.listdir('docs/referencias')[0], 'zz')")
    bloq = [r.returncode != 0 and "guarda-auditor-8b" in r.stderr for r in (g1, g2, g3)]
    B.ok("E1.01", "guarda: escrever/remover por link de outputs/tables e escrever direto no Forja bloqueados; escrever no sandbox funciona",
         all(bloq) and g4.returncode == 0 and not (PROJ / "outputs/logs/x_guarda_auditor.txt").exists(), [bloq, g4.returncode, g5.returncode])
    (BASE_S / "outputs/logs/x.txt").unlink(missing_ok=True)
    if not all(bloq):
        raise SystemExit("guarda falhou")
    with cf.ThreadPoolExecutor(4) as ex:
        f0 = ex.submit(caso, "controle")
        fr = ex.submit(caso, "controle_real", None, True)
        fc = ex.submit(caso, "commit", None, True, True)
        fm = {k: ex.submit(caso, k, m) for k, _, m, _ in MUT}
        r0, rr, rc = f0.result(), fr.result(), fc.result()
        rm = {k: f.result() for k, f in fm.items()}
    proj_rot = [r["verificacao"] for r in csv.DictReader(open(MS / f"checa_7b_{V14}.csv", newline=""))]
    B.ok("E2.01", "controle (checa sem assert): 137/137, mesmos rótulos e mesma ordem do checa_7b_v14 do projeto",
         r0["n"] == 137 and r0["falhas"] == [] and r0["rot"] == proj_rot, f"{r0['n']}; falhas {r0['falhas']}; err {r0['err'][-150:] if r0['rc'] else ''}")
    B.ok("E2.02", "checa de verdade (com assert) no sandbox: termina sem erro, 137/137", rr["rc"] == 0 and rr["n"] == 137 and rr["falhas"] == [], f"rc {rr['rc']}; {rr['n']}")
    nj = sum(1 for x in proj_rot if x.startswith("8b "))
    B.ok("E2.03", "bloco 9j: 9 verificações com prefixo '8b ' no checa", nj == 9, nj)
    B.ok("E2.04", "commit simulado com só os arquivos previstos (sem docs/referencias): o checa de verdade dá 137/137; pai = cdddf8f; nada fica por commitar",
         rc["rc"] == 0 and rc["n"] == 137 and rc["falhas"] == [] and rc["pai"] == "cdddf8f" and rc["status"] == "", f"{rc['n']}; pai {rc['pai']}; {rc['stat']}; status '{rc['status'][:80]}'; err {rc['err'][-120:] if rc['rc'] else ''}")
    for k, desc, _, alvo in MUT:
        r = rm[k]
        fl = r["falhas"] or []
        if alvo:
            B.ok(f"E3.{k[1:]}", f"mutação {k} ({desc}): o checa acusa '{alvo}'", r["falhas"] is not None and any(x.startswith(alvo) for x in fl),
                 f"falhas {[x[:50] for x in fl][:4]}; rc {r['rc']}")
        else:
            pega = r["falhas"] is not None and len(fl) > 0
            B.ok(f"E4.{k[1:]}", f"[ponto cego?] mutação {k} ({desc}): detectada pelo checa? → {'sim' if pega else 'NÃO'}", True,
                 f"falhas {[x[:60] for x in fl][:4]}; rc {r['rc']}")
    # gerador do RESUMO (sem o CSV do auditor no sandbox, como no projeto agora)
    d = TMP / "resumo"
    subprocess.run(["cp", "-cR", str(BASE_S), str(d)], check=True)
    r = subprocess.run([sys.executable, "scripts/resumos/etapa8b_01_resumo.py"], cwd=d, capture_output=True, text=True,
                       env={**ENV, "PYTHONPATH": os.pathsep.join([str(GD), str(d / "scripts")])}, timeout=600)
    igual = (d / "outputs/RESUMO_ETAPA8b_v1_20261026.md").read_bytes() == (PROJ / "outputs/RESUMO_ETAPA8b_v1_20261026.md").read_bytes()
    B.ok("E5.01", "gerador do RESUMO no sandbox (sem CSV do auditor): reproduz o RESUMO do projeto byte a byte", r.returncode == 0 and igual,
         f"rc {r.returncode}; {r.stderr[-200:]}")
    lg = (d / "outputs/logs/etapa8b_20261008.log").read_text() if (d / "outputs/logs/etapa8b_20261008.log").exists() else ""
    B.ok("E5.02", "o gerador grava só no sandbox (log e RESUMO); projeto intacto", "RESUMO_ETAPA8b gravado" in lg and
         (PROJ / "outputs/logs/etapa8b_20261008.log").stat().st_size == 127, lg[-160:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
B.ok("E9.01", "sandbox apagado", not TMP.exists(), str(TMP))
B.grava()
