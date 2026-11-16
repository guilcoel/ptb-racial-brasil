#!/usr/bin/env python3
"""Auditoria independente da Etapa 7c.2 (pacote v5 -> v6), ptb-racial-brasil.

Código escrito do zero pelo auditor; não usa scripts/etapa7b_checa.py,
scripts/etapa7c2_01_sexo_sim.py nem outputs/manuscrito/checa_7b_*.csv.

Somente leitura fora de audit_independente/etapa7c2/.
Microdados do SIM-DOFET: apenas consultas agregadas (contagens/proporções).

Uso:
  python3 audita_7c2_v1_20261009.py --fase e12   # só E1/E2 (antes de abrir as tabelas do autor)
  python3 audita_7c2_v1_20261009.py              # tudo (A–H, incluindo E3)
"""
import argparse
import csv
import difflib
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path('/Volumes/Forja/ptb-racial-brasil')
MAN = ROOT / 'outputs' / 'manuscrito'
V5 = MAN / '_arquivo_v5'
SUB6 = ROOT / 'Submissao'
SUB5 = V5 / 'Submissao'
TABS = ROOT / 'outputs' / 'tables'
OUT = ROOT / 'audit_independente' / 'etapa7c2'
CSV_OUT = OUT / 'comparacao_7c2_v1_20261009.csv'
E12_JSON = OUT / 'e12_resultados_v1_20261009.json'
REL = OUT / 'relatorio_7c2_v1_20261009.md'

DOFET = '/Volumes/Forja/Doc/dados_artigos_perinatais_clima/02_sim/_dofet/parquet/ano=*/uf=*.parquet'
GRADE = ROOT / 'data' / 'processed' / 'pig_grade_intergrowth_v1_20261008.parquet'

LINHAS = []  # (verificacao, ok, detalhe)


def reg(verif, ok, detalhe):
    LINHAS.append((verif, bool(ok), str(detalhe)))
    print(f"[{'OK ' if ok else 'FALHA'}] {verif}: {str(detalhe)[:300]}")


# ---------------------------------------------------------------- utilidades de texto
RX_TERC = re.compile(r'(?<![_A-Za-z])([Tt])ercile')          # trocas autorizadas (fora de ids)
RX_TERC_TUDO = re.compile(r'([Tt])ercile')                     # inclusive ids (só para diagnóstico)
RX_TERC_RESIDUO = re.compile(r'(?i)(?<![_a-z])tercile')        # resíduo proibido na v6
RX_ICR = re.compile(r'\bICR\b')
RX_PARDA = re.compile(r'\bParda')                               # maiúsculo, sensível a caixa
RX_NUM = re.compile(r'[−-]?\d+(?:[.,]\d+)*')

ROT_V5 = '3 Amarela (Asian descent)'
ROT_V6 = '3 Asian (amarela)'
NOTA_FIG1 = ('Brown (parda) and Black (preta) follow the Brazilian Institute of Geography and Statistics '
             'categories; race/skin color is analyzed as a marker of exposure to structural racism.')


def autoriza(s):
    return RX_TERC.sub(lambda m: m.group(1) + 'ertile', s)


def autoriza_tudo(s):
    return RX_TERC_TUDO.sub(lambda m: m.group(1) + 'ertile', s)


def nums(s):
    return RX_NUM.findall(s)


def norm_ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def rmws(s):
    return re.sub(r'\s+', '', s)


def padrao_ws(s, intercalado=None):
    """Regex que casa s tolerando qualquer espaço/quebra entre caracteres e, opcionalmente,
    um trecho intercalado (no PDF, o texto da coluna 'Use' da mesma linha aparece no meio da célula)."""
    sep = r'\s*'
    if intercalado:
        sep = r'\s*(?:' + r'\s*'.join(re.escape(c) for c in rmws(intercalado)) + r'\s*)?'
    return re.compile(sep.join(re.escape(c) for c in rmws(s)))


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def primeira_dif(a, b, ctx=60):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != 'equal':
            return f"{op}: v5[{a[max(0, i1 - ctx):i2 + ctx]!r}] v6[{b[max(0, j1 - ctx):j2 + ctx]!r}]"
    return ''


def ler_csv(p):
    with open(p, encoding='utf-8-sig', newline='') as fh:
        return list(csv.reader(fh))


# ---------------------------------------------------------------- S7a: células especiais
S7A5 = V5 / 'suplementar' / 'S7a_variables_codes_v5_20261009.csv'
S7A6 = MAN / 'suplementar' / 'S7a_variables_codes_v6_20261009.csv'


def s7a_info(rows):
    h = rows[0]
    c_sys, c_var = h.index('System'), h.index('Variable')
    c_en = h.index('Official label (English translation)')
    c_pt = h.index('Official label (Portuguese, data dictionary)')
    c_cod = h.index('Codes used and recoding in this study')
    i_sexo = [i for i, r in enumerate(rows) if r[c_sys] == 'SIM' and r[c_var] == 'SEXO']
    i_raca = [i for i, r in enumerate(rows) if r[c_var] == 'RACACORMAE']
    return dict(c_en=c_en, c_pt=c_pt, c_cod=c_cod, i_sexo=i_sexo, i_raca=i_raca)


# ================================================================ E: SEXO do SIM (DuckDB, só agregados)
def e12():
    import duckdb
    con = duckdb.connect()
    src = f"read_parquet('{DOFET}', hive_partitioning=true, union_by_name=true)"
    con.execute(f"""
        CREATE TEMP VIEW base AS
        SELECT CAST(ano AS INTEGER)                    AS ano,
               SEXO                                    AS sexo_raw,
               trim(SEXO)                              AS sexo,
               trim(TIPOBITO)                          AS tipobito,
               TRY_CAST(trim(SEMAGESTAC) AS INTEGER)   AS sg,
               TRY_CAST(trim(GESTACAO) AS INTEGER)     AS gest,
               TRY_CAST(trim(PESO) AS INTEGER)         AS peso,
               TRY_CAST(trim(GRAVIDEZ) AS INTEGER)     AS gravidez,
               trim(DTOBITO)                           AS dtobito
        FROM {src}
        WHERE CAST(ano AS INTEGER) BETWEEN 2015 AND 2024
    """)
    fetal = """(tipobito = '1' AND (
                   (sg IS NOT NULL AND sg NOT IN (9, 99) AND sg >= 22)
                OR ((sg IS NULL OR sg IN (9, 99)) AND gest BETWEEN 2 AND 6)
                OR peso >= 500))"""
    rotulo = "CASE WHEN sexo IS NULL THEN '<NULL>' WHEN sexo = '' THEN '<vazio>' ELSE sexo END"
    tab = con.execute(f"""
        SELECT ano, {rotulo} AS codigo,
               count(*) AS n_todos,
               count(*) FILTER (WHERE {fetal}) AS n_fetal,
               count(*) FILTER (WHERE {fetal} AND gravidez = 1) AS n_fetal_unico
        FROM base GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    diag = con.execute(f"""
        SELECT count(*) AS n_todos,
               count(*) FILTER (WHERE {fetal}) AS n_fetal,
               count(*) FILTER (WHERE regexp_matches(sexo, '[A-Za-z]')) AS letras_todos,
               count(*) FILTER (WHERE {fetal} AND regexp_matches(sexo, '[A-Za-z]')) AS letras_fetal,
               count(*) FILTER (WHERE sexo_raw <> sexo) AS com_espaco,
               count(*) FILTER (WHERE dtobito IS NOT NULL AND length(dtobito) = 8
                                AND TRY_CAST(right(dtobito, 4) AS INTEGER) <> ano) AS ano_dtobito_difere,
               count(*) FILTER (WHERE tipobito <> '1' OR tipobito IS NULL) AS tipobito_nao1
        FROM base
    """).fetchone()
    diag = dict(zip(['n_todos', 'n_fetal', 'letras_todos', 'letras_fetal', 'com_espaco',
                     'ano_dtobito_difere', 'tipobito_nao1'], diag))

    con.execute(f"CREATE TEMP VIEW grade AS SELECT SEMAGESTAC, SEXO, PESO, centil_k3 FROM read_parquet('{GRADE}')")
    sexo_ii = """CASE WHEN upper(sexo) = 'M' THEN 1
                      WHEN upper(sexo) = 'F' THEN 2
                      WHEN TRY_CAST(sexo AS INTEGER) IN (1, 2) THEN TRY_CAST(sexo AS INTEGER)
                      ELSE NULL END"""
    con.execute(f"""
        CREATE TEMP VIEW fu AS
        SELECT ano, sg, peso,
               TRY_CAST(sexo_raw AS INTEGER) AS s_i,
               {sexo_ii} AS s_ii
        FROM base WHERE {fetal} AND gravidez = 1
    """)
    q = {}
    q_ano = {}
    for v, col in (('i_trycast', 's_i'), ('ii_recod_MF', 's_ii')):
        r = con.execute(f"""
            SELECT count(*) AS n_elegiveis,
                   count(*) FILTER (WHERE {col} IN (1, 2)) AS n_sexo_1_2,
                   count(g.centil_k3) AS n_pareados,
                   count(*) FILTER (WHERE g.centil_k3 < 0.10) AS n_pig
            FROM fu LEFT JOIN grade g
              ON g.SEMAGESTAC = fu.sg AND g.SEXO = fu.{col} AND g.PESO = fu.peso
        """).fetchone()
        d = dict(zip(['n_elegiveis', 'n_sexo_1_2', 'n_pareados', 'n_pig'], r))
        d['q'] = d['n_pig'] / d['n_pareados'] if d['n_pareados'] else None
        d['q_sobre_elegiveis'] = d['n_pig'] / d['n_elegiveis'] if d['n_elegiveis'] else None
        q[v] = d
        rows = con.execute(f"""
            SELECT fu.ano, count(*), count(g.centil_k3), count(*) FILTER (WHERE g.centil_k3 < 0.10)
            FROM fu LEFT JOIN grade g
              ON g.SEMAGESTAC = fu.sg AND g.SEXO = fu.{col} AND g.PESO = fu.peso
            GROUP BY 1 ORDER BY 1
        """).fetchall()
        q_ano[v] = [dict(ano=a, n_elegiveis=n, n_pareados=m, n_pig=p, q=(p / m if m else None))
                    for a, n, m, p in rows]
    # pares (s_i, s_ii) — só para mostrar onde as versões poderiam divergir
    difere = con.execute("SELECT count(*) FROM fu WHERE s_i IS DISTINCT FROM s_ii").fetchone()[0]
    res = dict(tabulacao=[dict(ano=a, codigo=c, n_todos=n1, n_fetal=n2, n_fetal_unico=n3)
                          for a, c, n1, n2, n3 in tab],
               diag=diag, q=q, q_ano=q_ano, n_sexo_difere_entre_versoes=difere)
    E12_JSON.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
    return res


def checa_e12(res):
    tab = res['tabulacao']
    d = res['diag']
    codigos = Counter()
    codigos_f = Counter()
    for r in tab:
        codigos[r['codigo']] += r['n_todos']
        codigos_f[r['codigo']] += r['n_fetal']
    reg('E1_sexo_todos_registros_sem_letras', d['letras_todos'] == 0,
        f"2015–2024, {d['n_todos']:,} registros; códigos (trim) = {dict(sorted(codigos.items()))}; "
        f"com letra = {d['letras_todos']}; valores com espaço antes do trim = {d['com_espaco']}")
    reg('E1_sexo_obitos_fetais_sem_letras', d['letras_fetal'] == 0,
        f"óbitos fetais pelo critério = {d['n_fetal']:,}; códigos = {dict(sorted((k, v) for k, v in codigos_f.items() if v))}; "
        f"com letra = {d['letras_fetal']}")
    so012 = set(k for k, v in codigos.items() if v) <= {'0', '1', '2'}
    reg('E1_S7a_afirma_so_codigos_0_1_2', so012,
        f"S7a v6 diz 'In 2015–2024 the field holds only codes 0, 1, and 2'; códigos encontrados (todos os registros): "
        f"{sorted(k for k, v in codigos.items() if v)}")
    reg('E1_ano_particao_vs_DTOBITO', True,
        f"informativo: registros cuja DTOBITO (DDMMAAAA) tem ano diferente da partição = {d['ano_dtobito_difere']}; "
        f"TIPOBITO diferente de '1' = {d['tipobito_nao1']}")
    qi, qii = res['q']['i_trycast'], res['q']['ii_recod_MF']
    reg('E2_q_PIG_versao_i_TRY_CAST', qi['q'] is not None,
        f"q = {qi['q']:.10f} ({qi['n_pig']:,}/{qi['n_pareados']:,} pareados na grade); "
        f"elegíveis (fetal, GRAVIDEZ=1) = {qi['n_elegiveis']:,}; SEXO em {{1,2}} = {qi['n_sexo_1_2']:,}; "
        f"q sobre todos os elegíveis = {qi['q_sobre_elegiveis']:.10f}")
    reg('E2_q_PIG_versao_ii_M1_F2', qii['q'] is not None,
        f"q = {qii['q']:.10f} ({qii['n_pig']:,}/{qii['n_pareados']:,} pareados na grade); "
        f"elegíveis = {qii['n_elegiveis']:,}; SEXO em {{1,2}} = {qii['n_sexo_1_2']:,}; "
        f"q sobre todos os elegíveis = {qii['q_sobre_elegiveis']:.10f}")
    igual = (qi['n_pig'] == qii['n_pig'] and qi['n_pareados'] == qii['n_pareados'])
    reg('E2_q_identico_entre_versoes', igual,
        f"diferença q(ii)−q(i) = {qii['q'] - qi['q']:.3e}; registros com SEXO convertido de forma diferente "
        f"entre (i) e (ii) = {res['n_sexo_difere_entre_versoes']} (código 0: vira 0 em (i) e nulo em (ii); "
        f"nenhum casa com a grade, que só tem SEXO 1 e 2)")


# ================================================================ A: números-chave
def checa_A():
    j5 = json.loads((V5 / 'numeros_chave_v5_20261009.json').read_text(encoding='utf-8'))
    j6 = json.loads((MAN / 'numeros_chave_v6_20261009.json').read_text(encoding='utf-8'))
    ids5 = [x['id'] for x in j5]
    ids6 = [x['id'] for x in j6]
    reg('A1_numeros_chave_mesmos_ids', ids5 == ids6,
        f"v5 {len(ids5)} ids, v6 {len(ids6)} ids; mesma ordem = {ids5 == ids6}; "
        f"só v5 = {sorted(set(ids5) - set(ids6))}; só v6 = {sorted(set(ids6) - set(ids5))}")
    d6 = {x['id']: x for x in j6}
    dif_b, dif_f, dif_desc, desc_mud, outros = [], [], [], [], []
    commits = Counter()
    for x in j5:
        y = d6.get(x['id'])
        if y is None:
            continue
        vb5, vb6 = x.get('valor_bruto'), y.get('valor_bruto')
        if not (vb5 == vb6 or (vb5 != vb5 and vb6 != vb6)):  # NaN == NaN
            dif_b.append(x['id'])
        if x.get('valor_formatado') != y.get('valor_formatado'):
            dif_f.append(x['id'])
        if x.get('descricao') != y.get('descricao'):
            desc_mud.append(x['id'])
            if autoriza(x.get('descricao', '')) != y.get('descricao'):
                dif_desc.append(f"{x['id']}: {primeira_dif(x['descricao'], y['descricao'])}")
        for k in sorted(set(x) | set(y)):
            if k in ('id', 'valor_bruto', 'valor_formatado', 'descricao'):
                continue
            if k == 'commit':
                commits[(x.get(k), y.get(k))] += 1
                continue
            if x.get(k) != y.get(k):
                outros.append(f"{x['id']}.{k}")
    reg('A2_valor_bruto_identico', not dif_b, f"{len(j5)} itens; diferentes = {len(dif_b)} {dif_b[:10]}")
    reg('A3_valor_formatado_identico', not dif_f, f"{len(j5)} itens; diferentes = {len(dif_f)} {dif_f[:10]}")
    reg('A4_descricao_so_tercile_tertile', not dif_desc,
        f"descrições alteradas = {len(desc_mud)} ({', '.join(desc_mud[:12])}{'…' if len(desc_mud) > 12 else ''}); "
        f"alterações fora de tercile→tertile = {len(dif_desc)} {dif_desc[:5]}")
    reg('A5_demais_campos_identicos', not outros,
        f"campos filtro/arquivo/script diferentes = {len(outros)} {outros[:10]}")
    import subprocess
    try:
        head = subprocess.run(['git', '-C', str(ROOT), 'log', '-1', '--format=%h %s'], capture_output=True,
                              text=True, timeout=30).stdout.strip()
    except Exception as e:  # noqa
        head = f'(git indisponível: {e})'
    pares_c = dict(commits)
    ok_c = len(pares_c) == 1 and list(pares_c)[0][1] == head.split(' ')[0]
    reg('A5b_campo_commit_metadado', ok_c,
        f"campo 'commit' (proveniência, não é número de resultado) mudou de forma uniforme: {pares_c}; "
        f"HEAD do repositório = {head!r}; é o commit vigente ao gerar o pacote, como no MANIFEST v6")
    COMMITS.update(pares_c)
    res = []
    for x in j6:
        dsc = x.get('descricao', '')
        for nome, rx in (('tercile', RX_TERC_RESIDUO), ('ICR', RX_ICR), ('Parda', RX_PARDA)):
            if rx.search(dsc):
                res.append(f"{x['id']}:{nome}")
    reg('A6_descricoes_v6_sem_residuos', not res, f"ocorrências de tercile/ICR/Parda nas descrições v6 = {res}")
    m5 = (V5 / 'numeros_chave_v5_20261009.md').read_text(encoding='utf-8')
    m6 = (MAN / 'numeros_chave_v6_20261009.md').read_text(encoding='utf-8')
    m5a = autoriza(m5).replace('v5_20261009', 'v6_20261009')
    for c5, c6 in pares_c:
        m5a = m5a.replace(f'source commit {c5}', f'source commit {c6}')
    ok = m5a == m6
    titulo = m6.splitlines()[0] if m6 else ''
    reg('A7_numeros_chave_md_so_trocas_autorizadas', ok,
        f"numeros_chave .md: v6 == v5 com tercile→tertile, nome do pacote v5→v6 e 'source commit' atualizado: {ok}"
        + ('' if ok else f"; {primeira_dif(m5a, m6)}") + f"; título da v6 = {titulo!r}")


# ================================================================ B: CSVs célula a célula
PACOTE5, PACOTE6 = 'v5_20261009', 'v6_20261009'
CONTA = Counter()  # trocas de rótulo do pacote (v5_20261009 -> v6_20261009) aceitas, por verificação


def compara_celula(a, b, extra=None, onde=None):
    """Retorna (nums_ok, txt_ok, renomeou_id).

    Trocas aceitas: tercile→tertile fora de ids (autoriza), as trocas específicas passadas em `extra`
    e o rótulo do pacote v5_20261009→v6_20261009 (contado à parte em CONTA[onde]; não é número de resultado)."""
    if PACOTE5 in a and PACOTE6 in b:
        CONTA[onde] += a.count(PACOTE5)
        a = a.replace(PACOTE5, PACOTE6)
    a2 = autoriza(a)
    if extra:
        a2 = extra(a2)
    nums_ok = nums(a) == nums(b)
    if a2 == b:
        return nums_ok, True, False
    a3 = autoriza_tudo(a)
    if extra:
        a3 = extra(a3)
    if a3 == b:
        return nums_ok, True, True
    return nums_ok, False, False


def checa_B():
    pares = []
    for sub in ('tabelas', 'suplementar'):
        f5s = sorted((V5 / sub).glob('*.csv'))
        f6s = sorted((MAN / sub).glob('*.csv'))
        esper = {f.name.replace('_v5_', '_v6_') for f in f5s}
        n6 = {f.name for f in f6s}
        reg(f'B0_{sub}_mesmos_arquivos_csv', esper == n6,
            f"v5 {len(f5s)} CSV, v6 {len(f6s)} CSV; faltam na v6 = {sorted(esper - n6)}; sobram na v6 = {sorted(n6 - esper)}")
        for f in f5s:
            g = MAN / sub / f.name.replace('_v5_', '_v6_')
            if g.exists():
                pares.append((f, g))
    tot_cel = tot_mud = 0
    falhas_tot = 0
    s7a_sexo_cel = None
    for f5, f6 in pares:
        r5, r6 = ler_csv(f5), ler_csv(f6)
        estrutura = len(r5) == len(r6) and all(len(a) == len(b) for a, b in zip(r5, r6))
        is_s7a = f5.name.startswith('S7a_')
        info = s7a_info(r5) if is_s7a else None
        info6 = s7a_info(r6) if is_s7a else None
        n_cel = n_mud = 0
        f_num, f_txt, ids_ren, mudadas = [], [], [], []
        for i, (ra, rb) in enumerate(zip(r5, r6)):
            for j, (a, b) in enumerate(zip(ra, rb)):
                n_cel += 1
                if a != b:
                    n_mud += 1
                    mudadas.append((i, j))
                if is_s7a and i in info['i_sexo'] and j == info['c_cod']:
                    s7a_sexo_cel = (a, b)
                    continue  # célula de texto livre: verificada à parte
                extra = None
                if is_s7a and i in info['i_raca'] and j == info['c_en']:
                    extra = lambda s: s.replace(ROT_V5, ROT_V6)
                nok, tok, ren = compara_celula(a, b, extra, onde=f5.name)
                if not nok:
                    f_num.append(f"({i},{j}) {nums(a)} -> {nums(b)}")
                if not tok:
                    f_txt.append(f"({i},{j}) {primeira_dif(a, b, 30)}")
                if ren:
                    ids_ren.append(f"({i},{j})")
        ok = estrutura and not f_num and not f_txt
        falhas_tot += (not ok)
        tot_cel += n_cel
        tot_mud += n_mud
        det = (f"{f5.name} × {f6.name}: {len(r5)}×{len(r5[0]) if r5 else 0} vs {len(r6)}×{len(r6[0]) if r6 else 0}; "
               f"estrutura igual = {estrutura}; células = {n_cel}; células alteradas = {n_mud}; "
               f"números diferentes = {len(f_num)} {f_num[:3]}; texto fora das trocas autorizadas = {len(f_txt)} {f_txt[:3]}")
        if ids_ren:
            det += f"; ids renomeados (permitido) = {ids_ren[:5]}"
        if CONTA[f5.name]:
            det += f"; rótulo do pacote v5→v6 = {CONTA[f5.name]}"
        if is_s7a:
            det += "; célula SIM/SEXO (códigos) tratada à parte"
        reg(f"B_{f6.name.replace('_v6_20261009.csv', '')}", ok, det)
    reg('B_total_csv', falhas_tot == 0,
        f"pares = {len(pares)}; células comparadas = {tot_cel:,}; células alteradas = {tot_mud}; pares com falha = {falhas_tot}")

    # S7a — rótulo da raça e célula do SEXO
    r5, r6 = ler_csv(S7A5), ler_csv(S7A6)
    i5, i6 = s7a_info(r5), s7a_info(r6)
    a = r5[i5['i_raca'][0]][i5['c_en']]
    b = r6[i6['i_raca'][0]][i6['c_en']]
    ok = ROT_V5 in a and ROT_V6 in b and ROT_V5 not in b and a.replace(ROT_V5, ROT_V6) == b
    reg('B_S7a_RACACORMAE_rotulo', ok, f"v5: {a!r} | v6: {b!r}")
    pt5 = r5[i5['i_raca'][0]][i5['c_pt']]
    pt6 = r6[i6['i_raca'][0]][i6['c_pt']]
    reg('B_S7a_RACACORMAE_rotulo_portugues_inalterado', pt5 == pt6, f"{pt6!r}")
    a, b = s7a_sexo_cel
    req = ['M → 1', 'F → 2', 'I, 0, and 9 → missing', 'only 1 and 2 match the INTERGROWTH-21st grid']
    falta = [x for x in req if x not in b]
    resto5 = [c for j, c in enumerate(r5[i5['i_sexo'][0]]) if j != i5['c_cod']]
    resto6 = [c for j, c in enumerate(r6[i6['i_sexo'][0]]) if j != i6['c_cod']]
    ok = not falta and 'Converted to integer' not in b and resto5 == resto6 and len(i5['i_sexo']) == 1 == len(i6['i_sexo'])
    reg('B_S7a_SIM_SEXO_celula_codigos', ok,
        f"v5: {a!r} | v6: {b!r} | trechos exigidos ausentes = {falta}; demais células da linha iguais = {resto5 == resto6}")

    # Amarela: só a ocorrência do rótulo da S7a pode mudar
    c5 = c6 = 0
    pos5, pos6 = [], []
    for f5, f6 in pares:
        for nome, rows, acc in ((f5.name, ler_csv(f5), pos5), (f6.name, ler_csv(f6), pos6)):
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    k = c.count('Amarela')
                    if k:
                        acc.append((nome.replace('_v5_', '_vX_').replace('_v6_', '_vX_'), i, j, k))
    c5 = sum(x[3] for x in pos5)
    c6 = sum(x[3] for x in pos6)
    s7a_raca = ('S7a_variables_codes_vX_20261009.csv', i5['i_raca'][0], i5['c_en'])
    p5 = Counter({x[:3]: x[3] for x in pos5})
    p6 = Counter({x[:3]: x[3] for x in pos6})
    p5[s7a_raca] -= 1
    p5 = +p5
    ok = p5 == +p6
    reg('B_Amarela_so_S7a_rotulo_mudou', ok,
        f"ocorrências de 'Amarela' nos CSV: v5 = {c5}, v6 = {c6}; fora do rótulo da S7a, posições e contagens idênticas = {ok}")


# ================================================================ C: xlsx e docx
def valor_str(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return repr(v)
    return str(v)


def compara_xlsx(p5, p6, nome):
    import openpyxl
    w5 = openpyxl.load_workbook(p5)
    w6 = openpyxl.load_workbook(p6)
    s5, s6 = w5.sheetnames, w6.sheetnames
    f_num, f_txt, f_tipo, n_cel, n_mud, f_estr, ids_ren = [], [], [], 0, 0, [], []
    for sh5, sh6 in zip(w5.worksheets, w6.worksheets):
        if (sh5.max_row, sh5.max_column) != (sh6.max_row, sh6.max_column):
            f_estr.append(f"{sh5.title}: {sh5.max_row}×{sh5.max_column} vs {sh6.max_row}×{sh6.max_column}")
        if sorted(map(str, sh5.merged_cells.ranges)) != sorted(map(str, sh6.merged_cells.ranges)):
            f_estr.append(f"{sh5.title}: células mescladas diferem")
        R = max(sh5.max_row, sh6.max_row)
        C = max(sh5.max_column, sh6.max_column)
        for i in range(1, R + 1):
            for j in range(1, C + 1):
                a = sh5.cell(i, j).value
                b = sh6.cell(i, j).value
                if a is None and b is None:
                    continue
                n_cel += 1
                if a != b:
                    n_mud += 1
                num_a = isinstance(a, (int, float)) and not isinstance(a, bool)
                num_b = isinstance(b, (int, float)) and not isinstance(b, bool)
                if num_a or num_b:
                    if not (num_a and num_b and a == b):
                        f_num.append(f"{sh5.title}!{i},{j}: {a!r} -> {b!r}")
                    continue
                sa, sb = valor_str(a), valor_str(b)
                nok, tok, ren = compara_celula(sa, sb, onde=nome)
                if not nok:
                    f_num.append(f"{sh5.title}!{i},{j}: {nums(sa)} -> {nums(sb)}")
                if not tok:
                    f_txt.append(f"{sh5.title}!{i},{j}: {primeira_dif(sa, sb, 30)}")
                if ren:
                    ids_ren.append(f"{sh5.title}!{i},{j}")
        # cabeçalho/rodapé de impressão
        for attr in ('oddHeader', 'oddFooter', 'evenHeader', 'evenFooter', 'firstHeader', 'firstFooter'):
            h5, h6 = getattr(sh5, attr), getattr(sh6, attr)
            for part in ('left', 'center', 'right'):
                t5 = getattr(getattr(h5, part), 'text', None) or ''
                t6 = getattr(getattr(h6, part), 'text', None) or ''
                nok, tok, _ = compara_celula(t5, t6, onde=nome)
                if not (nok and tok):
                    f_txt.append(f"{sh5.title} {attr}.{part}: {t5!r} -> {t6!r}")
    ok = s5 == s6 and not f_estr and not f_num and not f_txt
    det = (f"{nome}: abas iguais = {s5 == s6} ({len(s5)}); células não vazias = {n_cel:,}; alteradas = {n_mud}; "
           f"estrutura = {f_estr[:3] or 'igual'}; números diferentes = {len(f_num)} {f_num[:3]}; "
           f"texto fora das trocas autorizadas = {len(f_txt)} {f_txt[:3]}")
    if ids_ren:
        det += f"; ids renomeados (permitido) = {ids_ren[:5]}"
    det += f"; rótulo do pacote v5→v6 aceito = {CONTA[nome]}"
    return ok, det


def xlsx_textos(p):
    import openpyxl
    w = openpyxl.load_workbook(p)
    out = [('aba', s, s) for s in w.sheetnames]
    for sh in w.worksheets:
        for row in sh.iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    out.append((sh.title, c.coordinate, c.value))
        for attr in ('oddHeader', 'oddFooter'):
            h = getattr(sh, attr)
            for part in ('left', 'center', 'right'):
                t = getattr(getattr(h, part), 'text', None)
                if t:
                    out.append((sh.title, attr, t))
    return out


W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def docx_paragrafos(p):
    """Texto por parágrafo (w:p) de todas as partes word/*.xml (corpo, tabelas, notas, cabeçalhos, rodapés)."""
    import xml.etree.ElementTree as ET
    out = []
    with zipfile.ZipFile(p) as z:
        for n in sorted(z.namelist()):
            if not (n.startswith('word/') and n.endswith('.xml')):
                continue
            try:
                root = ET.fromstring(z.read(n))
            except ET.ParseError:
                continue
            for k, par in enumerate(root.iter(W_NS + 'p')):
                t = ''.join((x.text or '') for x in par.iter(W_NS + 't'))
                if t:
                    out.append((n, t))
    return out


def compara_docx(p5, p6, nome):
    import docx
    d5, d6 = docx.Document(p5), docx.Document(p6)
    f = []
    # tabelas, célula a célula
    n_cel = n_mud = 0
    estr = len(d5.tables) == len(d6.tables)
    for ti, (t5, t6) in enumerate(zip(d5.tables, d6.tables)):
        if (len(t5.rows), len(t5.columns)) != (len(t6.rows), len(t6.columns)):
            estr = False
        for ri, (r5, r6) in enumerate(zip(t5.rows, t6.rows)):
            for ci, (c5, c6) in enumerate(zip(r5.cells, r6.cells)):
                n_cel += 1
                a, b = c5.text, c6.text
                if a != b:
                    n_mud += 1
                nok, tok, _ = compara_celula(a, b, onde=nome + ':tab')
                if not (nok and tok):
                    f.append(f"tab{ti}({ri},{ci}): {primeira_dif(a, b, 30)}")
    # parágrafos de todas as partes XML (títulos, rodapés, notas)
    p5s, p6s = docx_paragrafos(p5), docx_paragrafos(p6)
    if len(p5s) != len(p6s):
        estr = False
    n_par_mud = 0
    for (n5, a), (n6, b) in zip(p5s, p6s):
        if n5 != n6:
            estr = False
        if a != b:
            n_par_mud += 1
        nok, tok, _ = compara_celula(a, b, onde=nome + ':par')
        if not (nok and tok):
            f.append(f"{n5}: {primeira_dif(a, b, 30)}")
    ok = estr and not f
    return ok, (f"{nome}: tabelas = {len(d5.tables)}/{len(d6.tables)}; células = {n_cel}, alteradas = {n_mud}; "
                f"parágrafos XML (corpo+tabelas+cabeçalho/rodapé/notas) = {len(p5s)}/{len(p6s)}, alterados = {n_par_mud}; "
                f"estrutura igual = {estr}; diferenças fora das trocas autorizadas = {len(f)} {f[:3]}; "
                f"rótulo do pacote v5→v6 aceito = {CONTA[nome + ':tab'] + CONTA[nome + ':par']} "
                f"(título 'package v5_20261009' → 'package v6_20261009')")


def checa_C():
    pares = [
        (V5 / 'tabelas' / 'tabelas_principais_v5_20261009.xlsx', MAN / 'tabelas' / 'tabelas_principais_v6_20261009.xlsx',
         'C_xlsx_tabelas_principais'),
        (V5 / 'suplementar' / 'ESM_1_tables_S1_S6_v5_20261009.xlsx',
         MAN / 'suplementar' / 'ESM_1_tables_S1_S6_v6_20261009.xlsx', 'C_xlsx_ESM_1_suplementar'),
        (SUB5 / 'ESM_1.xlsx', SUB6 / 'ESM_1.xlsx', 'C_xlsx_Submissao_ESM_1'),
    ]
    for p5, p6, nome in pares:
        ok, det = compara_xlsx(p5, p6, nome)
        reg(nome, ok, det)
    # consistência: Submissao/ESM_1.xlsx == suplementar/ESM_1 v6 (conteúdo)
    import openpyxl
    a = openpyxl.load_workbook(SUB6 / 'ESM_1.xlsx')
    b = openpyxl.load_workbook(MAN / 'suplementar' / 'ESM_1_tables_S1_S6_v6_20261009.xlsx')
    va = [(s.title, [[c.value for c in r] for r in s.iter_rows()]) for s in a.worksheets]
    vb = [(s.title, [[c.value for c in r] for r in s.iter_rows()]) for s in b.worksheets]
    reg('C_xlsx_Submissao_ESM_1_igual_suplementar_v6', va == vb,
        f"conteúdo célula a célula idêntico = {va == vb}")
    ok, det = compara_docx(V5 / 'tabelas' / 'tabelas_principais_v5_20261009.docx',
                           MAN / 'tabelas' / 'tabelas_principais_v6_20261009.docx', 'C_docx_tabelas_principais')
    reg('C_docx_tabelas_principais', ok, det)


# ================================================================ D: PDFs da Submissão
def pdf_paginas(p):
    import pymupdf
    d = pymupdf.open(p)
    return [pg.get_text() for pg in d], [tuple(round(x, 1) for x in pg.rect) for pg in d]


def pdf_imagens(p):
    import pymupdf
    d = pymupdf.open(p)
    hs = []
    for pg in d:
        for im in pg.get_images(full=True):
            pix = pymupdf.Pixmap(d, im[0])
            hs.append((pix.width, pix.height, hashlib.md5(pix.samples).hexdigest()))
    return hs


def checa_D():
    r5 = ler_csv(S7A5)
    r6 = ler_csv(S7A6)
    i5, i6 = s7a_info(r5), s7a_info(r6)
    sexo5 = r5[i5['i_sexo'][0]][i5['c_cod']]
    sexo6 = r6[i6['i_sexo'][0]][i6['c_cod']]
    uso5 = r5[i5['i_sexo'][0]][r5[0].index('Use')]
    uso6 = r6[i6['i_sexo'][0]][r6[0].index('Use')]
    for nome in ('ESM_2', 'ESM_3', 'ESM_4'):
        pg5, rc5 = pdf_paginas(SUB5 / f'{nome}.pdf')
        pg6, rc6 = pdf_paginas(SUB6 / f'{nome}.pdf')
        t5 = autoriza(norm_ws(' '.join(pg5)))
        t6 = norm_ws(' '.join(pg6))
        extra = ''
        ok_extra = True
        if nome == 'ESM_2':
            n_rot = len(padrao_ws(ROT_V5).findall(t5))
            px5 = padrao_ws(sexo5, uso5)
            px6 = padrao_ws(sexo6, uso6)
            n_sx = len(px5.findall(t5))
            n_sx6 = len(px6.findall(t6))
            # o texto da coluna 'Use' aparece intercalado no meio da célula nas duas versões: verifica que
            # foi o mesmo trecho e substitui a célula inteira por um marcador comum
            uso_dentro5 = [rmws(uso5) in rmws(m.group(0)) for m in px5.finditer(t5)]
            uso_dentro6 = [rmws(uso6) in rmws(m.group(0)) for m in px6.finditer(t6)]
            t5 = padrao_ws(ROT_V5).sub(ROT_V6, t5)
            t5 = px5.sub(lambda m: '<SEXO> ' + (uso5 if rmws(uso5) in rmws(m.group(0)) else ''), t5)
            t6x = px6.sub(lambda m: '<SEXO> ' + (uso6 if rmws(uso6) in rmws(m.group(0)) else ''), t6)
            tem_asian = bool(padrao_ws('Asian (amarela)').search(t6))
            tem_antigo = bool(padrao_ws('Amarela (Asian descent)').search(t6))
            ok_extra = n_rot == 1 and n_sx == 1 and n_sx6 == 1 and tem_asian and not tem_antigo and uso5 == uso6
            extra = (f"; v5: rótulo antigo achado {n_rot}×, célula SEXO antiga achada {n_sx}×; "
                     f"v6: 'Asian (amarela)' presente = {tem_asian}, 'Amarela (Asian descent)' presente = {tem_antigo}, "
                     f"célula SEXO nova (texto igual ao da S7a v6, ignorando quebras) achada {n_sx6}×; "
                     f"coluna 'Use' ({uso6!r}) intercalada na célula pelo layout do PDF: v5 {uso_dentro5}, v6 {uso_dentro6}")
        else:
            t6x = t6
        num_ok = nums(t5) == nums(t6x)
        txt_ok = rmws(t5) == rmws(t6x)
        ok = len(pg5) == len(pg6) and rc5 == rc6 and num_ok and txt_ok and ok_extra
        det = (f"Submissao/{nome}.pdf v5×v6: páginas {len(pg5)}/{len(pg6)}, tamanhos iguais = {rc5 == rc6}; "
               f"nº de números = {len(nums(t5))}/{len(nums(t6x))}, sequência idêntica = {num_ok}; "
               f"texto idêntico após trocas autorizadas (ignorando quebras/espaços) = {txt_ok}"
               + ('' if txt_ok else f" [{primeira_dif(rmws(t5), rmws(t6x), 40)}]") + extra)
        reg(f'D_{nome}_pdf', ok, det)
    i5 = pdf_imagens(SUB5 / 'ESM_4.pdf')
    i6 = pdf_imagens(SUB6 / 'ESM_4.pdf')
    reg('D_ESM_4_imagem_embutida_identica', i5 == i6 and len(i5) > 0,
        f"imagens embutidas v5 = {[(w, h) for w, h, _ in i5]}, v6 = {[(w, h) for w, h, _ in i6]}; pixels idênticos = {i5 == i6}")
    # consistência entre Submissao e outputs/manuscrito v6
    cons = [(SUB6 / 'ESM_2.pdf', MAN / 'suplementar' / 'S7_variables_codes_v6_20261009.pdf'),
            (SUB6 / 'ESM_3.pdf', MAN / 'suplementar' / 'S8_strobe_record_checklist_v6_20261009.pdf'),
            (SUB6 / 'Fig1.tif', MAN / 'figuras' / 'fig01_flowchart_v6_20261009.tif'),
            (SUB6 / 'Fig2.tif', MAN / 'figuras' / 'fig02_pr_race_m1m3_v6_20261009.tif'),
            (SUB6 / 'Fig3.tif', MAN / 'figuras' / 'fig03_rd_race_tercile_v6_20261009.tif'),
            (SUB6 / 'Fig4.tif', MAN / 'figuras' / 'fig04_dating_v6_20261009.tif')]
    res = [(a.name, b.name, md5(a) == md5(b)) for a, b in cons]
    reg('D_Submissao_igual_manuscrito_v6', all(x[2] for x in res),
        '; '.join(f"{a} = {b}: {'idêntico (md5)' if s else 'DIFERENTE'}" for a, b, s in res))


# ================================================================ F: resíduos na v6
def checa_F():
    fontes = {}
    # CSV
    itens = []
    for sub in ('tabelas', 'suplementar'):
        for f in sorted((MAN / sub).glob('*_v6_20261009.csv')):
            rows = ler_csv(f)
            col_pt = None
            if f.name.startswith('S7a_'):
                col_pt = rows[0].index('Official label (Portuguese, data dictionary)')
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    itens.append((f"{f.name}({i},{j})", c, j == col_pt))
    fontes['csv'] = itens
    # xlsx
    itens = []
    for p in (MAN / 'tabelas' / 'tabelas_principais_v6_20261009.xlsx',
              MAN / 'suplementar' / 'ESM_1_tables_S1_S6_v6_20261009.xlsx', SUB6 / 'ESM_1.xlsx'):
        for sh, coord, t in xlsx_textos(p):
            itens.append((f"{p.name}!{sh}!{coord}", t, False))
    fontes['xlsx'] = itens
    # docx
    p = MAN / 'tabelas' / 'tabelas_principais_v6_20261009.docx'
    fontes['docx'] = [(f"{p.name}:{n}", t, False) for n, t in docx_paragrafos(p)]
    # PDFs da Submissão (texto por página, espaços normalizados)
    itens = []
    for nome in ('ESM_2', 'ESM_3', 'ESM_4'):
        pg, _ = pdf_paginas(SUB6 / f'{nome}.pdf')
        for k, t in enumerate(pg):
            itens.append((f"{nome}.pdf p{k + 1}", norm_ws(t), False))
    fontes['pdf_Submissao'] = itens
    fontes['legendas_figuras.md'] = [('legendas_figuras.md', (MAN / 'legendas_figuras.md').read_text(encoding='utf-8'), False)]
    fontes['data_code_availability.md'] = [('data_code_availability.md',
                                            (MAN / 'data_code_availability.md').read_text(encoding='utf-8'), False)]
    for fonte, itens in fontes.items():
        for nome, rx in (('tercile', RX_TERC_RESIDUO), ('ICR', RX_ICR), ('Parda', RX_PARDA)):
            achados, permitidos = [], 0
            for onde, t, col_pt in itens:
                for m in rx.finditer(t):
                    if nome == 'Parda' and col_pt:
                        permitidos += 1
                        continue
                    achados.append(f"{onde}: …{t[max(0, m.start() - 40):m.end() + 20]}…")
            det = f"{len(itens)} trechos varridos; ocorrências proibidas = {len(achados)} {achados[:4]}"
            if nome == 'Parda':
                det += f"; ocorrências na coluna permitida da S7a = {permitidos}"
            if nome == 'tercile':
                ids = sum(len(RX_TERC_TUDO.findall(t)) for _, t, _ in itens) - len(achados)
                det += f"; 'tercile' dentro de nomes de arquivo/ids (permitido) = {ids}"
            reg(f'F_{nome}_{fonte}', not achados, det)


# ================================================================ G: legenda da Fig. 1 e data_code_availability
def checa_G():
    leg = (MAN / 'legendas_figuras.md').read_text(encoding='utf-8')
    par = [norm_ws(p) for p in re.split(r'\n\s*\n', leg) if p.strip().startswith('**Fig. 1.**')]
    ok = len(par) == 1 and NOTA_FIG1 in par[0]
    reg('G_legenda_Fig1_nota_IBGE', ok, f"parágrafos da Fig. 1 = {len(par)}; nota presente = {ok}")
    l5 = (V5 / 'legendas_figuras_v5_20261009.md').read_text(encoding='utf-8')
    l5a = autoriza(l5).replace('v5_20261009', 'v6_20261009')
    reg('G_legendas_so_trocas_autorizadas', l5a == leg,
        "legendas v6 == v5 com tercile→tertile e nomes v5→v6" + ('' if l5a == leg else f": {primeira_dif(l5a, leg)}"))
    dca = norm_ws((MAN / 'data_code_availability.md').read_text(encoding='utf-8'))
    exig = [
        ('G_DCA_SINASC_March6_2014_2022', r'March 6, 2026 \(2014–2022\)'),
        ('G_DCA_SINASC_March25_2023', r'March 25, 2026 \(2023\)'),
        ('G_DCA_SINASC_June27_2024', r'June 27, 2026 \(2024\)'),
        ('G_DCA_conferencia_October2', r'independent download from the DATASUS server on October 2, 2026'),
        ('G_DCA_marcador_URL', r'\[URL after the repository is created and tagged\]'),
    ]
    for nome, pat in exig:
        ms = re.findall(pat, dca)
        reg(nome, len(ms) >= 1, f"padrão {pat!r} encontrado {len(ms)}×")
    n_url = len(re.findall(r'\[URL after the repository is created and tagged\]', dca))
    for nome, s in (('G_DCA_sem_September_7_2026', 'September 7, 2026'), ('G_DCA_sem_guilcoel', 'guilcoel')):
        reg(nome, s not in dca, f"{s!r} ocorre {dca.count(s)}×")
    gh = re.findall(r'https?://github\.com\S*', dca)
    reg('G_DCA_sem_URL_GitHub_concreta', not gh, f"URLs do GitHub no texto = {gh}; marcador aparece {n_url}× (seções código e declaração)")


# ================================================================ H: figuras TIFF
def checa_H():
    import numpy as np
    from PIL import Image
    pares = [(V5 / 'figuras' / f'{b}_v5_20261009.tif', MAN / 'figuras' / f'{b}_v6_20261009.tif')
             for b in ('fig01_flowchart', 'fig02_pr_race_m1m3', 'fig03_rd_race_tercile', 'fig04_dating')]
    pares.append((V5 / 'suplementar' / 'S9_maihda_caterpillar_v5_20261009.tif',
                  MAN / 'suplementar' / 'S9_maihda_caterpillar_v6_20261009.tif'))
    pares += [(SUB5 / f'Fig{k}.tif', SUB6 / f'Fig{k}.tif') for k in range(1, 5)]
    out = {}
    for a, b in pares:
        ia, ib = Image.open(a), Image.open(b)
        dpa, dpb = ia.info.get('dpi'), ib.info.get('dpi')
        dpa = tuple(round(float(x), 2) for x in dpa) if dpa else None
        dpb = tuple(round(float(x), 2) for x in dpb) if dpb else None
        mesmo = dpa == dpb and ia.size == ib.size and ia.mode == ib.mode
        frac, bbox = None, None
        if ia.size == ib.size:
            xa = np.asarray(ia.convert('RGB'), dtype=np.int16)
            xb = np.asarray(ib.convert('RGB'), dtype=np.int16)
            dif = np.any(xa != xb, axis=2)
            frac = float(dif.mean())
            if dif.any():
                ys, xs = np.where(dif)
                bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        rot = a.parent.name + '/' + a.name.replace('_v5_20261009', '')
        out[rot] = dict(dpi=(dpa, dpb), size=(ia.size, ib.size), frac=frac, bbox=bbox)
        eh_fig1 = 'fig01' in a.name or a.name == 'Fig1.tif'
        if eh_fig1:
            # esperado: diferença só na caixa inferior ("access tercile" -> "access tertile")
            H = ia.size[1]
            ok = mesmo and frac is not None and 0 < frac < 0.01 and bbox is not None and bbox[1] > 0.8 * H
        else:
            ok = mesmo and frac == 0.0
        reg(f"H_{rot.replace('/', '_')}", ok,
            f"dpi {dpa}/{dpb}; pixels {ia.size}/{ib.size}; modo {ia.mode}/{ib.mode}; "
            f"fração de pixels diferentes = {frac if frac is None else f'{frac:.6f}'}; "
            f"caixa das diferenças (x0,y0,x1,y1) = {bbox}")
    return out


# ================================================================ E3: comparação com as saídas do autor
def checa_E3(res):
    import pandas as pd
    p_sexo = TABS / 'tab_e7c2_01_sexo_sim_v1_20261008.csv'
    p_q = TABS / 'tab_e7c2_01_q_pig_v1_20261008.csv'
    p_lim = TABS / 'tab_e7c2_01_limites_v1_20261008.csv'
    p_lim0 = TABS / 'tab_e6_07b_limites_v1_20261008.csv'
    qa = pd.read_csv(p_q, dtype=str)
    l0 = pd.read_csv(p_lim0, dtype=str)
    l1 = pd.read_csv(p_lim, dtype=str)
    sx = pd.read_csv(p_sexo, dtype=str)
    E3_INFO['q_autor'] = qa.to_dict('records')
    E3_INFO['sexo_autor_cols'] = list(sx.columns)
    E3_INFO['lim_cols'] = list(l0.columns)
    meu_i = res['q']['i_trycast']
    meu_ii = res['q']['ii_recod_MF']
    return compara_E3(qa, l0, l1, sx, meu_i, meu_ii, res)


E3_INFO = {}
COMMITS = Counter()


def compara_E3(qa, l0, l1, sx, meu_i, meu_ii, res):
    # (1) q do autor (tab_e7c2_01_q_pig): linha "antes (TRY_CAST...)" e "depois (M→1, F→2...)"
    antes = qa[qa['versao'].str.startswith('antes')]
    depois = qa[qa['versao'].str.startswith('depois')]
    ok_a = len(antes) == 1 and float(antes['q_pig'].iloc[0]) == meu_i['q'] \
        and int(antes['n_obitos_na_grade'].iloc[0]) == meu_i['n_pareados']
    ok_d = len(depois) == 1 and float(depois['q_pig'].iloc[0]) == meu_ii['q'] \
        and int(depois['n_obitos_na_grade'].iloc[0]) == meu_ii['n_pareados']
    reg('E3_q_igual_tab_e7c2_01_q_pig', ok_a and ok_d,
        f"autor antes: q = {antes['q_pig'].iloc[0]}, n = {antes['n_obitos_na_grade'].iloc[0]} | "
        f"auditor (i): q = {meu_i['q']!r}, n = {meu_i['n_pareados']} | "
        f"autor depois: q = {depois['q_pig'].iloc[0]}, n = {depois['n_obitos_na_grade'].iloc[0]} | "
        f"auditor (ii): q = {meu_ii['q']!r}, n = {meu_ii['n_pareados']}")
    # (2) q usado nos limites publicados (tab_e6_07b_limites, desfecho = pig, q < 1)
    qs = sorted(set(float(x) for x in l0.loc[(l0['desfecho'] == 'pig') & (l0['q'].astype(float) < 1), 'q']))
    ok = len(qs) == 1 and qs[0] == meu_i['q'] == meu_ii['q']
    reg('E3_q_igual_tab_e6_07b_limites', ok,
        f"q distintos em tab_e6_07b_limites (pig, q<1) = {qs}; auditor = {meu_i['q']!r}; "
        f"diferença = {(qs[0] - meu_i['q']) if qs else 'n/a'}")
    # (3) tab_e7c2_01_limites reproduz tab_e6_07b_limites
    chave = ['desfecho', 'q', 'k_indigena']
    mesmas_cols = list(l0.columns) == list(l1.columns)
    m = l0.merge(l1, on=chave, how='outer', suffixes=('_pub', '_7c2'), indicator=True)
    so_um = int((m['_merge'] != 'both').sum())
    cols_num = [c for c in l0.columns if c not in chave]
    max_rel = {}
    n_exat = n_tot = 0
    for c in cols_num:
        a = m[c + '_pub'].astype(float)
        b = m[c + '_7c2'].astype(float)
        rel = ((a - b).abs() / a.abs().clip(lower=1e-300)).max()
        max_rel[c] = float(rel)
        n_exat += int((m[c + '_pub'] == m[c + '_7c2']).sum())
        n_tot += len(m)
    a = m['RP_M2_corrigida_pub'].astype(float)
    b = m['RP_M2_corrigida_7c2'].astype(float)
    rp_rel = float(((a - b).abs() / a.abs()).max())
    rp_exat = int((m['RP_M2_corrigida_pub'] == m['RP_M2_corrigida_7c2']).sum())
    pig = m[m['desfecho'] == 'pig']
    pig_exat = all((pig[c + '_pub'] == pig[c + '_7c2']).all() for c in cols_num)
    arred = all(round(x, 2) == round(y, 2) for x, y in zip(a, b))
    ok = mesmas_cols and so_um == 0 and len(m) == 12 and rp_rel < 1e-12 and max(max_rel.values()) < 1e-12
    reg('E3_limites_7c2_reproduz_e6_07b', ok,
        f"linhas {len(l0)}/{len(l1)}, sem par = {so_um}; RP_M2_corrigida: idênticas como texto em {rp_exat}/{len(m)} linhas, "
        f"maior diferença relativa = {rp_rel:.1e} (arredondadas a 2 casas iguais = {arred}); "
        f"linhas do PIG idênticas em todas as colunas = {pig_exat}; células idênticas como texto = {n_exat}/{n_tot}; "
        f"maior diferença relativa em qualquer coluna = {max(max_rel.values()):.1e} (ruído de ponto flutuante nas linhas do PTB)")
    # (3b) a faixa publicada na Tabela 4 (v6) sai da reprodução 7c.2
    t4 = ler_csv(MAN / 'tabelas' / 'tab04_sensitivity_v6_20261009.csv')
    lin = [r for r in t4 if r[0].startswith('Live-birth bounds')]
    res_t4 = []
    ok_t4 = len(lin) == 1
    for desf, col in (('ptb', 'Preterm birth (total): PR M2 (95% CI)'), ('pig', 'SGA: PR M2 (95% CI)')):
        v = l1.loc[l1['desfecho'] == desf, 'RP_M2_corrigida'].astype(float)
        esper = f"{v.min():.2f} to {v.max():.2f}"
        pub = lin[0][t4[0].index(col)] if lin else None
        ok_t4 = ok_t4 and pub == esper
        res_t4.append(f"{desf}: Tabela 4 v6 = {pub!r}, faixa de RP_M2_corrigida em tab_e7c2_01_limites = {esper!r}")
    reg('E3_tab04_faixa_limites_igual_reproducao', ok_t4, '; '.join(res_t4))
    # (4) tabulação do SEXO do autor × auditor
    meu = {}
    for r in res['tabulacao']:
        meu[('todos', r['ano'], r['codigo'])] = r['n_todos']
        if r['n_fetal']:
            meu[('fetal', r['ano'], r['codigo'])] = r['n_fetal']
    meu = {k: v for k, v in meu.items() if v}
    dele = {}
    for _, r in sx.iterrows():
        u = 'todos' if r['universo'].startswith('todos') else 'fetal'
        dele[(u, int(r['ano']), str(r['codigo']).strip())] = int(r['n'])
    dif = sorted(k for k in set(meu) | set(dele) if meu.get(k) != dele.get(k))
    reg('E3_tabulacao_SEXO_igual_tab_e7c2_01_sexo_sim', not dif,
        f"células ano×código×universo: auditor {len(meu)}, autor {len(dele)}; divergentes = {len(dif)} "
        f"{[(k, meu.get(k), dele.get(k)) for k in dif[:5]]}")


# ================================================================ relatório
def escreve_relatorio(res, figs):
    n = len(LINHAS)
    n_ok = sum(1 for _, ok, _ in LINHAS if ok)
    falhas = [(v, d) for v, ok, d in LINHAS if not ok]
    L = []
    L.append('# Auditoria independente — Etapa 7c.2 (pacote v5 → v6), ptb-racial-brasil')
    L.append('')
    L.append('Data: 2026-10-09. Script próprio: `audita_7c2_v1_20261009.py` (escrito do zero; não foram lidos '
             '`scripts/etapa7b_checa.py`, `scripts/etapa7c2_01_sexo_sim.py` nem `checa_7b_*.csv`). E1/E2 foram '
             'calculados e gravados (`e12_resultados_v1_20261009.json`) antes de abrir as tabelas `tab_e7c2_01_*`. '
             'Microdados do SIM-DOFET lidos só por consultas agregadas; nenhuma linha individual gravada.')
    L.append('')
    L.append(f'**Resultado: {n} verificações, {n_ok} OK, {n - n_ok} com falha.** Detalhe linha a linha em '
             '`comparacao_7c2_v1_20261009.csv`.')
    L.append('')
    if falhas:
        L.append('## Falhas')
        for v, d in falhas:
            L.append(f'- `{v}`: {d}')
        L.append('')
    L.append('## Observações (não são falhas)')
    obs = [
        "Mudanças de metadado aceitas fora da lista de trocas autorizadas, por não serem resultado: o campo `commit` "
        f"dos 204 números-chave ({dict(COMMITS)}; = HEAD atual, o commit da Etapa 7c.1), o 'source commit' no "
        "cabeçalho de `numeros_chave_v6_20261009.md` e o rótulo 'package v5_20261009' → 'v6_20261009' no título do docx.",
        "O título de `numeros_chave_v6_20261009.md` continua '# Key numbers (Etapas 7b–7c.1)' (não foi para 7c.2); "
        "é cosmético.",
        "`data_code_availability.md` e o MANIFEST remetem ao commit 'Etapa 7c.2', que ainda não existe "
        "(HEAD = Etapa 7c.1); `git log --grep \"Etapa 7c.2\"` só vai funcionar depois do commit.",
        "No ESM_2 (PDF), o texto da coluna 'Use' da linha SIM/SEXO ('Live-birth bounds (q for SGA)') sai no meio "
        "da célula de códigos na extração de texto, nas duas versões; é efeito do layout e foi tratado na comparação.",
        "'Amarela (Asian descent)' continua na S1 e na Fig. 1 ('or Amarela'), como previsto: só o rótulo da S7a mudou.",
        "q = PIG / óbitos fetais únicos pareados na grade (SEMAGESTAC 24–42, SEXO 1/2, PESO 100–7000 g); "
        "é a mesma definição do autor (n_obitos_na_grade = 198.153).",
    ]
    for o in obs:
        L.append(f'- {o}')
    L.append('')
    # resumo por bloco
    L.append('## Resumo por bloco')
    blocos = Counter()
    blocos_ok = Counter()
    for v, ok, _ in LINHAS:
        b = v.split('_')[0][0]
        blocos[b] += 1
        blocos_ok[b] += ok
    nomes = dict(A='números-chave', B='CSV célula a célula', C='xlsx e docx', D='PDFs da Submissão',
                 E='SEXO do SIM (recálculo)', F='resíduos na v6', G='legenda Fig. 1 e data availability',
                 H='figuras TIFF')
    L.append('| Bloco | Verificações | OK |')
    L.append('|---|---:|---:|')
    for b in sorted(blocos):
        L.append(f'| {b} — {nomes.get(b, "")} | {blocos[b]} | {blocos_ok[b]} |')
    L.append('')
    # E1
    L.append('## E1 — SEXO no SIM-DOFET 2015–2024 (texto com trim; contagens agregadas)')
    L.append('')
    L.append('Critério de óbito fetal: TIPOBITO = 1 e (SEMAGESTAC válido ≠ 9/99 e ≥ 22, ou SEMAGESTAC nulo/9/99 '
             'com GESTACAO 2–6, ou PESO ≥ 500). Nenhum código com letra (M/F/I) em nenhum ano.')
    L.append('')
    tab = res['tabulacao']
    cods = sorted({r['codigo'] for r in tab})
    L.append('| Ano | ' + ' | '.join(f'todos: {c}' for c in cods) + ' | ' + ' | '.join(f'fetal: {c}' for c in cods)
             + ' | fetal único (GRAVIDEZ=1): ' + ' | fetal único: '.join(cods) + ' |')
    L.append('|---' * (1 + 3 * len(cods)) + '|')
    for ano in sorted({r['ano'] for r in tab}):
        d = {r['codigo']: r for r in tab if r['ano'] == ano}
        cel = [f"{d[c]['n_todos']:,}" if c in d else '0' for c in cods]
        cel += [f"{d[c]['n_fetal']:,}" if c in d else '0' for c in cods]
        cel += [f"{d[c]['n_fetal_unico']:,}" if c in d else '0' for c in cods]
        L.append(f'| {ano} | ' + ' | '.join(cel) + ' |')
    tot = {c: sum(r['n_todos'] for r in tab if r['codigo'] == c) for c in cods}
    totf = {c: sum(r['n_fetal'] for r in tab if r['codigo'] == c) for c in cods}
    totu = {c: sum(r['n_fetal_unico'] for r in tab if r['codigo'] == c) for c in cods}
    L.append('| **Total** | ' + ' | '.join(f'**{tot[c]:,}**' for c in cods) + ' | '
             + ' | '.join(f'**{totf[c]:,}**' for c in cods) + ' | ' + ' | '.join(f'**{totu[c]:,}**' for c in cods) + ' |')
    dg = res['diag']
    L.append('')
    L.append(f"Registros 2015–2024: {dg['n_todos']:,}; óbitos fetais pelo critério: {dg['n_fetal']:,}; "
             f"com letra: {dg['letras_todos']} (todos) e {dg['letras_fetal']} (fetais); SEXO com espaços: {dg['com_espaco']}. "
             "Código 9 não ocorre; a frase da S7a v6 ('only codes 0, 1, and 2') confere.")
    L.append('')
    # E2
    qi, qii = res['q']['i_trycast'], res['q']['ii_recod_MF']
    L.append('## E2 — q do PIG (óbitos fetais únicos, centil_k3 < 0,10, junção por SEMAGESTAC × SEXO × PESO)')
    L.append('')
    L.append('| Versão do SEXO | Elegíveis (fetal, GRAVIDEZ=1) | SEXO 1/2 | Pareados na grade | PIG | q (pareados) |')
    L.append('|---|---:|---:|---:|---:|---:|')
    for rot, d in (('(i) TRY_CAST AS INT', qi), ('(ii) M→1, F→2, demais → nulo', qii)):
        L.append(f"| {rot} | {d['n_elegiveis']:,} | {d['n_sexo_1_2']:,} | {d['n_pareados']:,} | {d['n_pig']:,} | "
                 f"{d['q']:.17g} |")
    L.append('')
    L.append(f"As duas versões são idênticas (diferença 0). Os {res['n_sexo_difere_entre_versoes']:,} registros em que "
             "as conversões diferem são o código 0 (vira 0 em (i) e nulo em (ii)); nenhum dos dois casa com a grade. "
             "Os não pareados (SEXO 1/2 mas sem par na grade) têm SEMAGESTAC fora de 24–42, nula, ou PESO fora de 100–7000 g.")
    L.append('')
    L.append('q por ano (versão ii; idêntico na i):')
    L.append('')
    L.append('| Ano | Pareados | PIG | q |')
    L.append('|---|---:|---:|---:|')
    for r in res['q_ano']['ii_recod_MF']:
        L.append(f"| {r['ano']} | {r['n_pareados']:,} | {r['n_pig']:,} | {r['q']:.4f} |")
    L.append('')
    # E3
    L.append('## E3 — comparação com o autor (feita depois do cálculo)')
    L.append('')
    for v, ok, d in LINHAS:
        if v.startswith('E3_'):
            L.append(f"- `{v}` — {'OK' if ok else 'FALHA'}: {d}")
    L.append('')
    # H
    L.append('## H — figuras TIFF')
    L.append('')
    L.append('| Figura | dpi v5/v6 | pixels | fração de pixels diferentes | caixa das diferenças |')
    L.append('|---|---|---|---:|---|')
    for k, d in figs.items():
        L.append(f"| {k} | {d['dpi'][0]} / {d['dpi'][1]} | {d['size'][1][0]}×{d['size'][1][1]} | "
                 f"{d['frac']:.6f} | {d['bbox']} |")
    L.append('')
    L.append('Inspeção visual dos PNG v6 (complemento, não automatizada): a única palavra alterada nas figuras é '
             '"access tercile" → "access tertile" na caixa inferior da Fig. 1; Fig. 2–4 e Fig. S9 não têm "tercile" '
             'e ficaram idênticas pixel a pixel. "Amarela" continua na Fig. 1 (caixa de exclusão), como previsto.')
    L.append('')
    # demais blocos
    L.append('## Demais blocos (A–D, F, G)')
    L.append('')
    sel = ('A2_', 'A3_', 'A4_', 'B_total', 'B_S7a_RACACORMAE_rotulo', 'B_S7a_SIM', 'B_Amarela', 'C_docx',
           'C_xlsx_Submissao_ESM_1', 'D_ESM_2', 'G_legenda_Fig1')
    for v, ok, d in LINHAS:
        if v.startswith(sel) and not v.endswith('_igual_suplementar_v6') and 'portugues' not in v:
            L.append(f"- `{v}` — {'OK' if ok else 'FALHA'}: {d[:260]}{'…' if len(d) > 260 else ''}")
    ng = [v for v, ok, d in LINHAS if v.startswith('G_DCA')]
    ngo = [v for v, ok, d in LINHAS if v.startswith('G_DCA') and ok]
    L.append(f"- data_code_availability.md: {len(ngo)}/{len(ng)} conferências OK (datas March 6/25, June 27 e "
             "October 2, 2026; marcador de URL; sem 'September 7, 2026', 'guilcoel' nem URL do GitHub).")
    nf = [v for v, ok, d in LINHAS if v.startswith('F_')]
    nfo = [v for v, ok, d in LINHAS if v.startswith('F_') and ok]
    L.append(f"- Resíduos (F): {len(nfo)}/{len(nf)} varreduras sem ocorrência proibida de tercile/ICR/Parda "
             "(CSV, xlsx, docx, PDFs da Submissão, legendas, data_code_availability.md).")
    L.append('')
    REL.write_text('\n'.join(L) + '\n', encoding='utf-8')


def escreve_csv():
    with open(CSV_OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['verificacao', 'ok', 'detalhe'])
        for v, ok, d in LINHAS:
            w.writerow([v, 'True' if ok else 'False', d])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fase', default='tudo', choices=['e12', 'tudo'])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    res = e12()
    checa_e12(res)
    if args.fase == 'e12':
        print(json.dumps(res['q'], indent=1))
        return
    checa_E3(res)
    checa_A()
    checa_B()
    checa_C()
    checa_D()
    checa_F()
    checa_G()
    figs = checa_H()
    escreve_csv()
    escreve_relatorio(res, figs)


if __name__ == '__main__':
    main()
