"""
Auditoria independente final da 7c.6 — RODADA 6 (2026-10-13, mínima: a frase corrigida depois da rodada 5 e a reprodução). Acrescenta
linhas R6.* ao comparacao_7c6_final_v1_20261010.csv sem tocar nas 199 linhas das rodadas 1–5 (confere o MD5 dessa parte).

Passo feito ANTES deste script: etapa7c6b_01_resumo_copia_saida_auditor_r6.py rodada em 2026-10-13 10:11:07 com o CSV desta pasta
ainda com 199 linhas (MD5 75c265cf8d0c770368956a5d9c1c3054) → RESUMO_ETAPA7C6b_reproduzido_r6_v1_20261010.md.
Rodar: PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_R6_v1_20261010.py
"""
import csv
import difflib
import hashlib
import io
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True
from audita_7c6_final_lib_v1_20261010 import HEAD, PROJ, git  # noqa: E402

CSV_ = AQUI / "comparacao_7c6_final_v1_20261010.csv"
MD5_R5 = "75c265cf8d0c770368956a5d9c1c3054"
ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:200]}", flush=True)


ler = lambda p: Path(p).read_text(encoding="utf-8")
md5 = lambda b: hashlib.md5(b).hexdigest()
R6B = ler(PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md")
R6B_5 = ler(AQUI / "RESUMO_ETAPA7C6b_reproduzido_r5_v1_20261010.md")    # = RESUMO da rodada 5 (R5.02.01)
G6B = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
G6B_5 = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor_r5.py")

# ============================================ R6.01 frases
tipos = {e: sorted({Path(p).suffix for p in git("ls-files", f"audit_independente/{e}").split()}) for e in ("etapa2", "etapa3", "etapa4b", "etapa5", "etapa6")}
scripts_em_todas = all({".py"} & set(v) and ".txt" in v for v in tipos.values())
reg("R6.01.01", "testam a pasta do auditor, que está no git, com os `.txt` e os scripts do auditor" in R6B and "por causa dos `.txt`" not in R6B.split("## 4.")[1]
    and scripts_em_todas,
    f"item 6: 'testam a pasta do auditor, que está no git, com os .txt e os scripts do auditor' confere — tipos versionados por pasta: {tipos}")
reg("R6.01.02", "em seis rodadas" in R6B and "rodada 6: a frase que a rodada 5 mandou corrigir" in R6B and "com seis rodadas do auditor" in R6B,
    "INTRO e PEND: 'seis rodadas' e a linha da rodada 6 (só a frase e a reprodução) conferem")
par = R6B.split("**O que a rodada 5 corrigiu:**")[1].split("\n")[0]
reg("R6.01.03", "a R5.01.05" in par and "por causa dos `.txt`" in par and "(`.py` e `.R`)" in par and "A rodada 6 conferiu só essa frase e a reprodução" in par,
    "INDEP, 'O que a rodada 5 corrigiu': cita a minha única falha (R5.01.05) e a frase antiga; '(.py e .R)' vale para o conjunto das pastas (a etapa5 tem só .py, "
    "além dos .txt); 'a rodada 6 conferiu só essa frase e a reprodução' confere (esta rodada também conferiu estado e triagem, como pedido)")
dg = [l for l in difflib.unified_diff(G6B_5.splitlines(), G6B.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
dg_sem_saida = [l for l in dg if "write_text(out)" not in l]
reg("R6.01.04", "as rodadas 5 e 6 conferiram só o texto" in G6B and '"R6": "Rodada 6: frase corrigida depois da rodada 5"' in G6B and len(dg_sem_saida) == 5,
    f"gerador: 'as rodadas 5 e 6 conferiram só o texto' e NOMES com R6 conferem; fora a linha de saída da minha cópia, a diff contra o gerador da rodada 5 tem "
    f"{len(dg_sem_saida)} linhas ± (NOMES: 1 linha sai, 2 entram; frase da seção 2: 1 sai, 1 entra)")

# ============================================ R6.02 reprodução e diff
rep = (AQUI / "RESUMO_ETAPA7C6b_reproduzido_r6_v1_20261010.md").read_bytes()
cop = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor_r6.py")
dd = [l for l in difflib.unified_diff(G6B.splitlines(), cop.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
reg("R6.02.01", len(dd) == 2 and rep == (PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md").read_bytes() and md5(rep) == "daea1117b7280ba63a92ff44beaa24f8",
    f"cópia do gerador atual (10:09:07) difere só na saída; rodada em 13/10 10:11:07, ANTES das linhas R6, com o CSV de 199 linhas (MD5 {MD5_R5}, o citado): "
    f"saída idêntica byte a byte ao RESUMO do disco (MD5 {md5(rep)}, o citado). O Logger acrescentou 1 linha ao log da etapa7c6")
mud = [l for l in difflib.unified_diff(R6B_5.splitlines(), R6B.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
esperadas = r"seis rodadas|cinco rodadas|rodada 5: o texto|rodada 6: a frase|rodadas 5 e 6 conferiram|a rodada 5 conferiu só o texto|O que a rodada 5 corrigiu|" \
            r"^\+$|com os `\.txt` e os scripts do auditor|por causa dos `\.txt`. Num clone|^\+\| R5\. Rodada 5|^\+\| R5\.01\.05 "
fora = [l for l in mud if not re.search(esperadas, l)]
reg("R6.02.02", not fora,
    f"diff contra o RESUMO da rodada 5 ({len(mud)} linhas ±): só as mudanças listadas (INTRO, INDEP com 'rodadas 5 e 6' e 'O que a rodada 5 corrigiu', item 6, "
    f"PEND) e as tabelas geradas do meu CSV (linha R5 no quadro por bloco, falha R5.01.05, total 178/199); outras: {fora or 'nenhuma'}")

# ============================================ R6.03 estado e triagem
st = git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()
mod = sorted(l[3:] for l in st if not l.startswith("??"))
nao = sorted(l[3:] for l in st if l.startswith("??") and not l[3:].startswith(("docs/referencias/", "audit_independente/etapa7c6_final/")))
n_ref = sum(1 for l in st if l.startswith("?? docs/referencias/"))
esperado = {"outputs/RESUMO_ETAPA7C6b_v1_20261010.md", "outputs/manuscrito/_resumo7c6b_texto_v1_20261010.md", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv",
            "scripts/etapa7c6_02_audita_final.py", "scripts/resumos/etapa7c6b_01_resumo.py"}
pac = ["outputs/manuscrito/tabelas", "outputs/manuscrito/suplementar", "outputs/manuscrito/figuras", "Submissao",
       "outputs/manuscrito/numeros_chave_v11_20261009.json", "outputs/manuscrito/numeros_chave_v11_20261009.md", "outputs/manuscrito/checa_7b_v11_20261009.csv",
       "outputs/manuscrito/MANIFEST.md", "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "outputs/manuscrito/_arquivo_v10"]
dq = subprocess.run(["git", "-C", str(PROJ), "--no-optional-locks", "diff", "--quiet", HEAD, "--", *pac]).returncode
extra = git("ls-files", "-o", "--exclude-standard", *pac).split()
inalt = {p: md5((PROJ / p).read_bytes()) for p in ("scripts/etapa7c6_02_audita_final.py", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv",
                                                     "scripts/resumos/LEIAME.md", "docs/referencias/ATRIBUICAO.txt")}
reg("R6.03.01", mod == ["docs/referencias/ATRIBUICAO.txt", "scripts/resumos/LEIAME.md"] and set(nao) == esperado and n_ref == 93 and dq == 0 and not extra
    and git("rev-parse", "--short", "HEAD").strip() == HEAD and len(git("reflog").splitlines()) == 27
    and inalt["scripts/etapa7c6_02_audita_final.py"] == "31e926990048fa4dd4134dbe0f9899f9",
    f"HEAD = {HEAD}, reflog com 27 entradas; rastreados modificados: {mod}; não rastreados novos: os mesmos 5; docs/referencias/: {n_ref}; pacote, números-chave, "
    f"checa, MANIFEST, disponibilidade, legendas, _arquivo_v10 e Submissao/ iguais a {HEAD}: {dq == 0}; nada novo nessas pastas: {not extra}. Desde a rodada 5 "
    f"mudaram só o texto (10:09:07), o gerador (10:09:07), o RESUMO (10:09:08) e o log; a autoauditoria tem o mesmo MD5 da rodada 5 (31e92699…), e o CSV "
    f"dela, o LEIAME e o ATRIBUICAO não mudaram (mtimes de 13/10 08:52:21, 08:59:32 e 10/10 11:22:44)")
cand = [l[3:] for l in st if not l[3:].startswith("docs/referencias/") or l[3:] == "docs/referencias/ATRIBUICAO.txt"]
cand = [p for p in cand if subprocess.run(["git", "-C", str(PROJ), "check-ignore", "-q", p]).returncode != 0]
PAD = {"data_1900_2024": r"(?<!\d)(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/(19\d\d|20[01]\d|202[0-4])(?!\d)|(?<!\d)(19\d\d|20[01]\d|202[0-4])-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(?!\d)",
       "cns15": r"(?<![\d.,])[12789]\d{14}(?![\d.,])", "cpf": r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)",
       "linha_de_log": r"^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[[^\]]+\] .*\d"}
IDC = re.compile(r"\b(DTNASC|HORANASC|NUMERODN|NUMERODO|CODESTAB|CNES|DTOBITO|DTNASCMAE|CPF|CNS)\b")
ach, cols = {}, {}
for p in cand:
    tx = (PROJ / p).read_text(encoding="utf-8", errors="replace")
    h = {k: len(re.findall(v, tx, re.M)) for k, v in PAD.items() if re.findall(v, tx, re.M)}
    if h:
        ach[p] = h
    if p.endswith(".csv"):
        cols[p] = next(csv.reader(io.StringIO(tx)))
susp = {p: [c for c in v if IDC.search(c)] for p, v in cols.items() if any(IDC.search(c) for c in v)}
reg("R6.03.02", not ach and not susp,
    f"triagem: {len(cand)} arquivos novos/modificados fora do .gitignore ({sum(p.startswith('audit_independente/') for p in cand)} desta pasta). Datas 1900–2024, "
    f"CNS, CPF, linhas de log: {ach or 'nenhum'}; CSV não ignorado: {list(cols)}, sem nome de identificador")

# ============================================ gravação: preserva as rodadas 1–5 byte a byte
bruto = CSV_.read_bytes()
i = bruto.find(b"\nR6.")
base = bruto if i < 0 else bruto[:i + 1]
assert md5(base) == MD5_R5, "a parte das rodadas 1–5 do CSV mudou"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["verificacao", "ok", "detalhe"], lineterminator="\r\n")
ordem = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
w.writerows(sorted(ROWS, key=lambda r: ordem(r["verificacao"])))
CSV_.write_bytes(base + buf.getvalue().encode("utf-8"))
print(f"rodada 6: {sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK; CSV com 199 + {len(ROWS)} linhas")
