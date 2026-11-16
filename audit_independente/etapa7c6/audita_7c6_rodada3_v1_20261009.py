#!/usr/bin/env python3
"""
Auditoria independente da Etapa 7c.6 — rodada 3 (fechar a H4.06 e conferir o que mudou depois da rodada 2).

H4.06 refeita (a linha é atualizada no CSV com "rodada 3" no detalhe); I1 congelamento do commit_analise; I2 trava S5b com raise e
nenhum assert no etapa7b_04_submissao.py; I3 v11 regerada = v11 da rodada 2 (critérios do H3).

I1 testa o código real de commits_analise(): as funções _mesmo_valor, na_tabela e commits_analise são extraídas (AST) de
scripts/etapa7b_lib.py e executadas num namespace próprio. Nos testes sintéticos, MS aponta para uma pasta temporária fora do projeto
e o git é substituído por um dublê; na reprodução da v11 usa-se o projeto real (git só leitura).
O bloco 9g do etapa7b_checa.py é lido só nesta rodada, a pedido do coordenador, e só depois de concluídos os testes próprios
(por isso a leitura fica no fim e se limita ao trecho do bloco 9g).
"""
import ast
import csv
import json
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audita_7c6_v1_20261009 as A1  # noqa: E402
import audita_7c6_rodada2_v1_20261009 as A2  # noqa: E402

PROJ, MS, OUT, STAMP = A1.PROJ, A1.MS, A1.OUT, A1.STAMP
CSV_OUT = OUT / f"comparacao_7c6_v1_{STAMP}.csv"
MD5_JSON = "5f02c8c2885244c3fd738a84b4ee2196"
R = []


def reg(nome, ok, det):
    R.append((nome, bool(ok), str(det).replace("\n", " ")))
    print(f"[{'OK ' if ok else 'FALHA'}] {nome}: {str(det)[:400]}")


def funcoes_lib():
    """Código-fonte atual de _mesmo_valor, na_tabela e commits_analise (scripts/etapa7b_lib.py)."""
    src = A1.rt(A1.SCR / "etapa7b_lib.py")
    tree = ast.parse(src)
    seg = {n.name: ast.get_source_segment(src, n) for n in tree.body if isinstance(n, ast.FunctionDef)
           and n.name in ("_mesmo_valor", "na_tabela", "commits_analise")}
    return seg


def namespace(seg, ms, proj, subprocess_mod, na_tabela=None):
    ns = {"json": json, "np": np, "pd": pd, "subprocess": subprocess_mod, "MS": ms, "PROJ": proj}
    exec(seg["_mesmo_valor"], ns)
    exec(seg["na_tabela"], ns)
    if na_tabela is not None:
        ns["na_tabela"] = na_tabela
    exec(seg["commits_analise"], ns)
    return ns


# ---------------------------------------------------------------- dublê do git para os testes sintéticos
class Dubl:
    """Imita subprocess.run para os três usos de git em commits_analise: commit de adição do JSON arquivado, histórico e último commit
    do script. Commits fictícios: vN → 'cN' (adição do JSON da versão N)."""

    def __init__(self, hist, script_commit):
        self.hist, self.script_commit = hist, script_commit

    def run(self, cmd, capture_output=True, text=True):
        a = cmd[3:]                                  # tira "git -C <proj>"
        if a[:2] == ["log", "--diff-filter=A"]:
            n = re.search(r"numeros_chave_v(\d+)_", a[-1]).group(1)
            out = f"c{n}\n"
        elif a[:2] == ["log", "--format=%h %ct"]:
            out = "\n".join(f"{h} {t}" for t, h in self.hist) + "\n"
        elif a[:3] == ["log", "-1", "--format=%h"]:
            out = self.script_commit + "\n"
        else:
            raise AssertionError(f"chamada de git não prevista: {a}")
        return types.SimpleNamespace(stdout=out, returncode=0)


def monta(tmp, versoes):
    """versoes: {N: [itens]} → _arquivo_vN/numeros_chave_vN_20261009.json em tmp/outputs/manuscrito."""
    ms = Path(tmp) / "outputs" / "manuscrito"
    for n, itens in versoes.items():
        d = ms / f"_arquivo_v{n}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"numeros_chave_v{n}_{STAMP}.json").write_text(json.dumps(itens))
    return ms


def item(id_, fmt, bruto, **kw):
    d = dict(id=id_, valor_formatado=fmt, valor_bruto=bruto, arquivo="outputs/tables/x.csv", script="scripts/x.py")
    d.update(kw)
    return d


# ================================================================ I1
def bloco_I1():
    seg = funcoes_lib()
    reg("I1.01 commits_analise, na_tabela e _mesmo_valor extraídos do etapa7b_lib.py atual", len(seg) == 3, f"funções: {sorted(seg)}")
    cur = item("x", "1.00", 1.0)
    casos = []
    with tempfile.TemporaryDirectory() as tmp:
        def roda(versoes, it=cur, direto=False, script_commit="cS"):
            sub = tempfile.mkdtemp(dir=tmp)
            ms = monta(sub, versoes)
            Path(sub, "outputs", "tables").mkdir(parents=True, exist_ok=True)
            Path(sub, "outputs", "tables", "x.csv").write_text("v\n1.0\n")
            ns = namespace(seg, ms, Path(sub), Dubl([(0, "c0")] + [(10 ** 9 * 3, "cZ")], script_commit),
                           na_tabela=lambda i: direto)
            return ns["commits_analise"]([it])[it["id"]]
        # 1. herda da versão mais nova com o mesmo valor
        r = roda({10: [item("x", "1.00", 1.0, commit_analise="A10")], 9: [item("x", "1.00", 1.0, commit_analise="A9")]})
        casos.append(("mesmo valor em v10 (A10) e v9 (A9) → herda A10 (a mais nova)", r[1] == "A10" and r[0] == "c9", r))
        # 2. valor bruto mudou na v10 → não herda
        r = roda({10: [item("x", "1.00", 1.004, commit_analise="A10")]})
        casos.append(("bruto diferente na v10 (formatado igual) → não herda", r[1] != "A10", r))
        # 3. formatado mudou na v10 → não herda
        r = roda({10: [item("x", "1.0", 1.0, commit_analise="A10")]})
        casos.append(("formatado diferente na v10 (bruto igual) → não herda", r[1] != "A10", r))
        # 4. valor igual na v10, diferente na v9 com campo → herda só o da v10
        r = roda({10: [item("x", "1.00", 1.0, commit_analise="A10")], 9: [item("x", "2.00", 2.0, commit_analise="A9")]})
        casos.append(("igual na v10, diferente na v9 → herda A10, registro c10", r == ("c10", "A10"), r))
        # 5. diferente na v10, igual na v9 (valor voltou) → não herda da v9 (sequência interrompida)
        r = roda({10: [item("x", "2.00", 2.0, commit_analise="A10")], 9: [item("x", "1.00", 1.0, commit_analise="A9")]})
        casos.append(("diferente na v10, igual na v9 → não herda (nem A10 nem A9)", r[1] not in ("A10", "A9"), r))
        # 6. sem campo em nenhuma versão → cálculo antigo (derivado: commit_registro; direto: concordância a = b)
        r = roda({10: [item("x", "1.00", 1.0)], 9: [item("x", "1.00", 1.0)]})
        casos.append(("sem o campo nas versões arquivadas, derivado → commit_registro (c9), como na rodada 2", r == ("c9", "c9"), r))
        r = roda({10: [item("x", "1.00", 1.0)]}, direto=True, script_commit="cZ")
        casos.append(("sem o campo, direto com (a) = (b) → commit da etapa (cZ)", r == ("c10", "cZ"), r))
        r = roda({10: [item("x", "1.00", 1.0)]}, direto=True, script_commit="cOutro")
        casos.append(("sem o campo, direto com (a) ≠ (b) → vazio", r == ("c10", ""), r))
        # 7. herança tem precedência sobre o recálculo pelo mtime
        r = roda({10: [item("x", "1.00", 1.0, commit_analise="A10")]}, direto=True, script_commit="cOutro")
        casos.append(("com o campo, direto com (a) ≠ (b) → herda A10 (congelado, não esvazia)", r == ("c10", "A10"), r))
        # 8. id ausente nas versões → sem registro, vazio
        r = roda({10: [item("y", "1.00", 1.0, commit_analise="A10")]})
        casos.append(("id ausente nas versões arquivadas → vazio", r == ("", ""), r))
        # 9. bordas registradas (comportamento, não falha): campo vazio ou ausente na mais nova e preenchido numa mais antiga
        r9a = roda({10: [item("x", "1.00", 1.0, commit_analise="")], 9: [item("x", "1.00", 1.0, commit_analise="A9")]})
        r9b = roda({10: [item("x", "1.00", 1.0)], 9: [item("x", "1.00", 1.0, commit_analise="A9")]})
        # 10. lista como valor bruto
        r = roda({10: [item("x", "[1, 2]", [1.0, 2.0], commit_analise="A10")]}, it=item("x", "[1, 2]", [1.0, 2.0]))
        casos.append(("valor bruto em lista igual → herda A10", r[1] == "A10", r))
        r = roda({10: [item("x", "[1, 2]", [1.0, 2.5], commit_analise="A10")]}, it=item("x", "[1, 2]", [1.0, 2.0]))
        casos.append(("valor bruto em lista diferente → não herda", r[1] != "A10", r))
    ruins = [c for c in casos if not c[1]]
    reg("I1.02 testes sintéticos próprios do congelamento (código real, pasta temporária fora do projeto)", not ruins,
        f"{len(casos)} casos; " + "; ".join(f"{d}: {'ok' if o else 'FALHOU'} {r}" for d, o, r in casos))
    reg("I1.03 (registro) bordas do congelamento", True,
        f"campo vazio na versão mais nova e 'A9' numa mais antiga com o mesmo valor → {r9a[1] or '(vazio)'}; campo ausente na mais nova "
        f"e 'A9' na mais antiga → {r9b[1] or '(vazio)'} (herda a mais nova que tem o campo preenchido; vazio não congela)")

    # reprodução da v11 com o código atual e o projeto real (nenhuma versão arquivada tem o campo)
    J11 = json.loads(A1.rb(A1.keyjson(11)))
    tem = [n for n in range(1, 11) if any("commit_analise" in i for i in json.loads(A1.rb(MS / f"_arquivo_v{n}" / f"numeros_chave_v{n}_{STAMP}.json")))]
    reg("I1.04 nenhuma versão arquivada (v1–v10) tem commit_analise (logo nada é herdado hoje)", not tem, f"versões com o campo: {tem}")
    ns = namespace(seg, MS, PROJ, subprocess)
    itens = [{k: v for k, v in i.items() if k not in ("commit_registro", "commit_analise")} for i in J11]
    res = ns["commits_analise"](itens)
    dif = [i["id"] for i in J11 if res[i["id"]] != (i["commit_registro"], i["commit_analise"])]
    reg("I1.05 o commits_analise atual, rodado no projeto real, reproduz commit_registro e commit_analise da v11 (226 ids)", not dif,
        f"divergentes: {dif}")
    # o JSON v11 é o mesmo da rodada 2: MD5 informado e campos iguais aos registrados na rodada 2 (CSV por id)
    md5 = A1.md5b(A1.rb(A1.keyjson(11)))
    r2 = {r["id"]: r for r in csv.DictReader(open(OUT / f"commit_analise_rodada2_por_id_7c6_v1_{STAMP}.csv", encoding="utf-8"))}
    d2 = [i["id"] for i in J11 if (i["commit_analise"], i["commit_registro"]) != (r2[i["id"]]["commit_analise_json"], r2[i["id"]]["commit_registro_json"])]
    reg("I1.06 v11 não mudou: MD5 do JSON = 5f02c8c2885244c3fd738a84b4ee2196 e commits iguais aos registrados na rodada 2", md5 == MD5_JSON and not d2,
        f"MD5 {md5}; ids com commit diferente da rodada 2: {d2}")
    return seg


def bloco_I1_checa():
    """Leitura restrita ao teste sintético do congelamento no bloco 9g do etapa7b_checa.py (pedido do coordenador na rodada 3),
    feita depois dos testes próprios. Só o trecho entre o comentário do congelamento e o fim da chamada ok() correspondente."""
    # exceção documentada à trava de independência das rodadas 1–2 (A1.guarda recusa este arquivo): leitura pedida na rodada 3
    src = (A1.SCR / "etapa7b_checa.py").read_text(encoding="utf-8").splitlines()
    i9 = next((i for i, l in enumerate(src) if re.match(r"^# -+ 9g\.", l)), None)
    i0 = next((i for i in range(i9 or 0, len(src)) if "congelamento do commit_analise" in src[i]), None) if i9 is not None else None
    if i0 is None:
        reg("I1.07 teste sintético do congelamento no checa (bloco 9g)", False, "trecho não encontrado")
        return
    iok = next(i for i in range(i0, len(src)) if src[i].startswith("ok("))
    fim = next(i for i in range(iok + 1, len(src)) if src[i] and not src[i][0].isspace())
    t = "\n".join(src[i0:fim])
    versoes = sorted(set(re.findall(r"_arquivo_v(\d+)", t)))
    chamadas = t.count("commits_analise(")
    ok7 = "TemporaryDirectory" in t and chamadas >= 2 and "abc1234" in t and "r0[1] ==" in t and "r1[1] !=" in t
    reg("I1.07 o teste do checa (bloco 9g) roda o commits_analise real numa pasta temporária e verifica 'herda com o mesmo valor' e "
        "'não herda se o valor muda'", ok7,
        f"linhas {i0 + 1}–{fim}; TemporaryDirectory: {'TemporaryDirectory' in t}; chamadas a commits_analise: {chamadas}; "
        f"versões arquivadas sintéticas: {versoes}; asserções sobre r0 (herda 'abc1234') e r1 (não herda)")
    muda_bruto = bool(re.search(r"valor_bruto\s*=", t))
    muda_fmt = bool(re.search(r"valor_formatado\s*=", t))
    ok8 = len(versoes) >= 2 and muda_bruto and muda_fmt
    reg("I1.08 o teste do checa cobre toda a especificação: mudança do bruto (com formatado igual), mudança do formatado e precedência "
        "da versão arquivada mais nova", ok8,
        f"muda o formatado: {muda_fmt}; muda o bruto: {muda_bruto}; versões arquivadas no teste: {len(versoes)} (precedência da mais nova "
        f"{'testada' if len(versoes) >= 2 else 'não testada'}). Esses casos estão cobertos pelos testes próprios (I1.02) e o código passa "
        f"neles; a lacuna é só do teste do checa")


# ================================================================ I2
def bloco_I2():
    src = A1.rt(A1.SCR / "etapa7b_04_submissao.py")
    t = ast.parse(src)
    asserts = [n.lineno for n in ast.walk(t) if isinstance(n, ast.Assert)]
    ifs = [n for n in ast.walk(t) if isinstance(n, ast.If) and "S5b" in ast.unparse(n.test) and "INTERNAL" in ast.unparse(n.test)]
    ok = bool(ifs) and isinstance(ifs[0].body[0], ast.Raise) and ast.unparse(ifs[0].body[0].exc.func) == "RuntimeError"
    reg("I2.01 trava da aba S5b/INTERNAL no ESM_1: 'if ...: raise RuntimeError'", ok,
        f"L{ifs[0].lineno}: if {ast.unparse(ifs[0].test)} → L{ifs[0].body[0].lineno} raise RuntimeError" if ifs else "if não encontrado")
    reg("I2.02 nenhum assert no etapa7b_04_submissao.py", not asserts, f"asserts: {asserts}")
    lim = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "limpa_macos"]
    rs = [n.lineno for n in ast.walk(lim[0]) if isinstance(n, ast.Raise)] if lim else []
    ch = [n.lineno for n in t.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "limpa_macos"]
    trava = ifs[0].lineno if ifs else 0
    reg("I2.03 a trava S5b fica depois da montagem do ESM_1 e antes da limpeza final; limpa_macos mantém o raise", bool(rs) and len(ch) == 2
        and ch[0] < trava < ch[1], f"limpa_macos raise em L{rs}; chamadas L{ch}; trava L{trava}")
    sub = [x for x in A1.SUB.iterdir() if x.name == "ESM_1.xlsx"]
    import openpyxl
    abas = openpyxl.load_workbook(sub[0]).sheetnames if sub else []
    reg("I2.04 Submissao/ESM_1.xlsx regerado sem aba S5b/INTERNAL", sub and not any("S5b" in a or "INTERNAL" in a for a in abas), f"abas: {abas}")


# ================================================================ I3
def bloco_I3():
    A2.R.clear()
    A2.bloco_H3()
    for nome, ok, det in A2.R:
        R.append((nome.replace("H3.", "I3.", 1) + " (rodada 3, critério do H3)", ok, det))
        print(f"[{'OK ' if ok else 'FALHA'}] {R[-1][0]}: {det[:200]}")


# ================================================================ H4.06 refeita
def h406():
    st = A1.git("ls-files", "-s", "--", "docs/referencias/ATRIBUICAO.txt").split()
    wt = A1.git("hash-object", "--", "docs/referencias/ATRIBUICAO.txt").strip()
    idx = subprocess.run(["git", "-C", str(PROJ), "show", ":docs/referencias/ATRIBUICAO.txt"], capture_output=True).stdout.decode("utf-8", "replace")
    frase = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    ok = bool(st) and st[1] == wt and frase in A1.norm_ws(idx)
    det = (f"rodada 3: blob no índice {st[1] if st else '—'} = working tree {wt}: {bool(st) and st[1] == wt}; a frase '{frase}' está na cópia "
           f"do índice: {frase in A1.norm_ws(idx)}. (Rodada 2: FALHA, índice 1c6d414… × working tree ee3e33b…, sem 'CC BY 4.0'.)")
    return ok, det


def main():
    bloco_I1()
    bloco_I1_checa()
    bloco_I2()
    bloco_I3()
    ok, det = h406()
    print(f"[{'OK ' if ok else 'FALHA'}] H4.06 (refeita): {det}")
    linhas = list(csv.reader(open(CSV_OUT, encoding="utf-8")))
    cab, corpo = linhas[0], [r for r in linhas[1:] if not r[0].startswith("I")]
    n406 = 0
    for r in corpo:
        if r[0].startswith("H4.06"):
            r[1], r[2] = ("True" if ok else "False"), det
            n406 += 1
    assert n406 == 1
    R.sort(key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x[0].split()[0])])
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(corpo)
        for nome, ok_, det_ in R:
            w.writerow([nome, "True" if ok_ else "False", det_])
    tudo = list(csv.reader(open(CSV_OUT, encoding="utf-8")))[1:]
    n_ok = sum(1 for r in tudo if r[1] == "True")
    print(f"\nRodada 3: {len(R)} linhas I ({sum(1 for _, o, _ in R if o)} OK); CSV inteiro: {len(tudo)} linhas, {n_ok} OK")
    for r in tudo:
        if r[1] != "True":
            print("FALHA:", r[0], "—", r[2][:500])


if __name__ == "__main__":
    main()
