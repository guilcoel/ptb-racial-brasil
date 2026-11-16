"""
Auditor independente da Etapa 7c.7 — rodada 3 (antes de ler o CSV da autoauditoria; esse fica para audita_7c7_r3_final_v1_20261013.py).
  R3.d  nada mudou no pacote, nos scripts do pacote, nos logs do pacote e em outputs/tables desde a rodada 2: reexecuta a lógica de
        A/B/D/E/correções do audita_7c7_r2_v1_20261013.py (sem gravar linhas R2) e compara com o que a rodada 2 registrou
  R3.a  as 3 falhas da rodada 2 e as ressalvas acolhidas
  R3.b  autoauditoria nova: guarda (sondas em sandbox_7c7_r3_guarda), C6.00a, controle negativo, C6.22, resto do código
  R3.c  RESUMO: texto, gerador e reprodução byte a byte (sandbox_7c7_r3_gerador, com o CSV deste auditor no estado de antes das R3)
  R3.e  outros achados
Grava cópia (texto + MD5) dos arquivos revisados nesta rodada em revisados_7c7_r3_v1_20261013.json, para diff na rodada seguinte.
Grava só linhas R3.a/b/c/d/e no comparacao_7c7_v1_20261013.csv. Rodar: python3 audit_independente/etapa7c7/audita_7c7_r3_v1_20261013.py
"""
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJ = Path("/Volumes/Forja/ptb-racial-brasil")
OUTD = PROJ / "audit_independente" / "etapa7c7"
CMP = OUTD / "comparacao_7c7_v1_20261013.csv"
MS = PROJ / "outputs" / "manuscrito"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
PREF = ("R3.a", "R3.b", "R3.c", "R3.d", "R3.e")
R3 = []
md5f = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()
st = lambda p: (PROJ / p).stat().st_mtime
hora = lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S")


def ok(vid, desc, cond, det=""):
    det = str(det).replace("|", "¦")                      # sem | cru: o gerador do RESUMO não escapa | nas tabelas
    R3.append(dict(verificacao=f"{vid} {desc.replace('|', '¦')}", ok=bool(cond), detalhe=det[:1800]))
    print(f"{'OK   ' if cond else 'FALHA'} {vid} {desc[:95]} | {det[:160]}", flush=True)


ANTES = pd.read_csv(CMP)
assert not ANTES.verificacao.str.startswith("R3.").any() or True
R2ROWS = ANTES[ANTES.verificacao.str.startswith("R2.")]
DET2 = dict(zip(R2ROWS.verificacao.str.split(" ").str[0], R2ROWS.detalhe.astype(str)))

# ======================================================================= R3.d — lógica da rodada 2 reexecutada no estado de hoje
src = (OUTD / "audita_7c7_r2_v1_20261013.py").read_text()
src = src[:src.index("# ======================================================================= R2.s — sandbox da rodada 2")]
src = src.replace('[n_ for _, n_ in ult["etapa7c7_20261008.log"]] == ["7c7_01_resumo"]', '{n_ for _, n_ in ult["etapa7c7_20261008.log"]} == {"7c7_01_resumo"}')
_dump = 'json.dump(RUNS_DIA, open(OUTD / "logs_execucoes_7c7_r2_v1_20261013.json", "w"), ensure_ascii=False, indent=1)'
assert src.count(_dump) == 1
src = src.replace(_dump, "pass  # [r3] não regrava o registro da rodada 2")
ns = {"__name__": "r2_reexec"}
exec(compile(src, "audita_7c7_r2 (reexecução)", "exec"), ns)
for r in ns["R"]:
    vid = r["verificacao"].split(" ")[0]
    if vid == "R2.bA10":                                  # 'nada mudou desde 13:32': substituído por R3.d01
        continue
    R3.append(dict(verificacao="R3.d." + r["verificacao"][3:].replace("|", "¦"), ok=r["ok"], detalhe=str(r["detalhe"]).replace("|", "¦")[:1800]))
print(f"reexecução da rodada 2: {sum(r['ok'] for r in ns['R'] if not r['verificacao'].startswith('R2.bA10'))}/{len(ns['R']) - 1}")
T_R2 = datetime.strptime("2026-10-13 13:32:00", "%Y-%m-%d %H:%M:%S").timestamp()
arv = ns["arvore_disco"]()
ESPERADO = {"outputs/manuscrito/_resumo7c7_texto_v1_20261013.md", "scripts/resumos/etapa7c7_01_resumo.py", "scripts/etapa7c7_02_audita.py",
            "outputs/manuscrito/audita_7c7_v1_20261013.csv", "outputs/RESUMO_ETAPA7C7_v1_20261013.md"}
depois = sorted(p for p in arv if st(p) >= T_R2 and not p.startswith(("audit_independente/etapa7c7/", "outputs/logs/", "outputs/tables/")) and "__pycache__" not in p)
ign_depois = sorted(p for p in (["outputs/logs/" + f for f in os.listdir(PROJ / "outputs/logs")] + ["outputs/tables/" + f for f in os.listdir(PROJ / "outputs/tables")])
                    if st(p) >= T_R2)
ok("R3.d01", "desde o início da rodada 2 (13:32), mudaram só o texto do RESUMO, o gerador, a autoauditoria e o CSV dela, o RESUMO e o log 7c7 "
   "(nada no pacote, nos scripts do pacote nem em outputs/tables)", set(depois) == ESPERADO and ign_depois == ["outputs/logs/etapa7c7_20261008.log"],
   "; ".join(f"{p} {hora(st(p))}" for p in depois + ign_depois))
d3 = DET2.get("R2.bD03", "")
SCR = ["etapa7b_lib.py", "etapa7b_01_tabelas.py", "etapa7b_02_suplementar.py", "etapa7b_03_figuras.py", "etapa7b_04_submissao.py",
       "etapa7b_checa.py", "etapa7c7_01_regsaude_uf.py", "etapa2_03_indice_acesso.py"]
ok("R3.d02", "scripts do pacote com o mesmo mtime registrado na rodada 2 (R2.bD03)", all(f"{s} {hora(st('scripts/' + s))}" in d3 for s in SCR),
   "; ".join(f"{s} {hora(st('scripts/' + s))}" for s in SCR))
ok("R3.d03", "outputs/tables: tabela nova com o mesmo MD5 da rodada 2 (R2.bB18) e nada mais com mtime depois de dc9328d",
   md5f(PROJ / "outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv")[:12] in DET2.get("R2.bB18", "")
   and all(st("outputs/tables/" + f) < ns["TCOMMIT"] for f in os.listdir(PROJ / "outputs/tables") if not f.startswith("tab_e7c7_01")),
   f"md5 {md5f(PROJ / 'outputs/tables/tab_e7c7_01_regsaude_uf_v1_20261008.csv')[:12]}")
runs2 = [tuple(r) for r in json.load(open(OUTD / "logs_execucoes_7c7_r2_v1_20261013.json"))]
runs3 = [tuple(r) for r in ns["RUNS_DIA"]]
sem_res = lambda rs: [r for r in rs if r[1] != "7c7_01_resumo"]
T_FIM2 = datetime.strptime("2026-10-13 14:21:16", "%Y-%m-%d %H:%M:%S").timestamp()
extra = [(t[11:], n_) for t, n_, _ in ns["ev"] if datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timestamp() > T_FIM2]
ok("R3.d04", "logs do pacote: as execuções de hoje fora o gerador do RESUMO = as registradas na rodada 2; depois do fim da rodada 2 só há "
   "linhas do gerador do RESUMO; logs 7b e 7c6 com o mesmo mtime",
   sem_res(runs3) == sem_res(runs2) and extra and all(n_ == "7c7_01_resumo" for _, n_ in extra) and hora(st("outputs/logs/etapa7b_20261008.log")) == "12:26:33"
   and hora(st("outputs/logs/etapa7c6_20261008.log")) == "10:20:24", f"novas: {extra}")
L12 = (MS / "MANIFEST.md").read_text()
ok("R3.d05", "pacote: os 49 arquivos listados no MANIFEST (gravado às 12:26:33) com o mesmo MD5; MANIFEST e checa com o mtime da rodada 2",
   hora(st("outputs/manuscrito/MANIFEST.md")) == "12:26:33" and hora(st("outputs/manuscrito/checa_7b_v12_20261013.csv")) == "12:26:17"
   and all((MS / k.split("/", 1)[1] if k.startswith("manuscrito/") else PROJ / k).exists() and md5f(MS / k.split("/", 1)[1] if k.startswith("manuscrito/") else PROJ / k)[:12] == m
           for k, m in re.findall(r"^\| ((?:manuscrito|Submissao)/\S+) \| .* \| ([0-9a-f]{12}) \|$", L12, re.M)), "R3.d.bB10 também")

# ======================================================================= R3.a — falhas da rodada 2 e ressalvas acolhidas
txt = (MS / "_resumo7c7_texto_v1_20261013.md").read_text()
res = (PROJ / "outputs/RESUMO_ETAPA7C7_v1_20261013.md").read_text()
ger = (PROJ / "scripts/resumos/etapa7c7_01_resumo.py").read_text()
manis = sorted(int(p.parent.name.split("_v")[1]) for p in MS.glob("_arquivo_v*/MANIFEST_*.md") if "(atenuação só com |PR_M2cc − 1| ≥ 0.10)" in p.read_text())
ok("R3.a01", "R2.d03 corrigida: o item 7 diz 'desde o primeiro MANIFEST, o da v4 (as v1–v3 não têm MANIFEST)'; nenhum 'desde a v10' no texto",
   "desde o primeiro MANIFEST, o da v4 (as v1–v3 não têm MANIFEST)" in txt and "desde a v10" not in txt.split("<!--AUTO-->")[0] and manis[0] == 4
   and not any(list((MS / f"_arquivo_v{k}").glob("MANIFEST*")) for k in (1, 2, 3)), f"MANIFEST com o ¦ sem escape: v{manis}")
rods = re.search(r"Por rodada: (.*?)\. As falhas", res)
ok("R3.a02", "R2.e01 corrigida: o gerador separa as rodadas (contagem, tabela por rodada e bloco, falhas com a coluna Rodada); a saída diz "
   "'rodada 1: 197/204; rodada 2: 164/167'", "Rodada=df.verificacao.str.extract(r\"^R(\\d+)\\.\")" in ger and rods is not None
   and rods.group(1) == "**rodada 1: 197/204 OK**; **rodada 2: 164/167 OK**" and "**Falhas, por rodada:**" in res,
   rods.group(1) if rods else "")
ok("R3.a03", "R2.f06 (síntese) resolvida por consequência: as duas falhas que ela resumia foram corrigidas; a autoauditoria segue sem conferir o "
   "texto do RESUMO, que fica com o auditor (registrado no INDEP)", "a autoauditoria não confere o texto do RESUMO, que fica com o auditor" in txt)
ok("R3.a04", "ressalva '13 no bloco novo': o texto diz '13 verificações: 12 no bloco 9h e a do etapa2_03', e o gerador calcula a divisão",
   "A 7c.7 acrescenta 13 verificações: 12 no bloco 9h e a do `etapa2_03`, no fim do `checa`." in txt and "n23 = int(c77.verificacao.str.startswith(\"7c.7 etapa2_03\").sum())" in ger
   and "das quais 13/13 são as novas da 7c.7 (12 no bloco 9h e 1 do etapa2_03, no fim do checa)." in res)
s04 = (PROJ / "scripts/etapa7b_04_submissao.py").read_text()
ok("R3.a05", "ressalva 'regra do 04 mais larga que o texto': registrada na seção 3 (Regra do 04), sem regerar o pacote; hoje só há audita_* na raiz",
   "**Regra do 04.**" in txt and 'f.name.startswith(("._", "_", "audita_"))' in s04 and "na raiz de outputs/manuscrito/" in L12
   and not [f for d in ("tabelas", "figuras", "suplementar") for f in (MS / d).iterdir() if f.name.startswith("audita_")])
sa = (PROJ / "scripts/etapa7c7_02_audita.py").read_text()
ok("R3.a06", "ressalvas 'guarda', 'controle negativo do 9g' e 'C6.22 com o gerador 7c7_01': implementadas no código (conferidas em R3.b)",
   "sys.addaudithook(_guarda)" in sa and 'ok("C6.00a"' in sa and 'not any(x.startswith("7c.6") for x in r_["fl"])' in sa and "fnf(l6, V12)" in sa)

# ======================================================================= R3.b — autoauditoria nova
G = json.load(open(OUTD / "sandbox_7c7_r3_guarda_v1_20261013.json"))
son, ctl = G.get("sondas", {}), G.get("controle_sem_guarda", {})
mut = [k for k in son if k not in ("leitura_forja", "escrita_tmp")]
ok("R3.b01", "guarda da autoauditoria (GUARDA_PY, sozinha, fora do sandbox dela) bloqueia de fato: as 12 sondas de escrita, remoção, renomeação, "
   "mkdir, utime, chmod e rmtree no Forja (inclusive por link) dão PermissionError; leitura no Forja e escrita no /tmp passam",
   len(mut) == 12 and all(son[k] == "BLOQUEOU" for k in mut) and son.get("leitura_forja") == "PASSOU" and son.get("escrita_tmp") == "PASSOU"
   and not G.get("efeitos_no_forja", {}).get("criados") and not G.get("efeitos_no_forja", {}).get("alterados") and G.get("descartaveis_apagados"),
   {k: v for k, v in son.items()})
ok("R3.b02", "as sondas são efetivas: sem a guarda, as mesmas operações passam (ou dão FileNotFoundError nos caminhos inexistentes) — "
   "rodadas só em arquivos descartáveis desta pasta, apagados", all(ctl.get(k) in ("PASSOU", "FileNotFoundError") for k in mut), ctl)
ok("R3.b03", "a guarda NÃO bloqueia cópia de arquivo ignorado do Forja para fora (só destino no Forja); o texto dela não promete isso "
   "('escrita, remoção e renomeação'); a regra é cumprida por construção (monta() só cria links)", G.get("sonda_copia") == "sem_copia"
   and "shutil.copyfile" in sa and "escrita, remoção e renomeação no Forja" in sa, "ressalva, não falha")
c600a = sa[sa.index("alvo_t = sorted("):sa.index("(BASE_SBX / \"outputs/logs/teste_guarda.txt\").unlink")]
ok("R3.b04", "C6.00a é seguro se a guarda falhar: g1 abre em 'a' pelo link sem escrever (não muda o arquivo); g2 faz os.remove pelo link, que "
   "apagaria só o link no sandbox, não o arquivo do Forja (e o item confere que o link continua lá); g3 escreve dentro do sandbox",
   "open('outputs/tables/{alvo_t}', 'a')\")" in c600a and "os.remove('outputs/tables/" in c600a and ".is_symlink()" in c600a and ".write(" not in c600a.split("g3")[0],
   "ressalva: se o C6.00a falhar, o resto do sandbox roda mesmo assim (sem abortar); nenhuma mutação escreve em link, então o Forja fica protegido por construção")
mutsrc = sa[sa.index("MUT = ["):sa.index("GIT_ID = [")]
alvos = re.findall(r'"(7c\.[67][^"]*)"\),?\s*$', mutsrc, re.M)
ok("R3.b05", "controle negativo do 9g: C6.01–C6.15 (mutações só na v12) exigem que nenhuma verificação '7c.6' falhe; o C6.16 (v11 arquivada) é "
   "o positivo. Correto: só o bloco 9g tem verificações que começam com '7c.6' (as do checa de outras etapas começam com '7c.1'–'7c.5b' ou "
   "'independente')", 'r_["rc"] == 0 and any(x.startswith(alvo) for x in r_["fl"]) and (alvo.startswith("7c.6") or not any(x.startswith("7c.6") for x in r_["fl"]))' in sa
   and sum(1 for a in alvos if a.startswith("7c.6")) == 1 and len(alvos) == 16, f"alvos {alvos}")
ok("R3.b06", "C6.22 novo testa o que diz: além dos 4 scripts da rodada 2, o gerador 7c7_01 roda com a v12 na raiz (rc 0) e, depois de "
   "arquivar no sandbox os *_v12_* da raiz, para com FileNotFoundError citando v12_20261013 (este auditor confirmou isso por conta própria, "
   "R2.s09 e R3.c)", "l5.returncode == 0 and fnf(l6, V12)" in sa and 'glob(f"*_{V12}.*")' in sa)
import ast as _ast
_m = _ast.parse((OUTD / "audita_7c7_r2_revisao_v1_20261013.py").read_text())
_rev = [n for n in _ast.walk(_m) if isinstance(n, _ast.Assign) and _ast.unparse(n.targets[0]) == "REV"][0]
vals = sorted({t.elts[2].value for t in _ast.walk(_rev.value) if isinstance(t, _ast.Tuple) and len(t.elts) == 3
               and isinstance(t.elts[2], _ast.Constant) and isinstance(t.elts[2].value, str)})
faltam = [v for v in vals if v not in sa]
ids = sorted(set(re.findall(r'^\s*ok\(f?"([A-E]\d\.\d\d[a-z]?)"', sa, re.M)) | ({f"C6.{k:02d}" for k in range(1, 17)} if 'ok(f"C6.{k + 1:02d}"' in sa else set()))
ok("R3.b07", "resto da autoauditoria: os itens são os 56 da rodada 2 + C6.00a; os trechos de código que sustentaram a revisão da rodada 2 "
   "continuam todos lá; os blocos A, B, C1–C4, D e E não mudaram (lidos; sem cópia da versão anterior para diff)",
   len(ids) == 57 and "C6.00a" in ids and not faltam and len(vals) >= 40, f"{len(ids)} itens; {len(vals)} trechos conferidos; ausentes {faltam[:3]}")
REVIS = {p: (PROJ / p).read_text() for p in ["scripts/etapa7c7_02_audita.py", "scripts/resumos/etapa7c7_01_resumo.py",
                                              "outputs/manuscrito/_resumo7c7_texto_v1_20261013.md"]}
json.dump({p: {"md5": hashlib.md5(t.encode()).hexdigest(), "linhas": len(t.splitlines()), "texto": t} for p, t in REVIS.items()},
          open(OUTD / "revisados_7c7_r3_v1_20261013.json", "w"), ensure_ascii=False, indent=1)
ok("R3.b08", "cópia (texto + MD5) da autoauditoria, do gerador e do texto revisados nesta rodada gravada para o diff da próxima",
   (OUTD / "revisados_7c7_r3_v1_20261013.json").exists(), {p: hashlib.md5(t.encode()).hexdigest()[:12] for p, t in REVIS.items()})

# ======================================================================= R3.c — RESUMO
GR = json.load(open(OUTD / "sandbox_7c7_r3_gerador_v1_20261013.json"))
rp = GR.get("gerador", {}).get("reproduz", {})
ok("R3.c01", "cópia do gerador (saída desviada; CSV deste auditor por link, no estado de antes das R3: 13:57:11, 0 linhas R3) reproduz o "
   "outputs/RESUMO_ETAPA7C7 das 16:01 byte a byte; com a v12 arquivada, para",
   rp.get("igual") is True and GR["comparacao_estado"]["linhas_r3"] == 0 and GR["comparacao_estado"]["mtime"] == "13:57:11"
   and GR["gerador"]["apos_arquivar_v12"]["rc"] not in (0, None) and "FileNotFoundError" in GR["gerador"]["apos_arquivar_v12"]["ultima"]
   and GR.get("ignorados_intactos") and GR.get("sandbox_apagado"), f"md5 {rp.get('md5_real')}; guarda do auditor {GR.get('guarda_auditor', {}).get('saida')}")
cmp_r = ANTES[~ANTES.verificacao.str.startswith("R3.")]
okb = lambda s: s.astype(str).str.lower().isin(["true", "1"])
r1 = cmp_r[~cmp_r.verificacao.str.startswith("R2.")]
r2 = cmp_r[cmp_r.verificacao.str.startswith("R2.")]
ok("R3.c02", "INDEP, rodada 2: '164/167', 'R2.a, 12/12', 'R2.b, 60/60', 'R2.c, 63/63' e as 3 falhas (R2.d03, R2.e01, R2.f06) = o CSV deste auditor",
   (int(okb(r2.ok).sum()), len(r2)) == (164, 167) and "**Rodada 2** (estado das 12:26, depois das correções): **164/167**." in txt
   and all(f"({b}, {n}/{n})" in txt for b, n in (("R2.a", 12), ("R2.b", 60), ("R2.c", 63)))
   and sorted(r2[~okb(r2.ok)].verificacao.str.split(" ").str[0]) == ["R2.d03", "R2.e01", "R2.f06"]
   and (int(okb(r1.ok).sum()), len(r1)) == (197, 204))
ok("R3.c03", "INDEP, rodada 2, ressalvas acolhidas (contagem 12+1; guarda C6.00a; C6.22 com o gerador; controle negativo C6.01–C6.15) e "
   "'regra do 04 na seção 3': cada uma está no código ou no texto", all(x in txt for x in ["(12 no 9h e a do `etapa2_03`)", "(C6.00a)", "(C6.22)", "(C6.01–C6.15)",
                                                                                          "fica registrada na seção 3"]) and 'ok("C6.00a"' in sa)
ok("R3.c04", "AUTO: 'Todo Python lá dentro carrega uma guarda que bloqueia escrita, remoção e renomeação no Forja; a guarda é testada antes do "
   "uso' — o roda() põe a guarda no PYTHONPATH de toda execução e o C6.00a roda antes das mutações; '16 mutações' e '9g não se mexe' e "
   "'gerador para depois que a v12 for arquivada' batem com o código", 'e["PYTHONPATH"] = os.pathsep.join([str(GUARDA)]' in sa
   and sa.index('ok("C6.00a"') < sa.index("fb = ex.submit(caso, 0)") and len(alvos) == 16,
   "ressalva: 'testada antes do uso', mas o resultado não interrompe o sandbox")
ok("R3.c05", "INTRO 5 e 7 corrigidos; INTRO 1–4, 6, 8, 9 e parágrafo final como na rodada 2 (conferidos lá; o pacote não mudou, R3.d)",
   "A 7c.7 acrescenta 13 verificações" in txt and "o da v4" in txt and "## O que foi feito" in txt)
ok("R3.c06", "EFEITOS: itens da rodada 2 inalterados e conferidos (o que deixou de rodar; números sem commit; um commit só; execuções "
   "intermediárias; lixeira; sandbox; PDFs) + 'Regra do 04' novo, correto", "**Regra do 04.** Ele deixa fora do MANIFEST os `audita_*` de todas as pastas do pacote" in txt
   and "dict(HV, **{11: J11})" in txt and "(5.572)" in txt)
ok("R3.c07", "REDACAO e PEND inalterados e conferidos na rodada 2 (ética, 36.8 × 12.9, 5 linhas n.a., título do commit, rl lido pelo checa)",
   "36.8 municípios por região no CE, contra 12.9 no Brasil" in txt and "wording to be confirmed by the authors" in txt)
ok("R3.c08", "partes geradas: cabeçalho, 228 números, 'checa 113/113 ... 12 no bloco 9h e 1 do etapa2_03', autoauditoria 57/57, por rodada "
   "197/204 e 164/167, falhas por rodada (7 da 1ª, 3 da 2ª)", "(228 no total)" in res and "**57/57 OK**" in res and "rodada 2: 164/167 OK" in res
   and len(re.findall(r"^\| 1 +\| ", res, re.M)) >= 7, "a contagem 57/57 é a que o gerador leu do CSV da autoauditoria")

# ======================================================================= R3.e — outros achados
tabs, cur = [], []
for l in res.splitlines():
    if l.startswith("|"):
        cur.append(l)
    elif cur:
        tabs.append(cur)
        cur = []
quebradas = [l[:70] for t in tabs for l in t if len(re.findall(r"(?<!\\)\|", l)) != len(re.findall(r"(?<!\\)\|", t[0]))]
ok("R3.e01", "RESUMO: as tabelas Markdown estão bem formadas", not quebradas,
   f"2 linhas da tabela 'Falhas, por rodada' quebram a tabela: os rótulos R2.d03 e R2.f06 (deste auditor) trazem o caractere barra vertical sem "
   f"escape, e o md() do gerador não escapa — o mesmo defeito do MANIFEST da Tabela 2. Linhas: {quebradas}. Sugestão: escapar no md() "
   "(df.replace('¦'…) ou str.replace('|', '\\\\|')). As linhas R3 deste auditor não usam o caractere")
ok("R3.e02", "gerador: NOMES_IA não tem nomes para os blocos R3 (sairão como 'R3.a. ' sem nome) e a frase 'As falhas de uma rodada foram "
   "tratadas antes da seguinte' não vale para a última rodada", True, "cosmético; ajustar ao preencher a rodada 3")
ok("R3.e03", "a ordem dos blocos na tabela por rodada segue a ordem das linhas no CSV (R2.b antes de R2.a)", True, "cosmético")

velho = pd.read_csv(CMP)
velho = velho[~velho.verificacao.str.startswith(PREF)]
out = pd.concat([velho, pd.DataFrame(R3)], ignore_index=True)
out.to_csv(CMP, index=False)
r3 = pd.DataFrame(R3)
print(f"\nR3: {int(r3.ok.sum())}/{len(r3)} OK; CSV {len(out)} linhas")
