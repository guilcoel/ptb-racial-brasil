"""
Auditor independente da Etapa 7c.7 — testes dinâmicos em sandbox (módulo do audita_7c7_v1_20261013.py).

Monta uma cópia do projeto no scratch do sistema (/private/tmp/...), SEM data/, e roda lá:
  - o etapa7b_checa.py (cópia com o `assert` desligado, para registrar todas as verificações) na linha de base, depois de
    mutações dirigidas a cada verificação do bloco 9h e ao 9g re-apontado, e depois de commits simulados num clone descartável;
  - a função pacote_esperado (extraída do checa) nos dois ramos;
  - as cópias do etapa7c6_02_audita_final.py, do resumos/etapa7c6_01_resumo.py, do resumos/etapa7c5b_01_resumo.py e do
    resumos/etapa7c6b_01_resumo.py (afirmações do LEIAME), com a saída desviada;
  - o etapa7c7_01_regsaude_uf.py com um audit hook que registra cada arquivo aberto;
  - os geradores 01 e 03 do pacote (reprodução das saídas; 02 e 04 não, porque chamam o Chrome, que mexe fora do projeto).
Nada é gravado no projeto: o clone é feito com `git clone --no-checkout` (só leitura na origem) e o índice real é copiado.
O resultado vai para audit_independente/etapa7c7/sandbox_7c7_v1_20261013.json. O sandbox é apagado no fim.
Rodar: python3 audit_independente/etapa7c7/audita_7c7_sandbox_v1_20261013.py
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
SCRATCH = Path("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad")
V11, V12 = "v11_20261009", "v12_20261013"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", PYTHONDONTWRITEBYTECODE="1")
PY = sys.executable
RES = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S")}


def sh(cmd, cwd=None, check=True, env=None, timeout=1800):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env=env or ENV, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.returncode}\n{r.stderr[-2000:]}")
    return r


def git_real(*a):
    return sh(["git", "-C", PROJ, *a]).stdout


def gitc(d, *a, check=True):
    return sh(["git", "-C", d, "-c", "user.name=auditor7c7", "-c", "user.email=auditor@example.invalid", *a], check=check).stdout


# ------------------------------------------------------------------ sandbox base
def monta_base(root):
    base = root / "base"
    sh(["git", "clone", "--quiet", "--no-checkout", PROJ, base])
    gitc(base, "remote", "remove", "origin")
    shutil.copy2(PROJ / ".git" / "index", base / ".git" / "index")           # índice real (38 renomeações em stage)
    tracked = [p for p in git_real("ls-files", "-z").split("\0") if p]
    untracked = [p for p in git_real("ls-files", "-o", "--exclude-standard", "-z").split("\0") if p]
    pula = {"outputs/manuscrito/checa_7b_v12_20261013.csv", "outputs/manuscrito/audita_7c7_v1_20261013.csv"}
    n = 0
    for p in tracked + untracked:   # docs/referencias não rastreados entram: a base territorial (rl_municip_regsaud.csv) está lá
        if p.startswith(("data/", "audit_independente/etapa7c7/")) or p in pula:
            continue
        src = PROJ / p
        if src.is_file():
            (base / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, base / p)
            n += 1
    for f in sorted((PROJ / "outputs" / "tables").iterdir()):                 # ignorado pelo git; lido pelo checa e pelo 01
        if f.is_file() and not f.name.startswith("._"):
            (base / "outputs/tables").mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, base / "outputs/tables" / f.name)
            n += 1
    for f in sorted((PROJ / "audit_independente").glob("*/comparacao_*.csv")):  # lidos pelo checa e pelo 7c6b_01
        (base / f.relative_to(PROJ)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, base / f.relative_to(PROJ))
        n += 1
    (base / "outputs/logs").mkdir(parents=True, exist_ok=True)
    ck = base / "scripts" / "etapa7b_checa.py"
    src = ck.read_text()
    assert src.count("    assert cond, nome\n") == 1
    ck.write_text(src.replace("    assert cond, nome\n", "    pass  # [auditor 7c.7] assert desligado nesta cópia\n"))
    ls_b = gitc(base, "ls-files", "-s")
    ls_r = git_real("ls-files", "-s")
    RES["base"] = dict(arquivos=n, indice_igual=ls_b == ls_r, head=gitc(base, "rev-parse", "--short", "HEAD").strip())
    return base


def clona(base, nome):
    d = base.parent / nome
    sh(["cp", "-cpR", base, d])
    return d


def roda_checa(d, rotulo):
    t0 = time.time()
    r = sh([PY, "scripts/etapa7b_checa.py"], cwd=d, check=False, env=dict(ENV, PYTHONPATH=str(d / "scripts")), timeout=3600)
    csv = d / "outputs/manuscrito/checa_7b_v12_20261013.csv"
    linhas = []
    if csv.exists():
        import pandas as pd
        x = pd.read_csv(csv)
        linhas = [(v, bool(o)) for v, o in zip(x.verificacao, x.ok)]
    return dict(rotulo=rotulo, rc=r.returncode, seg=round(time.time() - t0, 1), n=len(linhas), linhas=linhas,
                erro=r.stderr[-1500:] if r.returncode else "")


# ------------------------------------------------------------------ mutações
def _json_edit(d, fn, rel=f"outputs/manuscrito/numeros_chave_{V12}.json"):
    p = d / rel
    J = json.load(open(p))
    fn(J)
    json.dump(J, open(p, "w"), ensure_ascii=False, indent=1)


def _xlsx_rodape(p, aba_prefixo):
    import openpyxl
    wb = openpyxl.load_workbook(p)
    ws = [w for w in wb.worksheets if w.title.startswith(aba_prefixo)][0]
    ult = [c for row in ws.iter_rows() for c in row if c.value is not None][-1]
    ult.value = str(ult.value) + " [mutado]"
    wb.save(p)


def _px(p):
    from PIL import Image
    im = Image.open(p)
    info = {k: v for k, v in im.info.items() if k in ("dpi",)}
    im = im.copy()
    x, y = im.size[0] // 2, im.size[1] // 2
    v = im.getpixel((x, y))
    nv = tuple((c + 37) % 256 for c in v) if isinstance(v, tuple) else (v + 37) % 256
    im.putpixel((x, y), nv)
    kw = dict(dpi=info["dpi"]) if "dpi" in info else {}
    if p.suffix == ".tif":
        kw["compression"] = "tiff_lzw"
    im.save(p, **kw)


def m01(d):   # 9h-1: descrição de um número antigo muda só na v12
    def f(J):
        J[0]["descricao"] += " [mutado]"
    _json_edit(d, f)


def m02(d):   # 9h-2: commit_pacote de um item
    def f(J):
        J[-1]["commit_pacote"] = "0000000"
    _json_edit(d, f)


def m03(d):   # 9h-3: base territorial com uma região de saúde a mais no CE (a recontagem tem de divergir do JSON)
    p = d / "docs/referencias/territorio_dez24/rl_municip_regsaud.csv"
    t = p.read_text()
    i = t.index('"23')
    j = t.index("\n", i)
    linha = t[i:j]
    nova = re.sub(r'"(23\d{4})","\d+"', r'"\1","23099"', linha)
    assert nova != linha
    p.write_text(t[:i] + nova + t[j:])


def m04(d):   # 9h-4: commit_registro de um número antigo trocado na v11 arquivada E na v12 (9h-1 continua igual)
    def f(J):
        J[3]["commit_registro"] = "abc1234"
    _json_edit(d, f)
    _json_edit(d, f, rel=f"outputs/manuscrito/_arquivo_v11/numeros_chave_{V11}.json")


def m05(d):   # 9h-5: uma célula de texto num CSV suplementar da v12
    p = d / f"outputs/manuscrito/suplementar/S3_multinomial_{V12}.csv"
    t = p.read_text()
    assert "Brown" in t
    p.write_text(t.replace("Brown", "Browm", 1))


def m06(d):   # 9h-6: rodapé da Tabela 1 no xlsx das tabelas principais da v12
    _xlsx_rodape(d / f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.xlsx", "tab01_")


def m07(d):   # 9h-7: rodapé da S3 no ESM_1 de Submissao/
    _xlsx_rodape(d / "Submissao/ESM_1.xlsx", "S3_")


def m08(d):   # 9h-8: uma célula de tabela no docx da v12
    import docx
    p = d / f"outputs/manuscrito/tabelas/tabelas_principais_{V12}.docx"
    D = docx.Document(p)
    c = D.tables[0].rows[1].cells[1]
    c.paragraphs[0].add_run(" [mutado]")
    D.save(p)


def m09(d):   # 9h-9: uma frase a mais na disponibilidade
    p = d / "outputs/manuscrito/data_code_availability.md"
    p.write_text(p.read_text() + "\nExtra sentence added by the auditor.\n")


def m10(d):   # 9h-10: legenda da Fig. 2 com uma palavra a mais
    p = d / "outputs/manuscrito/legendas_figuras.md"
    t = p.read_text()
    assert "**Fig. 2" in t
    p.write_text(t.replace("**Fig. 2", "**Fig. 2 [mutado]", 1))


def m11(d):   # 9h-11: um pixel na fig02 png da v12
    _px(d / f"outputs/manuscrito/figuras/fig02_pr_race_m1m3_{V12}.png")


def m12(d):   # 9h-12: um ._* em outputs/manuscrito
    (d / "outputs/manuscrito/._mutacao_auditor").write_bytes(b"\x00\x05\x16\x07")


def m12b(d):  # 9h-12: o 02 sem a chamada do dot_clean
    p = d / "scripts/etapa7b_02_suplementar.py"
    t = p.read_text()
    alvo = 'subprocess.run(["dot_clean", "-m", str(B.SUPD)], check=True)'
    assert alvo in t
    p.write_text(t.replace(alvo, "pass  # [auditor] dot_clean removido"))


def m13(d):   # 9h-13: código (não docstring) do etapa2_03
    p = d / "scripts/etapa2_03_indice_acesso.py"
    t = p.read_text()
    assert t.count("mes.between(1, 9)") == 1
    p.write_text(t.replace("mes.between(1, 9)", "mes.between(1, 8)"))


def m14(d):   # 9g: uma célula de CSV na v11 arquivada (o 9g tem de pegar)
    p = d / f"outputs/manuscrito/_arquivo_v11/suplementar/S3_multinomial_{V11}.csv"
    t = p.read_text()
    p.write_text(t.replace("Brown", "Browm", 1))


def m15(d):   # 9g: um pixel na Fig2.tif de _arquivo_v11/Submissao
    _px(d / "outputs/manuscrito/_arquivo_v11/Submissao/Fig2.tif")


def m16(d):   # 9g: frase a mais na disponibilidade arquivada da v11
    p = d / f"outputs/manuscrito/_arquivo_v11/data_code_availability_{V11}.md"
    p.write_text(p.read_text() + "\nExtra sentence added by the auditor.\n")


MUT = {  # id: (função, verificação-alvo (prefixo do nome no checa), descrição)
    "M01": (m01, "7c.7 números-chave", "descrição de um número antigo alterada só na v12"),
    "M02": (m02, "7c.7 commit_pacote", "commit_pacote de um item = 0000000"),
    "M03": (m03, "7c.7 n_regsaude_CE e n_regsaude_DF", "rl_municip_regsaud: um município do CE numa região nova (23099)"),
    "M04": (m04, "7c.7 commit_registro recalculado", "commit_registro de um número antigo = abc1234 na v11 arquivada e na v12"),
    "M05": (m05, "7c.7 v11 × v12 célula a célula", "S3 v12: 'Brown' → 'Browm' numa célula"),
    "M06": (m06, "7c.7 tabelas principais (xlsx)", "rodapé da Tabela 1 no xlsx v12 + ' [mutado]'"),
    "M07": (m07, "7c.7 ESM_1", "rodapé da S3 no Submissao/ESM_1.xlsx + ' [mutado]'"),
    "M08": (m08, "7c.7 docx", "célula [1,1] da 1ª tabela do docx v12 + ' [mutado]'"),
    "M09": (m09, "7c.7 data_code_availability", "frase a mais na disponibilidade v12"),
    "M10": (m10, "7c.7 legendas das figuras", "'**Fig. 2' → '**Fig. 2 [mutado]' nas legendas v12"),
    "M11": (m11, "7c.7 figuras (png e tif)", "um pixel alterado na fig02 png da v12"),
    "M12": (m12, "7c.7 ._*", "arquivo outputs/manuscrito/._mutacao_auditor"),
    "M12b": (m12b, "7c.7 ._*", "chamada do dot_clean removida do 02"),
    "M13": (m13, "7c.7 etapa2_03", "etapa2_03: mes.between(1, 9) → (1, 8)"),
    "M14": (m14, "7c.6 v10 × v11 célula a célula", "S3 da v11 arquivada: 'Brown' → 'Browm'"),
    "M15": (m15, "7c.6 Submissao/", "um pixel na Fig2.tif de _arquivo_v11/Submissao"),
    "M16": (m16, "7c.6 data_code_availability", "frase a mais na disponibilidade arquivada da v11"),
}


def roda_mutacao(base, mid):
    fn, alvo, desc = MUT[mid]
    d = clona(base, f"mut_{mid}")
    try:
        fn(d)
        r = roda_checa(d, mid)
    except Exception:
        r = dict(rotulo=mid, rc=-1, n=0, linhas=[], erro=traceback.format_exc()[-1500:])
    r.update(alvo=alvo, desc=desc)
    shutil.rmtree(d, ignore_errors=True)
    return r


# ------------------------------------------------------------------ commits simulados
def extrai_pacote_esperado(src_checa):
    m = ast.parse(src_checa)
    fn = [n for n in m.body if isinstance(n, ast.FunctionDef) and n.name == "pacote_esperado"][0]
    return ast.get_source_segment(src_checa, fn)


def chama_pacote_esperado(fonte, proj, commit_atual, versao):
    ns = {"subprocess": subprocess, "B": SimpleNamespace(PROJ=Path(proj), COMMIT=commit_atual)}
    old = os.environ.get("GIT_OPTIONAL_LOCKS")
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        exec(fonte, ns)
        return ns["pacote_esperado"](versao)
    finally:
        if old is None:
            os.environ.pop("GIT_OPTIONAL_LOCKS", None)
        else:
            os.environ["GIT_OPTIONAL_LOCKS"] = old


def cenarios_commit(base):
    fonte = extrai_pacote_esperado((PROJ / "scripts" / "etapa7b_checa.py").read_text())
    out = {"fonte_pacote_esperado": fonte}
    head_real = git_real("rev-parse", "--short", "HEAD").strip()
    out["real_v11"] = chama_pacote_esperado(fonte, PROJ, head_real, V11)          # só git log/rev-parse no repo real
    out["real_v12"] = chama_pacote_esperado(fonte, PROJ, head_real, V12)
    out["head_real"] = head_real
    # S1: commit único da etapa (tudo junto), como planejado
    s1 = clona(base, "commit_S1")
    gitc(s1, "add", "-A")
    gitc(s1, "commit", "-q", "-m", "Etapa 7c.7: pacote v12 com as decisões da 7c.6b (SIMULADO pelo auditor)")
    h1 = gitc(s1, "rev-parse", "--short", "HEAD").strip()
    J12 = json.load(open(s1 / f"outputs/manuscrito/numeros_chave_{V12}.json"))
    out["S1"] = dict(head=h1, pai=gitc(s1, "rev-parse", "--short", "HEAD^").strip(),
                     esp_v12=chama_pacote_esperado(fonte, s1, h1, V12), esp_v11=chama_pacote_esperado(fonte, s1, h1, V11),
                     commit_pacote_json=sorted({i["commit_pacote"] for i in J12}),
                     regra_antiga_passaria=all(i["commit_pacote"] == h1 for i in J12),
                     arquivos_no_commit=len(gitc(s1, "show", "--format=", "--name-only", "HEAD").split()))
    out["S1"]["checa"] = roda_checa(s1, "S1_commit_unico")
    shutil.rmtree(s1, ignore_errors=True)
    # S2: docstring do etapa2_03 num commit próprio antes (o plano antigo); depois o resto
    s2 = clona(base, "commit_S2")
    gitc(s2, "add", "scripts/etapa2_03_indice_acesso.py")
    gitc(s2, "commit", "-q", "-m", "etapa2_03: docstring (SIMULADO)")
    gitc(s2, "add", "-A")
    gitc(s2, "commit", "-q", "-m", "Etapa 7c.7 (SIMULADO)")
    h2 = gitc(s2, "rev-parse", "--short", "HEAD").strip()
    out["S2"] = dict(head=h2, esp_v12=chama_pacote_esperado(fonte, s2, h2, V12), commit_pacote_json=sorted({i["commit_pacote"] for i in J12}))
    r2 = roda_checa(s2, "S2_dois_commits")
    out["S2"]["checa_falhas"] = [v for v, o in r2["linhas"] if not o]
    out["S2"]["checa_n"] = r2["n"]
    shutil.rmtree(s2, ignore_errors=True)
    # S0: antes do commit (HEAD = dc9328d no clone)
    out["S0_v12"] = chama_pacote_esperado(fonte, base, gitc(base, "rev-parse", "--short", "HEAD").strip(), V12)
    return out


# ------------------------------------------------------------------ LEIAME: scripts que param depois do arquivamento
def roda_copia(base, nome, rel, trocas):
    d = clona(base, nome)
    p = d / rel
    t = p.read_text()
    desv = []
    for a, b in trocas:                                   # saída desviada para dentro do sandbox (pasta _saida_auditor)
        if a in t:
            t = t.replace(a, b)
            desv.append(a)
    p.write_text(t)
    (d / "_saida_auditor").mkdir(exist_ok=True)
    antes = {str(x.relative_to(d)) for x in d.rglob("*") if x.is_file() and ".git/" not in str(x)}
    r = sh([PY, rel], cwd=d, check=False, env=dict(ENV, PYTHONPATH=str(d / "scripts")), timeout=3600)
    depois = {str(x.relative_to(d)) for x in d.rglob("*") if x.is_file() and ".git/" not in str(x)}
    tb = r.stderr.strip().splitlines()
    linha = [l for l in tb if l.strip().startswith(f'File "{p}"')]
    res = dict(rc=r.returncode, ultima=tb[-1] if tb else "", linha_erro=linha[-1].strip() if linha else "", desviado=desv,
               novos=sorted(depois - antes), stdout_tail=r.stdout[-400:])
    if nome == "leiame_7c6b":
        out = d / "_saida_auditor" / "RESUMO_7c6b.md"
        res["igual_commitado"] = out.exists() and out.read_bytes() == sh(
            ["git", "-C", PROJ, "show", "dc9328d:outputs/RESUMO_ETAPA7C6b_v1_20261010.md"], env=ENV).stdout.encode()
    shutil.rmtree(d, ignore_errors=True)
    return res


def testes_leiame(base):
    out = {}
    out["audita_final_7c6b"] = roda_copia(base, "leiame_af", "scripts/etapa7c6_02_audita_final.py",
                                          [('SAIDA = MS / "audita_final_7c6_v1_20261010.csv"', 'SAIDA = PROJ / "_saida_auditor" / "af.csv"')])
    out["resumo_7c6"] = roda_copia(base, "leiame_7c6", "scripts/resumos/etapa7c6_01_resumo.py",
                                   [('(B.PROJ / "outputs" / "RESUMO_ETAPA7C6_v1_20261009.md").write_text(out)',
                                     '(B.PROJ / "_saida_auditor" / "RESUMO_7c6.md").write_text(out)')])
    out["resumo_7c5b"] = roda_copia(base, "leiame_7c5b", "scripts/resumos/etapa7c5b_01_resumo.py",
                                    [('(B.PROJ / "outputs" / "RESUMO_ETAPA7C5b_v1_20261009.md").write_text(out)',
                                      '(B.PROJ / "_saida_auditor" / "RESUMO_7c5b.md").write_text(out)')])
    out["resumo_7c6b"] = roda_copia(base, "leiame_7c6b", "scripts/resumos/etapa7c6b_01_resumo.py",
                                    [('(PROJ / "outputs" / "RESUMO_ETAPA7C6b_v1_20261010.md").write_text(out)',
                                      '(PROJ / "_saida_auditor" / "RESUMO_7c6b.md").write_text(out)')])
    return out


# ------------------------------------------------------------------ etapa7c7_01 com audit hook
HOOK = r'''
import sys, json, runpy
LOG = []
def _h(ev, args):
    if ev == "open":
        LOG.append(["open", str(args[0]), str(args[1]), args[2] if len(args) > 2 else None])
    elif ev.startswith(("os.", "shutil.")) and ev not in ("os.listdir", "os.scandir", "os.chdir", "os.walk", "os.putenv", "os.unsetenv"):
        LOG.append([ev, *[str(a) for a in args[:2]]])
sys.addaudithook(_h)
sys.argv = [sys.argv[1]]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    sys.audithook_log = LOG
    import builtins
    f = builtins.open(sys.argv_saida if hasattr(sys, "argv_saida") else "_hook_log.json", "w")
    json.dump(LOG, f)
    f.close()
'''


def testa_7c7_01(base):
    d = clona(base, "hook_7c7_01")
    tab = d / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv"
    tab.unlink()
    (d / "_hook.py").write_text(HOOK)
    r = sh([PY, "_hook.py", "scripts/etapa7c7_01_regsaude_uf.py"], cwd=d, check=False, env=dict(ENV, PYTHONPATH=str(d / "scripts")))
    log = json.load(open(d / "_hook_log.json")) if (d / "_hook_log.json").exists() else []
    pref = str(d.resolve())
    proj_ev = []
    for e in log:
        p = e[1] if len(e) > 1 else ""
        if p.startswith(pref) or (not p.startswith("/") and p not in ("", "None") and not p.isdigit()):
            rel = p[len(pref) + 1:] if p.startswith(pref) else p
            if rel.endswith((".py", ".pyc")) and rel.startswith("scripts/"):
                continue
            if rel == "_hook_log.json":
                continue
            proj_ev.append([e[0], rel, *e[2:]])
    real = (PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv").read_bytes()
    out = dict(rc=r.returncode, eventos=proj_ev, tabela_reproduzida=tab.exists() and tab.read_bytes() == real,
               stderr=r.stderr[-800:], stdout=r.stdout[-800:])
    shutil.rmtree(d, ignore_errors=True)
    return out


# ------------------------------------------------------------------ reprodução do 01 e do 03
def reproduz(base):
    d = clona(base, "repro")
    outs = {}
    for s in ("scripts/etapa7b_01_tabelas.py", "scripts/etapa7b_03_figuras.py"):
        r = sh([PY, s], cwd=d, check=False, env=dict(ENV, PYTHONPATH=str(d / "scripts"), MPLBACKEND="Agg"), timeout=3600)
        outs[s] = dict(rc=r.returncode, err=r.stderr[-600:])
    import hashlib
    md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
    comp = {}
    MS_r, MS_s = PROJ / "outputs/manuscrito", d / "outputs/manuscrito"
    for rel in [f"numeros_chave_{V12}.json", f"numeros_chave_{V12}.md", "legendas_figuras.md"] + \
               [f"tabelas/{x.name}" for x in sorted((MS_r / "tabelas").iterdir()) if x.suffix == ".csv"]:
        comp[rel] = (MS_s / rel).exists() and md5(MS_s / rel) == md5(MS_r / rel)
    import openpyxl
    import docx
    from PIL import Image
    cel = lambda f: [[(c.coordinate, c.value) for row in ws.iter_rows() for c in row if c.value is not None] for ws in openpyxl.load_workbook(f).worksheets]
    comp[f"tabelas/tabelas_principais_{V12}.xlsx (células)"] = cel(MS_s / f"tabelas/tabelas_principais_{V12}.xlsx") == cel(MS_r / f"tabelas/tabelas_principais_{V12}.xlsx")
    dx = lambda f: ([p.text for p in docx.Document(f).paragraphs], [[c.text for r in t.rows for c in r.cells] for t in docx.Document(f).tables])
    comp[f"tabelas/tabelas_principais_{V12}.docx (texto)"] = dx(MS_s / f"tabelas/tabelas_principais_{V12}.docx") == dx(MS_r / f"tabelas/tabelas_principais_{V12}.docx")
    px = lambda f: (lambda im: (im.size, im.mode, im.info.get("dpi"), hashlib.md5(im.tobytes()).hexdigest()))(Image.open(f))
    for x in sorted((MS_r / "figuras").iterdir()):
        comp[f"figuras/{x.name} (pixels)"] = (MS_s / "figuras" / x.name).exists() and px(MS_s / "figuras" / x.name) == px(x)
    for x in sorted((MS_r / "suplementar").glob("S9_*")):
        comp[f"suplementar/{x.name} (pixels)"] = px(MS_s / "suplementar" / x.name) == px(x)
    shutil.rmtree(d, ignore_errors=True)
    return dict(execucoes=outs, comparacoes=comp)


def main():
    root = Path(tempfile.mkdtemp(prefix="aud7c7_sbx_", dir=SCRATCH))
    RES["sandbox"] = str(root)
    try:
        base = monta_base(root)
        RES["linha_de_base"] = roda_checa(clona(base, "linha_base"), "linha_de_base")
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {m: ex.submit(roda_mutacao, base, m) for m in MUT}
            fut_c = ex.submit(cenarios_commit, base)
            fut_l = ex.submit(testes_leiame, base)
            fut_h = ex.submit(testa_7c7_01, base)
            fut_r = ex.submit(reproduz, base)
            RES["mutacoes"] = {m: f.result() for m, f in futs.items()}
            for k, f in (("commits", fut_c), ("leiame", fut_l), ("hook_7c7_01", fut_h), ("reproducao", fut_r)):
                try:
                    RES[k] = f.result()
                except Exception:
                    RES[k] = {"erro": traceback.format_exc()[-2000:]}
    finally:
        RES["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
        json.dump(RES, open(OUTD / "sandbox_7c7_v1_20261013.json", "w"), ensure_ascii=False, indent=1, default=str)
        shutil.rmtree(root, ignore_errors=True)
        RES["sandbox_apagado"] = not root.exists()
        json.dump(RES, open(OUTD / "sandbox_7c7_v1_20261013.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
