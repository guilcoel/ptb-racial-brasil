"""
Auditoria independente final — Etapa 7c.6 (commit b9d6272), ptb-racial-brasil. 2026-10-10.

Roda, a partir de qualquer pasta (caminhos absolutos):
    PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_v1_20261010.py [K L M]
Blocos: K (integridade do commit), L (afirmações do RESUMO e do relato final), M (fatos das decisões pendentes).
Depende de: audita_7c6_final_lib/K/L/M_v1_20261010.py (mesma pasta); web_7c6_final_v1_20261010.json (gerado por
audita_7c6_final_web_v1_20261010.py); excecao_L2b_7c6_final_v1_20261010.json (gerado por audita_7c6_final_excecao_L2b_v1_20261010.py,
que roda por último, depois de todos os outros itens, e é a única leitura do checa_7b_*.csv).
Saída: comparacao_7c6_final_v1_20261010.csv (verificacao, ok, detalhe). Nada fora desta pasta é gravado.
"""
import csv
import importlib
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True

ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:220]}", flush=True)


if __name__ == "__main__":
    blocos = sys.argv[1:] or ["K", "L", "M"]
    ctx = {}
    for b in blocos:
        t0 = time.time()
        importlib.import_module(f"audita_7c6_final_{b}_v1_20261010").run(reg, ctx)
        print(f"-- bloco {b}: {time.time() - t0:.0f} s", flush=True)
    saida = AQUI / ("comparacao_7c6_final_v1_20261010.csv" if blocos == ["K", "L", "M"] else f"_parcial_{''.join(blocos)}.csv")
    ordem = {"K": 0, "L": 1, "M": 2}
    import re
    chave = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
    ROWS.sort(key=lambda r: (ordem.get(r["verificacao"][0], 9), chave(r["verificacao"])))
    with open(saida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["verificacao", "ok", "detalhe"])
        w.writeheader()
        w.writerows(ROWS)
    print(f"{sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK → {saida.name}")
