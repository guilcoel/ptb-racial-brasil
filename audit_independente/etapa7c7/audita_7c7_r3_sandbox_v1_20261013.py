"""
Auditor independente da Etapa 7c.7, rodada 3 — testes dinâmicos em sandbox. Reaproveita o sandbox da rodada 2
(audita_7c7_r2_sandbox_v1_20261013.py): scratch do sistema; git por clone --no-checkout + índice real; cópia só de rastreados e de não
rastreados não ignorados; ignorados (outputs/tables/*, comparacao_*.csv) por link simbólico; guarda deste auditor (sitecustomize com
audit hook) em todo Python; MD5/mtime dos ignorados do Forja antes e depois; sandbox apagado no fim.
Fases (argumento):
  gerador — cópia do gerador do RESUMO com a saída desviada; o CSV deste auditor entra por link no estado de ANTES das linhas R3; compara
            com outputs/RESUMO_ETAPA7C7_v1_20261013.md byte a byte; depois arquiva a v12 no sandbox e roda de novo (tem de parar).
  guarda  — a guarda da autoauditoria (sitecustomize extraído do scripts/etapa7c7_02_audita.py), SOZINHA, contra sondas inofensivas: cada
            sonda, se a guarda falhar, só toca arquivos descartáveis criados aqui na pasta deste auditor (e apagados no fim) ou caminhos
            inexistentes do Forja.
Saída: audit_independente/etapa7c7/sandbox_7c7_r3_<fase>_v1_20261013.json
"""
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
SCRATCH = Path("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad")
spec = importlib.util.spec_from_file_location("sbx2", OUTD / "audita_7c7_r2_sandbox_v1_20261013.py")
S2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S2)
md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()


def fase_gerador(RES):
    foto0 = S2.foto_ignorados()
    root = Path(tempfile.mkdtemp(prefix="aud7c7r3_", dir=SCRATCH))
    try:
        base = S2.monta_base(root)
        RES["base"] = S2.RES["base"]
        RES["guarda_auditor"] = S2.teste_guarda(base, root)
        if RES["guarda_auditor"]["saida"] != ["BLOQUEOU", "BLOQUEOU"]:
            raise RuntimeError("guarda do auditor não carregou")
        cmp_ = PROJ / "audit_independente/etapa7c7/comparacao_7c7_v1_20261013.csv"
        RES["comparacao_estado"] = dict(mtime=time.strftime("%H:%M:%S", time.localtime(cmp_.stat().st_mtime)), md5=md5(cmp_),
                                        linhas_r3=sum(1 for l in cmp_.read_text().splitlines() if l.startswith(("R3.", '"R3.'))))
        RES["gerador"] = S2.gerador(base, root)
    except Exception:
        RES["erro"] = traceback.format_exc()[-2000:]
    finally:
        shutil.rmtree(root, ignore_errors=True)
        RES["sandbox_apagado"] = not root.exists()
        foto1 = S2.foto_ignorados()
        RES["ignorados_intactos"] = foto0 == foto1
        RES["n_ignorados"] = len(foto0)


SONDA = r'''
import os, shutil, sys, json
D = sys.argv[1]                      # pasta descartável na pasta do auditor (Forja)
NX = D + "/nao_existe/x.txt"         # caminho inexistente no Forja
out = {}
def t(nome, f):
    try:
        f(); out[nome] = "PASSOU"
    except PermissionError as e:
        out[nome] = "BLOQUEOU"
    except Exception as e:
        out[nome] = type(e).__name__
t("open_w_forja", lambda: open(D + "/sonda_w.txt", "w").close())
t("open_a_forja_existente", lambda: open(D + "/existente.txt", "a").close())
t("open_rplus_inexistente", lambda: open(NX, "r+").close())
t("open_w_por_link", lambda: open(sys.argv[2], "w").close())               # link no /tmp → arquivo descartável no Forja
t("os_open_wronly", lambda: os.close(os.open(D + "/existente.txt", os.O_WRONLY)))
t("remove_inexistente", lambda: os.remove(NX))
t("rename_inexistente", lambda: os.rename(NX, sys.argv[3] + "/y"))
t("replace_inexistente", lambda: os.replace(NX, sys.argv[3] + "/y"))
t("mkdir_forja", lambda: os.mkdir(D + "/sonda_dir"))
t("utime_descartavel", lambda: os.utime(D + "/existente.txt"))
t("chmod_descartavel", lambda: os.chmod(D + "/existente.txt", 0o700))
t("rmtree_inexistente", lambda: shutil.rmtree(D + "/nao_existe"))
if sys.argv[4] == "com_copia":                       # só quando a guarda diz bloquear cópia de ignorado para fora
    t("copia_ignorado_para_fora", lambda: shutil.copyfile(D + "/ignorado_teste.csv", sys.argv[3] + "/copia.csv"))
t("leitura_forja", lambda: open(D + "/existente.txt").read())
t("escrita_tmp", lambda: open(sys.argv[3] + "/livre.txt", "w").close())
print(json.dumps(out))
'''


def fase_guarda(RES):
    src = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()
    m = ast.parse(src)
    cands = [n for n in ast.walk(m) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
             and "addaudithook" in n.value.value]
    if not cands:
        RES["erro"] = "guarda não encontrada como constante no script"
        return
    guarda = cands[0].value.value
    RES["guarda_var"] = ast.unparse(cands[0].targets[0])
    RES["guarda_md5"] = hashlib.md5(guarda.encode()).hexdigest()
    desc = OUTD / "_sonda_guarda_r3"                     # pasta descartável na pasta deste auditor (Forja)
    tmp = Path(tempfile.mkdtemp(prefix="aud7c7r3g_", dir=SCRATCH))
    try:
        desc.mkdir(exist_ok=True)
        (desc / "existente.txt").write_text("x")
        (desc / "ignorado_teste.csv").write_text("x\n")  # *.csv em audit_independente: ignorado pelo .gitignore
        ign = subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q", str((desc / "ignorado_teste.csv").relative_to(PROJ))],
                             env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).returncode == 0
        (tmp / "_g").mkdir()
        (tmp / "_g" / "sitecustomize.py").write_text(guarda)
        os.symlink(desc / "alvo_link.txt", tmp / "link.txt")
        (tmp / "sonda.py").write_text(SONDA)
        antes = {p.name: (p.stat().st_mtime, p.stat().st_mode) for p in desc.iterdir()}
        copia = "com_copia" if ("copy" in guarda and ("_SENS" in guarda or "ignor" in guarda or "outputs/tables" in guarda)) else "sem_copia"
        RES["sonda_copia"] = copia
        r = subprocess.run([sys.executable, str(tmp / "sonda.py"), str(desc), str(tmp / "link.txt"), str(tmp), copia], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=str(tmp / "_g")), cwd=tmp)
        RES["sonda_rc"], RES["sonda_err"] = r.returncode, r.stderr[-800:]
        RES["sondas"] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
        depois = {p.name: (p.stat().st_mtime, p.stat().st_mode) for p in desc.iterdir()}
        RES["efeitos_no_forja"] = dict(criados=sorted(set(depois) - set(antes)), alterados=sorted(k for k in antes if k in depois and antes[k] != depois[k]))
        RES["ignorado_teste_ignorado_pelo_git"] = ign
        RES["copia_feita_fora"] = (tmp / "copia.csv").exists()
        # mesma sonda sem guarda nenhuma: controle (mostra que as sondas de fato tentam a operação)
        r0 = subprocess.run([sys.executable, str(tmp / "sonda.py"), str(desc), str(tmp / "link.txt"), str(tmp), "sem_copia"], capture_output=True, text=True,
                            env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, cwd=tmp)
        RES["controle_sem_guarda"] = json.loads(r0.stdout.strip().splitlines()[-1]) if r0.stdout.strip() else {"erro": r0.stderr[-300:]}
    except Exception:
        RES["erro"] = traceback.format_exc()[-1500:]
    finally:
        shutil.rmtree(desc, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
        RES["descartaveis_apagados"] = not desc.exists() and not tmp.exists()


if __name__ == "__main__":
    fase = sys.argv[1]
    RES = {"fase": fase, "inicio": time.strftime("%Y-%m-%d %H:%M:%S")}
    {"gerador": fase_gerador, "guarda": fase_guarda}[fase](RES)
    RES["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(RES, open(OUTD / f"sandbox_7c7_r3_{fase}_v1_20261013.json", "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in RES.items() if k not in ("gerador",)}, ensure_ascii=False, default=str)[:3000])
    if "gerador" in RES:
        print(json.dumps(RES["gerador"], ensure_ascii=False, default=str)[:1500])
