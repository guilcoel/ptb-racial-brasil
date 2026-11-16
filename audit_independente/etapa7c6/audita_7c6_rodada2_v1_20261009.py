#!/usr/bin/env python3
"""
Auditoria independente da Etapa 7c.6 — rodada 2 (só o que mudou depois do relatório da rodada 1).

H1 commit_analise / commit_registro recalculados por código próprio; H2 avaliação da nova definição (com evidência independente dos logs
de execução); H3 v10 arquivada × v11 regerada; H4 observações 7 e 8.

Regras: somente leitura fora de audit_independente/etapa7c6/; não lê etapa7b_checa.py nem checa_7b_*; não lê data/. Dos logs de
outputs/logs só extrai o carimbo de hora e a etiqueta do script ("[aaaa-mm-dd hh:mm:ss] [etiqueta]"); a mensagem é descartada.
Acrescenta as linhas H ao comparacao_7c6_v1_20261009.csv (as linhas A–G da rodada 1 são mantidas como estão) e grava
commit_analise_rodada2_por_id_7c6_v1_20261009.csv.
"""
import ast
import collections
import csv
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audita_7c6_v1_20261009 as A1  # noqa: E402  (funções da rodada 1: leitores, git, guarda)

PROJ, MS, SUB, TB, SCR, OUT = A1.PROJ, A1.MS, A1.SUB, A1.TB, A1.SCR, A1.OUT
git, git_show, rb, rt, guarda, mesmo = A1.git, A1.git_show, A1.rb, A1.rt, A1.guarda, A1.mesmo
STAMP = A1.STAMP
CSV_OUT = OUT / f"comparacao_7c6_v1_{STAMP}.csv"
R = []


def reg(nome, ok, det):
    R.append((nome, bool(ok), str(det).replace("\n", " ")))
    print(f"[{'OK ' if ok else 'FALHA'}] {nome}: {str(det)[:400]}")


FOCO = ["N_M2_ptb", "IC_Ind_T1_tertil_nacional_pig", "n_excl_estciv_ptb", "pct_amarela_fonte", "N_fonte", "prev_ptb_Branca"]


# ---------------------------------------------------------------- utilidades
def celulas(path):
    """Todas as células numéricas (float finito) do CSV de origem, com o nome da coluna (leitura célula a célula, sem pandas)."""
    rows = list(csv.reader(open(guarda(path), encoding="utf-8")))
    cab = rows[0] if rows else []
    out = []
    for r in rows[1:]:
        for j, c in enumerate(r):
            try:
                x = float(c)
            except ValueError:
                continue
            if math.isfinite(x):
                out.append((cab[j] if j < len(cab) else f"col{j}", x))
    return out


def casa(v, x):
    return abs(v - x) <= 1e-12 + 1e-9 * abs(v)


def direto(it, cel):
    vs = it["valor_bruto"] if isinstance(it["valor_bruto"], list) else [it["valor_bruto"]]
    return all(any(casa(float(v), x) for _, x in cel) for v in vs)


def historico():
    h = []
    for l in git("log", "--format=%h %ct %s").splitlines():
        hh, ct, s = l.split(" ", 2)
        h.append((int(ct), hh, s))
    return sorted(h)


def logs():
    """[(epoch, etiqueta, arquivo)] só com carimbo e etiqueta; a mensagem não é guardada."""
    out = []
    for p in sorted((PROJ / "outputs" / "logs").glob("*.log")):
        if p.name.startswith("._"):
            continue
        for l in rb(p).decode("utf-8", errors="replace").splitlines():
            m = re.match(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\]", l)
            if m:
                out.append((datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp(), m.group(2), p.name))
    return out


def registro_chain(J11):
    vers = []
    for n in range(1, 11):
        orig = f"outputs/manuscrito/numeros_chave_v{n}_{STAMP}.json"
        adds = git("log", "--diff-filter=A", "--format=%h", "--", orig).split()
        c = adds[-1] if adds else ""
        vers.append((n, c, {i["id"]: i for i in json.loads(git_show(c, orig))}))
    out = {}
    for it in J11:
        cr, vmin = "", None
        for n, c, J in sorted(vers, key=lambda x: -x[0]):
            x = J.get(it["id"])
            if x is None or x["valor_formatado"] != it["valor_formatado"] or not mesmo(x["valor_bruto"], it["valor_bruto"]):
                break
            cr, vmin = c, n
        out[it["id"]] = (cr, vmin)
    return out


# ================================================================ H1
def bloco_H1():
    J10 = json.loads(rb(A1.keyjson(10)))
    J11 = json.loads(rb(A1.keyjson(11)))
    d10, d11 = {i["id"]: i for i in J10}, {i["id"]: i for i in J11}
    ids = [i["id"] for i in J11]
    ok = ids == [i["id"] for i in J10] and all(mesmo(d10[k]["valor_bruto"], d11[k]["valor_bruto"], 0) and
                                               d10[k]["valor_formatado"] == d11[k]["valor_formatado"] for k in ids)
    reg("H1.01 JSON v11 regerado: mesmos 226 ids, na mesma ordem, com valor_bruto e valor_formatado idênticos aos da v10", ok,
        f"{len(J11)} ids")
    esperado = (set(d10[ids[0]]) - {"commit"}) | {"commit_pacote", "commit_registro", "commit_analise"}
    ok = all(set(i) == esperado for i in J11) and all(i["commit_pacote"] == A1.HEAD_ESPERADO for i in J11)
    reg("H1.02 campos: 'commit' da v10 → commit_pacote (8314417) + commit_registro + commit_analise; nenhum outro campo novo", ok,
        f"chaves: {list(J11[0].keys())}")

    chain = registro_chain(J11)
    dif = [k for k in ids if d11[k]["commit_registro"] != chain[k][0]]
    reg("H1.03 commit_registro recalculado (JSON das versões lidas do git; v10→v1 enquanto o valor é o mesmo) = JSON, id a id", not dif,
        f"226 ids; divergentes: {dif}")

    hist = historico()
    cache_cel, cache_b = {}, {}
    linhas = {}
    for k in ids:
        it = d11[k]
        cr = chain[k][0]
        arq = PROJ / it["arquivo"]
        sc = it["script"].split()[0] if it["script"] else ""
        if it["arquivo"] not in cache_cel:
            cache_cel[it["arquivo"]] = celulas(arq) if arq.exists() and arq.suffix == ".csv" else []
        cel = cache_cel[it["arquivo"]]
        dirv = bool(cel) and direto(it, cel)
        mt = arq.stat().st_mtime if arq.exists() else None
        a = next((h for t, h, _ in hist if mt is not None and t >= mt), "")
        if (cr, sc) not in cache_b:
            cache_b[(cr, sc)] = git("log", "-1", "--format=%h", cr, "--", sc).strip() if cr and sc else ""
        b = cache_b[(cr, sc)]
        if not cr or not sc:
            ca = ""
        elif dirv:
            ca = a if a and a == b else ""
        else:
            ca = cr
        linhas[k] = dict(id=k, direto=dirv, mtime=mt, a=a, b=b, commit_registro=cr, commit_analise=ca, script=sc, arquivo=it["arquivo"],
                         json_analise=it["commit_analise"], json_registro=it["commit_registro"], valor=it["valor_bruto"])
    dif = [k for k in ids if linhas[k]["commit_analise"] != d11[k]["commit_analise"]]
    reg("H1.04 commit_analise recalculado (leitura célula a célula da tabela; (a) 1º commit com data ≥ mtime; (b) último commit do script "
        "até o commit_registro; aceito se a = b; derivado → commit_registro) = JSON, id a id", not dif,
        f"226 ids; divergentes: {[(k, d11[k]['commit_analise'], linhas[k]['commit_analise']) for k in dif]}")
    nder = sum(1 for k in ids if not linhas[k]["direto"])
    ndir = len(ids) - nder
    disc = [k for k in ids if linhas[k]["direto"] and linhas[k]["a"] != linhas[k]["b"]]
    dist = collections.Counter(d11[k]["commit_analise"] for k in ids)
    vaz = sum(1 for k in ids if not d11[k]["commit_analise"])
    nome = {h: s.split(":")[0] for _, h, s in hist}
    reg("H1.05 (registro) distribuição de commit_analise, vazios e derivados", True,
        "; ".join(f"{c or '(vazio)'} [{nome.get(c, '')}]: {n}" for c, n in sorted(dist.items(), key=lambda x: [h for _, h, _ in hist].index(x[0])
                                                                                  if x[0] in nome else 99))
        + f"; vazios: {vaz}; lidos direto da tabela: {ndir}; derivados no pacote: {nder}; diretos com (a) ≠ (b): {len(disc)}")
    dreg = collections.Counter(d11[k]["commit_registro"] for k in ids)
    reg("H1.06 (registro) distribuição de commit_registro", True,
        "; ".join(f"{c} [{nome.get(c, '')}]: {n}" for c, n in dreg.items()) + f"; vazios: {sum(1 for k in ids if not d11[k]['commit_registro'])}")
    # md
    md = rt(MS / f"numeros_chave_v11_{STAMP}.md").splitlines()
    rows = [l for l in md if l.startswith("| ") and not l.startswith("| id ") and not l.startswith("|---")]
    cab = [l for l in md if l.startswith("| id ")]
    ruins = []
    for i, l in enumerate(rows):
        cel = re.split(r"(?<!\\)\|", l)
        if not l.startswith(f"| {J11[i]['id']} |") or cel[-3].strip() != J11[i]["commit_analise"] or cel[-2].strip() != J11[i]["commit_registro"]:
            ruins.append(J11[i]["id"])
    reg("H1.07 numeros_chave_v11.md: colunas commit_analise e commit_registro iguais ao JSON, na mesma ordem", len(rows) == 226 and not ruins
        and cab and cab[0].rstrip().endswith("| commit_analise | commit_registro |"), f"linhas: {len(rows)}; divergentes: {ruins[:10]}")
    return J11, d11, linhas, hist


def bloco_H1_foco(d11, linhas, logev, hist):
    nome = {h: s.split(":")[0] for _, h, s in hist}
    for j, k in enumerate(FOCO, 8):
        L_ = linhas[k]
        ev = logev.get(k, {})
        det = (f"valor {L_['valor']}; origem {L_['arquivo'].replace('outputs/tables/', '')} ({L_['script'].replace('scripts/', '')}); "
               f"{'lido direto da tabela' if L_['direto'] else 'derivado no pacote'}; ")
        if L_["direto"]:
            det += (f"mtime {datetime.fromtimestamp(L_['mtime']).strftime('%Y-%m-%d %H:%M:%S')} → (a) {L_['a']} [{nome.get(L_['a'], '')}]; "
                    f"(b) {L_['b']} [{nome.get(L_['b'], '')}]; log: {ev.get('det', '—')}; ")
        det += (f"commit_registro {L_['commit_registro']} [{nome.get(L_['commit_registro'], '')}]; commit_analise auditor "
                f"{L_['commit_analise']} × JSON {d11[k]['commit_analise']}")
        ok = L_["commit_analise"] == d11[k]["commit_analise"] and L_["commit_registro"] == d11[k]["commit_registro"] and \
            (not L_["direto"] or ev.get("ok", False))
        reg(f"H1.{j:02d} {k}", ok, det)


# ================================================================ H2
def bloco_H2(J11, d11, linhas, hist):
    ids = [i["id"] for i in J11]
    LG = logs()
    nome = {h: s.split(":")[0] for _, h, s in hist}
    tempo = {h: t for t, h, _ in hist}
    # evidência independente: o script de origem registrou no log uma linha a até 3 s do mtime da tabela
    srccache = {}
    logev = {}
    tabs = collections.OrderedDict()
    for k in ids:
        L_ = linhas[k]
        if not L_["direto"]:
            continue
        tabs.setdefault((L_["arquivo"], L_["script"], L_["commit_analise"]), []).append(k)
    tab_ok, tab_ruim = 0, []
    for (arq, sc, ca), ks in tabs.items():
        mt = linhas[ks[0]]["mtime"]
        if sc not in srccache:
            srccache[sc] = rt(PROJ / sc)
        perto = [(abs(t - mt), t, g, f) for t, g, f in LG if abs(t - mt) <= 3]
        meus = [x for x in perto if x[2] in srccache[sc]]
        if meus:
            _, t, g, f = min(meus)
            st = next((h for tt, h, _ in hist if tt >= t), "")
            ok = st == ca
            det = f"[{g}] em {f} às {datetime.fromtimestamp(t).strftime('%H:%M:%S')} → {st} [{nome.get(st, '')}]"
        else:
            ok, det = False, f"sem linha do script a ≤3 s (etiquetas próximas: {sorted(set(x[2] for x in perto))})"
        for k in ks:
            logev[k] = dict(ok=ok, det=det)
        if ok:
            tab_ok += 1
        else:
            tab_ruim.append(f"{arq.replace('outputs/tables/', '')}: {det}")
    ndir = sum(len(v) for v in tabs.values())
    reg("H2.01 evidência independente (logs de execução): para cada tabela de origem lida direto, o próprio script de origem gravou no log "
        "a ≤3 s do mtime, e o 1º commit depois desse carimbo é o commit_analise", not tab_ruim,
        f"{len(tabs)} tabelas ({ndir} ids diretos) confirmadas: {tab_ok}; não confirmadas: {tab_ruim}")
    # coerência temporal: a tabela atual já existia quando o valor foi registrado
    tard = [k for k in ids if linhas[k]["direto"] and linhas[k]["mtime"] > tempo.get(linhas[k]["commit_registro"], 0)]
    reg("H2.02 para os diretos, a tabela atual é anterior ao commit_registro (o valor registrado saiu desta versão da tabela)", not tard,
        f"ids com tabela mais nova que o registro: {tard}")
    # o script no commit_analise contém o nome da tabela (identidade do script pelo git)
    sem = []
    for (arq, sc, ca), ks in tabs.items():
        base = Path(arq).name.replace(f"_v1_20261008.csv", "")
        src = git_show(ca, sc).decode("utf-8", errors="replace") if ca else ""
        partes = [base, "_".join(base.split("_")[:3])]
        if not any(p in src for p in partes):
            sem.append(f"{base} em {sc}@{ca}")
    reg("H2.03 no commit_analise, o script de origem contém o nome (ou o prefixo) da tabela que gera", not sem, f"sem o nome: {sem}")
    # derivados: transformação trivial de uma célula (×100, ÷100, sinal)? — seria cálculo da etapa de análise, não do pacote
    triv = []
    for k in ids:
        L_ = linhas[k]
        if L_["direto"] or isinstance(L_["valor"], list):
            continue
        cel = celulas(PROJ / L_["arquivo"])
        v = float(L_["valor"])
        for nm, f in [("×100", lambda x: 100 * x), ("÷100", lambda x: x / 100), ("−x", lambda x: -x), ("x/1000", lambda x: x / 1000)]:
            if any(casa(v, f(x)) for _, x in cel):
                triv.append(f"{k} ({nm})")
                break
    reg("H2.04 nenhum valor 'derivado' é só uma célula da tabela reescalada (×100, ÷100, sinal, ÷1000)", not triv, f"casos: {triv}")
    # diretos ambíguos: inteiros pequenos ou valor presente em várias colunas (risco de coincidência)
    amb = []
    for k in ids:
        L_ = linhas[k]
        if not L_["direto"] or isinstance(L_["valor"], list):
            continue
        v = float(L_["valor"])
        cols = {c for c, x in celulas(PROJ / L_["arquivo"]) if casa(v, x)}
        if (float(v).is_integer() and abs(v) < 1000) or len(cols) > 1:
            amb.append(f"{k}={L_['valor']} em {sorted(cols)}")
    reg("H2.05 (registro) diretos com risco de coincidência (inteiro < 1000 ou valor em mais de uma coluna)", True, f"{len(amb)}: {amb}")
    # derivados: o código que calcula (etapa7b_01_tabelas.py) foi alterado no commit_registro
    ruins = []
    for k in ids:
        L_ = linhas[k]
        if L_["direto"]:
            continue
        cr = L_["commit_registro"]
        u = git("log", "-1", "--format=%h", cr, "--", "scripts/etapa7b_01_tabelas.py").strip()
        if u != cr:
            ruins.append(f"{k}: último commit do etapa7b_01_tabelas.py até {cr} = {u}")
    der = [k for k in ids if not linhas[k]["direto"]]
    reg("H2.06 derivados: o script do pacote que os calcula (etapa7b_01_tabelas.py) foi alterado no próprio commit_registro", not ruins,
        f"{len(der)} derivados {der}; divergências: {ruins}")
    # quanto o critério de concordância descarta, e se a regra (a) sozinha ou (b) sozinha mudaria algo
    so_a = sum(1 for k in ids if linhas[k]["direto"] and linhas[k]["a"] != linhas[k]["commit_analise"])
    so_b = sum(1 for k in ids if linhas[k]["direto"] and linhas[k]["b"] != linhas[k]["commit_analise"])
    reg("H2.07 (registro) concordância (a) mtime × (b) histórico do script nos diretos", True,
        f"diretos: {ndir}; (a) ≠ commit_analise: {so_a}; (b) ≠ commit_analise: {so_b}; vazios por discordância: "
        f"{sum(1 for k in ids if linhas[k]['direto'] and not linhas[k]['commit_analise'])}")
    # derivados com insumos calculados antes: commit_analise (pacote) ≠ commit das tabelas de origem
    ins = collections.Counter()
    for k in der:
        L_ = linhas[k]
        a = L_["a"]
        ins[(L_["commit_registro"], a)] += 1
    reg("H2.08 (registro) derivados: commit_analise (= commit_registro) × etapa que gerou a tabela de onde vêm os insumos ((a) pelo mtime)",
        True, "; ".join(f"{cr} [{nome.get(cr, '')}] com insumos de {a} [{nome.get(a, '')}]: {n}" for (cr, a), n in ins.items()))
    # 7c.3: quais ids têm commit_registro 3092186 e qual o commit_analise
    c73 = collections.Counter((linhas[k]["commit_analise"], "direto" if linhas[k]["direto"] else "derivado") for k in ids
                              if linhas[k]["commit_registro"] == "3092186")
    reg("H2.09 (registro) ids registrados na 7c.3 (3092186): commit_analise", True,
        "; ".join(f"{c} [{nome.get(c, '')}] ({t}): {n}" for (c, t), n in c73.items()))
    # gravar por id
    with open(OUT / f"commit_analise_rodada2_por_id_7c6_v1_{STAMP}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "lido_direto_da_tabela", "tabela_origem", "script_origem", "mtime_tabela", "a_1o_commit_apos_mtime",
                    "b_ultimo_commit_script_ate_registro", "evidencia_log", "commit_registro_auditor", "commit_registro_json",
                    "commit_analise_auditor", "commit_analise_json", "igual"])
        for k in ids:
            L_ = linhas[k]
            w.writerow([k, L_["direto"], L_["arquivo"].replace("outputs/tables/", ""), L_["script"],
                        datetime.fromtimestamp(L_["mtime"]).strftime("%Y-%m-%d %H:%M:%S") if L_["mtime"] else "", L_["a"], L_["b"],
                        logev.get(k, {}).get("det", "") if L_["direto"] else "", L_["commit_registro"], d11[k]["commit_registro"],
                        L_["commit_analise"], d11[k]["commit_analise"],
                        L_["commit_analise"] == d11[k]["commit_analise"] and L_["commit_registro"] == d11[k]["commit_registro"]])
    return logev, der, triv, amb


# ================================================================ H3
def bloco_H3():
    J10 = json.loads(rb(A1.keyjson(10)))
    J11 = json.loads(rb(A1.keyjson(11)))
    tira = lambda J, cs: [{k: v for k, v in i.items() if k not in cs} for i in J]
    ok = tira(J10, {"commit"}) == tira(J11, {"commit_pacote", "commit_registro", "commit_analise"})
    reg("H3.01 numeros_chave JSON: v11 = v10 fora os campos de commit (valores, descrições, origem idênticos)", ok, "226 itens")
    m10 = rt(A1.base(10) / f"numeros_chave_v10_{STAMP}.md").splitlines()
    m11 = rt(MS / f"numeros_chave_v11_{STAMP}.md").splitlines()
    corta = lambda ls: [re.split(r"(?<!\\)\|", l)[1:7] for l in ls if l.startswith("| ") and not l.startswith("| id ")]
    reg("H3.02 numeros_chave md: mesmas linhas (id, valor, descrição, arquivo, script, filtro); mudam só cabeçalho e colunas de commit",
        corta(m10) == corta(m11), f"{len(corta(m11))} linhas")
    c10, c11 = A1.csvs(10), A1.csvs(11)
    dif = [k for k in c10 if k in c11 and rb(c10[k]) != rb(c11[k])]
    reg("H3.03 CSV (tabelas/ e suplementar/) idênticos byte a byte", set(c10) == set(c11) and not dif, f"{len(c11)} arquivos; diferentes: {dif}")
    xd = []
    for wbn in A1.workbooks(10):
        X10, X11 = A1.xlsx_cells(A1.workbooks(10)[wbn]), A1.xlsx_cells(A1.workbooks(11)[wbn])
        for s in set(X10) | set(X11):
            if [(c, A1.norm_ver(str(v))) for c, v in X10.get(s, [])] != [(c, A1.norm_ver(str(v))) for c, v in X11.get(s, [])]:
                xd.append(f"{wbn}:{s}")
    reg("H3.04 xlsx (tabelas principais, ESM_1, Submissao/ESM_1): todas as células iguais, inclusive títulos e rodapés", not xd, f"diferenças: {xd}")
    d10 = A1.docx_text(A1.base(10) / "tabelas" / f"tabelas_principais_v10_{STAMP}.docx")
    d11 = A1.docx_text(MS / "tabelas" / f"tabelas_principais_v11_{STAMP}.docx")
    reg("H3.05 docx das tabelas principais: mesmo texto", [(k, A1.norm_ver(t)) for k, t in d10] == [(k, A1.norm_ver(t)) for k, t in d11],
        f"{len(d11)} blocos")
    f10, f11 = A1.pdfs(10), A1.pdfs(11)
    pdif = [k for k in f10 if [A1.norm_ver(x) for x in A1.pdf_text(f10[k])] != [A1.norm_ver(x) for x in A1.pdf_text(f11[k])]]
    reg("H3.06 PDFs (Submissao/ESM_2–4; S7, S8): mesmo texto página a página", not pdif, f"diferentes: {pdif}")
    t10, t11 = A1.tiffs(10), A1.tiffs(11)
    tdif = [k for k in t10 if A1.pix_sig(t10[k]) != A1.pix_sig(t11[k])]
    reg("H3.07 TIFF (figuras 1–4, S9, Submissao/Fig1–4): mesmos pixels", not tdif, f"diferentes: {tdif}")
    p10, p11 = A1.pngs(10), A1.pngs(11)
    pd_ = [k for k in p10 if A1.pix_sig(p10[k]) != A1.pix_sig(p11[k])]
    reg("H3.08 PNG: mesmos pixels", not pd_, f"diferentes: {pd_}")
    a = rt(A1.base(10) / f"data_code_availability_v10_{STAMP}.md").splitlines()
    b = rt(MS / "data_code_availability.md").splitlines()
    la = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    reg("H3.09 data_code_availability.md: só as linhas 1 e 30 (rótulo de versão e commit de referência) diferem da v10", la == [1, 30] and len(a) == len(b),
        f"linhas diferentes: {la}")
    a = rt(A1.base(10) / f"legendas_figuras_v10_{STAMP}.md")
    b = rt(MS / "legendas_figuras.md")
    reg("H3.10 legendas_figuras.md: igual fora o rótulo de versão", A1.norm_ver(a) == A1.norm_ver(b), "")
    sobra = [str(p.relative_to(SUB)) for p in SUB.rglob("*") if p.name.startswith("._") or p.name == ".DS_Store"]
    reg("H3.11 Submissao/ sem ._* e sem .DS_Store depois da regeração", not sobra, f"{sobra}")
    # MANIFEST
    man = rt(MS / "MANIFEST.md").splitlines()
    pref = {"manuscrito/tabelas": MS / "tabelas", "manuscrito/figuras": MS / "figuras", "manuscrito/suplementar": MS / "suplementar",
            "manuscrito": MS, "Submissao": SUB}
    ruins, n = [], 0
    for l in man:
        m = re.match(r"\| (manuscrito(?:/tabelas|/figuras|/suplementar)?|Submissao)/([^ |]+) \| [^|]* \| [^|]* \| ([0-9a-f]{12}) \|$", l)
        if not m or A1.PROIBIDO.search(m.group(2)):
            continue
        p = pref[m.group(1)] / m.group(2)
        n += 1
        if not p.exists() or A1.md5b(rb(p))[:12] != m.group(3):
            ruins.append(f"{m.group(1)}/{m.group(2)}")
    reg("H3.12 MANIFEST.md regerado: MD5 de cada arquivo listado confere com o disco (checa_7b_* não lido)", n > 0 and not ruins,
        f"{n} conferidos; divergentes: {ruins}")
    # integridade do _arquivo_v10 continua (não foi tocado pela regeração)
    ruins, n = [], 0
    mapa = {f"data_code_availability_v10_{STAMP}.md": "outputs/manuscrito/data_code_availability.md",
            f"legendas_figuras_v10_{STAMP}.md": "outputs/manuscrito/legendas_figuras.md", f"MANIFEST_v10_{STAMP}.md": "outputs/manuscrito/MANIFEST.md"}
    for p in sorted(A1.base(10).rglob("*")):
        if p.is_dir() or p.name.startswith("._") or A1.PROIBIDO.search(str(p)):
            continue
        rel = p.relative_to(A1.base(10))
        g = mapa.get(str(rel)) or ("Submissao/" + "/".join(rel.parts[1:]) if rel.parts[0] == "Submissao" else "outputs/manuscrito/" + str(rel))
        n += 1
        if git_show(A1.HEAD_ESPERADO, g) != rb(p):
            ruins.append(str(rel))
    reg("H3.13 _arquivo_v10 continua idêntico ao pacote v10 do commit 8314417", not ruins, f"{n} arquivos; diferentes: {ruins}")


# ================================================================ H4
def bloco_H4():
    src = rt(SCR / "etapa7b_04_submissao.py")
    tree = ast.parse(src)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "limpa_macos"]
    ok, det = False, "limpa_macos não encontrada"
    if fn:
        f = fn[0]
        asserts = [n for n in ast.walk(f) if isinstance(n, ast.Assert)]
        raises = [n for n in ast.walk(f) if isinstance(n, ast.Raise) and n.exc is not None and isinstance(n.exc, ast.Call)
                  and ast.unparse(n.exc.func) == "RuntimeError"]
        ifs = [n for n in ast.walk(f) if isinstance(n, ast.If) and any(r in ast.walk(n) for r in raises)]
        dc = [n for n in ast.walk(f) if isinstance(n, ast.Call) and ast.unparse(n.func) == "subprocess.run" and n.args
              and isinstance(n.args[0], ast.List) and [ast.unparse(x) for x in n.args[0].elts][:2] == ["'dot_clean'", "'-m'"]
              and any(k.arg == "check" and ast.unparse(k.value) == "True" for k in n.keywords)]
        globs = [n for n in ast.walk(f) if isinstance(n, ast.Call) and ast.unparse(n.func).endswith(".rglob") and n.args
                 and ast.unparse(n.args[0]) == "'._*'"]
        ok = bool(raises and ifs and dc and globs) and not asserts
        det = (f"L{f.lineno}–L{f.end_lineno}: dot_clean -m check=True em L{[n.lineno for n in dc]}; rglob('._*') em L{[n.lineno for n in globs]}; "
               f"if {[ast.unparse(n.test) for n in ifs]} → raise RuntimeError em L{[n.lineno for n in raises]}; asserts restantes: {len(asserts)}")
    reg("H4.01 observação 7: limpa_macos falha com 'raise RuntimeError' (não mais assert), mantendo dot_clean -m e a busca de ._*", ok, det)
    chamadas = [n.lineno for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                and ast.unparse(n.value.func) == "limpa_macos" and ast.unparse(n.value.args[0]) == "B.SUB"]
    esc = sorted({n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) in ("shutil.copy2", "B.html_pdf")
                  and any("B.SUB" in ast.unparse(a) for a in n.args)})
    reg("H4.02 limpa_macos(B.SUB) continua antes da 1ª e depois da última escrita em Submissao/", bool(chamadas and esc) and
        min(chamadas) < min(esc) and max(chamadas) > max(esc), f"chamadas L{chamadas}; escritas L{esc}")
    asserts_mod = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    reg("H4.03 (registro) outros assert no etapa7b_04_submissao.py (fora da trava de ._*)", True, f"linhas: {asserts_mod}")
    t = rt(PROJ / "docs/referencias/ATRIBUICAO.txt")
    tn = A1.norm_ws(t)
    frase = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    nota = bool(re.search(r"(?i)vers[aã]o.{0,120}(link|URL|site)|(link|URL|site).{0,120}vers[aã]o", tn))
    reg("H4.04 observação 8: ATRIBUICAO.txt diz 'Creative Commons Attribution 4.0 International (CC BY 4.0)', com nota de que a versão "
        "vem do link do site", frase in tn and nota, f"frase: {frase in tn}; nota sobre a origem da versão: {nota}")
    obra = ["Benchimol EI", "PLoS Med. 2015;12(10):e1001885", "doi:10.1371/journal.pmed.1001885",
            "https://www.record-statement.org/checklist.php", "https://www.record-statement.org/Files/checklist/RECORD%20Checklist.docx",
            "creativecommons.org/licenses/by/4.0", "d50bd10feb3c20398ccce6f3c27b7777"]
    reg("H4.05 ATRIBUICAO.txt mantém obra, DOI, URLs, link da licença e MD5 do docx", all(o in tn for o in obra),
        f"faltando: {[o for o in obra if o not in tn]}")
    st = git("ls-files", "-s", "--", "docs/referencias/ATRIBUICAO.txt").split()
    wt = git("hash-object", "--", "docs/referencias/ATRIBUICAO.txt").strip()
    idx = subprocess.run(["git", "-C", str(PROJ), "show", ":docs/referencias/ATRIBUICAO.txt"], capture_output=True).stdout.decode("utf-8", "replace")
    reg("H4.06 a versão nova do ATRIBUICAO.txt está no índice do git (o que vai para o commit)", bool(st) and st[1] == wt,
        f"blob no índice {st[1] if st else '—'} × working tree {wt}; a frase 'CC BY 4.0' {'está' if frase in A1.norm_ws(idx) else 'NÃO está'} "
        f"na cópia do índice")
    st = git("ls-files", "-s", "--", "docs/referencias/RECORD_checklist_acesso20261009.docx").split()
    wt = git("hash-object", "--", "docs/referencias/RECORD_checklist_acesso20261009.docx").strip()
    reg("H4.07 RECORD docx continua no índice e igual ao working tree", bool(st) and st[1] == wt, f"{st[1] if st else '—'} × {wt}")


def main():
    J11, d11, linhas, hist = bloco_H1()
    logev, der, triv, amb = bloco_H2(J11, d11, linhas, hist)
    bloco_H1_foco(d11, linhas, logev, hist)
    bloco_H3()
    bloco_H4()
    R.sort(key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x[0].split()[0])])
    antigas = [r for r in csv.reader(open(CSV_OUT, encoding="utf-8"))]
    cab, corpo = antigas[0], [r for r in antigas[1:] if not r[0].startswith("H")]
    assert cab == ["verificacao", "ok", "detalhe"], cab
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(corpo)
        for nome, ok, det in R:
            w.writerow([nome, "True" if ok else "False", det])
    n_ok = sum(1 for _, ok, _ in R if ok)
    print(f"\nRodada 2: {len(R)} verificações, {n_ok} OK, {len(R) - n_ok} falhas; linhas A–G mantidas: {len(corpo)}")
    for nome, ok, det in R:
        if not ok:
            print("FALHA:", nome, "—", det[:600])


if __name__ == "__main__":
    main()
