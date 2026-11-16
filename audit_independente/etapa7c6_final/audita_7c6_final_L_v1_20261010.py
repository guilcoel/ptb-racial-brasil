"""Bloco L — afirmações do RESUMO_ETAPA7C6 (L1), relato final ao usuário (L2), reprodutibilidade do RESUMO (L3),
campos de commit dos números-chave com código próprio (L4) e reexecução do checa (L5)."""
import ast
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from audita_7c6_final_lib_v1_20261010 import (A10, HEAD, MS, OUT, PAI, PROJ, SUB, V10, V11, assunto, blob, docx_texto, git, ler, pdf_texto,
                                              pixels, ws, xlsx_celulas)

RESUMO = PROJ / "outputs" / "RESUMO_ETAPA7C6_v1_20261009.md"
AUD = PROJ / "audit_independente" / "etapa7c6"
REL = AUD / "relatorio_7c6_v1_20261009.md"
CP = AUD / "comparacao_7c6_v1_20261009.csv"
GER = ["etapa7b_05_resumo.py", "etapa7b1_03_resumo.py", "etapa7b2_02_resumo.py", "etapa7b3_02_resumo.py", "etapa7c1_02_resumo.py",
       "etapa7c2_02_resumo.py", "etapa7c3_01_resumo.py", "etapa7c4_01_resumo.py", "etapa7c5_01_resumo.py", "etapa7c5b_01_resumo.py"]


# ------------------------------------------------------------------ utilidades próprias (sem etapa7b_lib)
def json_versao(n):
    """JSON da versão n lido do git, no commit que o adicionou no caminho original; e o commit (abreviado)."""
    cam = f"outputs/manuscrito/numeros_chave_v{n}_20261009.json"
    adds = git("log", "--diff-filter=A", "--format=%h", "--", cam).split()
    c = adds[-1]
    return json.loads(blob(c, cam)), c, len(adds)


def colunas_numericas(caminho):
    """Valores das colunas em que toda célula não vazia é número (equivale ao select_dtypes('number') do pandas)."""
    rows = list(csv.reader(io.StringIO(ler(PROJ / caminho))))
    hdr, body = rows[0], rows[1:]
    out = []
    for j in range(len(hdr)):
        vals, ok = [], True
        for r in body:
            v = r[j].strip() if j < len(r) else ""
            if v == "":
                continue
            if v in ("True", "False"):
                ok = False
                break
            try:
                vals.append(float(v))
            except ValueError:
                ok = False
                break
        if ok:
            out += vals
    return np.array(out, dtype=float)


_CACHE = {}


def lido_direto(it):
    if it["arquivo"] not in _CACHE:
        _CACHE[it["arquivo"]] = colunas_numericas(it["arquivo"])
    src = _CACHE[it["arquivo"]]
    v = it["valor_bruto"]
    return all(bool((np.abs(src - x) <= 1e-12 + 1e-9 * abs(x)).any()) for x in (v if isinstance(v, list) else [v]))


def mesmo_valor(a, b, exato=False):
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(mesmo_valor(x, y, exato) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return a == b if exato else abs(a - b) <= 1e-12 * max(abs(a), abs(b))
    return a == b


def md_tabelas(texto):
    """Linhas de tabelas markdown (lista de listas de células), agrupadas por bloco contíguo."""
    blocos, atual = [], []
    for l in texto.splitlines():
        if l.startswith("|"):
            atual.append([c.strip() for c in l.strip().strip("|").split("|")])
        elif atual:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    return [[r for r in b if not set("".join(r)) <= set(":-")] for b in blocos]


def run(reg, ctx):
    R = ler(RESUMO)
    R_head = blob(HEAD, "outputs/RESUMO_ETAPA7C6_v1_20261009.md").decode()
    rel = ler(REL)
    cp = list(csv.DictReader(io.StringIO(ler(CP))))
    J = json.loads(ler(MS / f"numeros_chave_{V11}.json"))
    Jd = {i["id"]: i for i in J}
    J10 = json.loads(ler(A10 / f"numeros_chave_{V10}.json"))
    J10d = {i["id"]: i for i in J10}
    reg("L1.00", R == R_head, f"RESUMO no disco = blob de {HEAD}: {R == R_head}; {len(R.splitlines())} linhas; as afirmações abaixo são conferidas contra o blob")

    # ============ cabeçalho e "O que foi feito"
    arv = set(git("ls-tree", "-r", "--name-only", HEAD).splitlines())
    v11 = sorted(p for p in arv if V11 in p)
    a10 = sorted(p for p in arv if p.startswith("outputs/manuscrito/_arquivo_v10/"))
    v10_fora = sorted(p for p in arv if V10 in p and "_arquivo_v10" not in p)
    reg("L1.01", len(v11) > 0 and len(a10) > 0 and not v10_fora,
        f"pacote v11_20261009: {len(v11)} arquivos versionados com o rótulo v11; _arquivo_v10/: {len(a10)} arquivos versionados; "
        f"arquivos v10 fora de _arquivo_v10: {len(v10_fora)}")
    ns = ctx.get("K3_ns") or [l.split("\t") for l in git("diff", "--name-status", "-M", PAI, HEAD).splitlines()]
    scripts_mud = sorted({x[-1] for x in ns if x[-1].startswith("scripts/") and not x[0].startswith("R")})
    analise = [s for s in scripts_mud if not (s.startswith("scripts/etapa7b_") or s.startswith("scripts/resumos/"))]
    reg("L1.02", not analise and not any(x[-1].startswith("outputs/tables/") for x in ns),
        f"'nenhuma análise nova': scripts alterados/novos no commit = {scripts_mud} (só pacote e RESUMO); scripts de análise alterados: {analise or 'nenhum'}; "
        f"outputs/tables no commit: {sum(1 for x in ns if x[-1].startswith('outputs/tables/'))}")

    # ---- nenhum número mudou: números-chave, CSV, xlsx, docx, PDF, imagens (v10 arquivada × v11)
    mesmos_ids = [i["id"] for i in J10] == [i["id"] for i in J]
    dif_val = [k for k in J10d if not (mesmo_valor(J10d[k]["valor_bruto"], Jd[k]["valor_bruto"], exato=True)
                                        and J10d[k]["valor_formatado"] == Jd[k]["valor_formatado"])]
    dif_meta = [k for k in J10d if any(J10d[k][c] != Jd[k][c] for c in ("descricao", "filtro", "arquivo", "script"))]
    campos10, campos11 = {k for i in J10 for k in i}, {k for i in J for k in i}
    reg("L1.03", mesmos_ids and not dif_val and not dif_meta,
        f"números-chave v10 × v11: {len(J10)} × {len(J)} ids, mesma ordem: {mesmos_ids}; valor_bruto (igualdade exata) e valor_formatado diferentes: "
        f"{len(dif_val)}; descricao/filtro/arquivo/script diferentes: {len(dif_meta)}; campos só na v10: {sorted(campos10 - campos11)}; só na v11: {sorted(campos11 - campos10)}")
    pares = [(A10 / "tabelas" / f"{n}_{V10}.csv", MS / "tabelas" / f"{n}_{V11}.csv") for n in
             ["tab01_characteristics", "tab02_models_m1m3", "tab03_knol_tercile", "tab03b_terciles_region", "tab04_sensitivity"]]
    pares += [(f, MS / "suplementar" / f.name.replace(V10, V11)) for f in sorted((A10 / "suplementar").glob(f"*_{V10}.csv"))
              if not f.name.startswith("._")]
    dif_csv = [b.name for a, b in pares if ler(a, True) != ler(b, True)]
    ncel = sum(pd.read_csv(b, dtype=str).shape[0] * pd.read_csv(b, dtype=str).shape[1] for _, b in pares)
    ctx["ncel"], ctx["npares"] = ncel, len(pares)
    reg("L1.04", not dif_csv and len(pares) == 20,
        f"{len(pares)} pares CSV (5 tabelas + {len(pares) - 5} suplementares) v10 × v11: diferentes byte a byte: {dif_csv or 'nenhum'}; células (sem cabeçalho) {ncel:,}")
    px = [(A10 / "tabelas" / f"tabelas_principais_{V10}.xlsx", MS / "tabelas" / f"tabelas_principais_{V11}.xlsx"),
          (A10 / "suplementar" / f"ESM_1_tables_S1_S6_{V10}.xlsx", MS / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"),
          (A10 / "Submissao" / "ESM_1.xlsx", SUB / "ESM_1.xlsx")]
    dx, nab, ncx = [], 0, 0
    for a, b in px:
        xa, xb = xlsx_celulas(str(a)), xlsx_celulas(str(b))
        nab += len(xb)
        ncx += sum(1 for v in xb.values() for r in v for c in r if c is not None)
        if list(xa) != list(xb) or any(xa[k] != xb[k] for k in xa):
            dx.append(b.name)
    reg("L1.05", not dx, f"xlsx (tabelas principais, ESM_1 da suplementar, Submissao/ESM_1) v10 × v11: {nab} abas, {ncx:,} células preenchidas; "
                         f"planilhas com alguma célula diferente (inclui títulos e rodapés): {dx or 'nenhuma'}; Submissao/ESM_1.xlsx difere da v10 só em docProps/core.xml (data de criação)")
    da = docx_texto(str(A10 / "tabelas" / f"tabelas_principais_{V10}.docx"))
    db = docx_texto(str(MS / "tabelas" / f"tabelas_principais_{V11}.docx"))
    dif_doc = [l for l in __import__("difflib").unified_diff(da.splitlines(), db.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    reg("L1.06", da.replace(V10, V11) == db, f"docx das tabelas principais v10 × v11 (parágrafos, tabelas, cabeçalhos/rodapés de seção; {len(db):,} caracteres): idêntico depois de "
                                             f"trocar o rótulo de versão: {da.replace(V10, V11) == db}; única diferença bruta = título do documento {dif_doc}")
    pdfs = [(A10 / "suplementar" / f"S7_variables_codes_{V10}.pdf", MS / "suplementar" / f"S7_variables_codes_{V11}.pdf"),
            (A10 / "suplementar" / f"S8_strobe_record_checklist_{V10}.pdf", MS / "suplementar" / f"S8_strobe_record_checklist_{V11}.pdf")]
    pdfs += [(A10 / "Submissao" / f"ESM_{k}.pdf", SUB / f"ESM_{k}.pdf") for k in (2, 3, 4)]
    dp = [b.name for a, b in pdfs if pdf_texto(str(a)) != pdf_texto(str(b))]
    bytes_dif = [b.name for a, b in pdfs if ler(a, True) != ler(b, True)]
    reg("L1.07", not dp, f"5 PDFs (S7, S8, Submissao/ESM_2–4) v10 × v11: texto diferente em {dp or 'nenhum'}; bytes diferentes em {len(bytes_dif)} "
                         f"({bytes_dif}) — só metadados (data de criação do Chrome)")
    ims = [(A10 / "figuras" / f.name.replace(V11, V10), f) for f in sorted((MS / "figuras").glob(f"*_{V11}.*")) if not f.name.startswith("._")]
    ims += [(A10 / "suplementar" / f"S9_maihda_caterpillar_{V10}.{e}", MS / "suplementar" / f"S9_maihda_caterpillar_{V11}.{e}") for e in ("png", "tif")]
    ims += [(A10 / "Submissao" / f"Fig{k}.tif", SUB / f"Fig{k}.tif") for k in range(1, 5)]
    di = [b.name for a, b in ims if pixels(str(a)) != pixels(str(b))]
    reg("L1.08", not di and len(ims) == 14, f"{len(ims)} imagens (fig01–04 png/tif, S9 png/tif, Submissao/Fig1–4) v10 × v11: tamanho, modo, dpi ou pixels diferentes: {di or 'nenhuma'}")
    md10 = ler(A10 / f"numeros_chave_{V10}.md").splitlines()
    md11 = ler(MS / f"numeros_chave_{V11}.md").splitlines()
    t10 = [l for l in md10 if l.startswith("| ")]
    t11 = [l for l in md11 if l.startswith("| ")]
    col10, col11 = t10[0].count(" | ") + 1, t11[0].count(" | ") + 1
    linhas_iguais = all(b.rsplit(" | ", 2)[0] + " |" == a for a, b in zip(t10[1:], t11[1:])) and len(t10) == len(t11)
    dca10, dca11 = ler(A10 / f"data_code_availability_{V10}.md").splitlines(), ler(MS / "data_code_availability.md").splitlines()
    dif_dca = [i + 1 for i, (a, b) in enumerate(zip(dca10, dca11)) if a != b] + ([f"n linhas {len(dca10)}→{len(dca11)}"] if len(dca10) != len(dca11) else [])
    lg10, lg11 = ler(A10 / f"legendas_figuras_{V10}.md"), ler(MS / "legendas_figuras.md")
    reg("L1.09", col11 - col10 == 2 and linhas_iguais and campos11 - campos10 == {"commit_pacote", "commit_registro", "commit_analise"}
        and campos10 - campos11 == {"commit"} and lg10.replace(V10, V11).replace("v10", "v11") == lg11,
        f"JSON: 'commit' → 'commit_pacote' + commit_registro + commit_analise; md: {col10} → {col11} colunas, linhas iguais fora as 2 colunas novas: {linhas_iguais}. "
        f"Ressalva de redação: além do JSON/md dos números-chave, também mudaram o título do docx das tabelas (rótulo 'package v10' → 'v11', L1.06), data_code_availability.md (linhas {dif_dca}: rótulo de versão e commit de referência), "
        f"legendas_figuras.md (só rótulo de versão: {lg10.replace(V10, V11).replace('v10', 'v11') == lg11}) e MANIFEST.md, e os bytes de Submissao/ESM_1–4 (metadados); "
        f"nenhuma mudança de conteúdo numérico")

    # ---- item 1 e seção 1: auditoria independente (contra relatório e CSV do auditor)
    blocos = Counter(r["verificacao"][0] for r in cp)
    oks = Counter(r["verificacao"][0] for r in cp if r["ok"] == "True")
    tab = {r[0].split(".")[0]: (int(r[1]), int(r[2])) for b in md_tabelas(R) for r in b[1:] if len(r) == 3 and r[0][:2] in
           {f"{x}." for x in "ABCDEFGHIJ"} and r[1].isdigit()}
    tab_ok = tab == {k: (blocos[k], oks[k]) for k in blocos}
    reg("L1.10", "v8 × v10" in rel and "v10 × v11" in rel and len(re.findall(r"^# Rodada [234] ", rel, re.M)) == 3,
        f"relatório do auditor: rodada 1 (A–G, v8 × v10 e v10 × v11) + seções 'Rodada 2', 'Rodada 3', 'Rodada 4' = 4 rodadas; cabeçalho do relatório "
        f"ainda diz 'HEAD 8314417 (7c.6 ainda não commitada)', coerente com auditoria antes do commit")
    reg("L1.11", len(cp) == 178 and sum(oks.values()) == 178 and tab_ok,
        f"CSV do auditor (comparacao_7c6_v1_20261009.csv, fora do git): {len(cp)} linhas, {sum(oks.values())} ok=True; por bloco {dict(sorted(blocos.items()))}; "
        f"tabela da seção 1 do RESUMO = contagem do CSV: {tab_ok}")
    rx = {"A.15": "A.15", "C.07": "C.07", "F.04": "F.04", "F.05": "F.05", "G3.08": "G3.08", "G3.09": "G3.09"}
    seis = all(f"**{k}**" in rel or f"**{k} e" in rel or f" {k}" in rel for k in rx)
    reg("L1.12", seis and "Rodada 2" in rel and "42 verificações, 41 OK, 1 falha" in rel and "174 linhas, 173 OK" in rel and "178 linhas, 178 OK" in rel,
        "relatório: 6 sinalizações da 1ª execução corrigidas no critério do auditor (A.15 rótulo do docx; C.07 MESPRENAT 2014; F.04/F.05 heurísticas de hora e CNS; "
        "G3.08/G3.09 erro 406) = as 4 causas citadas no RESUMO; rodada 2 '42 verificações, 41 OK, 1 falha' (H4.06); rodada 3 '174 linhas, 173 OK' (I1.08); "
        "rodada 4 '178 linhas, 178 OK'")

    # ---- item 2: RECORD versionado; S8 só depende do docx
    rec = "docs/referencias/RECORD_checklist_acesso20261009.docx"
    atr_head = blob(HEAD, "docs/referencias/ATRIBUICAO.txt").decode()
    s02 = ler(PROJ / "scripts/etapa7b_02_suplementar.py").splitlines()
    i8 = next(i for i, l in enumerate(s02) if l.startswith("# ---------- S8"))
    f8 = next(i for i in range(i8 + 1, len(s02)) if s02[i].startswith("# ----------") or "html_pdf" in s02[i])
    entradas8 = sorted(set(re.findall(r'"(docs/[^"]+|outputs/[^"]+)"', "\n".join(s02[i8:f8 + 1]))) | set(re.findall(r"rd\(\"([^\"]+)\"\)", "\n".join(s02[i8:f8 + 1]))))
    antes_rd = sorted(set(re.findall(r'rd\("([a-z0-9_]+)"\)', "\n".join(s02[:i8]))))
    reg("L1.13", {rec, "docs/referencias/ATRIBUICAO.txt"} <= arv and entradas8 == [rec],
        f"{rec} e ATRIBUICAO.txt na árvore de {HEAD}; o bloco S8 do etapa7b_02 (L{i8 + 1}–L{f8 + 1}) lê só {entradas8}. "
        f"Ressalva: 'um clone limpo já monta a S8' vale para a entrada do RECORD; o etapa7b_02 inteiro não roda num clone limpo, porque antes da S8 lê "
        f"{len(antes_rd)} tabelas de outputs/tables/ (ignorado pelo git)")

    # ---- item 3 e seção 3: ._*
    fora = [x for d in ("outputs", "scripts", "audit_independente", "docs") for x in (PROJ / d).rglob("._*")]
    porp = Counter(str(x.parent.relative_to(PROJ)) for x in fora)
    tab3 = {r[0]: int(r[1]) for b in md_tabelas(R) for r in b[1:] if len(r) == 2 and r[1].isdigit() and "/" in r[0]}
    sub_ = list(SUB.rglob("._*"))
    reg("L1.14", tab3 == dict(porp) and len(fora) == 36 and not sub_ and "Fora dela: **36**" in R,
        f"._* agora: Submissao/ {len(sub_)}; outputs+scripts+audit_independente+docs {len(fora)} em {len(porp)} pastas; tabela da seção 3 = contagem atual: "
        f"{tab3 == dict(porp)}. 'nada foi movido': não verificável diretamente (sem registro de antes), mas a contagem atual coincide com a do auditor na rodada 1 (36 em 17 pastas)")

    # ---- item 4: campos
    reg("L1.15", all(i["commit_pacote"] == PAI for i in J) and all(i["commit_analise"] and i["commit_registro"] for i in J),
        f"commit_pacote = {PAI} (pai de {HEAD}) em {sum(i['commit_pacote'] == PAI for i in J)}/{len(J)}; commit_analise vazio: "
        f"{sum(not i['commit_analise'] for i in J)}; commit_registro vazio: {sum(not i['commit_registro'] for i in J)}")

    # ---- item 5 e seção 5: geradores
    ren = {x[2].split("/")[-1]: (x[0], x[1]) for x in ns if x[0].startswith("R") and x[-1].startswith("scripts/resumos/")}
    iguais = [g for g in GER if ren.get(g, ("",))[0] == "R100" and ler(PROJ / "scripts/resumos" / g, True) == blob(PAI, f"scripts/{g}")
              and blob(HEAD, f"scripts/resumos/{g}") == blob(PAI, f"scripts/{g}")]
    sobra = [g for g in GER if (PROJ / "scripts" / g).exists() or f"scripts/{g}" in arv]
    lista = re.search(r"Arquivos: (.*)\.\n", R).group(1)
    lista = re.findall(r"`([^`]+)`", lista)
    reg("L1.16", len(iguais) == 10 and not sobra and "scripts/resumos/LEIAME.md" in arv
        and lista == sorted(x.name for x in (PROJ / "scripts/resumos").glob("*.py")),
        f"geradores R100 com blob = {PAI}:scripts/<nome> (disco e {HEAD}): {len(iguais)}/10; ainda em scripts/: {sobra or 'nenhum'}; LEIAME.md versionado: "
        f"{'scripts/resumos/LEIAME.md' in arv}; lista da seção 5 ({len(lista)} nomes) = .py em scripts/resumos/: {lista == sorted(x.name for x in (PROJ / 'scripts/resumos').glob('*.py'))}")
    leia = ler(PROJ / "scripts/resumos/LEIAME.md")
    fixo = {g: bool(re.search(r'^V\s*=\s*"v\d+_', ler(PROJ / "scripts/resumos" / g), re.M)) for g in GER + ["etapa7c6_01_resumo.py"]}
    usa_bv = {g: ("B.V" in ler(PROJ / "scripts/resumos" / g)) for g in GER}
    reg("L1.17", fixo["etapa7c5b_01_resumo.py"] and fixo["etapa7c6_01_resumo.py"] and sum(fixo[g] for g in GER) == 1,
        f"LEIAME: 'todos, exceto o etapa7c5b_01 (fixo na v10), leem B.V'. Versão fixa (V = \"vN_...\") em: {[g for g, v in fixo.items() if v]}; "
        f"usam B.V: {sum(usa_bv.values())}/10. Observação: o etapa7c6_01 (também na pasta) fixa V = v11, o que o LEIAME não menciona (ele fala dos 10 movidos)")

    # ---- item 6: raise e CC BY 4.0
    s04 = ler(PROJ / "scripts/etapa7b_04_submissao.py")
    arv04 = ast.parse(s04)
    n_assert = sum(isinstance(n, ast.Assert) for n in ast.walk(arv04))
    raises = [n.lineno for n in ast.walk(arv04) if isinstance(n, ast.Raise)]
    s04h = blob(HEAD, "scripts/etapa7b_04_submissao.py").decode()
    reg("L1.18", n_assert == 0 and len(raises) == 2 and s04 == s04h and "._* em" in s04 and "aba interna no ESM_1" in s04,
        f"etapa7b_04_submissao.py (= blob de {HEAD}: {s04 == s04h}): assert = {n_assert}; raise RuntimeError em L{raises} (trava de ._* em limpa_macos; trava da aba S5b/INTERNAL)")
    reg("L1.19", "CC BY 4.0" in atr_head and atr_head == ler(PROJ / "docs/referencias/ATRIBUICAO.txt"),
        f"ATRIBUICAO.txt em {HEAD} contém 'CC BY 4.0' literal ({atr_head.count('CC BY 4.0')}×) e = disco; blob {git('rev-parse', HEAD + ':docs/referencias/ATRIBUICAO.txt').strip()[:7]}")
    lib = ler(PROJ / "scripts/etapa7b_lib.py")
    fn = [n for n in ast.parse(lib).body if isinstance(n, ast.FunctionDef) and n.name == "commits_analise"][0]
    src_fn = ast.get_source_segment(lib, fn)
    congela = 'herda = herda or x.get("commit_analise", "")' in src_fn and "if herda:" in src_fn
    reg("L1.20", congela and lib == blob(HEAD, "scripts/etapa7b_lib.py").decode(),
        f"etapa7b_lib.commits_analise (L{fn.lineno}–L{fn.end_lineno}, = {HEAD}): herda o commit_analise da versão arquivada mais nova com o mesmo valor "
        f"(laço da mais nova para a mais antiga, para no 1º valor diferente): {congela}; comportamento testado no M2 (teste sintético próprio)")

    # ---- seção 1, rodada 1: código do índice
    e23 = ler(PROJ / "scripts/etapa2_03_indice_acesso.py").splitlines()
    e23h = blob(HEAD, "scripts/etapa2_03_indice_acesso.py").decode().splitlines()
    L_ = lambda n: e23[n - 1]
    checks = {
        "L4–L5": "MESPRENAT 1–3," in L_(4) and "entre os registros com MESPRENAT válido (1–9; 99 = ignorado e nulo ficam fora)" in L_(5),
        "L39": '"mes_valido": mes.between(1, 9).fillna(False), "tri1": mes.between(1, 3).fillna(False),' in L_(39),
        "L40": '"mes_nulo": mes.isna(), "mes_99": (mes == 99).fillna(False),' in L_(40),
        "L51": 'A["indice"] = 100 * A.tri1 / A.mes_valido' == L_(51).strip(),
        "L36": "CODMUNRES" in L_(36),
        "L74": "ano + 1" in L_(74),
    }
    uso40 = [i + 1 for i, l in enumerate(e23) if "mes_nulo" in l or "mes_99" in l]
    reg("L1.21", all(checks.values()) and e23 == e23h,
        f"etapa2_03_indice_acesso.py (= {HEAD}): {checks}; mes_nulo/mes_99 usados só nas linhas {uso40} (completude), não no índice (L51)")
    s = pd.Series([1, 3, 4, 9, 99, None, 0, 10, 2], dtype="Int16")
    den, num_ = s.between(1, 9).fillna(False), s.between(1, 3).fillna(False)
    s2 = pd.to_numeric(pd.Series(["1", "3", "4", "9", "99", "", "0", "10", " 2 "]).astype("string").str.strip().replace({"": pd.NA}),
                       errors="raise").astype("Int16")
    den2, num2 = s2.between(1, 9).fillna(False), s2.between(1, 3).fillna(False)
    esperado_den = [True, True, True, True, False, False, False, False, True]
    esperado_num = [True, True, False, False, False, False, False, False, True]
    reg("L1.22", list(den) == esperado_den == list(den2) and list(num_) == esperado_num == list(num2),
        f"teste sintético próprio (Int16 e caminho string de num()): valores [1,3,4,9,99,nulo,0,10,2] → denominador {list(map(int, den))}, numerador "
        f"{list(map(int, num_))}: 99, nulo, 0 e 10 ficam fora dos dois")

    # ---- Asian
    t6 = pd.read_csv(PROJ / "outputs/tables/tab06_fluxograma_regiao_v1_20261008.csv").query("regiao == 'Brasil' and passo == '0_fonte'")
    t7 = pd.read_csv(PROJ / "outputs/tables/tab07_fluxograma_motivos_v1_20261008.csv", dtype={"motivo": str}).query(
        "regiao == 'Brasil' and passo == '1_raca' and motivo == '3'")
    num_a, den_a = int(t7.n.iloc[0]), int(t6.restante.iloc[0])
    pct = 100 * num_a / den_a
    pa = Jd["pct_amarela_fonte"]
    reg("L1.23", (num_a, den_a) == (117549, 27489150) and f"{pct:.4f}" == "0.4276" and f"{pct:.2f}" == "0.43"
        and abs(pa["valor_bruto"] - pct) < 1e-12 and pa["valor_formatado"] == "0.43%" and "117,549 / 27,489,150 = 0.4276%" in R,
        f"tab07 (Brasil, 1_raca, motivo 3) = {num_a:,}; tab06 (Brasil, 0_fonte, restante) = {den_a:,}; 100×razão = {pct:.6f}% → 0.43%; "
        f"pct_amarela_fonte bruto {pa['valor_bruto']!r} (|dif| {abs(pa['valor_bruto'] - pct):.1e}), formatado {pa['valor_formatado']}")
    rod_s1 = lambda f: [v for v in xlsx_celulas(str(f))["S1_flow_excluded"] if any(c is not None for c in v)][-1][0]
    frase = re.search(r"Births to mothers of Asian \(amarela\) race/skin color were excluded because.*?regional study\.", rod_s1(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx")).group(0)
    nucleo = frase.split(" were ", 1)[1].rstrip(".")
    em = {"ESM_1 suplementar": frase in rod_s1(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx"),
          "Submissao/ESM_1": frase in rod_s1(SUB / "ESM_1.xlsx"),
          "data_code_availability.md": nucleo in ws(ler(MS / "data_code_availability.md"))}
    reg("L1.24", all(em.values()), f"texto aprovado ('… were {nucleo[:60]}…') presente e idêntico em: {em}")

    # ---- os 41 .txt
    txts = sorted(p for p in arv if p.startswith("audit_independente/") and p.endswith(".txt"))
    disco = sorted(str(x.relative_to(PROJ)) for x in (PROJ / "audit_independente").rglob("*.txt") if not x.name.startswith("._"))
    mud = git("diff", "--name-only", PAI, HEAD, "--", *txts).split()
    add = Counter(git("log", "--diff-filter=A", "--format=%h", "--", t).split()[-1] for t in txts)
    wt = [t for t in txts if ler(PROJ / t, True) != blob(HEAD, t)]
    reg("L1.25", len(txts) == 41 and disco == txts and not mud and not wt and add == Counter({PAI: 41}),
        f".txt de audit_independente: {len(txts)} versionados (= {len(disco)} no disco); alterados entre {PAI} e {HEAD}: {len(mud)}; working tree ≠ {HEAD}: {len(wt)}; "
        f"commit que os adicionou: {dict(add)}")
    from audita_7c6_final_K_v1_20261010 import varre_texto
    hits = {t: varre_texto(ler(PROJ / t)) for t in txts}
    hits = {k: v for k, v in hits.items() if v}
    colid = Counter()
    for t in txts:
        for l in ler(PROJ / t).splitlines():
            cel = [c.strip() for c in re.split(r"[│|,\t]", l) if c.strip()]
            for c in cel:
                if re.fullmatch(r"(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|CNES|DTOBITO|DTNASCMAE|CODMUNNASC|CPF|CNS)", c):
                    colid[t] += 1
    nlin = {t: len(ler(PROJ / t).splitlines()) for t in txts}
    big = max(nlin.items(), key=lambda x: x[1])
    reg("L1.26", not hits and not colid and big == ("audit_independente/etapa7b3/relatorio_etapa7b3_v1_20261009.txt", 163),
        f"varredura própria dos 41 .txt: datas 1900–2024 (3 formatos), CPF, CNS de 15 dígitos: {hits or 'nenhum'}; nome de variável identificadora como célula "
        f"isolada de tabela (│, |, vírgula, tab): {dict(colid) or 'nenhum'}; máximo de linhas: {big[1]} ({big[0].split('/', 1)[1]}); maior arquivo "
        f"{max((PROJ / t).stat().st_size for t in txts):,} bytes")

    def colunas_linha(l):
        s_ = l.rstrip("\n")
        if "│" in s_:
            return len([c for c in s_.split("│")[1:-1]]) if s_.strip().startswith("│") else len(s_.split("│"))
        if s_.strip().startswith("|") and s_.strip().endswith("|") and len(s_.strip()) > 1:
            return len(s_.strip()[1:-1].split("|"))
        m = re.search(r"\[\((.*?)\)", s_)
        if m:
            return len(m.group(1).split(","))
        tok = s_.split()
        numlike = sum(bool(re.fullmatch(r"[-−+]?\d[\d,._]*(e[-+]?\d+)?%?|NA|TRUE|FALSE|NaN|<NA>|nan", t)) for t in tok)
        return len(tok) if len(tok) >= 3 and numlike >= len(tok) / 2 else 1
    colmax = {t: max((colunas_linha(l) for l in ler(PROJ / t).splitlines()), default=0) for t in txts}
    tokmax = {t: max((len(l.split()) for l in ler(PROJ / t).splitlines()), default=0) for t in txts}
    mc, mt = max(colmax.values()), max(tokmax.values())
    fc = sorted(t.split("/", 1)[1] for t, v in colmax.items() if v == mc)
    ft = sorted(t.split("/", 1)[1] for t, v in tokmax.items() if v == mt)
    reg("L1.27", mc == 13 and "etapa5/audit_e5_compara_log_v1_20261008_antes.txt" in fc and mt == 80 and ft == ["etapa4b/log_duckdb_v1_20261008.txt"],
        f"máximo de colunas pela definição do auditor (reimplementada: célula │ ou | de tabela, campo de tupla, tokens de linha tabular, prosa = 1): {mc} "
        f"em {fc} (empate: o RESUMO cita só o _antes); medida bruta (tokens por espaço em qualquer linha): {mt} em {ft}")
    gi = ler(PROJ / ".gitignore").splitlines()
    i26 = [n for n in ast.walk(arv04) if isinstance(n, ast.FunctionDef) and n.name == "limpa_macos"][0]
    chamadas = [n.lineno for n in ast.walk(arv04) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "limpa_macos"]
    reg("L1.28", not sub_ and "._*" in gi and ".DS_Store" in gi and "dot_clean" in ast.get_source_segment(s04, i26) and len(chamadas) == 2,
        f"Submissao/: {len(sub_)} ._*; .gitignore com '._*' e '.DS_Store'; limpa_macos (L{i26.lineno}–L{i26.end_lineno}) roda dot_clean -m e é chamada em L{chamadas}")

    # ---- observações da rodada 1
    comp = pd.read_csv(PROJ / "outputs/tables/tab_e2_03_mesprenat_completude_v1_20261008.csv").query("macro == 'Brasil'")
    comp = comp.assign(outros=comp.n - comp.n_valido - comp.n_nulo - comp.n_99)
    s7a = pd.read_csv(MS / "suplementar" / f"S7a_variables_codes_{V11}.csv")
    txt_s7a = s7a[s7a.Variable == "MESPRENAT"]["Codes used and recoding in this study"].iloc[0]
    reg("L1.29", int(comp.outros.sum()) == 2607 and comp[comp.outros > 0].ano.tolist() == [2014]
        and "99, missing, and any other value excluded from numerator and denominator" in txt_s7a
        and "99 = ignorado e nulo ficam fora" in L_(5) and "outros" not in L_(5) and "audit_independente/**/*.csv" in gi,
        f"tab_e2_03_mesprenat_completude (Brasil): n − válidos − nulos − 99 = {int(comp.outros.sum()):,}, só em {comp[comp.outros > 0].ano.tolist()}; S7a: "
        f"'99, missing, and any other value excluded…'; docstring L5 cita só 99 e nulo; regra 'audit_independente/**/*.csv' no .gitignore; commit_pacote = pai (L1.15)")

    # ---- rodada 2
    atr_a = blob("a38f550", "docs/referencias/ATRIBUICAO.txt").decode()
    h406 = [r for r in cp if r["verificacao"].startswith("H4.06")][0]
    reg("L1.30", "H4.06" in rel and "1c6d414" in rel and git("rev-parse", HEAD + ":docs/referencias/ATRIBUICAO.txt").strip().startswith("ee3e33b")
        and "CC BY 4.0" in atr_a and h406["ok"] == "True",
        f"rodada 2: H4.06 falhou (índice 1c6d414…, sem 'CC BY 4.0'); no commit o blob do ATRIBUICAO.txt é "
        f"{git('rev-parse', HEAD + ':docs/referencias/ATRIBUICAO.txt').strip()[:7]}… (= ee3e33b do working tree da rodada 2), com 'CC BY 4.0' já em {AMEND_ANT_():s}; "
        f"linha H4.06 do CSV refeita na rodada 3: ok={h406['ok']}")
    h1 = {r["verificacao"][:5]: r for r in cp if r["verificacao"].startswith("H1.")}
    reg("L1.31", h1["H1.03"]["ok"] == h1["H1.04"]["ok"] == "True" and "vazios: 0" in h1["H1.05"]["detalhe"],
        f"CSV do auditor: H1.03 (commit_registro 226 ids) ok={h1['H1.03']['ok']}; H1.04 (commit_analise) ok={h1['H1.04']['ok']}; H1.05: "
        f"'{h1['H1.05']['detalhe'][-110:]}' (conferido de forma independente em L4)")

    # H2.01 com os logs: tabelas de origem dos diretos × linha de log a ±3 s
    linhas_log = []
    for f in sorted((PROJ / "outputs/logs").glob("*.log")):
        if f.name.startswith("._"):
            continue
        for l in ler(f).splitlines():
            m = re.match(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[([^\]]+)\]", l)
            if m:
                linhas_log.append((datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp(), m.group(2), f.name))
    lt = np.array([x[0] for x in linhas_log])
    diretos = [i for i in J if lido_direto(i)]
    tabelas = sorted({i["arquivo"] for i in diretos})
    conf, etq = [], {}
    for t in tabelas:
        mt_ = (PROJ / t).stat().st_mtime
        k = np.where(np.abs(lt - mt_) <= 3)[0]
        etq[t.split("/")[-1].replace("_v1_20261008.csv", "")] = sorted({linhas_log[j][1] for j in k})
        if len(k):
            conf.append(t)
    ctx["etq_logs"] = etq
    scr_tab = {i["arquivo"].split("/")[-1].replace("_v1_20261008.csv", ""): i["script"].split()[0] for i in diretos}
    tok = lambda t: {x for x in re.split(r"[_.\-/ ]", t) if len(x) >= 4 and not x.startswith("etapa") and x not in ("scripts",)}
    casa = {t: any(tok(Path(scr_tab[t]).stem) & tok(e) for e in etq[t]) for t in etq}
    reg("L1.32", len(tabelas) == 35 and len(conf) == 35 and all(casa.values()),
        f"tabelas de origem dos {len(diretos)} ids lidos direto: {len(tabelas)}; com linha de log (carimbo e etiqueta) a ≤3 s do mtime: {len(conf)}; a etiqueta "
        f"do próprio script de origem (palavra comum entre etiqueta e nome do script) está entre elas em {sum(casa.values())}/{len(casa)} (em 2 há também a etiqueta de "
        f"outro script que rodou no mesmo segundo). "
        f"Etiquetas: " + "; ".join(f"{k}: {v}" for k, v in list(etq.items())[:6]) + " … (todas em l1_32_logs_7c6_final_v1_20261010.json)")
    (OUT / "l1_32_logs_7c6_final_v1_20261010.json").write_text(json.dumps(etq, ensure_ascii=False, indent=1))

    # ---- teste sintético do checa (bloco 9g) e docstring da lib
    chk = ler(PROJ / "scripts/etapa7b_checa.py")
    casos = re.search(r"CASOS = \{(.*?)\}\nres_cong", chk, re.S).group(1)
    n_casos = len(re.findall(r'^\s*"[^"]+": \(\{', casos, re.M))
    reg("L1.33", n_casos == 6 and "Um campo vazio não congela" in ast.get_docstring(fn),
        f"etapa7b_checa.py (código; resultados não lidos): CASOS do congelamento = {n_casos} (2 originais + 3 do auditor + campo vazio); docstring de "
        f"commits_analise diz 'Um campo vazio não congela': {'Um campo vazio não congela' in ast.get_docstring(fn)}")
    reg("L1.34", "Exceção às regras de independência" in rel and "566–612" in rel and "checa_7b_*.csv` continuam não lidos" in rel,
        "relatório da rodada 3: exceção registrada (leitura de etapa7b_checa.py L566–L612, depois dos testes próprios; checa_7b_*.csv não lidos) = descrição do RESUMO. "
        "Ressalva de redação: na abertura da seção 1, 'sem ler os resultados da autoauditoria (exceção na rodada 3)' sugere que a exceção foi ler resultados; foi ler o "
        "código do checa (o parágrafo da rodada 3 diz isso corretamente)")
    libA = blob("a38f550", "scripts/etapa7b_lib.py")
    reg("L1.35", "J1.01" in rel and "não guardei cópia" in rel and libA == blob(HEAD, "scripts/etapa7b_lib.py"),
        f"rodada 4 / J: afirmação 'desde a rodada 3 só a docstring mudou' não é verificável de forma independente (estado da rodada 3 não versionado; o próprio auditor "
        f"registra que não guardou cópia). Verificável: lib idêntica em {AMEND_ANT_()} e {HEAD} (o amend não tocou nela)")

    # ---- seção 2: RECORD
    bloco = R.split("`docs/referencias/ATRIBUICAO.txt`:\n```\n", 1)[1].split("\n```", 1)[0]
    reg("L1.36", bloco == atr_head.rstrip(), f"bloco citado na seção 2 = ATRIBUICAO.txt de {HEAD} (rstrip): {bloco == atr_head.rstrip()} ({len(bloco.splitlines())} linhas)")
    db_ = blob(HEAD, rec)
    md5 = hashlib.md5(db_).hexdigest()
    mt_rec = datetime.fromtimestamp((PROJ / rec).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    reg("L1.37", md5 == "d50bd10feb3c20398ccce6f3c27b7777" and len(db_) == 17088 and db_ == ler(PROJ / rec, True) and mt_rec == "2026-10-09 10:02",
        f"docx em {HEAD}: {len(db_):,} bytes, MD5 {md5} (= disco: {db_ == ler(PROJ / rec, True)}); mtime local {mt_rec} ('cópia local de 2026-10-09 10:02')")
    tdoc = docx_texto(db_)
    reg("L1.38", "*Checklist is protected under Creative Commons Attribution (CC BY) license." in tdoc and "4.0" not in tdoc,
        f"texto do docx contém '*Checklist is protected under Creative Commons Attribution (CC BY) license.': True; o docx não cita '4.0': {'4.0' not in tdoc}")
    esm3 = ws(pdf_texto(str(SUB / "ESM_3.pdf")))
    reg("L1.39", "Benchimol et al., PLoS Med 2015; CC BY" in esm3 and any("RECORD_checklist_acesso20261009.docx" in l for l in s02[i8:f8]),
        "etapa7b_02 lê o docx no bloco S8 e o ESM_3.pdf (S8) traz a atribuição 'Items reproduced from the RECORD checklist (Benchimol et al., PLoS Med 2015; CC BY)'")

    # ---- seção 4: distribuições e exemplos (contra o JSON e o git)
    tabs = md_tabelas(R)
    t_ca = [b for b in tabs if b[0][0] == "commit_analise" and b[0][1] == "Etapa"][0][1:]
    t_cr = [b for b in tabs if b[0][0] == "commit_registro" and b[0][1] == "Etapa"][0][1:]
    t_par = [b for b in tabs if b[0][0].startswith("Entrou no pacote")][0][1:]
    t_ex = [b for b in tabs if b[0][0] == "id" and b[0][1] == "commit_analise"][0][1:]
    dca_ = Counter(i["commit_analise"] for i in J)
    dcr_ = Counter(i["commit_registro"] for i in J)
    ok_ca = {r[0]: int(r[2]) for r in t_ca} == dict(dca_) and all(assunto(r[0]) == r[1] for r in t_ca)
    ok_cr = {r[0]: int(r[2]) for r in t_cr} == dict(dcr_) and all(assunto(r[0]) == r[1] for r in t_cr)
    par = Counter((i["commit_registro"], i["commit_analise"]) for i in J if i["commit_registro"] != i["commit_analise"])
    ok_par = {(r[0].split()[0], r[1].split()[0]): int(r[2]) for r in t_par} == dict(par)
    ok_ex = all(Jd[r[0].strip("`")]["commit_analise"] == r[1].split()[0] and Jd[r[0].strip("`")]["commit_registro"] == r[2].split()[0] for r in t_ex)
    reg("L1.40", ok_ca, f"tabela commit_analise da seção 4 = JSON: {dict(dca_)}; rótulos de etapa = assunto do commit: {ok_ca}")
    reg("L1.41", ok_cr, f"tabela commit_registro = JSON: {dict(dcr_)}")
    reg("L1.42", ok_par, f"tabela 'onde os dois diferem' ({len(t_par)} linhas, {sum(par.values())} ids) = JSON: {ok_par}")
    reg("L1.43", ok_ex and len(t_ex) == 6, f"tabela de exemplos ({len(t_ex)} ids) = JSON: {ok_ex}")
    nder = sum(1 for i in J if not lido_direto(i))
    ctx["nder"] = nder
    reg("L1.44", nder == 11 and len(J) - nder == 215 and "226 números-chave; 11 derivados no pacote, 215 lidos direto da tabela; vazios: 0" in R,
        f"classificação própria (valor em coluna numérica da tabela de origem, tolerância 1e-9 rel.): derivados {nder}, lidos direto {len(J) - nder}, "
        f"vazios {sum(not i['commit_analise'] for i in J)}; derivados: {sorted(i['id'] for i in J if not lido_direto(i))}")
    # 21 da 7c.3 (detalhe em L2a)
    reg("L1.45", True, "afirmações sobre os 21 da 7c.3 ('só os 4 n_excl_estciv_* calculados lá'; 9 da Etapa 6; 8 da 6b): ver L2a.01–L2a.06")
    reg("L1.46", all(i["commit_pacote"] == PAI for i in J) and git("rev-parse", "--short", f"{HEAD}^").strip() == PAI,
        f"commit_pacote = {PAI} = pai de {HEAD} ('o commit anterior ao desta etapa')")

    # ---- seção 6 (fatos verificáveis sem ler o checa_7b): ver L2b para o 100/100
    tab6 = [b for b in tabs if b[0][0] == "Checagem"][0][1:]
    v_ = {r[0][:40]: r[1] for r in tab6}
    f20 = f"{ctx['npares']} pares; {ctx['ncel']:,} células; dif números []; dif texto []"
    reg("L1.47", any(f20 == r[1] for r in tab6) and any(r[1] == "10/10" for r in tab6) and any(r[1] == "178 verificações; falhas []" for r in tab6)
        and any(r[1].startswith(f"v10 {len(J10)}; v11 {len(J)}; idênticos {len(J)}") for r in tab6),
        f"fatos da tabela 'Checagens da 7c.6' recalculados aqui: '{f20}' (pares e células sem cabeçalho); '10/10' geradores; '178 verificações; falhas []'; "
        f"'v10 226; v11 226; idênticos 226'; distribuições = L1.40–L1.41 ({len(tab6)} linhas na tabela)")

    # ---- pendências
    pdfq = {f.name: subprocess_xattr(f) for f in sorted((MS / "suplementar").glob(f"*_{V11}.pdf")) if not f.name.startswith("._")}
    reg("L1.48", all("Chrome" in v for v in pdfq.values()),
        f"'o Chrome headless marca os arquivos com quarentena': com.apple.quarantine dos PDFs da v11 = {pdfq} (agente 'Chrome'); detalhes em M1")
    chk_cond = "if aud76.exists():" in chk
    gen_incond = 'cp = pd.read_csv(B.PROJ / "audit_independente/etapa7c6/comparacao_7c6_v1_20261009.csv")' in ler(PROJ / "scripts/resumos/etapa7c6_01_resumo.py")
    reg("L1.49", False,
        f"'A autoauditoria e o gerador deste RESUMO leem o .csv do auditor, então não rodam num clone limpo': correto para o gerador (leitura incondicional: {gen_incond}); "
        f"impreciso para a autoauditoria: o etapa7b_checa.py só lê o CSV do auditor se ele existir ('if aud76.exists():' = {chk_cond}; idem para os de 7b1–7b3 e 7c1–7c4) e "
        f"pularia a checagem; o checa não roda num clone limpo por outros motivos (lê outputs/tables/, ignorado). Falha de redação, menor")
    reg("L1.50", True, "não verificável: 'os Métodos v5.1 dizem \"among births with a known month of first visit (1–9)\"' — nenhum arquivo do projeto contém 'first visit' "
                       "ou 'Métodos v5.1' fora do próprio RESUMO e do texto-fonte (documento fora do repositório). A outra metade ('os rodapés dizem…') é conferida em M7")
    rsp = [str(p.relative_to(PROJ)) for p in (PROJ / "outputs").glob("*.md") if "e44" in ler(p) and "7C6" not in p.name]
    reg("L1.51", True, f"não verificável: 'RSP 2026;60:e44' (citação do estudo regional) só aparece como a mesma recomendação em RESUMOs anteriores ({rsp}); "
                       f"a frase que termina em 'our regional study' existe no pacote (S1 e data_code_availability, L1.24). Recomendação de redação, sem fonte primária no projeto")
    reg("L1.52", "Ela diverge do seu exemplo em 17 dos 21 números da 7c.3" in R, "'diverge do seu exemplo em 17 dos 21': coerente com L2a (4 com 3092186, 17 com 2285207/6905d9d)")

    hs = set(git("log", "--all", "--reflog", "--format=%h").split())
    com_hash = Counter()
    for f in sorted((PROJ / "outputs/logs").glob("*.log")):
        if f.name.startswith("._"):
            continue
        for l in ler(f).splitlines():
            m = re.match(r"^\[[^\]]+\] \[([^\]]+)\]", l)
            if any(h in hs for h in re.findall(r"\b[0-9a-f]{7}\b", l)):
                com_hash[(f.name, m.group(1) if m else "?")] += 1
    reg("L1.54", set(k[1] for k in com_hash) <= {"7b_checa"},
        f"'o log das análises não grava o commit': linhas de outputs/logs/*.log com algum hash de commit do repositório, por (log, etiqueta): {dict(com_hash)} — só a "
        f"autoauditoria do pacote (7b_checa) cita commits; nenhum log de script de análise. Confere (só etiquetas foram contadas)")

    # ============ L2a: os 21 da 7c.3
    J6, c6, _ = json_versao(6)
    J7, c7, _ = json_versao(7)
    novos = [i["id"] for i in J7 if i["id"] not in {x["id"] for x in J6}]
    reg("L2a.01", len(novos) == 21 and c7 == "3092186" and set(novos) <= set(Jd),
        f"ids da v7 (JSON adicionado em {c7}) que não estão na v6 (adicionado em {c6}), lidos do git: {len(novos)}")
    der = [k for k in novos if not lido_direto(Jd[k])]
    src = Counter(Jd[k]["arquivo"].split("/")[-1].replace("_v1_20261008.csv", "") for k in novos if k not in der)
    t6b = pd.read_csv(PROJ / "outputs/tables/tab_e6b_01_modelos_m1m3_v1_20261008.csv")
    difs = {k: (Jd[k]["valor_bruto"], int(t6b[(t6b.desfecho == k.replace("n_excl_estciv_", "")) & (t6b.modelo == "M2")].N.iloc[0]
                                          - t6b[(t6b.desfecho == k.replace("n_excl_estciv_", "")) & (t6b.modelo == "M3")].N.iloc[0])) for k in der}
    e7b01_3092186 = blob("3092186", "scripts/etapa7b_01_tabelas.py").decode()
    e7b01_6f9 = blob("2cde6a0", "scripts/etapa7b_01_tabelas.py").decode()
    reg("L2a.02", sorted(der) == sorted(f"n_excl_estciv_{d}" for d in ("ptb", "pig", "ptb_ind", "ptb_esp")) and all(a == b for a, b in difs.values())
        and "n_excl_estciv" in e7b01_3092186 and "n_excl_estciv" not in e7b01_6f9
        and all(Jd[k]["commit_analise"] == "3092186" for k in der),
        f"derivados entre os 21 (valor fora das colunas numéricas da tabela): {sorted(der)}; valor = N(M2) − N(M3) de tab_e6b_01_modelos_m1m3: "
        f"{ {k: v[0] for k, v in difs.items()} }; o cálculo 'n_excl_estciv' entra no etapa7b_01_tabelas.py em 3092186 (ausente em 2cde6a0)")
    grupos = {"tab_e3_02_interacao_rs": 3, "tab_e3_02_wald_rs": 3, "tab_e3_03a_indice_continuo_rs": 3, "tab_e6b_01_modelos_m1m3": 8}
    reg("L2a.03", dict(src) == grupos, f"17 lidos direto, por tabela de origem: {dict(src)}. Nota: 3 dos 9 da Etapa 6 vêm de tab_e3_03a_indice_continuo_rs, "
                                       f"que não se encaixa no padrão 'tab_e3_02_*_rs' citado no RESUMO (ver L1.53)")
    info = {}
    hist = sorted((int(t), h) for h, t in (x.split() for x in git("log", "--format=%h %ct", HEAD).splitlines()))
    for t, scr in [("tab_e3_02_interacao_rs", "scripts/etapa3_02_knol.py"), ("tab_e3_02_wald_rs", "scripts/etapa3_02_knol.py"),
                   ("tab_e3_03a_indice_continuo_rs", "scripts/etapa3_02_knol.py"), ("tab_e6b_01_modelos_m1m3", "scripts/etapa6b_01_modelos_rs.py")]:
        mt_ = (PROJ / f"outputs/tables/{t}_v1_20261008.csv").stat().st_mtime
        a = next(h for tt, h in hist if tt >= mt_)
        b = git("log", "-1", "--format=%h", "3092186", "--", scr).strip()
        info[t] = (datetime.fromtimestamp(mt_).strftime("%m-%d %H:%M:%S"), a, b, git("log", "--format=%h", "--", scr).split())
    tem_rs_2285 = "--rs" in blob("2285207", "scripts/etapa3_02_knol.py").decode()
    tem_rs_d2e = "--rs" in blob("d2e0f66", "scripts/etapa3_02_knol.py").decode()
    win = [f.name for f in (PROJ / "outputs/tables").glob("*.csv") if not f.name.startswith("._")
           and int(git("log", "-1", "--format=%ct", "2cde6a0").strip()) < f.stat().st_mtime <= int(git("log", "-1", "--format=%ct", "3092186").strip())]
    reg("L2a.04", all(v[1] == v[2] == "2285207" for k, v in info.items() if k.startswith("tab_e3")) and tem_rs_2285 and not tem_rs_d2e
        and not [w for w in win if w.startswith(("tab_e3_02", "tab_e3_03a", "tab_e6b_01"))],
        f"9 da Etapa 6: mtime das 3 tabelas {[v[0] for k, v in info.items() if k.startswith('tab_e3')]}; 1º commit depois = "
        f"{[v[1] for k, v in info.items() if k.startswith('tab_e3')]}; último commit do etapa3_02_knol.py até 3092186 = {info['tab_e3_02_wald_rs'][2]} "
        f"(histórico do script: {info['tab_e3_02_wald_rs'][3]}); opção --rs existe em 2285207: {tem_rs_2285}, em d2e0f66: {tem_rs_d2e}; logs [3.2-3.6_knol_rs] "
        f"em etapa6_*.log ({ctx['etq_logs'].get('tab_e3_02_wald_rs')}); tabelas de outputs/tables com mtime na janela da 7c.3 (2cde6a0 → 3092186): {win or 'nenhuma'}")
    v = info["tab_e6b_01_modelos_m1m3"]
    reg("L2a.05", v[1] == v[2] == "6905d9d" and v[3] == ["6905d9d"],
        f"8 da Etapa 6b: tab_e6b_01_modelos_m1m3 mtime {v[0]}; 1º commit depois = {v[1]}; histórico do etapa6b_01_modelos_rs.py = {v[3]}; log "
        f"{ctx['etq_logs'].get('tab_e6b_01_modelos_m1m3')}")
    reg("L2a.06", len(novos) == 21 and len(der) == 4 and sum(grupos.values()) == 17,
        "afirmação (a) do relato final CONFERE: dos 21 números novos da 7c.3 (3092186), só os 4 n_excl_estciv_* foram calculados lá (aritmética do pacote); "
        "17 vêm de tabelas geradas antes: 9 da Etapa 6 (2285207; etapa3_02_knol.py --rs, executado em 08/10 22:25–23:20) e 8 da Etapa 6b (6905d9d)")
    reg("L1.53", "tab_e3_03a_indice_continuo_rs" not in src, "seção 4 do RESUMO: '9 na Etapa 6 (2285207): tercis nacionais e índice contínuo, `tab_e3_02_*_rs`' — o índice contínuo (3 ids RP_int_5pp_indice_continuo_*) "
                        "vem de tab_e3_03a_indice_continuo_rs, fora do padrão citado. Imprecisão menor de nome de arquivo; contagem e commit corretos")

    # ============ L2b: 4 rodadas e 178/178; autoauditoria 100/100 (sem ler o checa CSV)
    reg("L2b.01", len(cp) == 178 and sum(oks.values()) == 178 and "Rodada 4" in rel,
        "dupla auditoria: 4 rodadas (relatório: rodada 1 + seções Rodada 2–4) e 178/178 OK no CSV do auditor (L1.10–L1.12)")
    n_ok = len(re.findall(r"^\s*ok\(", chk, re.M))
    ctx["n_ok_estatico"] = n_ok
    reg("L2b.02", True, f"autoauditoria 100/100 — conferência indireta (sem ler o checa_7b_*.csv): o RESUMO commitado diz '**100/100 OK**'; o checa tem "
                        f"{n_ok} chamadas ok( no código (algumas em laço, outras condicionais à existência de CSVs de auditores); contagem de execuções em L2b.03; "
                        f"leitura direta só no fim (L2b.04, exceção registrada)")

    exe, det_exe = execucoes_ok(chk)
    ctx["n_ok_exec"] = exe
    reg("L2b.03", exe == 100, f"execuções esperadas de ok() no checa, contadas no código (AST) com o estado atual do disco: {exe} ({det_exe}); "
                              f"= 100 do RESUMO: {exe == 100}")

    exc = OUT / "excecao_L2b_7c6_final_v1_20261010.json"
    if exc.exists():
        e = json.loads(ler(exc))
        reg("L2b.04", e["linhas"] == 100 and e["ok_true"] == 100 and e["disco_igual_commit"] and e["resumo_diz_100"] and ctx.get("n_ok_exec") == 100,
            f"EXCEÇÃO registrada (feita por último, {e['quando']}, só para o L2b): checa_7b_v11_20261009.csv (blob de {HEAD} = disco: {e['disco_igual_commit']}) tem "
            f"{e['linhas']} linhas, colunas {e['colunas']}, ok=True em {e['ok_true']}; = 100 execuções previstas pelo código (L2b.03). Afirmação (b) do relato final "
            f"CONFERE: 4 rodadas e 178/178 do auditor; autoauditoria 100/100")
        reg("L2b.05", e["tabela_7c6_igual_csv"] and e["tabela_7c6_resumo_n"] == e["linhas_7c6_csv"] == 11,
            f"a tabela 'Checagens da 7c.6' da seção 6 do RESUMO ({e['tabela_7c6_resumo_n']} linhas) = linhas do checa que contêm '7c.6' ({e['linhas_7c6_csv']}), "
            f"verificação e valor: {e['tabela_7c6_igual_csv']}")
        reg("K3.05", not any(e["padroes_individuais"].values()) and e["colunas"] == ["verificacao", "ok", "valor"],
            f"checa_7b_v11 (arquivo novo do commit, lido só na exceção do L2b): {e['linhas']}×{len(e['colunas'])} ({e['colunas']}), maior campo 'valor' "
            f"{e['maior_campo_valor']} caracteres; padrões de data 1900–2024/CNS/CPF: {e['padroes_individuais']}: sem dado individual. O checa_7b_v10 é R100 "
            f"(conteúdo idêntico ao versionado em 8314417) e não foi aberto")
    else:
        reg("L2b.04", False, "exceção do L2b ainda não executada (rodar audita_7c6_final_excecao_L2b_v1_20261010.py por último)")

    # ============ L2c: RECORD na web (GET públicos; resultado em web_7c6_final_v1_20261010.json)
    w = json.loads(ler(OUT / "web_7c6_final_v1_20261010.json"))
    ap, ae, apl = w["record_artigo_pmc"], w["record_artigo_epmc"], w["record_artigo_plos"]
    sup_ = ap["material_suplementar"]
    reg("L2c.01", ap["n_material_suplementar"] == 1 and sup_[0]["rotulo"] == "S1 Table" and sup_[0]["arquivos"] == ["pmed.1001885.s001.xlsx"]
        and apl["supp_links"] == ["journal.pmed.1001885.s001"],
        f"artigo {ae.get('titulo')} PLoS Med {ae.get('ano')};{ae.get('volume')}({ae.get('numero')}):{ae.get('pagina')} ({ae.get('pmcid')}; PMID {ae.get('pmid')}). "
        f"Material suplementar (XML do PMC, efetch, {w['quando']}): {ap['n_material_suplementar']} item — {sup_[0]['rotulo']}: '{sup_[0]['legenda'][:70]}' "
        f"({sup_[0]['arquivos']}); página da PLOS: itens SI {apl['si_titulos']} / {apl['supp_links']}. O checklist NÃO está no material suplementar: confere")
    t1 = [t for t in ap["tabelas"] if t["rotulo"] == "Table 1"]
    reg("L2c.02", bool(t1) and t1[0]["legenda"].startswith("The RECORD statement: Checklist of items, extended from the STROBE statement"),
        f"o checklist é a Table 1 do artigo: '{t1[0]['legenda'] if t1 else '-'}'")
    rp, rd = w["record_pagina"], w["record_docx"]
    reg("L2c.03", rp["frase_cc_by"] and "http://creativecommons.org/licenses/by/4.0/" in rp["links_cc"] and rd["md5"] == "d50bd10feb3c20398ccce6f3c27b7777"
        and rd["bytes"] == 17088,
        f"site do RECORD ({rp['url']}, HTTP {rp['status']}): '{rp['trecho']}' com link {rp['links_cc']}; docx do site ({rd['url']}, HTTP {rd['status']}), só em memória: "
        f"{rd['bytes']:,} bytes, MD5 {rd['md5']} = o versionado. 'O docx vem do site do RECORD e é CC BY 4.0': confere (CC BY no docx e no site; 4.0 pelo link do site)")
    lic_pl = w["record_artigo_plos_licenca"]
    reg("L2c.04", ae.get("license") == "cc by" and "creativecommons.org/licenses/by/4.0" in " ".join(ap["licenca_href"]),
        f"artigo: licença CC BY (Europe PMC '{ae.get('license')}'); XML do PMC <license xlink:href={ap['licenca_xlink']}>; página da PLOS: '{lic_pl['texto'][:120]}…' "
        f"com o texto 'Creative Commons Attribution License' ligado a {lic_pl['href']}")
    reg("L2c.05", False,
        "afirmação do RESUMO (seção 2) e do ATRIBUICAO.txt: 'a versão 4.0 vem só do link do site; o docx e o artigo dizem apenas \"CC BY\"'. O docx de fato só diz "
        f"'CC BY' (L1.38), mas o artigo também aponta a versão: na página da PLOS a declaração de licença liga 'Creative Commons Attribution License' a {lic_pl['href']} e "
        f"o XML do artigo no PMC tem <license xlink:href={ap['licenca_xlink']}>. Imprecisão menor, que não muda a conclusão (CC BY 4.0)")

    # ============ L3: reprodutibilidade do RESUMO
    rep = OUT / "RESUMO_ETAPA7C6_reproduzido_v1_20261010.md"
    copia = OUT / "etapa7c6_01_resumo_copia_saida_auditor.py"
    dif_copia = [l for l in __import__("difflib").unified_diff(ler(PROJ / "scripts/resumos/etapa7c6_01_resumo.py").splitlines(), ler(copia).splitlines(), lineterm="", n=0)
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    reg("L3.01", len(dif_copia) == 2 and "write_text(out)" in dif_copia[0] and "etapa7c6_final" in dif_copia[1],
        f"cópia do gerador difere do original em 1 linha (só o caminho de saída): {[d[:90] for d in dif_copia]}")
    iguais_rep = rep.exists() and ler(rep, True) == blob(HEAD, "outputs/RESUMO_ETAPA7C6_v1_20261009.md")
    reg("L3.02", iguais_rep, f"rodado da raiz com PYTHONPATH=scripts (e PYTHONDONTWRITEBYTECODE=1) em 2026-10-10 10:16:43: saída idêntica byte a byte ao RESUMO de {HEAD}: "
                             f"{iguais_rep} (MD5 {hashlib.md5(ler(rep, True)).hexdigest() if rep.exists() else '-'}). O Logger acrescentou 1 linha em "
                             f"outputs/logs/etapa7c6_20261008.log (ignorado pelo git). Uma linha anterior, de 10:16:32, não é desta auditoria. O gerador lê internamente o "
                             f"checa_7b_v11 (a seção 6 do RESUMO vem dele); o auditor não abriu esse CSV nesta etapa")

    # ============ L4: commit_registro e commit_analise com código próprio
    vers = {}
    for n in range(1, 11):
        Jn, cn, nadd = json_versao(n)
        arq = json.loads(ler(MS / f"_arquivo_v{n}" / f"numeros_chave_v{n}_20261009.json"))
        vers[n] = ({i["id"]: i for i in Jn}, cn, Jn == arq, nadd)
    reg("L4.01", all(v[2] for v in vers.values()), f"JSON v1–v10 lidos do git no commit de adição = cópias em _arquivo_vN: {all(v[2] for v in vers.values())}; "
                                                 f"commits de adição: { {n: v[1] for n, v in vers.items()} }")
    cr_meu, cr_exato = {}, {}
    for it in J:
        for ex, dest in ((False, cr_meu), (True, cr_exato)):
            c = ""
            for n in range(10, 0, -1):
                x = vers[n][0].get(it["id"])
                if x is None or x["valor_formatado"] != it["valor_formatado"] or not mesmo_valor(x["valor_bruto"], it["valor_bruto"], ex):
                    break
                c = vers[n][1]
            dest[it["id"]] = c
    div_cr = [k for k in Jd if cr_meu[k] != Jd[k]["commit_registro"]]
    reg("L4.02", not div_cr and cr_meu == cr_exato,
        f"commit_registro recalculado para os {len(J)} ids (v10→v1 enquanto formatado igual e bruto igual até 1e-12 rel.; commit de adição do JSON da versão mais antiga): "
        f"divergentes {div_cr or 'nenhum'}; com igualdade exata o resultado é o mesmo: {cr_meu == cr_exato}; distribuição {dict(Counter(cr_meu.values()))}")
    ca_meu = {}
    for it in J:
        cr = cr_meu[it["id"]]
        if not lido_direto(it):
            ca_meu[it["id"]] = cr
            continue
        mt_ = (PROJ / it["arquivo"]).stat().st_mtime
        a = next((h for tt, h in hist if tt >= mt_), "")
        b = git("log", "-1", "--format=%h", cr, "--", it["script"].split()[0]).strip()
        ca_meu[it["id"]] = a if a and a == b else ""
    div_ca = [k for k in Jd if ca_meu[k] != Jd[k]["commit_analise"]]
    anc = [k for k in Jd if Jd[k]["commit_analise"] and subprocess_ancestor(Jd[k]["commit_analise"], Jd[k]["commit_registro"]) is False]
    import random
    rnd = random.Random(20261010)
    amostra = sorted(set(novos) | set(rnd.sample(sorted(set(Jd) - set(novos)), 20)))
    reg("L4.03", not div_ca and not anc,
        f"commit_analise recalculado para TODOS os {len(J)} ids (derivado → commit_registro; lido direto → (a) 1º commit com data ≥ mtime da tabela = (b) último commit "
        f"do script até o commit_registro; nenhuma versão arquivada tem commit_analise, logo nada é herdado): divergentes {div_ca or 'nenhum'}; commit_analise não "
        f"ancestral do commit_registro: {anc or 'nenhum'}; amostra pedida ({len(amostra)} ids = os 21 da 7c.3 + 20 sorteados, semente 20261010) contida no total")
    (OUT / "l4_commits_por_id_7c6_final_v1_20261010.csv").write_text(
        "id,lido_direto,commit_registro_json,commit_registro_auditor,commit_analise_json,commit_analise_auditor,na_amostra\n"
        + "".join(f"{k},{lido_direto(Jd[k])},{Jd[k]['commit_registro']},{cr_meu[k]},{Jd[k]['commit_analise']},{ca_meu[k]},{k in amostra}\n" for k in Jd))
    mdl = [l for l in ler(MS / f"numeros_chave_{V11}.md").splitlines() if l.startswith("| ") and not l.startswith("| id ")]
    md_ok = len(mdl) == len(J) and all(l.rstrip(" |").rsplit(" | ", 2)[-2:] == [i["commit_analise"], i["commit_registro"]] for l, i in zip(mdl, J))
    reg("L4.04", md_ok, f"numeros_chave_v11.md: colunas commit_analise e commit_registro = JSON, na mesma ordem ({len(mdl)} linhas): {md_ok}")

    # ============ L5: reexecução do checa sobre o estado commitado
    head_short = git("rev-parse", "--short", "HEAD").strip()
    linha_cp = [i + 1 for i, l in enumerate(chk.splitlines()) if 'i["commit_pacote"] == B.COMMIT' in l]
    linha_rev = [i + 1 for i, l in enumerate(chk.splitlines()) if '"rev-list"' in l and "HEAD" in l]
    falha = head_short != PAI and all(i["commit_pacote"] == PAI for i in J)
    reg("L5.01", True, f"dependência do HEAD: etapa7b_lib.COMMIT = git rev-parse --short HEAD (lib L24) e o checa exige commit_pacote == B.COMMIT em todos os ids "
                       f"(checa L{linha_cp}); hoje HEAD = {head_short} e o JSON tem commit_pacote = {PAI} → essa checagem daria False: {falha}. Como ok() faz assert, "
                       f"o checa pararia ali (bloco 9g, 1ª checagem da 7c.6), sem rodar o resto nem gravar o CSV")
    reg("L5.02", True, f"outras referências ao HEAD no checa: rev-list --since=<mtime> HEAD (L{linha_rev}) — com HEAD = {head_short} o 1º commit depois do mtime não muda "
                       f"(b9d6272 é posterior a todas as tabelas), logo não falha. Demais limites de reprodução (não ligados ao HEAD): lê outputs/tables/ e CSVs de auditores "
                       f"(ignorados pelo git) e regrava outputs/manuscrito/checa_7b_v11 se chegar ao fim")
    aviso_checa = bool(re.search(r"(checa|autoauditoria)[^\n]{0,200}(HEAD|reexecu|depois do commit)", R + leia, re.I))
    reg("L5.03", not aviso_checa,
        f"o RESUMO e o LEIAME avisam que a reexecução do checa falha depois do commit? {'sim' if aviso_checa else 'não'}: o RESUMO só define commit_pacote como "
        f"'o HEAD quando o pacote foi gerado, ou seja, o commit anterior ao desta etapa'; o LEIAME trata só dos geradores de RESUMO (B.V). Limitação de "
        f"reprodutibilidade registrada, não reprova a etapa")


def AMEND_ANT_():
    return "a38f550"


def subprocess_xattr(f):
    import subprocess
    r = subprocess.run(["xattr", "-p", "com.apple.quarantine", str(f)], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def subprocess_ancestor(a, b):
    import subprocess
    r = subprocess.run(["git", "-C", str(PROJ), "merge-base", "--is-ancestor", a, b])
    return r.returncode == 0


def execucoes_ok(src):
    """Conta quantas vezes ok() rodaria: laços com iteração conhecida e ifs condicionais à existência de CSVs de auditores (só existência)."""
    arv = ast.parse(src)
    pais = {}
    for n in ast.walk(arv):
        for c in ast.iter_child_nodes(n):
            pais[c] = n
    chamadas = [n for n in ast.walk(arv) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "ok" and isinstance(pais.get(n), ast.Expr)]
    tifs = len([f for f in (MS / "figuras").glob(f"*_{V11}.tif")]) + len([f for f in (MS / "suplementar").glob(f"*_{V11}.tif")])
    total, laços, ifs = 0, Counter(), Counter()
    for c in chamadas:
        mult, n = 1, c
        while n in pais:
            n = pais[n]
            if isinstance(n, ast.For):
                it = ast.unparse(n.iter)
                k = 3 if it.startswith("['Maternal age group'") else tifs if "FIGD.glob" in it else 4 if it == "range(1, 5)" else None
                assert k is not None, it
                mult *= k
                laços[f"{ast.unparse(n.target)}×{k}"] += 1
            if isinstance(n, ast.If):
                t = ast.unparse(n.test)
                m = re.fullmatch(r"(\w+)\.exists\(\)", t)
                assert m, t
                var = m.group(1)
                atrib = [a for a in ast.walk(arv) if isinstance(a, ast.Assign) and any(getattr(x, "id", "") == var for x in a.targets)][-1]
                partes = re.findall(r'"([^"]+)"', ast.unparse(atrib.value).replace("'", '"'))
                existe = (PROJ.joinpath(*partes)).exists()
                ifs[f"{'/'.join(partes[-2:])}: {existe}"] += 1
                mult *= int(existe)
        total += mult
    return total, f"{len(chamadas)} chamadas no código; laços {dict(laços)}; condicionais (CSV do auditor existe?) {dict(ifs)}"
