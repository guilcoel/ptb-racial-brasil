"""Utilitários do auditor independente da Etapa 8b (somente leitura no projeto; escrita só em audit_independente/etapa8b/)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
AUD = PROJ / "audit_independente" / "etapa8b"
BASE = "cdddf8f"
V13, V14 = "v13_20261013", "v14_20261026"
MS = PROJ / "outputs" / "manuscrito"
A13 = MS / "_arquivo_v13"
TB = PROJ / "outputs" / "tables"
SUB = PROJ / "Submissao"


def git(*a, cwd=PROJ, binary=False):
    import os
    r = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, check=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    return r.stdout if binary else r.stdout.decode()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pfmt(p):
    """Formatação de p do pacote, reescrita aqui pela regra descrita no MANIFEST/pacotes anteriores: <0.0001 ou 3 algarismos significativos."""
    if p != p:
        return "n.a."
    if p < 1e-4:
        return "<0.0001"
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(repr(p))
    e = d.adjusted()                      # expoente do 1º algarismo significativo
    q = Decimal(1).scaleb(e - 2)          # 3 algarismos significativos
    r = d.quantize(q, rounding=ROUND_HALF_UP)
    return format(r, "f")


class Bloco:
    def __init__(self, nome):
        import os
        self.pre = os.environ.get("AUD_PREFIXO", "")
        self.nome, self.R = self.pre.lower().replace(".", "") + nome, []

    def ok(self, vid, desc, cond, det=""):
        cond = bool(cond)
        vid = self.pre + vid
        self.R.append({"verificacao": f"{vid} {desc}", "ok": cond, "detalhe": str(det)[:900]})
        print(("OK  " if cond else "FALHA ") + vid + " " + desc[:110] + (f"  [{str(det)[:200]}]" if det != "" else ""), flush=True)

    def grava(self):
        (AUD / f"res_{self.nome}_v1_20261026.json").write_text(json.dumps(self.R, ensure_ascii=False, indent=1))
        n = sum(r["ok"] for r in self.R)
        print(f"{self.nome}: {n}/{len(self.R)}")
