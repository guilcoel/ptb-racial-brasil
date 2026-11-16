"""Auxiliar do auditor independente da Etapa 8: caminhos e gravação dos resultados (só agregados) em JSON por bloco."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
AUD = PROJ / "audit_independente" / "etapa8"
MS = PROJ / "outputs" / "manuscrito"
TB = PROJ / "outputs" / "tables"
PROC = PROJ / "data" / "processed"
RAW = PROJ / "data" / "raw" / "aps_cobertura_ab"
HEAD = "dc54fb951e3c453572933a964ba41ce1b7a4720e"
V12, V13 = "v12_20261013", "v13_20261013"


class Res:
    def __init__(self, bloco):
        self.bloco, self.itens = bloco, []

    def ok(self, nome, cond, detalhe=""):
        self.itens.append(dict(verificacao=nome, ok=bool(cond), detalhe=str(detalhe)))
        print(("OK   " if cond else "FALHA"), nome, "|", str(detalhe)[:300], flush=True)

    def grava(self):
        import os
        p = AUD / f"res_{self.bloco.lower()}_{os.environ.get('RODADA', 'r1')}_v1_20261013.json"
        assert p.resolve().parent == AUD
        json.dump(self.itens, open(p, "w"), ensure_ascii=False, indent=1)
        n = len(self.itens)
        print(f"== bloco {self.bloco}: {sum(i['ok'] for i in self.itens)}/{n} OK")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def blob_sha(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
