#!/usr/bin/env python3
"""
Auditoria independente da Etapa 7c.6 — rodada 4 (refazer a I1.08).

1) Teste sintético do congelamento no etapa7b_checa.py (bloco 9g: _cong e CASOS): cobertura da especificação (estática) e execução
   do próprio código do teste contra o commits_analise real, em pasta temporária fora do projeto, sem rodar o checa inteiro
   (que gravaria saídas). Os resultados esperados de cada caso são conferidos também com o dublê próprio da rodada 3.
2) etapa7b_lib.py: só a docstring mudou desde a rodada 3. Comparação por AST, sem docstrings: os objetos alterados na 7c.6 contra o
   código visto nas rodadas 2 e 3 (transcrito abaixo); todo o resto contra o HEAD (8314417).
Atualiza a linha I1.08 do comparacao_7c6_v1_20261009.csv (detalhe com "rodada 4") e acrescenta as linhas J.
Leitura do etapa7b_checa.py restrita ao trecho do congelamento no bloco 9g (exceção pedida pelo coordenador desde a rodada 3).
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
import audita_7c6_rodada3_v1_20261009 as A3  # noqa: E402

PROJ, MS, OUT, STAMP = A1.PROJ, A1.MS, A1.OUT, A1.STAMP
CSV_OUT = OUT / f"comparacao_7c6_v1_{STAMP}.csv"
R = []


def reg(nome, ok, det):
    R.append((nome, bool(ok), str(det).replace("\n", " ")))
    print(f"[{'OK ' if ok else 'FALHA'}] {nome}: {str(det)[:500]}")


# código de etapa7b_lib.py visto nas rodadas 2 (na_tabela, Registro) e 3 (commits_analise) e na rodada 1 (origem, _mesmo_valor, V);
# docstrings omitidas (a comparação as ignora)
REF_R3 = r'''
V = "v11_20261009"


def origem(nome):
    f = f"outputs/tables/{nome}_v1_{S}.csv" if not nome.startswith("dicionario") else f"outputs/tables/{nome}_{S}.csv"
    return dict(arquivo=f, script=SRC[nome], commit_pacote=COMMIT)


def _mesmo_valor(a, b):
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(_mesmo_valor(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return bool(np.isclose(a, b, rtol=1e-12, atol=0))
    return a == b


def na_tabela(it):
    src = pd.read_csv(PROJ / it["arquivo"]).select_dtypes("number").to_numpy(dtype=float)
    v = it["valor_bruto"]
    return all(np.isclose(src, x, rtol=1e-9, atol=1e-12).any() for x in (v if isinstance(v, list) else [v]))


def commits_analise(itens):
    vers = []
    for d in MS.glob("_arquivo_v*"):
        js = sorted(d.glob("numeros_chave_v*_*.json"))
        if d.is_dir() and len(js) == 1:
            add = subprocess.run(["git", "-C", str(PROJ), "log", "--diff-filter=A", "--format=%h", "--", f"outputs/manuscrito/{js[0].name}"],
                                 capture_output=True, text=True).stdout.split()
            vers.append((int(d.name.split("_v")[1]), {i["id"]: i for i in json.load(open(js[0]))}, add[-1] if add else ""))
    vers.sort(key=lambda x: -x[0])
    git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True).stdout
    hist = sorted((int(t), h) for h, t in (x.split() for x in git("log", "--format=%h %ct").splitlines()))
    out = {}
    for it in itens:
        cr, herda = "", ""
        for _, J, c in vers:
            x = J.get(it["id"])
            if x is None or x["valor_formatado"] != it["valor_formatado"] or not _mesmo_valor(x["valor_bruto"], it["valor_bruto"]):
                break
            cr = c
            herda = herda or x.get("commit_analise", "")
        if herda:
            ca = herda
        elif not cr or not it["script"]:
            ca = ""
        elif na_tabela(it):
            mt = (PROJ / it["arquivo"]).stat().st_mtime
            a = next((h for t, h in hist if t >= mt), "")
            b = git("log", "-1", "--format=%h", cr, "--", it["script"].split()[0]).strip()
            ca = a if a and a == b else ""
        else:
            ca = cr
        out[it["id"]] = (cr, ca)
    return out


class Registro:
    def __init__(self):
        self.itens = []

    def add(self, id_, bruto, fmt, nome, descricao, filtro=""):
        o = origem(nome) if nome in SRC else dict(arquivo=nome, script="", commit_pacote=COMMIT)
        self.itens.append(dict(id=id_, valor_formatado=fmt, valor_bruto=bruto, descricao=descricao, filtro=filtro, **o))

    def grava(self):
        ca = commits_analise(self.itens)
        for i in self.itens:
            i["commit_registro"], i["commit_analise"] = ca[i["id"]]
        js = MS / f"numeros_chave_{V}.json"
        json.dump(self.itens, open(js, "w"), ensure_ascii=False, indent=1, default=float)
        md = ["# Key numbers (Etapas 7b–7c.6)", "", f"Package {V}; commit_pacote {COMMIT} (repository HEAD when the package was generated). "
              "commit_registro = commit in which the current value of each number first entered the key-number inventory. "
              "commit_analise = commit in which the number was calculated: for a value read directly from its source table, the commit "
              "of the step that produced the table (first commit after the table's modification time, accepted only when it is also the "
              "last commit of the source script up to commit_registro); for a value derived in the package (ratio, sum, difference, "
              "min/max of table cells), commit_registro. Empty: not determined. Each value comes from the file/script shown. "
              "IC = interaction contrast (ids starting with ICR_ are internal identifiers kept from earlier versions).", "",
              "| id | value | description | source file | script | filter | commit_analise | commit_registro |",
              "|---|---|---|---|---|---|---|---|"]
        esc = lambda t: str(t).replace("|", "\\|")
        for i in self.itens:
            md.append(f"| {i['id']} | {esc(i['valor_formatado'])} | {esc(i['descricao'])} | `{i['arquivo']}` | `{i['script']}` | {esc(i['filtro'])} "
                      f"| {i['commit_analise']} | {i['commit_registro']} |")
        (MS / f"numeros_chave_{V}.md").write_text("\n".join(md) + "\n")
'''
ALTERADOS = {"V", "origem", "_mesmo_valor", "na_tabela", "commits_analise", "Registro"}


def sem_doc(node):
    node = ast.parse(ast.unparse(node)).body[0]           # cópia
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return ast.dump(node, include_attributes=False)


def chave(n):
    if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
        return n.name
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        return n.targets[0].id
    return None


def nos(src):
    out = []
    for n in ast.parse(src).body:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
            continue                                       # docstring do módulo
        out.append((chave(n), sem_doc(n)))
    return out


# ================================================================ lib: só a docstring mudou
def bloco_lib():
    atual = A1.rt(A1.SCR / "etapa7b_lib.py")
    head = A1.git_show(A1.HEAD_ESPERADO, "scripts/etapa7b_lib.py").decode("utf-8")
    na, nh, nr = nos(atual), nos(head), dict(nos(REF_R3))
    # objetos alterados na 7c.6: iguais ao código visto nas rodadas 2–3
    dif_alt = [k for k, d in na if k in ALTERADOS and nr.get(k) != d]
    falt = sorted(ALTERADOS - {k for k, _ in na})
    reg("J1.01 etapa7b_lib.py: V, origem, _mesmo_valor, na_tabela, commits_analise e Registro iguais (AST, sem docstrings) ao código das "
        "rodadas 2–3", not dif_alt and not falt, f"diferentes: {dif_alt}; ausentes: {falt}")
    # todo o resto: igual ao HEAD 8314417, na mesma ordem (só com a inserção de na_tabela/commits_analise)
    resto_a = [(k, d) for k, d in na if k not in ALTERADOS]
    resto_h = [(k, d) for k, d in nh if k not in ALTERADOS]
    reg("J1.02 etapa7b_lib.py: todos os demais nós do módulo idênticos (AST, sem docstrings) aos do HEAD 8314417", resto_a == resto_h,
        f"{len(resto_a)} nós no atual × {len(resto_h)} no HEAD; diferentes: "
        f"{[k for (k, d), (k2, d2) in zip(resto_a, resto_h) if d != d2][:10]}")
    # docstring nova
    t = ast.parse(atual)
    fn = next(n for n in t.body if isinstance(n, ast.FunctionDef) and n.name == "commits_analise")
    doc = ast.get_docstring(fn) or ""
    ok = bool(re.search(r"(?i)vazio[^.]{0,80}n[ãa]o congela|n[ãa]o congela[^.]{0,80}vazio", " ".join(doc.split())))
    reg("J1.03 docstring de commits_analise diz que um campo vazio não congela", ok,
        "trecho: " + (re.search(r"(?i)[^.]*n[ãa]o congela[^.]*\.", " ".join(doc.split())) or re.search(".", "—")).group(0)[:300])
    # comportamento: os 12 casos próprios e a reprodução da v11 (226 ids) continuam
    A3.R.clear()
    A3.bloco_I1()
    res = {n.split()[0]: (ok_, det) for n, ok_, det in A3.R}
    ok = res["I1.02"][0] and res["I1.05"][0] and res["I1.06"][0]
    reg("J1.04 comportamento inalterado: 12 casos sintéticos próprios corretos, v11 reproduzida nos 226 ids e JSON com o mesmo MD5",
        ok, f"I1.02: {res['I1.02'][0]}; I1.05: {res['I1.05'][0]}; I1.06: {res['I1.06'][0]} ({res['I1.06'][1][:80]})")
    return ok


# ================================================================ teste do checa
def trecho_checa():
    src = (A1.SCR / "etapa7b_checa.py").read_text(encoding="utf-8").splitlines()   # exceção pedida pelo coordenador (rodadas 3–4)
    i9 = next(i for i, l in enumerate(src) if re.match(r"^# -+ 9g\.", l))
    i0 = next(i for i in range(i9, len(src)) if "congelamento do commit_analise" in src[i])
    iok = next(i for i in range(i0, len(src)) if src[i].startswith("ok(") and "congelado" in src[i])
    fim = next(i for i in range(iok + 1, len(src)) if src[i] and not src[i][0].isspace())
    return i0, iok, fim, src


def bloco_checa():
    i0, iok, fim, src = trecho_checa()
    codigo = "\n".join(src[i0:iok])                     # definição de _cong, it0, arq, CASOS e res_cong (sem a chamada ok)
    tree = ast.parse(codigo)
    casos_node = next(n for n in tree.body if isinstance(n, ast.Assign) and chave(n) == "CASOS")
    nomes = [ast.literal_eval(k) for k in casos_node.value.keys]
    # cobertura estática
    txt = "\n".join(src[i0:fim])
    cob = {
        "mesmo valor → herda": any("mesmo valor" in k and "herda" in k and "v98" not in k for k in nomes),
        "formatado mudou": any("formatado mudou" in k for k in nomes),
        "bruto mudou, formatado igual": any("bruto mudou" in k for k in nomes) and "valor_bruto=" in codigo,
        "duas versões com o mesmo valor → a mais nova": any("v98 e v99" in k for k in nomes),
        "mais nova mudou, mais antiga igual → não herda": any("v99 mudou" in k for k in nomes),
        "campo vazio não congela": any("campo vazio" in k for k in nomes),
        "conferência caso a caso": bool(re.search(r"all\(res_cong\[k\] == e for k, \(_, e\) in CASOS\.items\(\)\)", txt)),
    }
    # execução do próprio código do teste contra o commits_analise real, em pasta temporária (sem rodar o checa inteiro)
    lib_src = A1.rt(A1.SCR / "etapa7b_lib.py")
    seg = A3.funcoes_lib()
    Bm = types.ModuleType("B_lib")
    Bm.__dict__.update({"json": json, "np": np, "pd": pd, "subprocess": subprocess, "MS": MS, "PROJ": PROJ})
    for nome in ("_mesmo_valor", "na_tabela", "commits_analise"):
        exec(seg[nome], Bm.__dict__)
    J = json.loads(A1.rb(A1.keyjson(11)))
    ns = {"B": Bm, "J": J, "json": json}
    ms0 = Bm.MS
    exec(compile(codigo, "etapa7b_checa.py[9g congelamento]", "exec"), ns)
    assert Bm.MS == ms0, "o teste não restaurou B.MS"
    CASOS, res = ns["CASOS"], ns["res_cong"]
    caso_a_caso = {k: (res[k], e, res[k] == e) for k, (_, e) in CASOS.items()}
    # os esperados conferem com o dublê próprio (código real com git fictício)? mapeia cada caso nas versões sintéticas
    it0 = ns["it0"]
    proprio = {}
    with tempfile.TemporaryDirectory() as tmp:
        for k, (vers, e) in CASOS.items():
            sub = tempfile.mkdtemp(dir=tmp)
            ms = A3.monta(sub, {n: [x] for n, x in vers.items()})
            nsd = A3.namespace(seg, ms, Path(sub), A3.Dubl([(0, "c0"), (3 * 10 ** 9, "cZ")], "cZ"), na_tabela=lambda i: False)
            r = nsd["commits_analise"]([dict(it0)])[it0["id"]][1]
            # no dublê as versões têm commit fictício (cN); sem herança o derivado recebe o commit_registro; no checa (JSON fora do git)
            # o mesmo caso dá vazio. Comparam-se as heranças: herdou o mesmo valor ou não herdou nada.
            herd = r if r and not r.startswith("c") else ""
            proprio[k] = (herd, e, herd == e)
    ok_cob = all(cob.values())
    ok_exec = all(v[2] for v in caso_a_caso.values()) and len(CASOS) == 6
    ok_prop = all(v[2] for v in proprio.values())
    return dict(i0=i0, fim=fim, nomes=nomes, cob=cob, caso=caso_a_caso, proprio=proprio, ok=ok_cob and ok_exec and ok_prop,
                ok_cob=ok_cob, ok_exec=ok_exec, ok_prop=ok_prop)


def main():
    okj = bloco_lib()
    c = bloco_checa()
    det = (f"rodada 4: teste do checa (bloco 9g, L{c['i0'] + 1}–L{c['fim']}, _cong e CASOS) com {len(c['nomes'])} casos. Cobertura: "
           + "; ".join(f"{k}: {'sim' if v else 'NÃO'}" for k, v in c["cob"].items())
           + ". Execução do próprio código do teste contra o commits_analise real (pasta temporária): "
           + "; ".join(f"{k} → '{r}' (esperado '{e}') {'ok' if o else 'ERRO'}" for k, (r, e, o) in c["caso"].items())
           + ". Esperados conferidos com o dublê próprio: " + ("todos" if c["ok_prop"] else
                                                              str({k: v for k, v in c['proprio'].items() if not v[2]}))
           + ". (Rodada 3: FALHA, só mudava o formatado e usava uma versão arquivada.)")
    print(f"[{'OK ' if c['ok'] else 'FALHA'}] I1.08 (refeita): {det}")
    linhas = list(csv.reader(open(CSV_OUT, encoding="utf-8")))
    cab, corpo = linhas[0], [r for r in linhas[1:] if not r[0].startswith("J")]
    n = 0
    for r in corpo:
        if r[0].startswith("I1.08"):
            r[1], r[2] = ("True" if c["ok"] else "False"), det
            n += 1
    assert n == 1
    R.sort(key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x[0].split()[0])])
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(corpo)
        for nome, ok_, det_ in R:
            w.writerow([nome, "True" if ok_ else "False", det_])
    tudo = list(csv.reader(open(CSV_OUT, encoding="utf-8")))[1:]
    print(f"\nCSV inteiro: {len(tudo)} linhas, {sum(1 for r in tudo if r[1] == 'True')} OK")
    for r in tudo:
        if r[1] != "True":
            print("FALHA:", r[0], "—", r[2][:500])


if __name__ == "__main__":
    main()
