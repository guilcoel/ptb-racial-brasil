"""
Auditoria independente final da 7c.6 — RODADA 3 (2026-10-13). Acrescenta linhas R3.* ao comparacao_7c6_final_v1_20261010.csv
sem tocar nas 142 linhas das rodadas 1 e 2 (confere o MD5 dessa parte antes de gravar).

Objetos: a autoauditoria refeita (scripts/etapa7c6_02_audita_final.py + outputs/manuscrito/audita_final_7c6_v1_20261010.csv),
o LEIAME de scripts/resumos/, o gerador e o texto do RESUMO 7c.6b, o RESUMO 7c.6b regenerado. Leitura da autoauditoria liberada.

Passos feitos ANTES deste script (evidência nesta pasta):
- R3.04: etapa7c6b_01_resumo_copia_saida_auditor_r3.py rodada em 2026-10-13 08:35:29 com o CSV desta pasta ainda com as 142 linhas
  (MD5 616f3002d9463e11b6f6ce9c0180c9af) → RESUMO_ETAPA7C6b_reproduzido_r3_v1_20261010.md.
- R3.01: etapa7c6_02_audita_final_copia_auditor_r3.py (cópia com: PROJ fixo, status sem reescrever o índice, saída e tmp do L7.01
  nesta pasta, memória fora do projeto não lida, auto-exclusão pelo nome original) → audita_final_reexecucao_auditor_r3_v1_20261010.csv
  e RESUMO_ETAPA7C6_reexec_autoaud_r3_v1_20261010.md; rodou até o fim (exit 0).
- R3.01.03: teste sintético num repositório git descartável criado e apagado dentro desta pasta (_teste_k101_git): um arquivo do
  pacote movido para audit_independente/etapa7c6_final/ aparece em 'git diff --name-only' só pelo destino.
Rodar: PYTHONDONTWRITEBYTECODE=1 python3 audit_independente/etapa7c6_final/audita_7c6_final_R3_v1_20261010.py
"""
import csv
import hashlib
import io
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True
from audita_7c6_final_lib_v1_20261010 import HEAD, MS, PROJ, git, pdf_texto, ws, xlsx_celulas  # noqa: E402

CSV_ = AQUI / "comparacao_7c6_final_v1_20261010.csv"
MD5_R2 = "616f3002d9463e11b6f6ce9c0180c9af"
ROWS = []


def reg(vid, ok, det):
    ROWS.append(dict(verificacao=vid, ok=bool(ok), detalhe=str(det)))
    print(f"{'OK   ' if ok else 'FALHA'} {vid}: {str(det)[:200]}", flush=True)


ler = lambda p: Path(p).read_text(encoding="utf-8")
md5 = lambda b: hashlib.md5(b).hexdigest()
R6B = ler(PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md")
AUTO = ler(PROJ / "scripts/etapa7c6_02_audita_final.py")
LEIA = ler(PROJ / "scripts/resumos/LEIAME.md")
lerc = lambda p: {r["verificacao"].split()[0]: r for r in csv.DictReader(io.StringIO(ler(p)))}
NOVO = lerc(MS / "audita_final_7c6_v1_20261010.csv")
ANTES = lerc("/private/tmp/claude-501/-Users-guilherme/e1c712c9-85af-4f6d-89f1-cb28b034e571/scratchpad/audita_final_antes_r2.csv")
MEU = lerc(AQUI / "audita_final_reexecucao_auditor_r3_v1_20261010.csv")
chk = ler(PROJ / "scripts/etapa7b_checa.py").splitlines()

# ============================================ R3.01 autoauditoria
dif = [k for k in NOVO if (NOVO[k]["ok"], NOVO[k]["detalhe"]) != (MEU[k]["ok"], MEU[k]["detalhe"])]
reg("R3.01.01", list(NOVO) == list(MEU) and set(dif) <= {"L7.01", "L9.01"} and MEU["L7.01"]["ok"] == "True",
    f"roda até o fim no estado atual: a cópia (só com os desvios de escrita/leitura listados na docstring) terminou com exit 0 e {len(MEU)} itens, "
    f"{sum(r['ok'] == 'True' for r in MEU.values())}/57 OK. Diferenças para o CSV do autor (50/57): {dif} — L7.01 só no caminho do arquivo temporário (ok=True "
    f"nos dois) e L9.01 False porque o auditor não lê a memória fora do projeto. O L4.01 não quebra mais (lista de scripts/resumos de b9d6272)")
fix = {"ATRIBUICAO (L4.03, L7.01)": 'gitb("show", f"{HEAD}:docs/referencias/ATRIBUICAO.txt")' in AUTO,
       "LEIAME (L8.01)": 'git("show", f"{HEAD}:scripts/resumos/LEIAME.md")' in AUTO,
       "lista de scripts/resumos (L4.01, L7.01)": 'git("ls-tree", "--name-only", f"{HEAD}:scripts/resumos")' in AUTO,
       "troca da lista só se o trecho existir 1 vez": 'code.replace(lista, "RES_HEAD") if code.count(lista) == 1 else ""' in AUTO}
reg("R3.01.02", all(fix.values()) and MEU["L7.01"]["ok"] == "True" and MEU["L8.01"]["ok"] == "False",
    f"fixações em {HEAD}: {fix}. Legítimas: o objeto é o estado commitado, e o RESUMO 7c.6, o LEIAME e a lista de b9d6272 são exatamente o que se audita. "
    f"Não mascaram: se o trecho da lista não for achado o L7.01 não roda (False); se o do ATRIBUICAO não for achado, entra o do disco e o L7.01 falha; o L8.01 "
    f"lido de {HEAD} continua False (o LEIAME novo avisa, o commitado não). Os outros insumos do L7.01 (._*, checa_7b_v11, comparacao_7c6, JSON) continuam "
    f"vindo do disco, então o L7.01 deixa de passar se os ._* forem movidos (ver R3.03.13)")
k1 = re.search(r'depois = .*?\n', AUTO).group(0).strip()
reg("R3.01.03", False,
    f"K1.01 aceita mais do que deve: usa '{k1}' — 'git diff --name-only' com a detecção de renomeação padrão mostra só o caminho de DESTINO de um arquivo movido. "
    f"Teste sintético (repositório descartável nesta pasta, git 2.39.5): mover outputs/manuscrito/tabelas/tab01.csv para audit_independente/etapa7c6_final/ "
    f"aparece só como 'audit_independente/etapa7c6_final/tab01.csv', que da7c6b() aceita; com --no-renames aparecem os dois caminhos. Assim um commit que "
    f"tirasse um arquivo do pacote (ou de qualquer lugar) movendo-o para a pasta do auditor, ou para um nome do conjunto E7C6B, passaria no K1.01. Correção "
    f"simples: --no-renames. O K4.01 falha do lado seguro: uma renomeação no índice aparece como 'R  antigo -> novo' (fora do conjunto) e uma no disco como "
    f"' D antigo' (fora do conjunto). Fora isso a lógica faz o que diz: HEAD descendente de {HEAD} (merge-base --is-ancestor) e diferença líquida só em E7C6B "
    f"ou na pasta do auditor; o K4.01 não confere que docs/referencias continua com 93")
ruins = {"M6.01": "a lista 'leitores' (scripts que contêm 'audit_independente' e '.csv') inclui 3 que não leem CSV de auditoria: etapa4_07_auditoria_sintese "
                  "(só lista a pasta), resumos/etapa7c5_01 (conta ._*) e resumos/etapa7c5b_01 (lista .txt); os números (118 CSVs, 21.7 MB, 72,415 em 4 "
                  "arquivos, 12 comparacao_*) conferem"}
oks = {"M3.01": "9.53 MB empacotado; 741 objetos, 22.45 MB no disco; 45.0 MB sem compressão (todos os objetos, inclusive árvores e commits; 44.7 só blobs); "
                "0.0 MB exclusivos de _arquivo_v*; checkout c8eddce (131.5, 113.0) e b9d6272 (166.0, 147.0) MB — tudo conferido. Os 5 'maiores' aparecem todos "
                "como 'Submissao/Fig1.tif' (o 1º caminho em ordem alfabética), pouco informativo mas correto",
       "M4.01": "os 5 lidos (sidra JSON, INTERGROWTH CSV, rl_municip_regsaud, tb_municip, tb_regsaud) = os meus",
       "M5.01": "'scripts que citam: nenhum (exceto este)' correto pelo rótulo; mas o próprio etapa7c6_02 LÊ o .txt (L428) — ver R3.03.11",
       "M1.02": "34 de 34 PDFs com ._* têm quarentena; só o 04 roda dot_clean",
       "L2.08": "desvio 0 s em 34 tabelas e −2 s na tab07_fluxograma_motivos = o meu",
       "M10.01": "contagens no corpus declarado no rótulo (sem PDFs/docx/JSON); 'small for gestational age' 1 nesse corpus (legendas)"}
reg("R3.01.04", False, "detalhes reescritos: " + "; ".join(f"{k}: {v}" for k, v in oks.items()) + ". ERRO MENOR: " + "; ".join(f"{k}: {v}" for k, v in ruins.items()))
rot = [k for k in ANTES if ANTES[k]["verificacao"] != NOVO[k]["verificacao"]]
okd = [k for k in ANTES if ANTES[k]["ok"] != NOVO[k]["ok"]]
reg("R3.01.05", list(ANTES) == list(NOVO) and not okd and sum(r["ok"] == "True" for r in NOVO.values()) == 50,
    f"CSV anterior (scratchpad, audita_final_antes_r2.csv, 57 itens) × atual (57): mesmos ids na mesma ordem; ok diferentes: {okd or 'nenhum'}; rótulos "
    f"reescritos: {rot}; 50/57 e as mesmas 7 falhas ({[k for k, r in NOVO.items() if r['ok'] == 'False']})")

# ============================================ R3.02 LEIAME
n526 = [i + 1 for i, l in enumerate(chk) if 'i["commit_pacote"] == B.COMMIT' in l]
g6 = ler(PROJ / "scripts/resumos/etapa7c6_01_resumo.py")
g6b = ler(PROJ / "scripts/resumos/etapa7c6b_01_resumo.py")
le6 = ["docs/referencias/ATRIBUICAO.txt" in g6, 'glob("*.py")' in g6, 'rglob("._*")' in g6,
       'pd.read_csv(B.PROJ / "audit_independente/etapa7c6/comparacao_7c6_v1_20261009.csv")' in g6]
le6b = 'pd.read_csv(PROJ / "audit_independente/etapa7c6_final/comparacao_7c6_final_v1_20261010.csv")' in g6b
reg("R3.02.01", n526 == [526] and all(le6) and le6b and MEU["L7.01"]["ok"] == "True",
    f"itens novos do LEIAME conferem: checa L{n526} exige commit_pacote = B.COMMIT (= HEAD); o etapa7c6_01 lê do disco o ATRIBUICAO, a lista de "
    f"scripts/resumos (glob *.py) e os ._* (rglob), e lê sem condição o comparacao_7c6 (ignorado); o etapa7c6b_01 lê sem condição o comparacao_7c6_final "
    f"(ignorado); a autoauditoria reproduz o RESUMO 7c.6 com o ATRIBUICAO e a lista de b9d6272 (L7.01 True na minha execução). Detalhe: o etapa7c6_01 também "
    f"lê do disco o checa_7b_v11 e o JSON dos números-chave (versionados), que o LEIAME não precisa citar")
usa_bv = {g: ("B.V" in ler(PROJ / "scripts/resumos" / g)) for g in sorted(p.name for p in (PROJ / "scripts/resumos").glob("*.py"))}
fixo = {g: bool(re.search(r'^V\s*=\s*"v\d+_', ler(PROJ / "scripts/resumos" / g), re.M)) for g in usa_bv}
reg("R3.02.02", False,
    f"a linha 6 do LEIAME (inalterada) diz 'todos, exceto o etapa7c5b_01_resumo.py (fixo na v10), leem a versão atual do pacote (B.V)'. Não vale para "
    f"2 dos {len(usa_bv)} geradores da pasta: versão fixa em {[g for g, v in fixo.items() if v]} (o etapa7c6_01 fixa V = v11) e o etapa7c6b_01 nem importa a "
    f"etapa7b_lib (usa B.V: {usa_bv['etapa7c6b_01_resumo.py']}). É a minha ressalva L1.17 da rodada 1, que continua aberta (ver R3.03.12)")

# ============================================ R3.03 fatos novos/alterados do RESUMO 7c.6b
arv = lambda c: [(int(l.split()[3]), l.split("\t", 1)[1]) for l in git("ls-tree", "-r", "-l", c).splitlines() if l.split()[1] == "blob"]
tam = {c: (round(sum(s for s, _ in arv(c)) / 1e6, 1), round(sum(s for s, p in arv(c) if "/_arquivo_v" in p) / 1e6, 1)) for c in ("c8eddce", HEAD)}
reg("R3.03.01", tam == {"c8eddce": (131.5, 113.0), HEAD: (166.0, 147.0)} and "166.0 MB em b9d6272, dos quais 147.0 MB" in R6B and "131.5 MB, com 113.0 MB" in R6B,
    f"checkout (soma dos blobs da árvore; _arquivo_v*): c8eddce {tam['c8eddce']} MB; {HEAD} {tam[HEAD]} MB — confere com o RESUMO e com o ~131 MB da 7c.5b")
j = [i + 1 for i, l in enumerate(chk) if re.match(r"J\d+ = \{i\[\"id\"\]: i for i in json\.load\(open\(A\d+", l)]
hv = [i + 1 for i, l in enumerate(chk) if l.startswith("HV = ")]
arqdef = [i + 1 for i, l in enumerate(chk) if re.match(r"A\d+, V\d+ = B\.MS / \"_arquivo_v\d+\"", l)]
lib = ler(PROJ / "scripts/etapa7b_lib.py")
reg("R3.03.02", arqdef == list(range(312, 319)) and j == list(range(319, 326)) and hv == [530],
    f"'tirar os _arquivo_v* quebraria o checa, que lê os números-chave de v1 a v10 e compara com v4 a v10': confere — L{arqdef[0]}–L{arqdef[-1]} definem "
    f"_arquivo_v4…v10, L{j[0]}–L{j[-1]} leem os JSON v4–v10 (blocos 9a–9g comparam CSV, xlsx, PDFs e TIFF dessas versões) e L{hv[0]} lê os JSON v1–v10 "
    f"(commit_registro). Acrescento: o etapa7b_lib.commits_analise também lê os _arquivo_v* ('{'MS.glob(\"_arquivo_v*\")' in lib}'), então uma regeração do "
    f"pacote sem eles perderia commit_registro e o congelamento do commit_analise")
s7b = [r for r in csv.reader(io.StringIO(ler(MS / "suplementar/S7b_dictionary_v11_20261009.csv"))) if r and r[0] == "pig_tabela_oficial"]
b1 = ler(PROJ / "scripts/etapa1_01_base_v2.py")
r2b = ler(PROJ / "scripts/etapa1_02b_pig_grade.R")
reg("R3.03.03", bool(s7b) and "p10_oficial_kg_k3" in b1 and "stopifnot(!anyNA(g$p10_oficial_kg_k3)" in r2b and "intergrowth21_bw_centis_oficial.csv" in r2b,
    f"INTERGROWTH (seção 4 item 4 e decisão 4) confere: etapa1_02b lê o CSV (L22) e para sem ele (stopifnot); o PIG principal vem do gigs (centil_k3); o P10 do "
    f"CSV define pig_tabela_oficial (etapa1_01_base_v2 L78–L80), listada na S7b como {s7b[0][1] if s7b else '-'}; também lido pelo etapa1_02a (L18) e pelo "
    f"etapa1_08 (L75)")
cit = {}
for nome in ("Dicionario_SIM_2025.pdf", "SINASC_Estrutura_2024.pdf"):
    cit[nome] = sorted(f"{p.relative_to(PROJ)}:{i + 1}" for p in (PROJ / "scripts").rglob("*") if p.suffix in (".py", ".R") and not p.name.startswith("._")
                       for i, l in enumerate(ler(p).splitlines()) if nome in l and re.search(r"read_|open\(|Document\(|pymupdf|fitz", l))
man = ler(MS / "MANIFEST.md")
reg("R3.03.04", not any(cit.values()) and all(n in man for n in cit),
    f"'os dois PDFs de dicionário (SINASC e SIM) são citados em comentários e no MANIFEST, mas nenhum script os lê': confere — nenhuma linha de leitura os "
    f"abre ({cit}); citados no docstring do etapa1_06 (L8), no comentário do etapa7b_02 (L366) e nas strings de origem do etapa7b_04 que vão para o MANIFEST "
    f"(linhas 55–56). Há ainda uma 3ª cópia de dicionário (SINASC_Estrutura_CGIAE_diaad), citada só na nota tpmetestim_codigo8_busca")
cnt = {}
for f in [PROJ / p for p in git("ls-files", "-o", "-i", "--exclude-standard", "audit_independente").split() if p.endswith(".csv") and "etapa7c6_final" not in p]:
    cols = next(csv.reader(io.StringIO(f.read_text(encoding="utf-8", errors="replace"))))
    c = [x for x in cols if x in ("n", "N")]
    if c:
        import pandas as pd
        v = pd.to_numeric(pd.read_csv(f, usecols=[c[0]])[c[0]], errors="coerce")
        if (v == 1).any():
            cnt[str(f.relative_to(PROJ / "audit_independente"))] = int((v == 1).sum())
reg("R3.03.05", sum(cnt.values()) == 72415 and len(cnt) == 4 and cnt.get("etapa2/agregado_m2_raca_idade_ano_macro_mun.csv") == 65178,
    f"72,415 = {' + '.join(f'{v:,}' for v in cnt.values())} em {len(cnt)} arquivos ({cnt}); 65,178 no arquivo por município e "
    f"{sum(v for k, v in cnt.items() if 'etapa6' in k):,} em 3 arquivos por região de saúde da Etapa 6: confere")
ig = [PROJ / p for p in git("ls-files", "-o", "-i", "--exclude-standard", "audit_independente").split() if p.endswith(".csv")]
comp = [p for p in ig if p.name.startswith("comparacao") and "etapa7c6_final" not in str(p)]
reg("R3.03.06", len(comp) == 11 and max(p.stat().st_size for p in comp) <= 34500,
    f"{len(comp)} comparacao_*.csv fora desta pasta, o maior com {max(p.stat().st_size for p in comp):,} bytes; CSVs ignorados em audit_independente agora: "
    f"{len(ig)} ({sum(p.stat().st_size for p in ig) / 1e6:.1f} MB, contando os desta pasta) — o '118, 21.7 MB' do RESUMO é a contagem da autoauditoria às 17:20 "
    f"de 12/10; os números mudam a cada CSV novo desta auditoria")
import json
t = json.loads(ler(AQUI / "m7_m10_termos_7c6_final_v1_20261010.json"))["M10"]
reg("R3.03.07", sum(t["PR (sigla)"].values()) == 379 and sum(t["SGA"].values()) == 592 and sorted(t["small for gestational age"]) ==
    ["Submissao/ESM_2.pdf", "legendas_figuras.md", "suplementar/S7_variables_codes_v11_20261009.pdf"]
    and sorted(t["relative risk"]) == ["Submissao/ESM_3.pdf", "suplementar/S8_strobe_record_checklist_v11_20261009.csv", "suplementar/S8_strobe_record_checklist_v11_20261009.pdf"]
    and "Por extenso (\"small for gestational age\"), só 3, contadas à parte" in R6B,
    "seção 4 item 10: PR 379; SGA 592 e mais 3 por extenso, à parte (S7 PDF, sua cópia Submissao/ESM_2.pdf e legendas); 'relative risk' só no texto STROBE da S8 "
    "(CSV, PDF e a cópia Submissao/ESM_3.pdf): confere com a minha contagem")
reg("R3.03.08", "o auditor conferiu no texto oficial do gov.br que são os incisos II e V" in R6B,
    "redação 3: 'o auditor conferiu no texto oficial do gov.br que são os incisos II e V' — confere (Res. CNS 510/2016, art. 1º, parágrafo único: II, informações de "
    "acesso público, Lei 12.527/2011; V, bancos de dados com informações agregadas, sem identificação individual; PDF oficial lido em 10/10)")
L4 = [l for l in R6B.split("## 3. Errata")[1].split("## 4.")[0].splitlines() if l.startswith("| Abertura")][0]
reg("R3.03.09", all(s in L4 for s in ["12 arquivos diferem em bytes", "Em 4 mudou o rótulo de versão", "Nos outros 8 mudaram só metadados"]),
    "nova linha 4 da errata confere na contagem (12 = 3 .md + docx + 2 xlsx + 2 PDFs do pacote + ESM_1–4 de Submissao/; os 8 só em metadados: células e texto "
    "iguais). Ressalva: nos 3 .md mudou mais que o rótulo de versão — data_code_availability também troca o commit de referência (linha 30) e o MANIFEST troca "
    "o commit de geração, 9 MD5 e a nota da S8 ('CC BY; ver docs/referencias/ATRIBUICAO.txt')")
exc = R6B.split("**Exceções à independência**")[1].split("**Erro do próprio auditor")[0]
reg("R3.03.10", len(re.findall(r"^\d\. ", exc, re.M)) == 4 and "L1.54" in exc and "L2b" in exc and "com autorização" in exc,
    "as 4 exceções da seção 2 (grep acidental de 3 linhas; leitura do checa CSV só no L2b; leitura interna do checa pelo gerador no L3; contagem de etiquetas de "
    "log no L1.54) e a leitura autorizada da autoauditoria na rodada 2 = o meu relatório")
le_auto = {"Evans .txt (M5.01, L428)": "evans2024_maihda_tutorial_PMC11059336.txt\").read_text" in AUTO,
           "comparacao_7c6 sem condição (L1.01, L105)": 'pd.read_csv(PROJ / "audit_independente/etapa7c6/comparacao_7c6_v1_20261009.csv")' in AUTO,
           "rl_municip_regsaud (M8.01)": 'territorio_dez24/rl_municip_regsaud.csv"' in AUTO,
           "outputs/tables (L2.04, L2.06, L5.02)": "tab_e2_03_mesprenat_completude" in AUTO}
reg("R3.03.11", False,
    f"as afirmações sobre 'quem lê' deixam de fora a própria autoauditoria, que é um script de scripts/ e vai para o git: ela lê {le_auto}. Por isso (a) seção 4 "
    f"item 5: 'nenhum script lê nem cita o .txt' do Evans é falso (o etapa7c6_02 o lê na L428, para procurar a licença); (b) item 4: 'os scripts leem só 5' "
    f"exclui essa leitura; (c) item 6: a lista de quem lê os comparacao_*.csv e a de quem falha num clone limpo omitem a autoauditoria (lê o comparacao_7c6 sem "
    f"condição e também outputs/tables/). Relevante para a decisão 4 ('não versionar o .txt, porque nenhum script o lê'): sem o .txt, o etapa7c6_02 para com "
    f"FileNotFoundError na L428")
reg("R3.03.12", False,
    "seção 2, 'Ressalvas do auditor na rodada 1': 'o LEIAME … não dizia que o gerador da 7c.6 também lê o disco. Agora diz.' Não é a minha ressalva. A L1.17 "
    "dizia que o LEIAME afirma que todos os geradores, exceto o 7c5b, leem B.V, mas o etapa7c6_01 fixa V = v11 (e na rodada 2 o RESUMO a citava assim: 'também "
    "tem a versão fixa'). A frase nova troca o conteúdo da ressalva e a dá por resolvida; a linha 6 do LEIAME continua inexata (R3.02.02)")
reg("R3.03.13", False,
    "decisão 2, efeito colateral: diz só que 'os geradores da 7c.5 e da 7c.6 passariam a mostrar 0'. Falta: mover os ._* faz a autoauditoria falhar no L4.04 "
    "(exige 36 fora de Submissao/ e a tabela por pasta igual ao disco) e no L7.01 (o gerador da 7c.6 recalcula a seção 3 a partir do disco, então o RESUMO "
    "regenerado deixa de ser igual ao commitado). Isso contradiz a decisão 7 e o LEIAME ('a autoauditoria o reproduz com esses dois fixados em b9d6272'), que "
    "só valem enquanto os ._* não forem mexidos")
outros = {"seção 1: M3.01/M4.01/M5.01/L2.08/M1.02/M6.01 corrigidos": True,
          "seção 1: 50/57 com as mesmas 7 falhas": sum(r["ok"] == "True" for r in NOVO.values()) == 50,
          "seção 4 item 1 cita os geradores da 7c.5 e da 7c.6": "os geradores da 7c.5 e da 7c.6 os contam ao vivo" in R6B,
          "seção 4 item 3: 9.53 MB; 22.45 MB; ~45 MB; 0 exclusivo; 4.8 MB": all(s in R6B for s in ["9.53 MB", "22.45 MB", "cerca de 45 MB", "4.8 MB"]),
          "decisão 1: 34 no mesmo segundo e 2 s na tab07": "34 e a 2 s na outra" in R6B,
          "decisão 4: nenhum arquivo > 5 MB; checkout 166 MB": "nenhum arquivo passa de 5 MB" in R6B and "166 MB" in R6B,
          "redação 6: SGA por extenso só na S7 e nas legendas": "só acontece na S7 e nas legendas" in R6B,
          "pendências: 7 decisões e 8 itens de redação": "as 7 decisões e os 8 itens de redação" in R6B,
          "tabela 'O que a rodada 2 corrigiu' (R2.04.03–R2.04.11)": "| R2.04.11 | 8 decisões | 7 decisões" in R6B}
reg("R3.03.14", all(outros.values()),
    "demais fatos novos ou alterados conferem: " + "; ".join(f"{k}: {v}" for k, v in outros.items())
    + ". Não verificáveis: a conferência do autor no PMC em 12/10 e o histórico da 1ª versão da autoauditoria (51/51)")
reg("R3.03.15", True,
    "o que sobrou da rodada 2: das falhas, nada — R2.04.03, .04, .06, .07, .08, .09 e .11 e R2.02.04/05 foram corrigidas (R2.00 era erro meu e está registrado). "
    "Das ressalvas: a linha 6 do LEIAME (R3.02.02, apresentada como resolvida em R3.03.12) e o L1.04 da autoauditoria, que ainda confere só o texto das "
    "verificações do checa, não os valores. Novos nesta rodada: R3.01.03 (K1.01 e renomeações), R3.01.04 (leitores do M6.01), R3.03.11 e R3.03.13")

# ============================================ R3.04 reprodução do RESUMO 7c.6b
cop = ler(AQUI / "etapa7c6b_01_resumo_copia_saida_auditor_r3.py")
dd = [l for l in __import__("difflib").unified_diff(g6b.splitlines(), cop.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
rep = (AQUI / "RESUMO_ETAPA7C6b_reproduzido_r3_v1_20261010.md").read_bytes()
reg("R3.04.01", len(dd) == 2 and rep == (PROJ / "outputs/RESUMO_ETAPA7C6b_v1_20261010.md").read_bytes(),
    f"cópia do gerador difere só na linha de saída; rodada da raiz com PYTHONPATH=scripts em 2026-10-13 08:35:29, ANTES das linhas R3, com o CSV desta pasta "
    f"com 142 linhas (MD5 {MD5_R2}): saída idêntica byte a byte ao RESUMO 7c.6b do disco (MD5 {md5(rep)}; o do disco foi gerado às 17:20:02 de 12/10). O "
    f"Logger acrescentou 1 linha ao log da etapa7c6. Depois das linhas R3 o gerador muda de saída (bloco R3 e falhas R3)")

# ============================================ R3.05 triagem
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
reg("R3.05.01", not ach and not susp,
    f"{len(cand)} arquivos novos/modificados fora do .gitignore ({sum(p.startswith('audit_independente/') for p in cand)} desta pasta: .py, .md, .json; os CSV "
    f"daqui são ignorados), inclusive o LEIAME e o ATRIBUICAO. Datas 1900–2024, CNS, CPF e linhas de log: {ach or 'nenhum'}. CSV não ignorado: {list(cols)} "
    f"(colunas {list(cols.values())}), sem nome de identificador. Nenhuma linha de microdado nem contagem fina copiada de log")

# ============================================ R3.06 nada mais mudou
mod = sorted(l[3:] for l in st if not l.startswith("??"))
nao = sorted(l[3:] for l in st if l.startswith("??") and not l[3:].startswith(("docs/referencias/", "audit_independente/etapa7c6_final/")))
n_ref = sum(1 for l in st if l.startswith("?? docs/referencias/"))
esperado = {"outputs/RESUMO_ETAPA7C6b_v1_20261010.md", "outputs/manuscrito/_resumo7c6b_texto_v1_20261010.md", "outputs/manuscrito/audita_final_7c6_v1_20261010.csv",
            "scripts/etapa7c6_02_audita_final.py", "scripts/resumos/etapa7c6b_01_resumo.py"}
reg("R3.06.01", mod == ["docs/referencias/ATRIBUICAO.txt", "scripts/resumos/LEIAME.md"] and set(nao) == esperado and n_ref == 93
    and git("rev-parse", "--short", "HEAD").strip() == HEAD and len(git("reflog").splitlines()) == 27,
    f"HEAD = {HEAD}; reflog com as mesmas 27 entradas; rastreados modificados: {mod}; não rastreados novos: os 5 de antes; docs/referencias/: {n_ref}. "
    f"Arquivos alterados desde o fim da rodada 2 (find -newermt, fora desta pasta): os 6 listados pelo coordenador e o log da etapa7c6 (linhas do autor em 12/10 "
    f"16:58:22, 17:19:59 e 17:20:02; minhas em 13/10 08:35:29 e 08:37:55). Nada em data/, outputs/tables/, Submissao/ nem no pacote")
pac = ["outputs/manuscrito/tabelas", "outputs/manuscrito/suplementar", "outputs/manuscrito/figuras", "Submissao",
       "outputs/manuscrito/numeros_chave_v11_20261009.json", "outputs/manuscrito/numeros_chave_v11_20261009.md", "outputs/manuscrito/checa_7b_v11_20261009.csv",
       "outputs/manuscrito/MANIFEST.md", "outputs/manuscrito/data_code_availability.md", "outputs/manuscrito/legendas_figuras.md", "outputs/manuscrito/_arquivo_v10"]
dq = subprocess.run(["git", "-C", str(PROJ), "--no-optional-locks", "diff", "--quiet", HEAD, "--", *pac]).returncode
extra = git("ls-files", "-o", "--exclude-standard", *pac).split()
reg("R3.06.02", dq == 0 and not extra,
    f"pacote (tabelas/, suplementar/, figuras/, números-chave, checa_7b_v11, MANIFEST, disponibilidade, legendas, _arquivo_v10) e Submissao/ iguais a {HEAD}: "
    f"{dq == 0}; não rastreados nessas pastas: {extra or 'nenhum'}")

# ============================================ gravação: preserva as rodadas 1 e 2 byte a byte
bruto = CSV_.read_bytes()
i = bruto.find(b"\nR3.")
base = bruto if i < 0 else bruto[:i + 1]
assert md5(base) == MD5_R2, "a parte das rodadas 1 e 2 do CSV mudou"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["verificacao", "ok", "detalhe"], lineterminator="\r\n")
ordem = lambda v: [int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", v)]
w.writerows(sorted(ROWS, key=lambda r: ordem(r["verificacao"])))
CSV_.write_bytes(base + buf.getvalue().encode("utf-8"))
print(f"rodada 3: {sum(r['ok'] for r in ROWS)}/{len(ROWS)} OK; CSV com 142 + {len(ROWS)} linhas")
