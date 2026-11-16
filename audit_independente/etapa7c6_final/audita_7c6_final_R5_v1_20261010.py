"""
Auditoria independente final da 7c.6 — RODADA 5 (2026-10-13, curta: só o texto corrigido depois da rodada 4). Acrescenta linhas R5.*
ao comparacao_7c6_final_v1_20261010.csv sem tocar nas 188 linhas das rodadas 1–4 (confere o MD5 dessa parte antes de gravar).
A autoauditoria não foi rodada de novo (o código não mudou desde a rodada 4; R5.03.01 confere isso).

Passo feito ANTES deste script: etapa7c6b_01_resumo_copia_saida_auditor_r5.py rodada em 2026-10-13 10:03:27 com o CSV desta pasta
ainda com 188 linhas (MD5 7d66d3e4e843dfcc99963d28c8e1b156) → RESUMO_ETAPA7C6b_reproduzido_r5_v1_20261010.md.
Rodar: PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_R5_v1_20261010.py
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
from audita_7c6_final_lib_v1_20261010 import HEAD, MS, PROJ, git  # noqa: E402

CSV_ = AQUI / "comparacao_7c6_final_v1_20261010.csv"
MD5_R4 = "7d66d3e4e843dfcc99963d28c8e1b156"
ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:200]}", flush=True)


ler = lambda p: Path(p).read_text(encoding="utf-8")
md5 = lambda b: hashlib.md5(b).hexdigest()
lerc = lambda p: {r["verificacao"].split()[0]: r for r in csv.DictReader(io.StringIO(ler(p)))}
R6B = ler(PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md")
R6B_4 = ler(AQUI / "RESUMO_ETAPA7C6b_reproduzido_r4_v1_20261010.md")   # = RESUMO da rodada 4 (R4.04.01)
G6B = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
AUTO_CSV = lerc(MS / "audita_final_7c6_v1_20261010.csv")
R3CP = lerc(AQUI / "audita_final_reexecucao_auditor_r3_v1_20261010.csv")
mud = [l for l in difflib.unified_diff(R6B_4.splitlines(), R6B.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]

# ============================================ R5.01 frases novas ou alteradas
reg("R5.01.01", "em cinco rodadas" in R6B and "rodada 5: o texto que a rodada 4 mandou corrigir" in R6B and "com cinco rodadas do auditor" in R6B,
    "INTRO e PEND: 'cinco rodadas' e a linha da rodada 5 (só texto) — confere com o que a rodada 5 faz (texto e reprodução, sem rodar a autoauditoria)")
rot = [k for k in AUTO_CSV if AUTO_CSV[k]["verificacao"] != R3CP[k]["verificacao"]]
det = [k for k in AUTO_CSV if AUTO_CSV[k]["detalhe"] != R3CP[k]["detalhe"] and k != "L9.01"]
frase = "No código, mudaram o K1.01, o M4.01, o M5.01 e o M6.01; no CSV, só os detalhes do M4.01, do M5.01 e do M6.01, os rótulos do M4.01 e do M5.01 e o caminho temporário do L7.01."
reg("R5.01.02", frase in R6B and rot == ["M4.01", "M5.01"] and sorted(det) == ["L7.01", "M4.01", "M5.01", "M6.01"],
    f"AUTO: '{frase[:80]}…' confere — CSV da autoauditoria (13/10 08:52) × o de 12/10 (= a minha reexecução da rodada 3, fora o L9.01, que nela é False só "
    f"porque o auditor não lê a memória): rótulos mudaram em {rot}; detalhes em {sorted(det)}; no código, K1.01 (--no-renames), M4.01/M5.01 (LEITURA ampliado, "
    f"o que a autoauditoria lê) e M6.01 (critério de leitores), além da docstring (diff da rodada 4)")
reg("R5.01.03", "nas rodadas 2 a 4, a autoauditoria foi um dos objetos auditados, e a rodada 5 conferiu só o texto" in G6B
    and "Nas rodadas 2 a 4, com autorização, ele leu e rodou uma cópia da autoauditoria" in R6B and '"R4": ' in G6B and '"R5": ' in G6B,
    "INDEP e gerador: 'rodadas 2 a 4' (li e rodei cópias da autoauditoria nas rodadas 2, 3 e 4; nesta não) e NOMES com R4 e R5 (o gerador agrupa por "
    "'^(R\\d|[A-Z])'): confere")
t4 = R6B.split("**O que a rodada 4 corrigiu**")[1].split("**Não verificáveis")[0]
lin4 = [l for l in t4.splitlines() if l.startswith("| ") and not l.startswith("| Item")]
reg("R5.01.04", len(lin4) == 3 and lin4[0].startswith("| R4.03.09 |") and "testam o próprio CSV" in lin4[1] and "separado o que mudou no código e no CSV" in lin4[2],
    "tabela 'O que a rodada 4 corrigiu': a minha única falha (R4.03.09, causa incompleta na decisão 4) e as 2 ressalvas (o if exists() das auditorias 2–6 e "
    "'código × CSV' do AUTO) — confere com a rodada 4. A 3ª ressalva da rodada 4 (seção 2 dizer 'rodadas 2 a 4') foi corrigida no gerador, fora da tabela")
it6 = R6B.split("6. **CSVs das auditorias:**")[1].split("7. **Denominador")[0]
tipos = {e: sorted({Path(p).suffix for p in git("ls-files", f"audit_independente/{e}").split()}) for e in ("etapa2", "etapa3", "etapa4b", "etapa5", "etapa6")}
reg("R5.01.05", False,
    f"item 6: 'o if exists() só protege o checa e o etapa6b_03, que testam o próprio CSV' confere (checa: 8 × if audX.exists(); 6b_03: any(AUD.glob('comparacao*.csv'))); "
    f"'As auditorias das Etapas 2, 3, 4b, 5 e 6 testam a pasta do auditor … Num clone, a condição é verdadeira e a leitura do CSV falha' confere; 'num clone limpo, "
    f"os geradores da 7c.6 e da 7c.6b param na falta do CSV do auditor' confere. IMPRECISO (menor): 'a pasta do auditor, que está no git por causa dos .txt' — "
    f"essas pastas têm também os scripts do auditor versionados: {tipos}. A pasta existiria num clone mesmo sem os .txt")
d4 = [l for l in R6B.splitlines() if "O da 7c.6 roda, mas não reproduz o RESUMO byte a byte" in l and l.lstrip().startswith("- Versionar")][0]
reg("R5.01.06", "a 7c.6b mudou o ATRIBUICAO e a lista de `scripts/resumos/`, e ele conta os `._*` do disco (decisão 7)" in d4,
    "decisão 4: a causa agora está completa (ATRIBUICAO corrigido, lista de scripts/resumos com 12 .py e ._* do disco), = R2.01.03, R3.01 e a decisão 7: confere")
outras = [l for l in mud if not re.search(r"cinco rodadas|rodada 5|rodadas 2 a 4|No código, mudaram|O que a rodada 4|R4\.03\.09|ressalva \||^\+\|:--|"
                                          r"^\+\| Item|^\+$|if exists\(\)|geradores da 7c\.6 e da 7c\.6b param|O da 7c\.6 roda|quatro rodadas|rodada 4: o que|"
                                          r"Corrigida depois da rodada 3|149/168|168/188|Nas rodadas 2 e 3|rodada 2 em diante|só com `if exists|quatro que leem|"
                                          r"^[-+]\| (L|R[2-5])[0-9.]+ |^[-+]\| R[2-5]\. Rodada", l)]
reg("R5.01.07", not outras,
    f"nenhuma outra mudança no RESUMO além das listadas pelo coordenador e das tabelas geradas a partir do meu CSV (linhas R4 e totais 168/188): "
    f"{outras or 'nenhuma'} ({len(mud)} linhas ± no diff contra o RESUMO da rodada 4)")

# ============================================ R5.02 reprodução
cop = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor_r5.py")
dd = [l for l in difflib.unified_diff(G6B.splitlines(), cop.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
rep = (AQUI / "RESUMO_ETAPA7C6b_reproduzido_r5_v1_20261010.md").read_bytes()
reg("R5.02.01", len(dd) == 2 and rep == (PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md").read_bytes() and md5(rep) == "2bf6ffcd268820376cfbd72fa1cc3a37",
    f"cópia do gerador atual (10:02:58) difere só na saída; rodada em 13/10 10:03:27, ANTES das linhas R5, com o CSV de 188 linhas (MD5 {MD5_R4}, o citado "
    f"pelo coordenador): saída idêntica byte a byte ao RESUMO do disco (MD5 {md5(rep)}, o citado). O Logger acrescentou 1 linha ao log da etapa7c6")

# ============================================ R5.03 estado e triagem
auto = ler(PROJ / "scripts/etapa7c6_02_audita_final.py")
subs = [('PROJ = Path(__file__).resolve().parents[1]', 'PROJ = Path("/Volumes/Forja/ptb-racial-brasil")  # AUDITOR: cópia fora de scripts/'),
        ('st = [l for l in git("status", "--porcelain", "--untracked-files=all").splitlines()]',
         'st = [l for l in git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()]  # AUDITOR: sem reescrever o índice'),
        ('tmp = Path(tempfile.mkdtemp()) / "RESUMO_reproduzido.md"',
         'tmp = PROJ / "audit_independente/etapa7c6_final/RESUMO_ETAPA7C6_reexec_autoaud_r4_v1_20261010.md"  # AUDITOR: saída desviada'),
        ('mem = Path.home() / ".claude/projects/-Users-guilherme/memory/ptb-racial-brasil-estado.md"',
         'mem = Path("/nao/lido/pelo/auditor")  # AUDITOR: arquivo fora do projeto, não lido'),
        ('out.to_csv(SAIDA, index=False)',
         'out.to_csv(PROJ / "audit_independente/etapa7c6_final/audita_final_reexecucao_auditor_r4_v1_20261010.csv", index=False)  # AUDITOR: saída desviada'),
        ('Path(__file__).read_text()', '(PROJ / "scripts/etapa7c6_02_audita_final.py").read_text()')]
for a, b in subs:
    auto = auto.replace(a, b)
auto = auto.replace('Path(__file__).name', '"etapa7c6_02_audita_final.py"')
igual_r4 = auto == ler(AQUI / "etapa7c6_02_audita_final_copia_auditor_r4.py")
reg("R5.03.01", igual_r4,
    f"o código da autoauditoria não mudou desde a rodada 4: aplicadas ao arquivo atual as mesmas trocas da minha cópia da rodada 4, o resultado é idêntico a ela "
    f"({igual_r4}); o CSV dela é o de 13/10 08:52:21")
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
reg("R5.03.02", mod == ["docs/referencias/ATRIBUICAO.txt", "scripts/resumos/LEIAME.md"] and set(nao) == esperado and n_ref == 93 and dq == 0 and not extra
    and git("rev-parse", "--short", "HEAD").strip() == HEAD and len(git("reflog").splitlines()) == 27,
    f"HEAD = {HEAD}, reflog com 27 entradas; rastreados modificados: {mod}; não rastreados novos: os mesmos 5; docs/referencias/: {n_ref}; pacote, números-chave, "
    f"checa, MANIFEST, disponibilidade, legendas, _arquivo_v10 e Submissao/ iguais a {HEAD}: {dq == 0}; nada novo nessas pastas: {not extra}. Mudaram desde a "
    f"rodada 4 (fora desta pasta): texto (10:02:50), gerador (10:02:58), RESUMO (10:02:59) e o log; ATRIBUICAO, LEIAME, autoauditoria e o CSV dela sem mudança")
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
reg("R5.03.03", not ach and not susp,
    f"triagem: {len(cand)} arquivos novos/modificados fora do .gitignore ({sum(p.startswith('audit_independente/') for p in cand)} desta pasta). Datas 1900–2024, "
    f"CNS, CPF, linhas de log: {ach or 'nenhum'}; CSV não ignorado: {list(cols)}, sem nome de identificador")

# ============================================ gravação: preserva as rodadas 1–4 byte a byte
bruto = CSV_.read_bytes()
i = bruto.find(b"\nR5.")
base = bruto if i < 0 else bruto[:i + 1]
assert md5(base) == MD5_R4, "a parte das rodadas 1–4 do CSV mudou"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["verificacao", "ok", "detalhe"], lineterminator="\r\n")
ordem = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
w.writerows(sorted(ROWS, key=lambda r: ordem(r["verificacao"])))
CSV_.write_bytes(base + buf.getvalue().encode("utf-8"))
print(f"rodada 5: {sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK; CSV com 188 + {len(ROWS)} linhas")
