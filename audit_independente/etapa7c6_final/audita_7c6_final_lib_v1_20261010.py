"""
Auditoria independente final da Etapa 7c.6 — utilitários comuns (só leitura do projeto).

Regras embutidas:
- git: só comandos de leitura (log, show, diff, ls-files, ls-tree, cat-file, rev-list, reflog, rev-parse, for-each-ref,
  remote, tag -l, check-ignore, interpret-trailers --parse) e `status` com --no-optional-locks (não reescreve o índice).
- independência: ler() recusa checa_7b_*, audita_final_7c6_* e scripts/etapa7c6_02_audita_final.py.
- não importa etapa7b_lib (as funções da lib usadas no teste sintético do M2 são extraídas por AST e rodadas com um git falso).
- grava só em audit_independente/etapa7c6_final/.
"""
import json
import re
import subprocess
from pathlib import Path

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUT = PROJ / "audit_independente" / "etapa7c6_final"
HEAD = "b9d6272"
PAI = "8314417"
AMEND_ANT = "a38f550"
V10, V11 = "v10_20261009", "v11_20261009"
MS = PROJ / "outputs" / "manuscrito"
A10 = MS / "_arquivo_v10"
SUB = PROJ / "Submissao"
PROIBIDOS = ("checa_7b_", "audita_final_7c6", "etapa7c6_02_audita_final")

GIT_LEITURA = {"log", "show", "diff", "ls-files", "ls-tree", "cat-file", "rev-list", "reflog", "rev-parse", "for-each-ref",
               "remote", "tag", "check-ignore", "interpret-trailers", "count-objects", "merge-base", "status", "config"}


def git(*a, binary=False, check=True, entrada=None):
    assert a[0] in GIT_LEITURA or (a[0] == "--no-optional-locks" and a[1] == "status"), a
    if a[0] == "tag":
        assert a[1:] in (("-l",), ()), a
    if a[0] == "config":
        assert a[1] in ("--get-regexp", "-l", "--list"), a
    if a[0] == "status":
        raise AssertionError("use git('--no-optional-locks', 'status', ...)")
    r = subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, check=check, input=entrada)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def proibido(p):
    return any(x in str(p) for x in PROIBIDOS)


def ler(p, binary=False):
    p = Path(p)
    if proibido(p):
        raise PermissionError(f"independência: leitura recusada ({p.name})")
    return p.read_bytes() if binary else p.read_text(encoding="utf-8")


def blob(commit, caminho):
    if proibido(caminho):
        raise PermissionError(f"independência: leitura recusada ({caminho})")
    return git("show", f"{commit}:{caminho}", binary=True)


def assunto(c):
    return git("log", "-1", "--format=%s", c).strip().split(":")[0] if c else "(vazio)"


def ws(t):
    return " ".join(str(t).split())


# ---------- extração de texto (pacote)
def xlsx_celulas(fonte):
    """{aba: [[valores da linha]]} com openpyxl (fonte = caminho ou bytes)."""
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(fonte) if isinstance(fonte, bytes) else fonte, read_only=True)
    return {ws_.title: [list(r) for r in ws_.iter_rows(values_only=True)] for ws_ in wb.worksheets}


def xlsx_texto(fonte):
    return "\n".join(" ".join(str(c) for r in rows for c in r if c is not None) for rows in xlsx_celulas(fonte).values())


def docx_texto(fonte, cabecalhos=True):
    import io
    import docx
    d = docx.Document(io.BytesIO(fonte) if isinstance(fonte, bytes) else fonte)
    partes = [p.text for p in d.paragraphs]
    partes += [c.text for t in d.tables for r in t.rows for c in r.cells]
    if cabecalhos:
        for s in d.sections:
            partes += [p.text for p in s.header.paragraphs] + [p.text for p in s.footer.paragraphs]
    return "\n".join(partes)


def pdf_texto(fonte):
    import pymupdf
    doc = pymupdf.open(stream=fonte, filetype="pdf") if isinstance(fonte, bytes) else pymupdf.open(fonte)
    return "\n".join(pg.get_text() for pg in doc)


def pixels(fonte):
    import hashlib
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(fonte) if isinstance(fonte, bytes) else fonte)
    return (im.size, im.mode, im.info.get("dpi"), hashlib.md5(im.tobytes()).hexdigest())


def pacote_v11():
    """Arquivos do pacote v11 em disco: {rótulo: caminho}."""
    arq = {}
    for d in ("tabelas", "suplementar", "figuras"):
        for f in sorted((MS / d).glob(f"*_{V11}.*")):
            if not f.name.startswith("._"):
                arq[f"{d}/{f.name}"] = f
    for n in ("data_code_availability.md", "legendas_figuras.md", "MANIFEST.md", f"numeros_chave_{V11}.json", f"numeros_chave_{V11}.md"):
        arq[n] = MS / n
    for f in sorted(SUB.iterdir()):
        if not f.name.startswith("."):
            arq[f"Submissao/{f.name}"] = f
    return arq


def texto_arquivo(f):
    s = f.suffix.lower()
    if s == ".xlsx":
        return xlsx_texto(str(f))
    if s == ".docx":
        return docx_texto(str(f))
    if s == ".pdf":
        return pdf_texto(str(f))
    if s in (".csv", ".md", ".json", ".txt", ".py"):
        return ler(f)
    return ""


def json_dump(obj, nome):
    (OUT / nome).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


ID_COLS = re.compile(r"^(DTNASC|HORANASC|NUMERODN|NUMERODO|NUMERODV|CODESTAB|CNES|CNS|CPF|DTOBITO|HORAOBITO|DTNASCMAE|DTULTMENST|"
                     r"DTCADASTRO|DTRECEBIM|CODMUNNASC|NOME|NOMEMAE|ENDERECO|ENDRES|CEP|DTDECLARAC|NUMEROLOTE|CODINST)$", re.I)
