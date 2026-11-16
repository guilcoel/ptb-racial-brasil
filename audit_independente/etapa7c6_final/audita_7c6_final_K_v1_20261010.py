"""Bloco K — integridade do commit b9d6272 (amend, trailers, refs, arquivos do commit, ._*, dado individual, árvore de trabalho)."""
import csv
import io
import re
from collections import Counter
from pathlib import PurePosixPath

from audita_7c6_final_lib_v1_20261010 import (AMEND_ANT, HEAD, ID_COLS, PAI, PROJ, docx_texto, git, pdf_texto, proibido, xlsx_celulas)

TRAILER1 = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
TRAILER2 = "Claude-Session: [session URL removed for publication]"
FRASE_ANT = "Foram duas rodadas; a segunda conferiu o que mudou depois da primeira."
FRASE_NOVA = "Foram quatro rodadas; cada uma conferiu o que mudou depois da anterior."

# padrões de dado individual (contagem; nada é copiado para o relatório)
PAD = {
    "data_dd/mm/aaaa_1900-2024": re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19\d\d|20[01]\d|202[0-4])(?!\d)"),
    "data_aaaa-mm-dd_1900-2024": re.compile(r"(?<!\d)(19\d\d|20[01]\d|202[0-4])-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(?!\d)"),
    "data_ddmmaaaa_1900-2024": re.compile(r"(?<![\d.,])(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(19\d\d|20[01]\d|202[0-4])(?![\d.,])"),
    "cpf_###.###.###-##": re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"),
    "cns_15_digitos": re.compile(r"(?<![\d.,])[12789]\d{14}(?![\d.,])"),
}


def varre_texto(t):
    return {k: len(p.findall(t)) for k, p in PAD.items() if p.findall(t)}


def conteudo_arquivo(caminho, dados):
    """(texto, info) de um blob do commit; info = linhas/colunas/colunas suspeitas para tabelas."""
    suf = PurePosixPath(caminho).suffix.lower()
    info = {}
    if suf == ".csv":
        t = dados.decode("utf-8", "replace")
        rows = list(csv.reader(io.StringIO(t)))
        info = dict(linhas=max(len(rows) - 1, 0), colunas=max((len(r) for r in rows), default=0),
                    cols_suspeitas=[c for c in (rows[0] if rows else []) if ID_COLS.match(c.strip())])
        return t, info
    if suf == ".xlsx":
        cel = xlsx_celulas(dados)
        info = dict(linhas=max(len(v) for v in cel.values()), colunas=max((len(r) for v in cel.values() for r in v), default=0),
                    cols_suspeitas=sorted({str(c) for v in cel.values() for r in v[:4] for c in r if c is not None and ID_COLS.match(str(c).strip())}))
        return "\n".join(" ".join(str(c) for r in v for c in r if c is not None) for v in cel.values()), info
    if suf == ".docx":
        return docx_texto(dados), info
    if suf == ".pdf":
        return pdf_texto(dados), info
    if suf in (".png", ".tif", ".tiff"):
        return "", dict(imagem=True)
    return dados.decode("utf-8", "replace"), info


def run(reg, ctx):
    # ---------------- K1: amend
    rl = git("reflog", "--format=%h|%gs").splitlines()
    ent = {h: s for h, s in (x.split("|", 1) for x in rl)}
    pa = git("rev-parse", f"{AMEND_ANT}^").strip()
    pb = git("rev-parse", f"{HEAD}^").strip()
    pai = git("rev-parse", PAI).strip()
    msg_a, msg_b = git("cat-file", "commit", AMEND_ANT), git("cat-file", "commit", HEAD)
    corpo = lambda m: m.split("\n\n", 1)[1]
    autor = lambda m: [l for l in m.splitlines() if l.startswith("author ")][0]
    ok1 = (ent.get(HEAD, "").startswith("commit (amend)") and ent.get(AMEND_ANT, "").startswith("commit:") and pa == pb == pai
           and corpo(msg_a) == corpo(msg_b) and autor(msg_a) == autor(msg_b))
    reg("K1.01", ok1, f"reflog: {HEAD} = '{ent.get(HEAD, '')[:16]}…', {AMEND_ANT} = '{ent.get(AMEND_ANT, '')[:8]}…'; mesmo pai "
        f"{pai[:7]} ({pa == pb == pai}); mensagem idêntica ({corpo(msg_a) == corpo(msg_b)}); mesma linha author ({autor(msg_a) == autor(msg_b)}); "
        f"árvores {git('rev-parse', AMEND_ANT + '^{tree}').strip()[:7]} → {git('rev-parse', HEAD + '^{tree}').strip()[:7]}")
    ns = [l.split("\t") for l in git("diff", "--name-status", AMEND_ANT, HEAD).splitlines()]
    esperado = {"outputs/RESUMO_ETAPA7C6_v1_20261009.md", "outputs/manuscrito/_resumo7c6_texto_v1_20261009.md"}
    reg("K1.02", {x[1] for x in ns} == esperado and all(x[0] == "M" for x in ns),
        f"arquivos diferentes entre {AMEND_ANT} e {HEAD}: {len(ns)} — " + "; ".join(f"{x[0]} {x[1]}" for x in ns))
    det, ok3 = [], True
    for f in sorted(esperado):
        d = git("diff", "-U0", AMEND_ANT, HEAD, "--", f).splitlines()
        menos = [l[1:] for l in d if l.startswith("-") and not l.startswith("---")]
        mais = [l[1:] for l in d if l.startswith("+") and not l.startswith("+++")]
        so_frase = (len(menos) == len(mais) == 1 and FRASE_ANT in menos[0] and FRASE_NOVA in mais[0]
                    and menos[0].replace(FRASE_ANT, "") == mais[0].replace(FRASE_NOVA, ""))
        ok3 &= so_frase
        det.append(f"{f.split('/')[-1]}: -{len(menos)} +{len(mais)} linha(s); única mudança '{FRASE_ANT}' → '{FRASE_NOVA}': {so_frase}")
    reg("K1.03", ok3, " | ".join(det) + ". (A afirmação do autor cita 'duas' → 'quatro'; a troca real inclui também o resto da frase.)")

    # ---------------- K2: mensagem, trailers, refs
    m = corpo(msg_b)
    linhas = m.rstrip("\n").split("\n")
    fim_ok = m.endswith(f"\n\n{TRAILER1}\n{TRAILER2}\n") and linhas[-2:] == [TRAILER1, TRAILER2]
    tr = git("interpret-trailers", "--parse", entrada=m.encode()).splitlines()
    reg("K2.01", fim_ok and tr == [TRAILER1, TRAILER2],
        f"últimas 2 linhas da mensagem = as exigidas: {linhas[-2:] == [TRAILER1, TRAILER2]}; termina exatamente nelas (+ '\\n' final): {fim_ok}; "
        f"git interpret-trailers --parse → {tr}; título: '{linhas[0]}'")
    refs = git("for-each-ref", "--format=%(refname)").split()
    rem, tags = git("remote", "-v").strip(), git("tag", "-l").strip()
    cfg = (PROJ / ".git" / "config").read_text()
    reg("K2.02", not rem and not tags and refs == ["refs/heads/main"] and "[remote" not in cfg,
        f"git remote -v: {'(vazio)' if not rem else rem}; git tag -l: {'(vazio)' if not tags else tags}; refs: {refs}; '[remote' em .git/config: {'[remote' in cfg}; "
        f"packed-refs: {(PROJ / '.git' / 'packed-refs').exists()}")

    # ---------------- K3: arquivos do commit
    ns = [l.split("\t") for l in git("diff", "--name-status", "-M", PAI, HEAD).splitlines()]
    cnt = Counter(x[0] for x in ns)
    nr = Counter(l.split("\t")[0] for l in git("diff", "--name-status", "--no-renames", PAI, HEAD).splitlines())
    ctx["K3_ns"] = ns
    reg("K3.01", True, f"git diff --name-status -M {PAI} {HEAD}: {len(ns)} entradas — {dict(cnt)}; sem detecção de renomeação: {dict(nr)}. "
        f"R100: 10 geradores (scripts/ → scripts/resumos/) e 38 arquivos do pacote v10 (outputs/manuscrito/... → _arquivo_v10/...); "
        f"M: Submissao/ESM_1–4, MANIFEST.md, data_code_availability.md, legendas_figuras.md e 4 scripts etapa7b_ (lib, 02, 04, checa); "
        f"D: {cnt.get('D', 0)}. Lista completa em k3_arquivos_commit_7c6_final_v1_20261010.csv")
    with open(PROJ / "audit_independente/etapa7c6_final/k3_arquivos_commit_7c6_final_v1_20261010.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["status", "caminho_antigo", "caminho_novo"])
        for x in ns:
            w.writerow([x[0], x[1] if len(x) == 3 else "", x[-1]])
    arv = git("ls-tree", "-r", "--name-only", HEAD).splitlines()
    lixo_head = [p for p in arv if PurePosixPath(p).name.startswith("._") or PurePosixPath(p).name == ".DS_Store"]
    commits = sorted(set(git("rev-list", "--all", "--reflog").split()))
    lixo_hist, todos = set(), set()
    for c in commits:
        for p in git("ls-tree", "-r", "--name-only", c).splitlines():
            todos.add(p)
    lixo_hist = sorted(p for p in todos if PurePosixPath(p).name.startswith("._") or PurePosixPath(p).name == ".DS_Store")
    ctx["todos_caminhos"] = todos
    ctx["commits_todos"] = commits
    reg("K3.02", not lixo_head and not lixo_hist,
        f"._*/.DS_Store na árvore de {HEAD}: {len(lixo_head)}; em qualquer árvore de {len(commits)} commits (--all --reflog, inclui {AMEND_ANT}; "
        f"{len(todos)} caminhos distintos): {len(lixo_hist)}")
    # conteúdo: arquivos novos/modificados/renomeados (lado novo), lidos do blob do commit
    achados, maiores, susp, adiados, n_arq = {}, [], [], [], 0
    for x in ns:
        if x[0].startswith("D"):
            continue
        cam = x[-1]
        if proibido(cam):
            adiados.append(cam)
            continue
        dados = git("show", f"{HEAD}:{cam}", binary=True)
        n_arq += 1
        t, info = conteudo_arquivo(cam, dados)
        h = varre_texto(t)
        if h:
            achados[cam] = h
        if info.get("linhas") is not None:
            maiores.append((info["linhas"], info["colunas"], cam))
        if info.get("cols_suspeitas"):
            susp.append((cam, info["cols_suspeitas"]))
    maiores.sort(reverse=True)
    ctx["K3_achados"] = achados
    reg("K3.03", not susp,
        f"{n_arq} arquivos (lado novo de A/M/R) lidos do blob de {HEAD}; colunas com nome de identificador (DTNASC, HORANASC, NUMERODN, CODESTAB, CNES, "
        f"CNS, CPF, DTOBITO etc.) em CSV/xlsx: {susp or 'nenhuma'}; maiores tabelas (linhas × colunas): "
        + "; ".join(f"{c.split('/')[-1]} {l}×{k}" for l, k, c in maiores[:4])
        + f". Não lidos aqui por independência: {adiados} (ver L2b.04)")
    # classificação dos padrões encontrados (contagens por arquivo; contexto conferido à mão, sem copiar linhas)
    reg("K3.04", True,
        "padrões de data 1900–2024 / CPF / CNS de 15 dígitos (contagem por arquivo): "
        + ("; ".join(f"{k.split('/')[-1]}: {v}" for k, v in sorted(achados.items())) if achados else "nenhum")
        + ". Classificação na seção K do relatório.")

    # ---------------- K4: árvore de trabalho
    st = git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()
    rastreados_mod = [l for l in st if not l.startswith("??")]
    nao = [l[3:] for l in st if l.startswith("??")]
    ref = [p for p in nao if p.startswith("docs/referencias/")]
    outros = [p for p in nao if not p.startswith("docs/referencias/")]
    reg("K4.01", not rastreados_mod and len(ref) == 93,
        f"arquivos rastreados modificados/removidos/no índice: {len(rastreados_mod)}; não rastreados em docs/referencias/: {len(ref)}; "
        f"outros não rastreados agora: {len(outros)} ({sorted({o.split('/')[0] + '/' + o.split('/')[1] if o.count('/') > 1 else o for o in outros})}). "
        f"No início desta auditoria (10:12) havia só os 93 de docs/referencias/; scripts/etapa7c6_02_audita_final.py e "
        f"outputs/manuscrito/audita_final_7c6_v1_20261010.csv apareceram depois (autoauditoria do autor, em paralelo, 10:15–10:2x) e "
        f"audit_independente/etapa7c6_final/ é esta auditoria. Ignorados pelo .gitignore (não contados): ver M1/M6.")
