"""
Auditor independente da Etapa 7c.7 — rodada 2: revisão do código da autoauditoria nova (R2.c), conferência do RESUMO (R2.d) e outros
achados (R2.e). Lido depois das verificações próprias (audita_7c7_r2_v1_20261013.py); o CSV da autoauditoria NÃO é lido aqui (fica para
audita_7c7_r2_final_v1_20261013.py). Os vereditos da revisão de código vêm da leitura do scripts/etapa7c7_02_audita.py (681 linhas) e são
registrados com a evidência mínima conferida por código (presença do trecho no script).
Grava as linhas R2.c/R2.d/R2.e no comparacao_7c7_v1_20261013.csv (refaz as suas a cada execução).
Rodar: python3 audit_independente/etapa7c7/audita_7c7_r2_revisao_v1_20261013.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd
import pymupdf

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
MS = PROJ / "outputs" / "manuscrito"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
R = []
PREF = ("R2.c1", "R2.c2", "R2.d", "R2.e")


def ok(vid, desc, cond, det=""):
    R.append(dict(verificacao=f"{vid} {desc}", ok=bool(cond), detalhe=str(det)[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {str(det)[:150]}", flush=True)


git = lambda *a: subprocess.run(["git", "-C", str(PROJ), *a], capture_output=True, text=True, env=ENV, check=True).stdout
sa = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()
ids = re.findall(r'^\s*ok\(f?"([A-E]\d\.\d\d)"', sa, re.M)
ids += [f"C6.{k:02d}" for k in range(1, 17)] if 'ok(f"C6.{k + 1:02d}"' in sa else []
ids = sorted(set(ids))
SB2 = json.load(open(OUTD / "sandbox_7c7_r2_v1_20261013.json"))

# ======================================================================= R2.c — revisão item a item (56)
REV = {  # item: (mede o que diz?, nota; trecho do código que sustenta)
    "A0.01": (True, "HEAD = dc9328d ou um commit só, com o título exato, sobre ele; só refs/heads/main (pega tag); sem remoto; stash vazio", "head_ok = h == BASE or"),
    "A1.01": (True, "listas exatas (38 v12, 49 do _arquivo_v11, 5 fixos + RESUMO); docs/referencias = 93 com mtime < dc9328d; auditor pelo padrão de "
                    "nome. 'ficam fora do commit' é intenção (vale no E1.01), não medida aqui", "resto = [p for p in adic if p not in PAC12 | ARQ11 | FIXOS"),
    "A1.02": (True, "bytes de dc9328d (não o blob do índice)", "mov = [p for p in VELHOS"),
    "A1.03": (True, "ok", "arq(A11, V11) == arq(A10"),
    "A1.04": (True, "git status --ignored -uall lista arquivo por arquivo, inclusive em data/, e faz stat (mtime) neles: só metadado, como diz a "
                    "docstring ('data/ só por nome e mtime'), mas é mais que 'só nomes'", 'ign = [p for c, p in st("--ignored")'),
    "A2.01": (True, "os.walk no projeto inteiro (raiz incluída); em data/ só nomes", "for raiz, dirs, fs in os.walk(PROJ)"),
    "A2.02": (True, "ok", 'git("log", "--all", "--format=", "--name-only")'),
    "B1.01": (True, "agora com ordem; tipo do valor bruto não comparado (5 == 5.0 passaria)", '[i["id"] for i in J12l[:226]] == list(J11)'),
    "B1.02": (True, "ok", '{i["commit_pacote"] for i in J12l} == {BASE}'),
    "B2.01": (True, "ok", "conta = {u: rl.loc[rl.CO_MUNICIP.str.startswith(c)"),
    "B2.02": (True, "descrição exata", 'DESC = "Health regions in {} in the municipality-to-health-region map'),
    "B2.03": (True, "tabela inteira recalculada, siglas pela tb_uf", 't7.fillna("").astype(str).equals(eu.fillna("").astype(str))'),
    "B2.04": (True, "cruzamento com tb_regsaud e tb_municip", 'nt == {"CE": 25, "DF": 8}'),
    "B3.01": (True, "ok", "len(pares) == 20 and len(ig) == 20"),
    "B4.01": (True, "todas as células; não confere a ordem das abas", "len(dx) == 1 and dx[0][0].startswith(\"tab04_\")"),
    "B4.02": (True, "ok (Submissao/ESM_1 por células)", "e11 == e12 == es"),
    "B4.03": (True, "registra as outras 5 linhas n.a.", "len(na_out) == 6"),
    "B5.01": (True, "texto; formatação (runs/itálico) não", "c11 == c12 and len(p11) == len(p12)"),
    "B6.01": (True, "texto dos PDFs; imagem do ESM_4 e renderização não", "txt(SUB / f\"ESM_{k}.pdf\") == txt(A11"),
    "B7.01": (True, "pixels/modo/dpi; compressão do TIFF não", "len(ims) == 10 and len(im_ok) == 10"),
    "B8.01": (True, "3 linhas mudam (título, abertura, Tabela 2); MD5 normalizado", "len(m11) == len(m12) and len(dm) == 3"),
    "B8.02": (True, "ok", "md_ok = [m and md5(lugar(m.group(1))"),
    "B8.03": (True, "completo com a regra nova (fecha a falha B7.05)", "sorted(lis) == sorted(esp)"),
    "B8.04": (True, "tabela bem formada (fecha a ressalva do |)", r'len(re.findall(r"(?<!\\)\|", l)) in (4, 5)'),
    "B8.05": (True, "disponibilidade (espaços normalizados) e legendas", "volta == d_11 and d_12.count("),
    "C1.01": (True, "ok", "corpo(velho) == corpo(novo)"),
    "C2.01": (True, "lista exata de trocas que reproduz o arquivo atual (fecha C5.C2.01); cobre o LEIAME", "if cont != [1] * len(trocas) or v_ != n_"),
    "C3.01": (True, "lê o CSV do checa (o C6.00 confere a mesma coisa rodando o checa)", "len(c12) == 113 and c12.ok.astype(bool).all()"),
    "C3.02": (True, "removidas e acrescentadas por região (regiões largas: o 9g/9h inteiro)", "add_fora = sorted(i for i in add_l"),
    "C4.01": (True, "estático; a docstring nova (CE 25, DF 8) conferida por texto", '"(CE 25, DF 8)" in src7'),
    "C6.00": (True, "checa sem assert no sandbox, com os mesmos rótulos do CSV real", 'rb["rot"] == set(c12.verificacao)'),
    **{f"C6.{k:02d}": (True, "mutação pertinente: derruba a verificação-alvo (não confere que outras não mudam)", "any(x.startswith(alvo) for x in r_[\"fl\"])")
       for k in range(1, 17)},
    "C6.20": (True, "checa com assert depois do commit único: 113/113 e pai = dc9328d", 'ru["pai"] == BASE'),
    "C6.21": (True, "commit no meio derruba o commit_pacote", 'any(x.startswith("7c.7 commit_pacote") for x in ri["fl"])'),
    "C6.22": (True, "testa de fato os 4 scripts que cita (7c6_02, 7c6_01 e 7c5b_01 param por FileNotFoundError da versão na raiz; 7c6b_01 "
                    "reproduz o RESUMO 7c.6b). Não testa a frase nova do LEIAME 'o etapa7c7_01 fixa a v12 do mesmo jeito' (este auditor testou: "
                    "R2.s09) nem 'não rodam num clone limpo'; 'logo no começo' não é medido pela linha", 'fnf(l1, V11) and fnf(l2, V11) and fnf(l3, "v10_20261009")'),
    "C6.23": (True, "tamanho e mtime de outputs/tables antes/depois e sandbox apagado: confere depois, não impede escrita pelos links", "tab_antes == tab_depois and not TMP.exists()"),
    "D1.01": (True, "sequência = lista fixa no código (SEQ), escrita depois dos fatos; não é cruzada com o texto do RESUMO (este auditor cruzou: R2.d)",
              'SEQ = ["7c6_01_resumo",'),
    "D1.02": (True, "scripts editados antes da rodada final e saídas na janela do script; Submissao = cópias", "all((PROJ / s).stat().st_mtime < t7c for s in SCR)"),
    "E1.01": (True, "ok (sem os 93 de docs/referencias)", 'vai = sorted(set(p for s, p in ns if s != "D")'),
    "E1.02": (True, "colunas identificadoras e ≤ 1.000 linhas", "grandes = {p: n for p, n in lin_max.items() if n > 1000}"),
    "E1.03": (True, "ok", '(PROJ / ".gitignore").read_text() == git("show", f"{BASE}:.gitignore")'),
}
ok("R2.c10", "autoauditoria nova: 56 itens no código, todos revisados aqui", len(ids) == 56 and set(ids) == set(REV), f"{len(ids)} no código; sem revisão {sorted(set(ids) - set(REV))}")
for i in sorted(REV):
    m, nota, trecho = REV[i]
    ok(f"R2.c11.{i}", f"autoauditoria {i}: mede o que diz", m and trecho in sa, nota)
ok("R2.c20", "mutações (16): pertinentes; cobrem as 13 verificações '7c.7' (n_regsaude e ._* com 2 cada) e uma do 9g", True,
   "sem controle negativo (nenhuma confere que uma mutação só na v12 não mexe no 9g); a do pixel converte RGBA → RGB, o que já muda o "
   "modo; nenhuma mexe na base territorial (a n_regsaude é derrubada pelo JSON, não pela recontagem)")
regras = {"clone -s (alternates, só leitura dos objetos do Forja)": '["git", "clone", "-q", "-s", str(PROJ), str(BASE_SBX)]' in sa,
          "rastreados mudados copiados (permitido)": "shutil.copy2(PROJ / p, BASE_SBX / p)" in sa,
          "docs/referencias não rastreados fora, menos o rl": 'not p.startswith("docs/referencias/") or p.endswith("territorio_dez24/rl_municip_regsaud.csv")' in sa,
          "outputs/tables por link": '(BASE_SBX / "outputs/tables" / f.name).symlink_to(f)' in sa,
          "comparacao_*.csv por link": "(BASE_SBX / f.relative_to(PROJ)).symlink_to(f)" in sa,
          "nada de data/": "data/" not in re.sub(r"#.*", "", sa[sa.index("def monta"):sa.index("def roda(")]),
          "apagado no fim": "shutil.rmtree(TMP, ignore_errors=True)" in sa}
ok("R2.c21", "sandbox da autoauditoria respeita as regras: nada ignorado copiado para fora do Forja (outputs/tables e comparacao_*.csv por "
   "link), nada de data/, apagado no fim; outputs/tables intacta (R2.c01) e logs reais sem linhas dela (R2.c03)", all(regras.values()),
   f"{regras}. Ressalva: os links não têm guarda técnica contra escrita (o C6.23 só confere depois); os não rastreados não ignorados, "
   "inclusive os arquivos deste auditor e o CSV da própria autoauditoria, vão por cópia (permitido)")
ok("R2.c22", "D1.01/D1.02 pegariam o D1.04 e o B7.05? D1.04 (checa duas vezes, editado no meio): na rodada final, sim — o D1.01 exige um "
   "checa_ini só e o D1.02 exige todo script editado antes do início; na 1ª rodada, o D1.01 só registra (a SEQ foi escrita com as duas "
   "execuções). B7.05: o D não pega (só mtime do MANIFEST), mas o B8.03 (MANIFEST completo) pega, e a regra nova tira os audita_*",
   '"checa_ini", "checa_ini", "checa_fim", "04"' in sa and "all((PROJ / s).stat().st_mtime < t7c for s in SCR)" in sa and "sorted(lis) == sorted(esp)" in sa,
   "conferido pela leitura do código; não reexecutado com logs sintéticos (os logs são ignorados pelo git e não podem ser copiados para fora do Forja)")

# ======================================================================= R2.d — RESUMO (texto e gerador)
txt = (MS / "_resumo7c7_texto_v1_20261013.md").read_text()
res = (PROJ / "outputs/RESUMO_ETAPA7C7_v1_20261013.md").read_text()
dados = json.load(open(MS / "numeros_chave_v12_20261013.json"))
s02 = (PROJ / "scripts/etapa2_02_regsaude.py").read_text() if (PROJ / "scripts/etapa2_02_regsaude.py").exists() else \
    "".join(p.read_text() for p in (PROJ / "scripts").glob("etapa2_02*.py"))
s03 = (PROJ / "scripts/etapa2_03_indice_acesso.py").read_text()
manis = {p.parent.name: p.read_text() for p in sorted(MS.glob("_arquivo_v*/MANIFEST_*.md"))}
desde = sorted((int(k.split("_v")[1]) for k, v in manis.items() if "(atenuação só com |PR_M2cc − 1| ≥ 0.10)" in v))
ok("R2.d01", "INTRO 1–2: frase da Tabela 4 só no rodapé (xlsx/docx), CSV idêntico; CE 5 e DF 1 com a descrição do mapa; origem tab_e7c7_01; "
   "rl_municip_regsaud é o arquivo que o etapa2_02 lê; o índice (etapa2_03) usa o mapa que o etapa2_02 grava; 530000 → 53001, não conta como município",
   "rl_municip_regsaud.csv" in s02 and "municipio_regsaude_dez24" in s02 and "municipio_regsaude_dez24" in s03
   and [i["valor_formatado"] for i in dados[-2:]] == ["5", "1"], "R2.bB02, bB15, bB17, bB18 e grep nos scripts")
ok("R2.d02", "INTRO 2 (tb_regsaud 25/8; 20 e 7 sem município), 4 (docstring do etapa2_03), 5 (checa) e 6 (grep; sem âncora, 2 commits)", True,
   "R2.bB18, R2.a10, R2.s05–s07; ressalva: '13 verificações no bloco novo' — são 12 no bloco 9h + a do etapa2_03, que fica no fim do arquivo")
ok("R2.d03", "INTRO 7: 'A linha da Tabela 2 tinha |PR_M2cc − 1| sem escape desde a v10'", desde and desde[0] == 10,
   f"falso: o | sem escape está em todos os MANIFEST arquivados desde o primeiro, o da v4 ({desde}); a v1–v3 não têm MANIFEST. O erro vem do "
   "relatório da rodada 1 deste auditor ('já vinha da v10'), que também fica corrigido")
ok("R2.d04", "INTRO 3, 8, 9 e parágrafo final: ._* (36 sumiram, o de data/processed ficou, dot_clean + raise no 02); arquivamento como na v10; "
   "duas gerações (10:40–10:46 e 12:24–12:26, com as listas certas); LEIAME; só mudam rodapé, 2 números, âncora, MANIFEST e rótulos",
   True, "R2.bA07, bA08, bD01, bD04, bB01–bB17; a lixeira em si não é verificável (fora do projeto)")
ok("R2.d05", "AUTO: a descrição da autoauditoria bate com o código (A–E; trocas exatas; 16 mutações; commit único e no meio; LEIAME; "
   "sandbox com alternates e links, sem data/, apagado)", True,
   "ressalvas: 'links só de leitura' é convenção (sem guarda); 'as afirmações do LEIAME' são 4 dos scripts, não todas (R2.c11.C6.22)")
ok("R2.d06", "INDEP: rodada 1 = 197/204 (estado das 10:46); as 7 falhas e o que foi feito; ressalvas acolhidas; o que fica para o autor está "
   "na seção 4 e nas pendências", "**Rodada 1** (estado das 10:46, antes das correções): **197/204**" in txt, "conferido contra o CSV deste auditor (rodada 1: 197/204)")
ok("R2.d07", "EFEITOS: o que deixou de rodar (7c6_02, 7c6_01; 7c5b_01 desde a 7c.6, a v10 já não estava na raiz em dc9328d); commit_registro/"
   "analise vazios por desenho; um commit só (C6.21)",
   not [p for p in git("ls-tree", "-r", "--name-only", "dc9328d", "outputs/manuscrito/tabelas").split() if "v10_" in p]
   and "commit_registro = commit in which" in (MS / "numeros_chave_v12_20261013.md").read_text(), "R2.s09, round 1 C6.04–C6.05, R2.s06")
v_err = False
try:
    dict({1: {}}, **{11: {}})
except TypeError:
    v_err = True
ok("R2.d08", "EFEITOS (execuções intermediárias): 7c7_01 três vezes (10:36:26 com 5,572 municípios; 10:36:44; 12:24:02); checa três vezes "
   "(10:43:50 parou por erro de código — `dict(HV, **{11: J11})` levanta TypeError — ; 10:44:57 113/113; 12:25:23 113/113)",
   v_err and "dict(HV, **{11: J11})" in txt and "{**HV, 11: J11}" in (PROJ / "scripts/etapa7b_checa.py").read_text(), "R2.bD04 e logs (F4.01/F4.02 da rodada 1)")
ok("R2.d09", "EFEITOS (lixeira, sandbox, PDFs): os 36 sumiram e a lista está no scratchpad; o sandbox é como descrito; título tmpXXXX.html e "
   "Chrome 154 → 155, texto e renderização iguais",
   "HeadlessChrome/155" in pymupdf.open(PROJ / "Submissao/ESM_2.pdf").metadata["creator"] and pymupdf.open(PROJ / "Submissao/ESM_2.pdf").metadata["title"].startswith("tmp"),
   "a lixeira não é verificável; o sandbox leva também os não rastreados não ignorados (RESUMO, CSV da autoauditoria, arquivos do auditor) — "
   "cabem em 'as mudanças da 7c.7'")
dca = (MS / "data_code_availability.md").read_text()
tn = pd.read_csv(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv").set_index("uf")
ok("R2.d10", "REDACAO 3, 7, 8 e PEND: ética 'wording to be confirmed by the authors' na disponibilidade; 36.8 no CE × 12.9 no Brasil e fora dos "
   "números-chave; 5 outras linhas n.a.; título do commit citado no MANIFEST e na disponibilidade; rl lido pelo script novo e pelo checa",
   "wording to be confirmed by the authors" in dca and float(tn.municipios_por_regiao["CE"]) == 36.8 and float(tn.municipios_por_regiao["Brasil"]) == 12.9
   and not [i for i in dados if str(i["valor_formatado"]) in ("36.8", "12.9")] and "rl_municip_regsaud.csv" in (PROJ / "scripts/etapa7b_checa.py").read_text(),
   "redação 1, 2, 4, 5 e 6 são decisões fora do projeto (não verificáveis aqui)")
g = (PROJ / "scripts/resumos/etapa7c7_01_resumo.py").read_text()
ok("R2.d11", "gerador: lê só o que a docstring diz (autoauditoria, checa, números-chave, CSV do auditor, texto) e grava o RESUMO + 1 linha de "
   "log; versão fixa (para depois de arquivada: R2.s09); reproduz o RESUMO byte a byte (R2.s08)",
   all(x in g for x in ['MS / "audita_7c7_v1_20261013.csv"', 'PROJ / "audit_independente/etapa7c7/comparacao_7c7_v1_20261013.csv"', 'MS / f"checa_7b_{V}.csv"',
                        'MS / f"numeros_chave_{V}.json"', 'MS / "_resumo7c7_texto_v1_20261013.md"']) and g.count("read_csv(") + g.count("read_text(") + g.count("json.load(") == 5
   and SB2["gerador"]["reproduz"]["igual"], f"md5 {SB2['gerador']['reproduz']['md5_real'][:12]}")
ok("R2.d12", "gerador, cabeçalho: base dc9328d (7c.6b, v11), 'nenhum número do pacote mudou', 228 números, checa 113/113 e 13/13",
   "base: commit dc9328d (Etapa 7c.6b, pacote v11)" in res and "nenhum número do pacote mudou" in res and "(228 no total)" in res
   and "**checa da v12: 113/113 OK**, das quais 13/13 no bloco novo da 7c.7." in res, "ressalva: '13/13 no bloco novo' = 12 do 9h + a do etapa2_03")

# ======================================================================= R2.e — outros achados
ok("R2.e01", "gerador do RESUMO: 'X/Y OK (todas as rodadas)' e a lista de falhas do auditor juntam as rodadas — depois da rodada 2, as 7 "
   "falhas da rodada 1, já corrigidas, continuam listadas como falhas, sem indicação da rodada", False,
   "sugestão: tabela por rodada (bloco R2 já existe) e falhas da rodada 1 marcadas como corrigidas, ou só as da última rodada")
ok("R2.e02", "a regra do 04 tira 'audita_*' de todas as pastas do pacote, não só da raiz (o MANIFEST diz 'na raiz'); hoje não há nenhum fora da raiz",
   True, "inofensivo hoje; registrar")
ok("R2.e03", "sandbox da autoauditoria sem guarda técnica: um script que escrevesse num arquivo de outputs/tables pelo link alteraria o Forja; "
   "o C6.23 só detecta depois", True, "sugestão: sitecustomize com sys.addaudithook bloqueando escrita em /Volumes/Forja (como o sandbox deste auditor)")

velho = pd.read_csv(CMP)
velho = velho[~velho.verificacao.str.startswith(PREF)]
out = pd.concat([velho, pd.DataFrame(R)], ignore_index=True)
out.to_csv(CMP, index=False)
print(f"\nR2.c/d/e: {sum(r['ok'] for r in R)}/{len(R)} OK; CSV total {len(out)}")
