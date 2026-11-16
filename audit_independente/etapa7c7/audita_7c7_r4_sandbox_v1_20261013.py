"""
Auditor independente da Etapa 7c.7, rodada 4 — sandbox (mesmas regras das rodadas 2 e 3: scratch do sistema; clone --no-checkout + índice
real; cópia só de rastreados e não rastreados não ignorados; ignorados por link; guarda deste auditor em todo Python; MD5/mtime dos ignorados
antes e depois; apagado no fim). Sem bytecode (sys.dont_write_bytecode): a rodada 3 deixou um __pycache__ nesta pasta ao importar o módulo
da rodada 2.
  1. gerador: cópia com a saída desviada, CSV deste auditor por link no estado de ANTES das linhas R4; compara com o RESUMO das 19:52.
  2. GuardaFalhou: cópia da autoauditoria num espelho do projeto, com a guarda dela quebrada de propósito (o addaudithook vira pass); tem de
     dar C6.00a falso, C6.99 e nenhuma mutação, commit simulado ou teste do LEIAME (C6.00–C6.22), e apagar o sandbox dela.
Saída: audit_independente/etapa7c7/sandbox_7c7_r4_v1_20261013.json
"""
import sys

sys.dont_write_bytecode = True
import importlib.util
import json
import os
import shutil
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
RES = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S")}


def guarda_quebrada(base, root):
    d = S2.clona(base, "espelho_gf")
    shutil.copy2(PROJ / "outputs/manuscrito/checa_7b_v12_20261013.csv", d / "outputs/manuscrito/checa_7b_v12_20261013.csv")   # rastreável
    for f in sorted((PROJ / "outputs/logs").glob("etapa7*_20261008.log")):         # ignorados: só link (o D da autoauditoria os lê)
        os.symlink(f, d / "outputs/logs" / f.name)
    p = d / "scripts/etapa7c7_02_audita.py"
    t = p.read_text()
    assert t.count("sys.addaudithook(_guarda)") == 1
    p.write_text(t.replace("sys.addaudithook(_guarda)", "pass  # [auditor r4] guarda quebrada de propósito"))
    saida = d / "outputs/manuscrito/audita_7c7_v1_20261013.csv"
    if saida.exists():
        saida.unlink()
    t0 = time.time()
    r = S2.sh([sys.executable, "scripts/etapa7c7_02_audita.py"], cwd=d, check=False, env=S2.env_sbx(d, root), timeout=3600)
    out = dict(rc=r.returncode, seg=round(time.time() - t0, 1), erro=r.stderr[-1200:])
    if saida.exists():
        import pandas as pd
        x = pd.read_csv(saida)
        ids = list(x.verificacao.str.split(" ").str[0])
        out.update(ids_c6=[i for i in ids if i.startswith("C6.")], c600a=bool(x.set_index(x.verificacao.str.split(" ").str[0]).ok.get("C6.00a")),
                   c699=x[x.verificacao.str.startswith("C6.99")].detalhe.astype(str).tolist(),
                   c623=bool(x.set_index(x.verificacao.str.split(" ").str[0]).ok.get("C6.23")), n=len(x),
                   blocos_depois=[i for i in ids if i[0] in "DE"])
    shutil.rmtree(d, ignore_errors=True)
    return out


def main():
    foto0 = S2.foto_ignorados()
    root = Path(tempfile.mkdtemp(prefix="aud7c7r4_", dir=SCRATCH))
    RES["sandbox"] = str(root)
    try:
        base = S2.monta_base(root)
        RES["base"] = S2.RES["base"]
        RES["guarda_auditor"] = S2.teste_guarda(base, root)
        if RES["guarda_auditor"]["saida"] != ["BLOQUEOU", "BLOQUEOU"]:
            raise RuntimeError("guarda do auditor não carregou")
        cmp_ = OUTD / "comparacao_7c7_v1_20261013.csv"
        RES["comparacao_estado"] = dict(mtime=time.strftime("%H:%M:%S", time.localtime(cmp_.stat().st_mtime)),
                                        linhas_r4=sum(1 for l in cmp_.read_text().splitlines() if l.startswith(("R4.", '"R4.'))))
        RES["gerador"] = S2.gerador(base, root)
        RES["guarda_quebrada"] = guarda_quebrada(base, root)
    except Exception:
        RES["erro"] = traceback.format_exc()[-2000:]
    finally:
        shutil.rmtree(root, ignore_errors=True)
        RES["sandbox_apagado"] = not root.exists()
        foto1 = S2.foto_ignorados()
        RES["ignorados_intactos"] = foto0 == foto1
        RES["n_ignorados"] = len(foto0)
        RES["pycache_criado"] = (OUTD / "__pycache__" / "audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc").exists() and \
            (OUTD / "__pycache__" / "audita_7c7_r2_sandbox_v1_20261013.cpython-312.pyc").stat().st_mtime > time.mktime(time.strptime(RES["inicio"], "%Y-%m-%d %H:%M:%S"))
        RES["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
        json.dump(RES, open(OUTD / "sandbox_7c7_r4_v1_20261013.json", "w"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
    print(json.dumps({k: v for k, v in RES.items() if k != "gerador"}, ensure_ascii=False, default=str)[:3500])
    print(json.dumps(RES.get("gerador", {}).get("reproduz", {}), ensure_ascii=False)[:600])
