"""
9a.1 Zip de release (v1.0-submission) para o GitHub e o REDU: git archive de uma árvore do git (respeita o .gitattributes, export-ignore),
reempacotado em zip determinístico (ordem alfabética, data fixa 2026-11-15 00:00, permissões fixas, deflate). A mesma árvore dá o mesmo
SHA-256, o que permite conferir o zip depois do commit (git 2.39 não tem git archive --mtime).
Uso: python3 scripts/etapa9a_01_release.py [árvore]    (padrão: a árvore do índice, git write-tree; depois do commit: HEAD^{tree})
Saída: release/ptb-racial-brasil_v1.0-submission.zip (fora do git) e release/CONTEUDO_v1.0-submission.txt.
Trava: falha se entrar no zip manuscrito/, .docx, tabela INTERNAL, RESUMO, ._*, microdado (data/, .parquet, .dbc, .csv.gz),
outputs/tables, outputs/logs, CSV de audit_independente ou o e-mail pessoal.
"""
import hashlib
import io
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
NOME = "ptb-racial-brasil_v1.0-submission"
DATA = (2026, 11, 15, 0, 0, 0)
arvore = sys.argv[1] if len(sys.argv) > 1 else subprocess.run(["git", "-C", str(PROJ), "write-tree"], capture_output=True, text=True,
                                                                check=True).stdout.strip()
tar = subprocess.run(["git", "-C", str(PROJ), "archive", "--format=tar", f"--prefix={NOME}/", arvore], capture_output=True, check=True).stdout
membros = []
with tarfile.open(fileobj=io.BytesIO(tar)) as t:
    for m in t.getmembers():
        if m.isfile():
            membros.append((m.name, t.extractfile(m).read()))
membros.sort()
PROIBIDO = re.compile(rf"(^{NOME}/manuscrito/|^{NOME}/Submissao/.*\.docx$|/montagem/(Manuscript_|ESM_3_.*\.docx$|confere_7d_numeros)|INTERNAL|"
                      r"/RESUMO_|/_resumo|/\._|/data/|\.parquet$|\.dbc$|\.dbf$|\.csv\.gz$|/outputs/tables/|/outputs/logs/|"
                      r"/audit_independente/.*\.csv$|/audit_independente/etapa9a/|/scripts/resumos/|(?i:resumo)|/etapa4b/(relatorio_etapa4b|log_R_modelos|log_duckdb)_)")
ruins = [n for n, _ in membros if PROIBIDO.search(n)]
PESSOAL = (b"guico" + b"2lh", b"@" + b"gmail")        # montado em partes para o próprio script não conter o e-mail
email = [n for n, b in membros if any(x in b for x in PESSOAL)]
sessao = [n for n, b in membros if b"claude.ai/code/" + b"session_" in b]   # 9a, dupla auditoria: identificador de sessão interno
if ruins or email or sessao:
    raise RuntimeError(f"itens excluídos no zip: {ruins[:5]}; e-mail pessoal em {email[:5]}; URL de sessão em {sessao[:5]}")
for obrig in ("README.md", "LICENSE", "CITATION.cff", "requirements.txt", "R_sessionInfo.txt", "Submissao/ESM_4.xlsx",
              "outputs/manuscrito/numeros_chave_v15_20261115.json"):
    if f"{NOME}/{obrig}" not in dict(membros):
        raise RuntimeError(f"faltou no zip: {obrig}")
out = PROJ / "release"
out.mkdir(exist_ok=True)
zp = out / f"{NOME}.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for n, b in membros:
        zi = zipfile.ZipInfo(n, date_time=DATA)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        zi.create_system = 3
        z.writestr(zi, b, compresslevel=9)
sha = hashlib.sha256(zp.read_bytes()).hexdigest()
por = {}
for n, b in membros:
    k = "/".join(n.split("/")[1:3]) if n.count("/") > 1 else n.split("/", 1)[1]
    por.setdefault(k, [0, 0])
    por[k][0] += 1
    por[k][1] += len(b)
linhas = [f"{NOME}.zip  árvore {arvore}  {zp.stat().st_size} bytes  SHA-256 {sha}", f"{len(membros)} arquivos; "
          f"{sum(len(b) for _, b in membros)} bytes sem compressão", ""] + [f"{v[0]:5d} arquivos {v[1]:>12,d} bytes  {k}" for k, v in sorted(por.items())]
(out / "CONTEUDO_v1.0-submission.txt").write_text("\n".join(linhas) + "\n\n" + "\n".join(n for n, _ in membros) + "\n")
subprocess.run(["dot_clean", "-m", str(out)], check=True)
print("\n".join(linhas))
