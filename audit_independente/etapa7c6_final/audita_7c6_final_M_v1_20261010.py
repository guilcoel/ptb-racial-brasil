"""Bloco M — fatos por trás das decisões pendentes (só levantamento; ok=True quando o fato foi levantado com evidência)."""
import ast
import csv
import io
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from audita_7c6_final_lib_v1_20261010 import (HEAD, ID_COLS, MS, OUT, PROJ, SUB, V11, git, ler, pacote_v11, proibido, texto_arquivo, ws,
                                              xlsx_celulas)


def xattr_nomes(f):
    r = subprocess.run(["xattr", str(f)], capture_output=True, text=True)
    return r.stdout.split()


def xattr_q(f):
    r = subprocess.run(["xattr", "-p", "com.apple.quarantine", str(f)], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def scripts_legiveis():
    fs = [f for f in sorted((PROJ / "scripts").rglob("*")) if f.suffix in (".py", ".R") and not f.name.startswith("._") and "__pycache__" not in str(f)]
    return [f for f in fs if not proibido(f)]


def run(reg, ctx):
    # ======================= M1: ._*
    todos = [x for x in PROJ.rglob("._*") if ".git/" not in str(x) and "/.git" not in str(x.parent)]
    por = Counter(str(x.parent.relative_to(PROJ)) for x in todos)
    arv = set(git("ls-tree", "-r", "--name-only", HEAD).splitlines())
    vers = [str(x.relative_to(PROJ)) for x in todos if str(x.relative_to(PROJ)) in arv]
    ign = git("check-ignore", "--no-index", *[str(x.relative_to(PROJ)) for x in todos], check=False).split("\n")
    n_ign = len([l for l in ign if l.strip()])
    base_ok = all((x.parent / x.name[2:]).exists() for x in todos)
    reg("M1.01", True,
        f"._* no projeto (fora de .git): {len(todos)} — outputs/: {sum(v for k, v in por.items() if k.startswith('outputs'))} em "
        f"{sum(1 for k in por if k.startswith('outputs'))} pastas (= tabela do RESUMO) e data/processed: {por.get('data/processed', 0)} (fora do escopo da contagem do "
        f"gerador, que olha só outputs/, scripts/, audit_independente/ e docs/); Submissao/: {por.get('Submissao', 0)}; versionados em {HEAD}: {len(vers)} "
        f"(em nenhum commit do histórico: K3.02); cobertos pelo .gitignore ('._*', git check-ignore --no-index): {n_ign}/{len(todos)}; todos têm o arquivo-base "
        f"ao lado: {base_ok}; cada um tem 4,096 bytes: {all(x.stat().st_size == 4096 for x in todos)}")
    # globs dos scripts que poderiam pegar ._* (pathlib: '*' casa com nomes que começam com ponto)
    GLOBS = [
        ("scripts/etapa7b_lib.py:203-204", MS, "_arquivo_v*/numeros_chave_v*_*.json", False),
        ("scripts/etapa7b_checa.py:136", MS / "figuras", f"*_{V11}.tif", False),
        ("scripts/etapa7b_checa.py:136", MS / "suplementar", f"*_{V11}.tif", False),
        ("scripts/etapa7b_checa.py:626", MS / "tabelas", f"*_{V11}.csv", False),
        ("scripts/etapa7b_checa.py:626", MS / "suplementar", f"*_{V11}.csv", False),
        ("scripts/etapa7b_checa.py:634", SUB, "ESM_*.pdf", False),
        ("scripts/resumos/etapa7c1_02_resumo.py:70", MS / "_arquivo_v4" / "suplementar", "*_v4_20261009.csv", False),
        ("scripts/resumos/etapa7c2_02_resumo.py:47", MS / "_arquivo_v5" / "suplementar", "*_v5_20261009.csv", None),
        ("scripts/resumos/etapa7c3_01_resumo.py:58", MS / "_arquivo_v6" / "suplementar", "*_v6_20261009.csv", None),
    ]
    det = []
    for onde, base, pad, _ in GLOBS:
        hits = [p.name for p in base.glob(pad) if p.name.startswith("._")]
        det.append(f"{onde} {base.relative_to(PROJ)}/{pad}: {len(hits)}")
    contam = [f"{f.relative_to(PROJ)}:{i + 1}" for f in scripts_legiveis() for i, l in enumerate(ler(f).splitlines())
              if re.search(r'rglob\("\._\*"\)', l)]
    reg("M1.02", True,
        f"globs sem exclusão de ._* que hoje casariam com algum ._* existente: {'; '.join(det)} → nenhum casa hoje (os ._* existentes acompanham só PDFs, 1 CSV de "
        f"outputs/tables e 1 log, fora dos padrões). Scripts cuja SAÍDA depende dos ._* (contam-nos): {contam} — os geradores de RESUMO 7c.5 e 7c.6 (seção 3) e a trava "
        f"de Submissao/ no etapa7b_04; apagar os ._* fora de Submissao/ mudaria a seção 3 do RESUMO 7c.6 numa regeração (o L3 deixaria de reproduzir byte a byte). "
        f"Nenhuma checagem do etapa7b_checa.py conta ._* fora de Submissao/. Exemplo do risco de pathlib: a própria primeira versão do L1.48 desta auditoria "
        f"pegou ._S7/._S8 com glob('*_v11….pdf')")
    pdfs = sorted(f for f in MS.rglob("*.pdf") if not f.name.startswith("._")) + sorted(f for f in SUB.glob("*.pdf") if not f.name.startswith("._"))
    q = {str(f.relative_to(PROJ)): xattr_q(f) for f in pdfs}
    com_q = sorted(k for k, v in q.items() if v)
    sem_q = sorted(k for k, v in q.items() if not v)
    prov = {str(x.relative_to(PROJ)): xattr_nomes(x.parent / x.name[2:]) for x in todos if not str(x).startswith(str(PROJ / "outputs/manuscrito"))}
    reg("M1.03", True,
        f"com.apple.quarantine (agente 'Chrome') nos PDFs: {len(com_q)}/{len(q)} — v11 em suplementar/: "
        f"{[k.split('/')[-1] for k in com_q if V11 in k]}; arquivados: {sum(1 for k in com_q if '_arquivo_v' in k)} (S7/S8 de v1–v10 e ESM_2–4 de "
        f"_arquivo_v4–v7/Submissao). Sem quarentena: {sem_q} (Submissao/ e _arquivo_v8–v10/Submissao passaram por dot_clean -m). Os ._* fora de outputs/manuscrito "
        f"guardam outro xattr: {prov}")
    dc_exec = [f"{f.relative_to(PROJ)}:{i + 1}" for f in scripts_legiveis() for i, l in enumerate(ler(f).splitlines())
               if re.search(r'\[\s*"dot_clean"', l) and "count(" not in l]
    dc = [f"{f.relative_to(PROJ)}:{i + 1}" for f in scripts_legiveis() for i, l in enumerate(ler(f).splitlines()) if "dot_clean" in l]
    s04 = ler(PROJ / "scripts/etapa7b_04_submissao.py")
    chamadas = [n.lineno for n in ast.walk(ast.parse(s04)) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "limpa_macos"]
    reg("M1.04", True,
        f"chamadas de execução de dot_clean (lista de argumentos de subprocess): {dc_exec}; todas as menções (docstrings, log, checa): {dc}. Execução real só em "
        f"scripts/etapa7b_04_submissao.py:25 (subprocess dot_clean -m, "
        f"dentro de limpa_macos), chamada em L{chamadas} sobre Submissao/ (B.SUB). O etapa7b_02 (que gera S7/S8 com o Chrome headless em outputs/manuscrito/suplementar) "
        f"não chama dot_clean. O checa só lê o texto do etapa7b_04 para contar o dot_clean. Não pesquisado: scripts/etapa7c6_02_audita_final.py (independência)")

    # ======================= M2: docstring do etapa2_03 e efeito nos campos de commit
    e23 = ler(PROJ / "scripts/etapa2_03_indice_acesso.py").splitlines()
    comp = pd.read_csv(PROJ / "outputs/tables/tab_e2_03_mesprenat_completude_v1_20261008.csv").query("macro == 'Brasil'")
    outros = int((comp.n - comp.n_valido - comp.n_nulo - comp.n_99).sum())
    reg("M2.01", True,
        f"docstring L4–L5: numerador 'MESPRENAT 1–3' (= código L39 tri1 = between(1, 3)); denominador 'MESPRENAT válido (1–9; 99 = ignorado e nulo ficam fora)' "
        f"(= código L39 mes_valido = between(1, 9).fillna(False)). Correta no que diz, incompleta no que exclui: o código também deixa fora qualquer outro código "
        f"(0, 10–98, >99): {outros:,} registros, todos de 2014 (tab_e2_03_mesprenat_completude). A S7a já diz 'any other value excluded'. Outra exclusão não citada "
        f"na docstring: nascimentos cujo CODMUNRES não tem região de saúde ficam fora da agregação (L46, d[d.CO_REGSAUD.notna()]), embora L6 diga 'Universo: TODOS'")
    J = json.loads(ler(MS / f"numeros_chave_{V11}.json"))
    scr = Counter(i["script"].split()[0] for i in J if i["script"])
    reg("M2.02", True,
        f"nenhum número-chave tem etapa2_03 como script de origem: {'scripts/etapa2_03_indice_acesso.py' not in scr} ({len(scr)} scripts de origem distintos). "
        f"Pela lib (commits_analise): commit_registro depende só dos commits que adicionaram os JSON arquivados; commit_analise (lido direto) usa (a) 1º commit após o "
        f"mtime da tabela e (b) 'git log -1 <commit_registro> -- <script>', ambos anteriores a qualquer commit novo; e, a partir da v12, é herdado da v11 arquivada "
        f"(congelado). No checa (bloco 9g), _ca usa as versões 1–10 e _calc usa 'rev-list --since=<mtime> HEAD' (o mais antigo) e o mesmo (b): um commit novo no fim "
        f"não altera nenhum dos dois. Só commit_pacote (= HEAD ao gerar) mudaria, por definição")
    res = teste_sintetico_m2()
    reg("M2.03", res["ok"],
        "teste sintético próprio (funções _mesmo_valor, na_tabela e commits_analise extraídas por AST do etapa7b_lib.py e rodadas com um git falso, dados em "
        f"m2_sintetico/): {res['det']}")

    # ======================= M3: tamanho do repositório e histórico
    obj = [Path(dp) / f for dp, _, fs in os.walk(PROJ / ".git" / "objects") for f in fs if not f.startswith("._")]
    soltos = [o for o in obj if re.fullmatch(r"[0-9a-f]{2}", o.parent.name)]
    packs = [o for o in obj if o.parent.name == "pack"]
    cov = git("count-objects", "-vH")
    bytes_soltos = sum(o.stat().st_size for o in soltos)
    commits = ctx.get("commits_todos") or sorted(set(git("rev-list", "--all", "--reflog").split()))
    caminhos = defaultdict(set)
    tam = {}
    head_bytes, head_arq = 0, 0
    for c in commits:
        for l in git("ls-tree", "-r", "-l", c).splitlines():
            meta, cam = l.split("\t", 1)
            _, tipo, h, sz = meta.split()
            if tipo != "blob":
                continue
            caminhos[h].add(cam)
            tam[h] = int(sz)
    total_unico = sum(tam.values())
    em_arq = {h for h, ps in caminhos.items() if any("/_arquivo_v" in p for p in ps)}
    so_arq = {h for h, ps in caminhos.items() if all("/_arquivo_v" in p for p in ps)}
    for l in git("ls-tree", "-r", "-l", HEAD).splitlines():
        meta, cam = l.split("\t", 1)
        sz = int(meta.split()[3])
        head_bytes += sz
        head_arq += sz if "/_arquivo_v" in cam else 0
    top = sorted(tam.items(), key=lambda x: -x[1])[:15]
    with open(OUT / "m3_maiores_blobs_7c6_final_v1_20261010.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["blob", "bytes", "caminhos"])
        for h, s in top:
            w.writerow([h, s, " ; ".join(sorted(caminhos[h]))])
    mb = lambda b: f"{b / 1e6:.2f} MB"
    reg("M3.01", True,
        f"git count-objects -vH: {' / '.join(x for x in cov.splitlines() if x.startswith(('count', 'size:', 'in-pack', 'size-pack')))} — o 'size' vem de blocos alocados "
        f"(exFAT, cluster de 1 MB) e infla; soma real dos {len(soltos)} objetos soltos (stat st_size): {mb(bytes_soltos)}; packs: {len(packs)}. "
        f"Blobs únicos em {len(commits)} commits (--all --reflog): {len(tam)}, {mb(total_unico)} sem compressão. Árvore de {HEAD}: {mb(head_bytes)}, dos quais "
        f"{mb(head_arq)} ({100 * head_arq / head_bytes:.1f}%) em outputs/manuscrito/_arquivo_v*. No histórico: blobs que aparecem em algum _arquivo_v* = "
        f"{mb(sum(tam[h] for h in em_arq))} ({100 * sum(tam[h] for h in em_arq) / total_unico:.1f}% dos bytes únicos); só em _arquivo_v* (nunca fora) = "
        f"{mb(sum(tam[h] for h in so_arq))} ({100 * sum(tam[h] for h in so_arq) / total_unico:.1f}%)")
    reg("M3.02", True,
        f"15 maiores blobs (bytes; caminho de origem + nº de outros caminhos com o mesmo blob): " + "; ".join(
            f"{s:,} {origem(caminhos[h])}" + (f" (+{len(caminhos[h]) - 1})" if len(caminhos[h]) > 1 else "") for h, s in top)
        + f". Acima de 50 MB: {sum(s > 50e6 for s in tam.values())}; acima de 100 MB: {sum(s > 100e6 for s in tam.values())}; maior: {mb(top[0][1])}. "
          f"Lista completa em m3_maiores_blobs_7c6_final_v1_20261010.csv")
    todos_cam = ctx.get("todos_caminhos") or {p for ps in caminhos.values() for p in ps}
    ext = Counter(PurePosixPath(p).suffix.lower() or "(sem)" for p in todos_cam)
    dados_ext = sorted(p for p in todos_cam if PurePosixPath(p).suffix.lower() in (".parquet", ".dbc", ".dbf", ".gz", ".rds", ".rdata", ".feather", ".sav",
                                                                                     ".dta", ".zip", ".sqlite", ".db", ".duckdb", ".arrow"))
    tabs = []
    for h, ps in caminhos.items():
        p = sorted(ps)[0]
        suf = PurePosixPath(p).suffix.lower()
        if suf not in (".csv", ".tsv", ".json", ".xlsx", ".txt", ".md"):
            continue
        if any(proibido(x) for x in ps):
            continue
        b = git("cat-file", "blob", h, binary=True)
        if suf in (".csv", ".tsv"):
            t = b.decode("utf-8", "replace")
            rows = list(csv.reader(io.StringIO(t), delimiter="\t" if suf == ".tsv" else ","))
            cols = rows[0] if rows else []
            tabs.append((len(rows) - 1, len(cols), p, [c for c in cols if ID_COLS.match(c.strip())], cols))
        elif suf == ".xlsx":
            cel = xlsx_celulas(b)
            n = max(len(v) for v in cel.values())
            hdr = sorted({str(c) for v in cel.values() for r in v[:4] for c in r if c is not None and ID_COLS.match(str(c).strip())})
            tabs.append((n, max((len(r) for v in cel.values() for r in v), default=0), p, hdr, []))
        else:
            n = b.count(b"\n")
            tabs.append((n, 0, p, [], []))
    tabs.sort(key=lambda x: -x[0])
    susp = [(p, s) for n, k, p, s, _ in tabs if s]
    csvs = [x for x in tabs if x[2].endswith(".csv")]
    reg("M3.03", not dados_ext and not susp,
        f"{len(todos_cam)} caminhos já versionados em algum commit; extensões: {dict(ext.most_common(12))}. Arquivos com extensão de dado (.parquet, .dbc, .dbf, .gz, .rds, "
        f".zip, …): {dados_ext or 'nenhum'}. Colunas com nome de identificador (DTNASC, HORANASC, NUMERODN, CODESTAB, CNES, CNS, CPF, DTOBITO …) em CSV/xlsx de "
        f"qualquer versão: {susp or 'nenhuma'}. Maiores CSV por linhas: "
        + "; ".join(f"{p.split('/')[-1]} {n:,}×{k} (colunas: {', '.join(c[:12] for c in cols[:8])}{'…' if len(cols) > 8 else ''})" for n, k, p, _, cols in csvs[:5])
        + f". Maior texto por linhas: {[(x[2].split('/')[-1], x[0]) for x in tabs if not x[2].endswith(('.csv', '.xlsx'))][:2]}. "
          f"checa_7b_*.csv não lidos aqui (independência). Nenhum volume compatível com registros individuais (≥ 1e5 linhas): {sum(1 for x in tabs if x[0] >= 1e5)}")

    # ======================= M4: docs/referencias não rastreados
    st = git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "docs/referencias").splitlines()
    nao = sorted(l[3:] for l in st if l.startswith("??"))
    ign = git("ls-files", "-o", "-i", "--exclude-standard", "docs/referencias").split()
    scripts = scripts_legiveis()
    texto_scr = {f: ler(f) for f in scripts}
    leitura_re = re.compile(r"read_csv|read\.csv|json\.load|open\(|Document\(|read_text|read_parquet|fread|readRDS|TER /")
    linhas = []
    for p in nao:
        nome = PurePosixPath(p).name
        lido, citado = [], []
        for f, t in texto_scr.items():
            for i, l in enumerate(t.splitlines()):
                if nome in l:
                    (lido if leitura_re.search(l) and not l.lstrip().startswith("#") else citado).append(f"{f.relative_to(PROJ)}:{i + 1}")
        linhas.append(dict(arquivo=p, bytes=(PROJ / p).stat().st_size, lido_por=" ; ".join(lido), citado_em=" ; ".join(citado)))
    df = pd.DataFrame(linhas)
    df.to_csv(OUT / "m4_referencias_nao_rastreadas_7c6_final_v1_20261010.csv", index=False)
    lidos = df[df.lido_por != ""]
    terr = df[df.arquivo.str.startswith("docs/referencias/territorio_dez24/")]
    raiz = df[~df.arquivo.str.contains("territorio_dez24/")]
    reg("M4.01", True,
        f"não rastreados em docs/referencias/: {len(nao)} ({df.bytes.sum():,} bytes) — territorio_dez24/: {len(terr)} ({terr.bytes.sum():,} bytes; 20 csv, 20 txt, "
        f"20 xml, 20 _layout.txt, zip …); demais: " + "; ".join(f"{r.arquivo.replace('docs/referencias/', '')} {r.bytes:,}" for r in raiz.itertuples())
        + f". Também ignorados pelo .gitignore (não aparecem como não rastreados): {len(ign)} ({sorted({PurePosixPath(x).suffix for x in ign})})")
    reg("M4.02", True,
        "lidos por algum script (linha de leitura, fora de comentário): " + "; ".join(f"{r.arquivo.replace('docs/referencias/', '')} ← {r.lido_por}" for r in lidos.itertuples())
        + f". Os outros {len(df) - len(lidos)} não são abertos por nenhum script (PDFs só citados em docstring/rodapé/MANIFEST; da base territorial só 3 de "
          f"{len(terr)} arquivos são lidos). Lista em m4_referencias_nao_rastreadas_7c6_final_v1_20261010.csv")
    fontes = {
        "territorio_dez24/* (102 arq.)": fonte_registrada("docs/referencias/territorio_dez24/ACESSO.txt"),
        "censo2022/sidra_9605_n6_2022.json": fonte_registrada("docs/referencias/censo2022/ACESSO.txt"),
        "intergrowth21_bw_centis_oficial.csv e grow_*.pdf": "scripts/etapa1_02a_pig_validacao.R:7–8 ('tabelas oficiais … intergrowth21.com, baixadas em 2026-10-08'); "
                                                             "data_code_availability ('official tables (grow_*_bw_table.pdf) downloaded on 2026-10-08'); sem URL exata",
        "SINASC_Estrutura_CGIAE_diaad_acesso20261008.pdf, Manual_preenchimento_DN_govbr_acesso20261008.pdf": "docs/referencias/tpmetestim_codigo8_busca_v1_20261008.md:7,9 (título, URL, MD5)",
        "SINASC_Estrutura_2024.pdf, Dicionario_SIM_2025.pdf": "citados em etapa7b_02 L366, etapa7b_04 (MANIFEST) e etapa1_06 (docstring); sem URL registrada além da "
                                                             "cópia 'diaad' (mesmo tamanho do SINASC_Estrutura_2024)",
        "STROBE_checklist_cross_sectional_acesso20261009.pdf": "só na tabela do RESUMO 7c.5b; sem URL nem licença",
        "evans2024_maihda_tutorial_PMC11059336.txt": "docs/referencias/maihda_formulas_fonte_v1_20261008.md:3–7 (referência completa, PMID/PMCID/DOI, 'obtido do PMC em 2026-10-08')",
    }
    lic = [f"{f.relative_to(PROJ)}" for f in list(PROJ.glob("docs/referencias/**/*.md")) + list(PROJ.glob("docs/referencias/**/ACESSO.txt"))
           if re.search(r"licen", ler(f), re.I)]
    reg("M4.03", True,
        "fonte registrada no projeto: " + " | ".join(f"{k}: {v}" for k, v in fontes.items())
        + f". Licença registrada: só a do RECORD (ATRIBUICAO.txt, versionado). Nenhum ACESSO.txt ou nota de docs/referencias fala de licença ({lic or 'nenhum'}); "
          "o RESUMO 7c.5b diz do Evans 'Antes de versionar, é preciso conferir a licença'. Nenhuma licença é presumida aqui")

    # ======================= M5: Evans 2024
    web = json.loads(ler(OUT / "web_7c6_final_v1_20261010.json"))
    ev, evp = web["evans_epmc"], web["evans_pmc"]
    leem = [f"{f.relative_to(PROJ)}" for f, t in texto_scr.items() if "evans2024_maihda_tutorial" in t]
    reg("M5.01", ev.get("pmcid") == "PMC11059336" and "creativecommons.org/licenses/by/4.0" in evp["licenca_href"],
        f"referência: {ev.get('autores')} {ev.get('titulo')} {ev.get('revista')} {ev.get('ano')};{ev.get('volume')}:{ev.get('pagina')}. doi:{ev.get('doi')}; "
        f"PMID {ev.get('pmid')}; {ev.get('pmcid')} (= docs/referencias/maihda_formulas_fonte_v1_20261008.md). Licença declarada no XML do PMC (efetch, {web['quando']}): "
        f"{evp['licenca'][0] if evp['licenca'] else '-'}; {evp['copyright']}; Europe PMC: license='{ev.get('license')}', isOpenAccess={ev.get('isOpenAccess')}. "
        f"O serviço OA antigo ({web['evans_oa_fcgi']['url']}) respondeu {web['evans_oa_fcgi']['status']}. O .txt (76,555 bytes, 359 linhas) não traz título, autores "
        f"nem licença no próprio texto. Scripts que abrem o .txt: {leem or 'nenhum'} (etapa5_02_maihda.R e etapa6_06 citam só a nota maihda_formulas_fonte em comentário)")

    # ======================= M6: CSVs ignorados em audit_independente
    ig = [PROJ / p for p in git("ls-files", "-o", "-i", "--exclude-standard", "audit_independente").split() if p.endswith(".csv")]
    ig_ant = [f for f in ig if "etapa7c6_final" not in str(f)]
    info = []
    for f in ig_ant:
        rows = list(csv.reader(io.StringIO(ler(f))))
        cols = rows[0] if rows else []
        info.append((len(rows) - 1, len(cols), str(f.relative_to(PROJ)), [c for c in cols if ID_COLS.match(c.strip())], cols))
    info.sort(key=lambda x: -x[0])
    leit = {
        "scripts/etapa1_08_auditoria_propria.py (L97, L118, L131: leitura incondicional)": "etapa1",
        "scripts/etapa2_06_auditoria_propria.py (L96–L106, se a pasta existir)": "etapa2",
        "scripts/etapa3_06_auditoria_propria.py (L108–L121, se a pasta existir)": "etapa3",
        "scripts/etapa4b_05_auditoria.py (L79–L94, se a pasta existir)": "etapa4b",
        "scripts/etapa5_04_auditoria.py (L90–L103, se a pasta existir)": "etapa5",
        "scripts/etapa6_08_auditoria.py (L100–L102, se a pasta existir)": "etapa6",
        "scripts/etapa6b_03_auditoria.py (L78: só se houver comparacao*.csv)": "etapa6b",
        "scripts/etapa7b_checa.py (L201–L231, L710–L737: só se o arquivo existir)": "etapa7b1–7b3, 7c1–7c4, 7c6",
        "scripts/resumos/etapa7c6_01_resumo.py (L26: leitura incondicional)": "etapa7c6",
    }
    reg("M6.01", True,
        f"CSVs ignorados pela regra audit_independente/**/*.csv (sem esta auditoria): {len(ig_ant)}, {sum(f.stat().st_size for f in ig_ant):,} bytes, em "
        f"{len({f.parent for f in ig_ant})} pastas; também ignorados: {len(ig) - len(ig_ant)} desta auditoria")
    reg("M6.02", True,
        "quem os lê: " + "; ".join(f"{k} → {v}" for k, v in leit.items())
        + ". Num clone limpo (pastas audit_independente/etapaN existem pelos .txt/.py versionados, mas sem os CSV): falham por arquivo ausente etapa1_08, etapa2_06, "
          "etapa3_06, etapa4b_05, etapa5_04, etapa6_08 (que também exigem data/) e o gerador do RESUMO 7c.6; o checa e o etapa6b_03 pulam a checagem")
    peq = []
    for n_, k_, cam, _, cols in info:
        cn = [c for c in cols if c in ("n", "N", "n_nasc", "nasc")]
        if not cn:
            continue
        v = pd.to_numeric(pd.read_csv(PROJ / cam, usecols=[cn[0]])[cn[0]], errors="coerce")
        peq.append((cam.replace("audit_independente/", ""), cn[0], int((v == 1).sum()), int(((v >= 1) & (v < 5)).sum()), len(v)))
    peq.sort(key=lambda x: -x[3])
    larg = max(info, key=lambda x: x[1])
    reg("M6.03", not any(x[3] for x in info),
        f"dado individual: colunas com nome de identificador: {[(x[2], x[3]) for x in info if x[3]] or 'nenhuma'}; máximo de linhas {info[0][0]:,} ({info[0][2]}); "
        f"máximo de colunas {larg[1]} ({larg[2].replace('audit_independente/', '')}). São tabelas agregadas (células com contagem), mas finas: arquivos com coluna de "
        f"contagem e células com contagem 1 / entre 1 e 4 (de N linhas): " + "; ".join(f"{c} [{col}] {a1:,} / {a4:,} de {nn:,}" for c, col, a1, a4, nn in peq[:5])
        + f" (total em {len(peq)} arquivos: {sum(x[2] for x in peq):,} células com contagem 1). 5 maiores: " + "; ".join(f"{x[2].replace('audit_independente/', '')} {x[0]:,}×{x[1]} ({', '.join(c[:14] for c in x[4][:7])}"
                                                                         f"{'…' if len(x[4]) > 7 else ''})" for x in info[:5]))

    # ======================= M7: denominador do índice no pacote v11
    corpus = {k: texto_arquivo(f) for k, f in pacote_v11().items() if f.suffix.lower() in (".csv", ".xlsx", ".docx", ".pdf", ".md", ".json")}
    corpus = {k: ws(v) for k, v in corpus.items()}
    ctx["corpus"] = corpus
    FR = {"among births with known month of prenatal care initiation": r"among births with known month of prenatal care initiation",
          "known month of first visit": r"known month of first visit", "first visit": r"first visit",
          "month of prenatal care initiation (qualquer)": r"month of prenatal care initiation",
          "prenatal care initiated in the first trimester": r"prenatal care initiated in the first trimester",
          "valid MESPRENAT": r"valid MESPRENAT", "first prenatal (visit/consultation)": r"first prenatal",
          "month of gestation in which prenatal care started": r"[Mm]onth of gestation in which prenatal care started"}
    cont = {k: {f: len(re.findall(p, t)) for f, t in corpus.items() if re.findall(p, t)} for k, p in FR.items()}
    tot = {k: sum(v.values()) for k, v in cont.items()}
    (OUT / "m7_m10_termos_7c6_final_v1_20261010.json").write_text(json.dumps({"M7": cont}, ensure_ascii=False, indent=1))
    reg("M7.01", True,
        "formulações no pacote v11 (CSV, xlsx, docx, PDFs de suplementar/ e Submissao/, md e JSON; espaços normalizados): "
        + "; ".join(f"'{k}': {tot[k]} em {len(cont[k])} arquivos" + (f" {dict((x.split('/')[-1], n) for x, n in cont[k].items())}" if 0 < len(cont[k]) <= 4 else "")
                    for k in FR)
        + ". Detalhe por arquivo em m7_m10_termos_7c6_final_v1_20261010.json")
    reg("M7.02", True,
        "código (etapa2_03_indice_acesso.py): variável MESPRENAT do SINASC ('Mês de gestação em que iniciou o pré-natal'; S7a: 'Month of gestation in which "
        "prenatal care started'); numerador = MESPRENAT 1–3 (L39 tri1), denominador = MESPRENAT 1–9 (L39 mes_valido); 99, nulo e outros códigos fora dos dois; "
        "índice = 100·Σtri1/Σmes_valido por região de saúde de residência × ano (L46–L51), atribuído ao ano seguinte (L74). Não há variável de 'first visit' no código: "
        "MESPRENAT é o mês de início do pré-natal; 'first visit' só aparece no RESUMO (Métodos v5.1, documento fora do projeto)")

    # ======================= M8: CE e DF
    T = PROJ / "docs/referencias/territorio_dez24"
    tb = pd.read_csv(T / "tb_regsaud.csv", dtype=str)
    rl = pd.read_csv(T / "rl_municip_regsaud.csv", dtype=str)
    u = pd.read_csv(PROJ / "outputs/tables/tab_e6_06_u_regsaude_v1_20261008.csv", dtype=str)
    ind = pd.read_csv(PROJ / "data/processed/indice_acesso_regsaude_ano_v1_20261008.csv", dtype={"CO_REGSAUD": str}, usecols=["CO_REGSAUD", "ano"])
    contag = {uf: dict(tb_regsaud=int((tb.REGSAUD.str[:2] == cod).sum()), com_municipio=int(rl[rl.CO_REGSAUD.str[:2] == cod].CO_REGSAUD.nunique()),
                       municipios=int(rl[rl.CO_REGSAUD.str[:2] == cod].CO_MUNICIP.nunique()),
                       no_indice=int(ind[ind.CO_REGSAUD.str[:2] == cod].CO_REGSAUD.nunique()),
                       na_analise_433=int((u.CO_REGSAUD.str[:2] == cod).sum()))
              for uf, cod in (("CE", "23"), ("DF", "53"))}
    reg("M8.01", True,
        "justificativas registradas: (1) código, scripts/etapa1_07_sensibilidade_ce_df.py:2 'as duas UFs com pior completude de RACACORMAE na Etapa 0' — "
        "quantificada: CE 17,5%, DF 16,9% de ausente+ignorado (RESUMO_ETAPA0 L23; seguintes PB 7,8%, BA 6,3%, GO 6,1%); (2) 'índice de acesso mais grosseiro' — "
        "vem da especificação da Etapa 4 (prompt, fora do repositório; ficha_metodos_7c0 §14 marca 'NÃO DETERMINÁVEL'); o único registro qualitativo é o RESUMO_ETAPA2 L13 "
        "('o DF é uma região só…; o CE tem 5 regiões grandes…; nas duas UFs o índice é mais grosseiro'), sem número de comparação. Os RESUMOs 7c.1–7c.6 listam essa "
        "segunda razão como 'não quantificada'")
    reg("M8.02", True,
        f"base territorial dez/2024 (docs/referencias/territorio_dez24, só leitura): {contag['CE']['tb_regsaud']} regiões de saúde do CE e {contag['DF']['tb_regsaud']} do DF em "
        f"tb_regsaud (todas ATIVO); com município em rl_municip_regsaud: CE {contag['CE']['com_municipio']} ({contag['CE']['municipios']} municípios), DF "
        f"{contag['DF']['com_municipio']} (códigos 530000 e 530010). No índice por região-ano (agregado, data/processed): CE {contag['CE']['no_indice']}, DF "
        f"{contag['DF']['no_indice']}; entre as 433 regiões das análises com tercil (tab_e6_06_u_regsaude): CE {contag['CE']['na_analise_433']}, DF "
        f"{contag['DF']['na_analise_433']} — coerente com G = 427 sem CE/DF (ficha_metodos_7c0 §13; RESUMO_ETAPA7B1)")

    # ======================= M9: Tabela 4, n.a. e imputação múltipla
    t4 = pd.read_csv(MS / "tabelas" / f"tab04_sensitivity_{V11}.csv", dtype=str).fillna("")
    mi = t4[t4.Scenario.str.startswith("Multiple imputation")].iloc[0]
    na_mi = [c for c in t4.columns if mi[c].startswith("n.a.")]
    x4 = [v for k, v in xlsx_celulas(str(MS / "tabelas" / f"tabelas_principais_{V11}.xlsx")).items() if k.startswith("tab04")][0]
    rod = [r[0] for r in x4 if r and r[0]][-1]
    frase_mi = re.findall(r"Multiple imputation:[^.]*\.", rod)
    reg("M9.01", True,
        f"Tabela 4 (tab04_sensitivity_v11 CSV/xlsx/docx), linha '{mi.Scenario}': 'n.a.' nas colunas {na_mi}; as demais células da linha têm valor (PR M2 e IC dos 3 "
        f"desfechos). Rodapé: {frase_mi} — não explica o 'n.a.' do Wald (não há menção a Wald combinado sob imputação); o rodapé não usa a sigla 'n.a.' em nenhum "
        f"lugar (presente: {'n.a.' in rod}). Outras linhas com 'n.a.' têm motivo no próprio rótulo ou célula ('SGA only', '(not reclassified)', '(unchanged)', bounds)")

    # ======================= M10: PR × RR, PTB indicado e SGA
    T10 = {"prevalence ratio(s)": r"\b[Pp]revalence ratios?\b", "PR (sigla)": r"\bPRs?\b", "risk ratio(s)": r"\b[Rr]isk ratios?\b",
           "relative risk": r"\b[Rr]elative risks?\b", "RR (sigla)": r"\bRRs?\b", "RRR": r"\bRRR\b", "relative risk ratio": r"\b[Rr]elative risk ratios?\b",
           "provider-initiated": r"[Pp]rovider-initiated", "indicated (palavra)": r"\bindicated\b", "SGA": r"\bSGA\b",
           "small for gestational age": r"[Ss]mall[- ]for[- ]gestational[- ]age"}
    c10 = {k: {f: len(re.findall(p, t)) for f, t in corpus.items() if re.findall(p, t)} for k, p in T10.items()}
    j = json.loads(ler(OUT / "m7_m10_termos_7c6_final_v1_20261010.json"))
    j["M10"] = c10
    (OUT / "m7_m10_termos_7c6_final_v1_20261010.json").write_text(json.dumps(j, ensure_ascii=False, indent=1))
    reg("M10.01", True, "contagens no pacote v11 (mesmo corpus do M7): " + "; ".join(f"'{k}': {sum(v.values())} ({len(v)} arq.)" for k, v in c10.items())
        + ". 'prevalence ratio' por extenso: título e rodapé da Tabela 2 (xlsx/docx) e legenda da Fig. 2; 'relative risk' só no texto do item 16c do checklist "
          "STROBE (S8); 'RRR' = razão de risco relativo do multinomial (S3, números-chave). Nenhum 'RR' ou 'risk ratio' no pacote")
    b1 = ler(PROJ / "scripts/etapa1_01_base_v2.py").splitlines()
    li = [i + 1 for i, l in enumerate(b1) if "ind = (tp == 1)" in l or "esp = ~ind" in l]
    s7a = pd.read_csv(MS / "suplementar" / f"S7a_variables_codes_{V11}.csv")
    defs7 = [c for c in s7a["Codes used and recoding in this study"].astype(str) if "Provider-initiated =" in c]
    s1b = [v for k, v in xlsx_celulas(str(MS / "suplementar" / f"ESM_1_tables_S1_S6_{V11}.xlsx")).items() if k.startswith("S1b")][0]
    rod_s1b = [r[0] for r in s1b if r and r[0]][-1]
    d_s1b = re.findall(r"Provider-initiated: [^.]*\.", rod_s1b)
    reg("M10.02", True,
        f"código (scripts/etapa1_01_base_v2.py L{li}): indicado = STTRABPART == 1 (induzido) OU (PARTO == 2 e STCESPARTO == 1, cesárea antes do trabalho de parto); "
        f"espontâneo = não indicado e STTRABPART == 2 e (PARTO == 1 ou (PARTO == 2 e STCESPARTO == 2)); o resto dos PTB = sem classificação (131,809 na amostra "
        f"analítica); ptb_ind/ptb_esp em etapa2_01_base_v3.py L51–L55 (o outro tipo e os termos = 0; sem classificação = nulo). S7a: {defs7[:1]}; rodapé da S1b: "
        f"{d_s1b}; rodapé da Tabela 1: denominadores excluem os 131,809 não classificados. Descrições consistentes com o código")
    reg("M10.03", True,
        f"'SGA' no pacote: {sum(c10['SGA'].values())} ocorrências em {len(c10['SGA'])} arquivos; por extenso 'small for gestational age': "
        f"{sum(c10['small for gestational age'].values())} ({sorted(c10['small for gestational age'])[:4]}). Rótulo do desfecho no código: OUTC['pig'] = 'SGA' "
        f"(etapa7b_lib L28); SGA = peso < P10 INTERGROWTH-21st por IG e sexo (etapa1_01_base_v2)")


def origem(ps):
    ps = sorted(ps)
    return next((p for p in ps if "_arquivo_v" not in p and not p.startswith("Submissao/")), next((p for p in ps if "_arquivo_v" not in p), ps[0]))


def fonte_registrada(rel):
    return f"{rel} → " + " / ".join(l.strip() for l in ler(PROJ / rel).splitlines() if l.strip())[:300]


# ---------------------------------------------------------------- M2: teste sintético
def teste_sintetico_m2():
    import shutil
    lib = ler(PROJ / "scripts/etapa7b_lib.py")
    fns = {n.name: ast.get_source_segment(lib, n) for n in ast.parse(lib).body if isinstance(n, ast.FunctionDef)
           and n.name in ("_mesmo_valor", "na_tabela", "commits_analise")}
    base = OUT / "m2_sintetico"
    if base.exists():
        shutil.rmtree(base)
    (base / "ms").mkdir(parents=True)
    (base / "tab").mkdir()
    tabela = base / "tab" / "tab_fonte.csv"
    tabela.write_text("desfecho,N,PR\nptb,1000,1.25\n")
    T0 = 1_790_000_000                                   # datas realistas: o exFAT não guarda mtime anterior a 1980
    os.utime(tabela, (T0 + 1000, T0 + 1000))            # tabela gerada em T0 + 1000
    itens = [dict(id="direto", valor_formatado="1.25", valor_bruto=1.25, arquivo="tab/tab_fonte.csv", script="scripts/etapa6b_01_modelos_rs.py"),
             dict(id="derivado", valor_formatado="500", valor_bruto=500, arquivo="tab/tab_fonte.csv", script="scripts/etapa6b_01_modelos_rs.py")]

    def arquiva(n, com_ca=None):
        d = base / "ms" / f"_arquivo_v{n}"
        d.mkdir(exist_ok=True)
        js = [dict(i, **({"commit_analise": com_ca[i["id"]]} if com_ca else {})) for i in itens]
        (d / f"numeros_chave_v{n}_20261009.json").write_text(json.dumps(js))

    class Git:
        def __init__(self, hist, adds):
            self.hist, self.adds = hist, adds         # hist: [(h, t, {arquivos})] do mais antigo ao mais novo

        def run(self, args, capture_output=True, text=True):
            a = args[3:]
            out = ""
            if a[:3] == ["log", "--diff-filter=A", "--format=%h"]:
                out = self.adds.get(Path(a[-1]).name, "")
            elif a == ["log", "--format=%h %ct"]:
                out = "\n".join(f"{h} {t}" for h, t, _ in reversed(self.hist))
            elif a[:3] == ["log", "-1", "--format=%h"]:
                ate, arq = a[3], a[5]
                idx = [h for h, _, _ in self.hist].index(ate)
                out = next((h for h, _, fs in reversed(self.hist[:idx + 1]) if arq in fs), "")
            return type("R", (), {"stdout": out, "returncode": 0})()

    def roda(git):
        ns = {"json": json, "np": np, "pd": pd, "subprocess": git, "PROJ": base, "MS": base / "ms"}
        for f in ("_mesmo_valor", "na_tabela", "commits_analise"):
            exec(fns[f], ns)
        return ns["commits_analise"](itens)

    H0 = [("c1aaaaa", T0 + 1500, {"scripts/etapa6b_01_modelos_rs.py"}), ("c2bbbbb", T0 + 2000, {"scripts/etapa7b_01_tabelas.py", "numeros_chave_v1_20261009.json"})]
    adds = {"numeros_chave_v1_20261009.json": "c2bbbbb"}
    arquiva(1)
    rA = roda(Git(H0, adds))                                                     # pacote gerado sobre o histórico atual
    H1 = H0 + [("c3ccccc", T0 + 3000, {"scripts/etapa2_03_indice_acesso.py"})]      # commit novo: só a docstring do etapa2_03
    rB = roda(Git(H1, adds))
    arquiva(2, com_ca={k: v[1] for k, v in rA.items()})                          # v2 arquivada já com commit_analise (congelado)
    adds2 = dict(adds, **{"numeros_chave_v2_20261009.json": "c3ccccc"})
    rC = roda(Git(H1, adds2))
    os.utime(tabela, (T0 + 3500, T0 + 3500))                                               # contraprova: tabela regravada depois de c3
    H2 = H1 + [("c4ddddd", T0 + 4000, {"scripts/etapa6b_01_modelos_rs.py"})]
    rD = roda(Git(H2, adds2))                                                    # com congelamento: não muda
    shutil.rmtree(base / "ms" / "_arquivo_v2")
    rE = roda(Git(H2, adds))                                                     # sem a versão congelada: o recálculo muda/esvazia
    ok = rA == rB == rC == rD == {"direto": ("c2bbbbb", "c1aaaaa"), "derivado": ("c2bbbbb", "c2bbbbb")} and rE["direto"][1] != "c1aaaaa"
    shutil.rmtree(base)
    det = (f"histórico atual → {rA}; + commit que só muda a docstring do etapa2_03 → {rB}; + v2 arquivada com commit_analise (congelado) → {rC}; "
           f"contraprova com a tabela regravada e o script de origem alterado depois: congelado {rD}, sem congelamento {rE}. "
           f"Conclusão: o commit só de docstring não muda commit_registro nem commit_analise")
    return dict(ok=ok, det=det)
