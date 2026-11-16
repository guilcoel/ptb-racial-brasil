"""
Auditoria independente final da 7c.6 — RODADA 4 (2026-10-13). Acrescenta linhas R4.* ao comparacao_7c6_final_v1_20261010.csv sem
tocar nas 168 linhas das rodadas 1–3 (confere o MD5 dessa parte antes de gravar). Seed 42 (não há sorteio nesta rodada).

Passos feitos ANTES deste script (evidência nesta pasta):
- R4.04: etapa7c6b_01_resumo_copia_saida_auditor_r4.py rodada em 2026-10-13 09:37:43 com o CSV desta pasta ainda com 168 linhas
  (MD5 7ffca56b792844ba10184b9001ce3b19) → RESUMO_ETAPA7C6b_reproduzido_r4_v1_20261010.md.
- R4.01: etapa7c6_02_audita_final_copia_auditor_r4.py (desvios: PROJ fixo, status sem reescrever o índice, saída e tmp do L7.01 nesta
  pasta, memória fora do projeto não lida, auto-exclusão e auto-leitura pelo arquivo original) → audita_final_reexecucao_auditor_r4_v1_20261010.csv;
  exit 0.
- R4.01.01: teste sintético do K1.01 num repositório git descartável criado e apagado nesta pasta (_teste_k101_git_r4).
Rodar: PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_R4_v1_20261010.py
"""
import csv
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
MD5_R3 = "7ffca56b792844ba10184b9001ce3b19"
ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:200]}", flush=True)


ler = lambda p: Path(p).read_text(encoding="utf-8")
md5 = lambda b: hashlib.md5(b).hexdigest()
lerc = lambda p: {r["verificacao"].split()[0]: r for r in csv.DictReader(io.StringIO(ler(p)))}
R6B = ler(PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md")
AUTO = ler(PROJ / "scripts/etapa7c6_02_audita_final.py")
LEIA = ler(PROJ / "scripts/resumos/LEIAME.md").splitlines()
NOVO = lerc(MS / "audita_final_7c6_v1_20261010.csv")
MEU4 = lerc(AQUI / "audita_final_reexecucao_auditor_r4_v1_20261010.csv")
MEU3 = lerc(AQUI / "audita_final_reexecucao_auditor_r3_v1_20261010.csv")

# ============================================ R4.01 autoauditoria
k1 = re.search(r"depois = .*?\n", AUTO).group(0)
reg("R4.01.01", '"--no-renames"' in k1,
    "K1.01 agora usa 'git diff --name-only --no-renames'. Teste sintético repetido (repositório descartável nesta pasta, git 2.39.5, apagado depois), com a "
    "mesma função da7c6b: mover outputs/manuscrito/tabelas/tab01.csv para audit_independente/etapa7c6_final/ → sem a opção a lista é só o destino e o K1.01 "
    "dá True; com --no-renames a lista traz destino e origem e o K1.01 dá False (também com um commit seguinte que só muda o ATRIBUICAO). Contraprova: um commit "
    "que só muda arquivos da 7c.6b (ATRIBUICAO e um .md na pasta do auditor) continua aceito (True)")
m6 = NOVO["M6.01"]["detalhe"]
lido = dict(re.findall(r"'([\w/]+\.py)': '(sem condição|com if exists\(\))'", m6.split("leitores {")[1].split("}")[0]))
VERDADE = {  # leitura conferida linha a linha pelo auditor (rodadas 1 e 4)
    "etapa1_08_auditoria_propria.py": ("sem condição", "L97, L118, L131 no nível de topo"),
    "etapa2_06_auditoria_propria.py": ("com if exists()", "L96 'if AUD.exists():' (pasta etapa2)"),
    "etapa3_06_auditoria_propria.py": ("com if exists()", "L108 'if AUD.exists():' (pasta etapa3)"),
    "etapa4b_05_auditoria.py": ("com if exists()", "L79 (pasta etapa4b)"),
    "etapa5_04_auditoria.py": ("com if exists()", "L90 (pasta etapa5)"),
    "etapa6_08_auditoria.py": ("com if exists()", "L100 (pasta etapa6)"),
    "etapa6b_03_auditoria.py": ("com if exists()", "L78 'if AUD.exists() and any(AUD.glob(\"comparacao*.csv\"))' (o próprio CSV)"),
    "etapa7b_checa.py": ("com if exists()", "8 × 'if audX.exists():' (o próprio CSV)"),
    "etapa7c6_02_audita_final.py": ("sem condição", "L107 comparacao_7c6"),
    "resumos/etapa7c6_01_resumo.py": ("sem condição", "L26 comparacao_7c6"),
    "resumos/etapa7c6b_01_resumo.py": ("sem condição", "L35 comparacao_7c6_final"),
}
igual = lido == {k: v[0] for k, v in VERDADE.items()}
rast = {k: len(git("ls-files", f"audit_independente/{k}").split()) for k in ("etapa2", "etapa3", "etapa4b", "etapa5", "etapa6", "etapa6b")}
reg("R4.01.02", igual,
    f"M6.01, critério novo: os 11 leitores e a classificação = a minha conferência linha a linha ({igual}); nenhum de fora — os outros scripts que citam "
    f"audit_independente (etapa4_07, resumos/etapa7c5_01, resumos/etapa7c5b_01) não leem CSV dele, e nenhum .R de scripts/ cita a pasta. etapa1_08 'sem condição' "
    f"(L97, L118, L131 no topo) e etapa2_06/etapa3_06 'com if exists()' (L96, L108) estão certos como descrição do código. RESSALVA: nas auditorias próprias das "
    f"Etapas 2, 3, 4b, 5 e 6 o exists() testa a PASTA audit_independente/etapaN, que está no git ({rast} arquivos rastreados); num clone ela existe e a leitura "
    f"do CSV falha do mesmo jeito. Só o checa e o etapa6b_03 testam o próprio CSV e pulam de fato")
m4, m5 = NOVO["M4.01"]["detalhe"], NOVO["M5.01"]["detalhe"]
cinco = ["censo2022/sidra_9605_n6_2022.json", "intergrowth21_bw_centis_oficial.csv", "territorio_dez24/rl_municip_regsaud.csv",
         "territorio_dez24/tb_municip.csv", "territorio_dez24/tb_regsaud.csv"]
cita = sorted(str(p.relative_to(PROJ)) for p in (PROJ / "scripts").rglob("*") if p.suffix in (".py", ".R") and not p.name.startswith("._")
              and "evans2024" in ler(p))
reg("R4.01.03", f"lidos pelos outros scripts: {cinco}" in m4 and "lidos por esta autoauditoria: ['evans2024_maihda_tutorial_PMC11059336.txt', "
    "'territorio_dez24/rl_municip_regsaud.csv']" in m4 and "outros scripts que citam: nenhum" in m5 and cita == ["scripts/etapa7c6_02_audita_final.py"],
    f"M4.01: os outros scripts leem os mesmos 5 (o LEITURA ampliado com read_text, read_bytes, fread, readLines, fromJSON e readRDS não acrescenta nenhum "
    f"não rastreado) e a autoauditoria lê o .txt do Evans (L432) e o rl_municip_regsaud.csv (M8.01): confere. M5.01: nenhum outro script cita o .txt; o único "
    f"arquivo de scripts/ com 'evans2024' é {cita}: confere; o rótulo diz que a autoauditoria o lê")
ok_dif = [k for k in NOVO if NOVO[k]["ok"] != MEU3[k]["ok"] and k != "L9.01"]
det_dif = sorted(k for k in NOVO if (NOVO[k]["detalhe"], NOVO[k]["verificacao"]) != (MEU3[k]["detalhe"], MEU3[k]["verificacao"]))
rod = [k for k in NOVO if (NOVO[k]["ok"], NOVO[k]["detalhe"]) != (MEU4[k]["ok"], MEU4[k]["detalhe"])]
reg("R4.01.04", list(NOVO) == list(MEU4) == list(MEU3) and not ok_dif and set(rod) <= {"L7.01", "L9.01"} and MEU4["L7.01"]["ok"] == "True"
    and sum(r["ok"] == "True" for r in NOVO.values()) == 50,
    f"a cópia roda até o fim (exit 0), {sum(r['ok'] == 'True' for r in MEU4.values())}/57; difere do CSV do autor só em {rod} (caminho temporário; memória fora do "
    f"projeto não lida pelo auditor). CSV do autor (50/57) × rodada 3 (minha reexecução de 13/10 08:37, que igualava o do autor): mesmos 57 ids, ok idênticos "
    f"item a item (fora o L9.01, que é True no autor nas duas e False só nas minhas cópias); detalhes ou rótulos mudaram em {det_dif} — o L9.01 por causa da minha "
    f"cópia; o K1.01 mudou só no código")

# ============================================ R4.02 LEIAME
res = sorted(p.name for p in (PROJ / "scripts/resumos").glob("*.py"))
ns = [l.split("\t") for l in git("diff", "--name-status", "-M", "8314417", HEAD).splitlines()]
movidos = sorted(x[2].split("/")[-1] for x in ns if x[0] == "R100" and x[2].startswith("scripts/resumos/"))
criados = sorted(set(res) - set(movidos))
usa_bv = {g: "B.V" in ler(PROJ / "scripts/resumos" / g) for g in res}
fixo = {g: bool(re.search(r'^V\s*=\s*"v\d+_', ler(PROJ / "scripts/resumos" / g), re.M)) for g in res}
ate7c5 = [g for g in res if g in movidos and g != "etapa7c5b_01_resumo.py"]
le6b = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
reg("R4.02.01", len(movidos) == 10 and criados == ["etapa7c6_01_resumo.py", "etapa7c6b_01_resumo.py"] and len(ate7c5) == 9 and all(usa_bv[g] for g in ate7c5)
    and fixo["etapa7c5b_01_resumo.py"] and fixo["etapa7c6_01_resumo.py"] and "etapa7b_lib" not in le6b and "numeros_chave" not in le6b,
    f"linhas 3, 5 e 6 conferem: {len(movidos)} geradores R100 em {HEAD} e 2 criados ({criados}); os 9 até o etapa7c5_01 usam B.V; o etapa7c5b_01 fixa v10 e o "
    f"etapa7c6_01 fixa v11; o etapa7c6b_01 não importa a etapa7b_lib nem lê arquivo do pacote (lê o CSV da autoauditoria, o deste auditor e o texto). Na linha 5, "
    f"'importam módulos de scripts/ (etapa7b_lib, etapa0_lib)': o etapa7c6b_01 importa só o etapa0_lib")
l9 = [l for l in LEIA if "Isso só vale enquanto os `._*` ficarem onde estão" in l]
l11 = [l for l in LEIA if "também não roda num clone limpo" in l]
le_auto = all(s in AUTO for s in ["tab_e2_03_mesprenat_completude", 'audit_independente/etapa7c6/comparacao_7c6_v1_20261009.csv"',
                                   'evans2024_maihda_tutorial_PMC11059336.txt").read_text', 'territorio_dez24/rl_municip_regsaud.csv"'])
l44 = re.search(r'ok\("L4\.04".*?len\(fora\) == 36 and tab_p == dict\(porp\)', AUTO, re.S) is not None
reg("R4.02.02", bool(l9) and bool(l11) and le_auto and l44,
    "linhas 9–11 conferem com o código: o L4.04 exige len(fora) == 36 e a tabela por pasta igual ao disco, e o L7.01 regenera o RESUMO 7c.6 com os ._* do "
    "disco, então os dois falham se os ._* forem movidos; a autoauditoria lê outputs/tables/ (ex.: tab_e2_03_mesprenat_completude), o comparacao_7c6 sem "
    "condição, o .txt do Evans e o rl_municip_regsaud.csv. A linha 12 (checa, L526) não mudou e continua certa. Detalhe: a autoauditoria lê também a memória em "
    "~/.claude (L9.01), mas só como 'se existir'; isso não a impede de rodar")

# ============================================ R4.03 texto/RESUMO 7c.6b
sec = lambda a, b: R6B.split(a)[1].split(b)[0]
reg("R4.03.01", "em quatro rodadas" in R6B and "rodada 4: o que a rodada 3 mandou corrigir" in R6B and "com quatro rodadas do auditor" in R6B
    and "a autoauditoria só reproduz o RESUMO 7c.6 enquanto os `._*` ficarem onde estão" in R6B,
    "INTRO e PEND: quatro rodadas; item do LEIAME (versão fixa, leitura do disco, ._*, checa) = o LEIAME atual")
auto = sec("**Corrigida depois da rodada 3**", "## 2.")
reg("R4.03.02", all(s in auto for s in ["50/57", "--no-renames", "sem condição ou só com `if exists()`", "o `.txt` do Evans e o `rl_municip_regsaud.csv`",
                                        "os mesmos 5 arquivos", "L4.04 e o L7.01"]),
    "AUTO, 'Corrigida depois da rodada 3': 50/57 com as mesmas 7 falhas; K1.01 com --no-renames; M6.01 com o critério novo; M4.01/M5.01 com o que a autoauditoria "
    "lê; LEITURA ampliado sem mudar os 5 dos outros scripts; docstring com o clone limpo e os ._* — tudo confere (R4.01). 'Mudaram só o K1.01, o M4.01, o M5.01 "
    "e o M6.01' vale para o código; no CSV mudaram detalhes de M4.01, M5.01, M6.01 e o caminho temporário do L7.01")
tab3 = [l for l in sec("**O que a rodada 3 corrigiu**", "Também acertei as ressalvas da rodada 3").splitlines() if l.startswith("| R3.")]
ids3 = [l.split("|")[1].strip() for l in tab3]
reg("R4.03.03", ids3 == ["R3.01.03", "R3.01.04", "R3.02.02", "R3.03.11", "R3.03.12", "R3.03.13"]
    and "o L1.04 da autoauditoria confere só o texto" in R6B and "a minha conferência da licença do Evans no PMC (2026-10-12)" in R6B
    and "O da 7c.6 também fixa a versão (v11)" in R6B and "Nas rodadas 2 e 3, com autorização" in R6B,
    f"INDEP: a tabela 'O que a rodada 3 corrigiu' tem as minhas 6 falhas ({ids3}); L1.17 reescrita certa (versão fixa v11); limitação do L1.04 registrada; a "
    f"conferência do autor no PMC entre os não verificáveis; leitura autorizada da autoauditoria nas rodadas 2 e 3 (a rodada 4 também a leu). Confere")
e4 = [l for l in R6B.splitlines() if l.startswith("| Abertura")][0]
reg("R4.03.04", all(s in e4 for s in ["Em 4 mudou o texto", "Nas legendas e no título do docx, só o rótulo de versão",
                                      "No MANIFEST e no `data_code_availability`, também a etapa e o commit de referência",
                                      "os MD5 dos arquivos alterados e a nota da S8"]),
    "nova linha 4 da errata confere com o diff (rótulos normalizados): legendas e título do docx só com o rótulo; data_code_availability com etapa (linha 1) e "
    "commit de referência (linha 30); MANIFEST com etapa (linha 1), commit (linha 3), 13 linhas só de MD5 e a nota da S8 nas 2 linhas da S8 (CSV só a nota; PDF "
    "nota e MD5); os outros 8 arquivos só em metadados")
reg("R4.03.05", "nenhuma checagem do `checa` depende deles" in R6B and "a autoauditoria confere essa contagem no disco (L4.04) e reproduz o RESUMO 7c.6 com ela (L7.01)" in R6B,
    "item 1: o checa não depende dos ._* (só confere Submissao/), a autoauditoria os usa no L4.04 e no L7.01: confere")
reg("R4.03.06", "fora a autoauditoria, os scripts leem só 5" in R6B and "a autoauditoria lê ainda o `.txt` do Evans (M5.01) e o `rl_municip_regsaud.csv` (M8.01)" in R6B
    and "nenhum script de análise lê nem cita o `.txt`. Só a autoauditoria o lê" in R6B,
    "itens 4 e 5: os 5 dos outros scripts; a autoauditoria lê o Evans (L432) e o rl_municip_regsaud; nenhum script de análise lê nem cita o .txt: confere")
ig = [PROJ / p for p in git("ls-files", "-o", "-i", "--exclude-standard", "audit_independente").split() if p.endswith(".csv") and "etapa7c6_final" not in p]
tabs_ = {}
for f in ["etapa1_08_auditoria_propria", "etapa2_06_auditoria_propria", "etapa3_06_auditoria_propria", "etapa4_07_auditoria_sintese", "etapa4b_05_auditoria",
          "etapa5_04_auditoria", "etapa6_08_auditoria", "etapa6b_03_auditoria"]:
    tabs_[f] = bool(re.search(r"L\.TAB|E\.L\.TAB", ler(PROJ / f"scripts/{f}.py")))
chk_tab = "B.TB /" in ler(PROJ / "scripts/etapa7b_checa.py")
reg("R4.03.07", len(ig) == 112 and round(sum(p.stat().st_size for p in ig) / 1e6, 1) == 21.6 and all(tabs_.values()) and chk_tab,
    f"item 6: {len(ig)} CSVs ignorados fora de etapa7c6_final, {sum(p.stat().st_size for p in ig):,} bytes (21.6 MB): confere. Leitores (sem condição: etapa1_08, "
    f"geradores 7c.6 e 7c.6b, autoauditoria; com if exists(): checa e auditorias das Etapas 2, 3, 4b, 5, 6 e 6b) = R4.01.02. 'O checa, a autoauditoria e as "
    f"auditorias próprias das Etapas 1–6 também leem outputs/tables/ ou data/': confere (todas usam L.TAB/E.L.TAB; o checa usa B.TB). RESSALVA: 'num clone limpo, "
    f"os quatro que leem sem condição param na falta do CSV do auditor' é verdade, mas sugere que os outros pulam; nas Etapas 2, 3, 4b, 5 e 6 o exists() testa a "
    f"pasta, que está no git, e eles também parariam (R4.01.02). Sem efeito prático hoje, porque todos leem outputs/tables/ antes")
d2 = sec("**Efeito colateral:**", "**Exige:**")
reg("R4.03.08", "falharia no L4.04" in d2 and "no L7.01" in d2 and "CSV da autoauditoria commitado nesta etapa" in d2,
    "decisão 2, efeito colateral: os geradores da 7c.5 e da 7c.6 mostrariam 0; a autoauditoria falharia no L4.04 e no L7.01; o registro são os RESUMOs e o CSV da "
    "autoauditoria commitados — confere com o código (R4.02.02). O L4.05 também mudaria de detalhe (já é False)")
d4 = sec("**Evans 2024:** não versionar", "5. **GitHub")
reg("R4.03.09", False,
    "decisão 4: o Evans (nenhum script de análise o lê; a autoauditoria o lê, mas já não roda num clone limpo) confere. Incompleto: 'O da 7c.6 roda, mas não "
    "reproduz o RESUMO byte a byte, porque conta os ._* do disco'. Num clone limpo depois do commit da 7c.6b, a saída também difere pelo ATRIBUICAO corrigido "
    "(seção 2) e pela lista de scripts/resumos, que terá 12 .py (seção 5), como diz a decisão 7. Menor: a conclusão (não reproduz) está certa")
reg("R4.03.10", "mas só enquanto os `._*` ficarem onde estão (decisão 2)" in R6B,
    "decisão 7: a reprodução pela autoauditoria com ATRIBUICAO e lista fixados vale só enquanto os ._* ficarem onde estão: confere (L7.01 True nas minhas cópias "
    "das rodadas 3 e 4)")

# ============================================ R4.04 reprodução do RESUMO 7c.6b
g6b = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
cop = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor_r4.py")
dd = [l for l in __import__("difflib").unified_diff(g6b.splitlines(), cop.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
rep = (AQUI / "RESUMO_ETAPA7C6b_reproduzido_r4_v1_20261010.md").read_bytes()
reg("R4.04.01", len(dd) == 2 and rep == (PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md").read_bytes(),
    f"cópia do gerador (inalterado desde 12/10 17:18) difere só na saída; rodada em 13/10 09:37:43, ANTES das linhas R4, com o CSV de 168 linhas (MD5 "
    f"{MD5_R3}): saída idêntica byte a byte ao RESUMO do disco (MD5 {md5(rep)}). Nota: o MD5 12970a42… citado na mensagem é o do RESUMO, não o do CSV")

# ============================================ R4.05 triagem
st = git("--no-optional-locks", "status", "--porcelain", "--untracked-files=all").splitlines()
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
reg("R4.05.01", not ach and not susp,
    f"{len(cand)} arquivos novos/modificados fora do .gitignore ({sum(p.startswith('audit_independente/') for p in cand)} desta pasta: .py, .md, .json; CSVs "
    f"daqui ignorados), inclusive LEIAME, ATRIBUICAO, autoauditoria, gerador, texto e RESUMO 7c.6b. Datas 1900–2024, CNS, CPF, linhas de log: {ach or 'nenhum'}. "
    f"CSV não ignorado: {list(cols)} ({list(cols.values())}), sem nome de identificador")

# ============================================ R4.06 nada mais mudou
mod = sorted(l[3:] for l in st if not l.startswith("??"))
nao = sorted(l[3:] for l in st if l.startswith("??") and not l[3:].startswith(("docs/referencias/", "audit_independente/etapa7c6_final/")))
n_ref = sum(1 for l in st if l.startswith("?? docs/referencias/"))
esperado = {"outputs/RESUMO_ETAPA7C6b_v1_20261010.md", "outputs/manuscrito/_resumo7c6b_texto_v1_20261010.md", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv",
            "scripts/etapa7c6_02_audita_final.py", "scripts/resumos/etapa7c6b_01_resumo.py"}
reg("R4.06.01", mod == ["docs/referencias/ATRIBUICAO.txt", "scripts/resumos/LEIAME.md"] and set(nao) == esperado and n_ref == 93
    and git("rev-parse", "--short", "HEAD").strip() == HEAD and len(git("reflog").splitlines()) == 27,
    f"HEAD = {HEAD}, reflog com 27 entradas; rastreados modificados: {mod}; não rastreados novos: os mesmos 5; docs/referencias/: {n_ref}. Alterados desde o fim "
    f"da rodada 3 (fora desta pasta): autoauditoria (08:52:02), seu CSV (08:52:21), texto (08:59:23), LEIAME (08:59:32), RESUMO (08:59:33) e o log da etapa7c6 "
    f"(minhas linhas: 09:37:43 e a do L7.01 da cópia). ATRIBUICAO e gerador sem mudança desde 10/10 e 12/10")
pac = ["outputs/manuscrito/tabelas", "outputs/manuscrito/suplementar", "outputs/manuscrito/figuras", "Submissao",
       "outputs/manuscrito/numeros_chave_v11_20261009.json", "outputs/manuscrito/numeros_chave_v11_20261009.md", "outputs/manuscrito/checa_7b_v11_20261009.csv",
       "outputs/manuscrito/MANIFEST.md", "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "outputs/manuscrito/_arquivo_v10"]
dq = subprocess.run(["git", "-C", str(PROJ), "--no-optional-locks", "diff", "--quiet", HEAD, "--", *pac]).returncode
extra = git("ls-files", "-o", "--exclude-standard", *pac).split()
reg("R4.06.02", dq == 0 and not extra,
    f"pacote, números-chave, checa, MANIFEST, disponibilidade, legendas, _arquivo_v10 e Submissao/ iguais a {HEAD}: {dq == 0}; não rastreados nessas pastas: "
    f"{extra or 'nenhum'}")

# ============================================ gravação: preserva as rodadas 1–3 byte a byte
bruto = CSV_.read_bytes()
i = bruto.find(b"\nR4.")
base = bruto if i < 0 else bruto[:i + 1]
assert md5(base) == MD5_R3, "a parte das rodadas 1–3 do CSV mudou"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["verificacao", "ok", "detalhe"], lineterminator="\r\n")
ordem = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
w.writerows(sorted(ROWS, key=lambda r: ordem(r["verificacao"])))
CSV_.write_bytes(base + buf.getvalue().encode("utf-8"))
print(f"rodada 4: {sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK; CSV com 168 + {len(ROWS)} linhas")
