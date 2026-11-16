#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria independente da Etapa 7c.1 (pacote v4 -> v5, ptb-racial-brasil).

Escrito do zero pelo auditor; NAO usa scripts/etapa7b_checa.py nem checa_7b_*.csv.
Somente leitura fora de audit_independente/etapa7c1/.

Saida: comparacao_7c1_v1_20261009.csv (verificacao, ok, detalhe)
"""
import csv
import collections
import difflib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import docx
import numpy as np
import openpyxl
import pymupdf
from PIL import Image, ImageChops

Image.MAX_IMAGE_PIXELS = None

ROOT = Path('/Volumes/Forja/ptb-racial-brasil')
MS = ROOT / 'outputs/manuscrito'
V4 = MS / '_arquivo_v4'
SUB4 = V4 / 'Submissao'
SUB5 = ROOT / 'Submissao'
SRC = ROOT / 'outputs/tables'
OUT = ROOT / 'audit_independente/etapa7c1'
OUT_CSV = OUT / 'comparacao_7c1_v1_20261009.csv'

NOTE = ("Brown (parda) and Black (preta) follow the Brazilian Institute of Geography and Statistics "
        "categories; race/skin color is analyzed as a marker of exposure to structural racism.")
DEF_T3 = ("IC = risk difference (group vs White) within tercile k minus the same difference within T3, "
          "per 100 live births; RERI = relative excess risk due to interaction.")
EXTENDED = "extended model"

RACES = ['White', 'Brown', 'Black', 'Indigenous']
RANK = {r: i for i, r in enumerate(RACES)}

RESULTS = []


def add(verificacao, ok, detalhe):
    RESULTS.append((verificacao, bool(ok), str(detalhe)))
    print(('OK   ' if ok else 'FALHA'), verificacao, '|', str(detalhe)[:300])


# ----------------------------------------------------------------------------
# utilitarios
# ----------------------------------------------------------------------------
NUM_RE = re.compile(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?')
VERSION_TAG = re.compile(r'v\d+_\d{8}')


def nums(s):
    """Sequencia de numeros de um texto: milhar com virgula, decimal com ponto,
    sinal de menos '−' ou '-' so quando nao vem colado a letra/digito."""
    if s is None:
        return []
    s = str(s)
    out = []
    for m in NUM_RE.finditer(s):
        tok = m.group(0).replace(',', '')
        i = m.start()
        if i > 0 and s[i - 1] in '−-':
            prev = s[i - 2] if i > 1 else ' '
            if not prev.isalnum():
                tok = '-' + tok
        out.append(tok)
    return out


def nums_noversion(s):
    return nums(VERSION_TAG.sub(' ', str(s or '')))


def subst(s):
    """Trocas autorizadas (itens 1 e 2)."""
    if s is None:
        return s
    s = str(s)
    s = re.sub(r'\bICR\b', 'IC', s)
    s = s.replace('Parda', 'Brown')
    return s


def norm_ws(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def nows(s):
    return re.sub(r'\s+', '', str(s or ''))


def is_excl2024(row):
    return any('Excluding 2024' in str(c) for c in row if c is not None)


def read_csv(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def word_delta(a, b, maxlen=600):
    """Diferencas de palavras entre a (v4 com trocas autorizadas) e b (v5)."""
    aw, bw = a.split(), b.split()
    sm = difflib.SequenceMatcher(a=aw, b=bw, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        parts.append(f"[{tag}] -'{' '.join(aw[i1:i2])}' +'{' '.join(bw[j1:j2])}'")
    s = '; '.join(parts)
    return s if len(s) <= maxlen else s[:maxlen] + ' ...'


def lead_race(cell):
    m = re.match(r'\s*(White|Brown|Black|Indigenous)\b', str(cell or ''))
    return m.group(1) if m else None


# Rodada 2: reordenacao autorizada da Tabela 2 (White (reference) primeiro em cada bloco de desfecho)
TAB2_NAMES = ('tab02_models_m1m3',)


def white_first(rows):
    """Em cada sequencia contigua de linhas cujo rotulo (col. 1) comeca por uma raca, move as linhas
    'White' para o inicio (ordenacao estavel). Retorna (linhas reordenadas, n de linhas White movidas)."""
    out, run, moved = [], [], 0

    def race_v4(cell):  # na v4 o rotulo ainda e 'Parda'
        m = re.match(r'\s*(White|Parda|Brown|Black|Indigenous)\b', str(cell or ''))
        return m.group(1) if m else None

    def flush():
        nonlocal moved
        if run:
            w = [r for r in run if race_v4(r[0]) == 'White']
            o = [r for r in run if race_v4(r[0]) != 'White']
            if w and run[0] is not w[0]:
                moved += len(w)
            out.extend(w + o)
            run.clear()

    for r in rows:
        if r and race_v4(r[0]):
            run.append(r)
        else:
            flush()
            out.append(r)
    flush()
    return out, moved


# ----------------------------------------------------------------------------
# comparacao generica de grades (CSV, corpo de xlsx, tabelas docx)
# ----------------------------------------------------------------------------
def compare_grid(rows4, rows5, label):
    """Compara celula a celula. Remove de v4 so linhas 'Excluding 2024'.
    Retorna dict com contagens e lista de diferencas."""
    removed = [r for r in rows4 if is_excl2024(r)]
    rows4f = [r for r in rows4 if not is_excl2024(r)]
    diffs_num, diffs_txt, shape = [], [], []
    cells = 0
    if any(is_excl2024(r) for r in rows5):
        shape.append('v5 ainda contem linha Excluding 2024')
    if len(rows4f) != len(rows5):
        shape.append(f'n linhas v4(sem Excl.2024)={len(rows4f)} != v5={len(rows5)}')
    for i, (r4, r5) in enumerate(zip(rows4f, rows5)):
        if len(r4) != len(r5):
            shape.append(f'linha {i + 1}: n colunas {len(r4)} != {len(r5)}')
        for j in range(max(len(r4), len(r5))):
            c4 = r4[j] if j < len(r4) else None
            c5 = r5[j] if j < len(r5) else None
            cells += 1
            # celulas numericas nativas (xlsx)
            if isinstance(c4, (int, float)) and not isinstance(c4, bool) or \
               isinstance(c5, (int, float)) and not isinstance(c5, bool):
                same = (type(c4) == type(c5)) and (c4 == c5 or (isinstance(c4, float) and isinstance(c5, float)
                                                                  and math.isnan(c4) and math.isnan(c5)))
                if not same:
                    diffs_num.append(f'L{i + 1}C{j + 1}: {c4!r} -> {c5!r}')
                continue
            s4 = '' if c4 is None else str(c4)
            s5 = '' if c5 is None else str(c5)
            if nums(s4) != nums(s5):
                diffs_num.append(f'L{i + 1}C{j + 1}: {nums(s4)} -> {nums(s5)}')
            if subst(s4) != s5:
                diffs_txt.append(f"L{i + 1}C{j + 1}: '{s4[:80]}' -> '{s5[:80]}'")
    return dict(removed=removed, cells=cells, diffs_num=diffs_num, diffs_txt=diffs_txt, shape=shape,
                nrows4=len(rows4), nrows5=len(rows5))


# ----------------------------------------------------------------------------
# A. numeros-chave
# ----------------------------------------------------------------------------
def check_A():
    a = json.load(open(V4 / 'numeros_chave_v4_20261009.json', encoding='utf-8'))
    b = json.load(open(MS / 'numeros_chave_v5_20261009.json', encoding='utf-8'))
    da = {x['id']: x for x in a}
    db = {x['id']: x for x in b}
    dup = (len(da) != len(a)) or (len(db) != len(b))
    only4 = sorted(set(da) - set(db))
    only5 = sorted(set(db) - set(da))
    ok_ids = (len(only4) == 3 and all('sem_2024' in k for k in only4) and not only5 and not dup)
    add('A1. Numeros-chave: ids v5 = v4 menos os 3 ids sem_2024', ok_ids,
        f'n v4={len(a)}, n v5={len(b)}; so em v4={only4}; so em v5={only5}; ids duplicados={dup}; '
        f'ids sem_2024 restantes em v5={[k for k in db if "sem_2024" in k]}')

    common = [k for k in da if k in db]
    bad_bruto, bad_fmt = [], []
    for k in common:
        x, y = da[k]['valor_bruto'], db[k]['valor_bruto']
        same = (x == y) or (isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y))
        if not same or type(x) != type(y):
            bad_bruto.append(f'{k}: {x!r} -> {y!r}')
        if da[k]['valor_formatado'] != db[k]['valor_formatado']:
            bad_fmt.append(f"{k}: {da[k]['valor_formatado']!r} -> {db[k]['valor_formatado']!r}")
    add('A2. Numeros-chave: valor_bruto e valor_formatado identicos em todos os ids comuns',
        not bad_bruto and not bad_fmt,
        f'{len(common)} ids comparados; valor_bruto diferentes={len(bad_bruto)} {bad_bruto[:5]}; '
        f'valor_formatado diferentes={len(bad_fmt)} {bad_fmt[:5]}')

    # descricoes
    def desc_map(s):
        s = re.sub(r'\bICR\b', 'IC', s)
        for o, n in [('Parda', 'Brown'), ('Branca', 'White'), ('Preta', 'Black'), ('Indigena', 'Indigenous')]:
            s = s.replace(o, n)
        s = re.sub(r'(White|Brown|Black|Indigenous)-T(\d)', r'\1–T\2', s)
        return s

    changed = [k for k in common if da[k]['descricao'] != db[k]['descricao']]
    unexpl = [f"{k}: {da[k]['descricao']!r} -> {db[k]['descricao']!r}" for k in changed
              if desc_map(da[k]['descricao']) != db[k]['descricao']]
    cat = collections.Counter()
    for k in changed:
        d4 = da[k]['descricao']
        if re.search(r'\bICR\b', d4):
            cat['ICR->IC'] += 1
        for o, n in [('Parda', 'Brown'), ('Branca', 'White'), ('Preta', 'Black'), ('Indigena', 'Indigenous')]:
            if o in d4:
                cat[f'{o}->{n}'] += 1
        if re.search(r'(Parda|Branca|Preta|Indigena)-T\d', d4):
            cat["hifen '-T' -> travessao '–T'"] += 1
    resid = [f"{k}: {db[k]['descricao']}" for k in db
             if re.search(r'\bICR\b|Parda|Branca|Preta|Indigena', db[k]['descricao'])]
    add('A3. Numeros-chave: descricoes alteradas so por troca de rotulo (sem residuo ICR/Parda nas descricoes v5)',
        not unexpl and not resid,
        f'{len(changed)} descricoes alteradas; categorias (ocorrencias): {dict(cat)}; '
        f'nao explicadas por troca de rotulo={len(unexpl)} {unexpl[:5]}; residuos em v5={resid[:5]}. '
        f'Obs.: alem de Parda->Brown e ICR->IC (itens 1-2), as descricoes tambem trocaram Branca/Preta/Indigena '
        f'por White/Black/Indigenous e o hifen por travessao em "X-Tk" (so rotulo, sem numero).')

    other = collections.defaultdict(collections.Counter)
    for k in common:
        for f in sorted(set(da[k]) | set(db[k])):
            if f in ('descricao',):
                continue
            if da[k].get(f) != db[k].get(f):
                other[f][f'{da[k].get(f)!r}->{db[k].get(f)!r}'] += 1
    nonc = {f: dict(c) for f, c in other.items() if f != 'commit'}
    add('A4. Numeros-chave: demais campos (filtro, arquivo, script) inalterados; campo commit informado',
        not nonc,
        f'campos alterados fora descricao/commit={nonc}; campo commit: {dict(other.get("commit", {}))} '
        f'(metadado; nao e numero de resultado)')


# ----------------------------------------------------------------------------
# B. CSVs
# ----------------------------------------------------------------------------
CSV_PAIRS = [
    ('tabelas', 'tab01_characteristics', 'tab01_characteristics'),
    ('tabelas', 'tab02_models_m1m3', 'tab02_models_m1m3'),
    ('tabelas', 'tab03_knol_tercile', 'tab03_knol_tercile'),
    ('tabelas', 'tab03b_terciles_region', 'tab03b_terciles_region'),
    ('tabelas', 'tab04_sensitivity', 'tab04_sensitivity'),
    ('suplementar', 'S1_flow_excluded', 'S1_flow_excluded'),
    ('suplementar', 'S1b_missing_data', 'S1b_missing_data'),
    ('suplementar', 'S2_knol_spontaneous', 'S2_knol_spontaneous'),
    ('suplementar', 'S3_multinomial', 'S3_multinomial'),
    ('suplementar', 'S4_exploratory_strata', 'S4_exploratory_strata'),
    ('suplementar', 'S4b_exploratory_family', 'S4b_exploratory_family'),
    ('suplementar', 'S5_weight_ga_plausibility', 'S5_weight_ga_plausibility'),
    ('suplementar', 'S5b_centerwest_rsp_by_method_INTERNAL', 'S5b_centerwest_rsp_by_method_INTERNAL'),
    ('suplementar', 'S5c_other_method_by_code', 'S5c_other_method_by_code'),
    ('suplementar', 'S5d_spontaneous_by_code_wald', 'S5d_spontaneous_by_code_wald'),
    ('suplementar', 'S6_maihda', 'S6_maihda'),
    ('suplementar', 'S7_dictionary', 'S7b_dictionary'),
    ('suplementar', 'S8_strobe_record_checklist', 'S8_strobe_record_checklist'),
]
EXPECTED_REMOVED = {'tab04_sensitivity': 1, 'S5d_spontaneous_by_code_wald': 1}


def check_B():
    # inventario de arquivos csv
    v4_csv = sorted(p.name for d in ('tabelas', 'suplementar') for p in (V4 / d).glob('*_v4_20261009.csv'))
    v5_csv = sorted(p.name for d in ('tabelas', 'suplementar') for p in (MS / d).glob('*_v5_20261009.csv'))
    exp5 = sorted(n.replace('_v4_', '_v5_').replace('S7_dictionary', 'S7b_dictionary') for n in v4_csv)
    sem_par4 = sorted(set(exp5) - set(v5_csv))
    novos5 = sorted(set(v5_csv) - set(exp5))
    add('B0. Inventario CSV: todo CSV v4 tem par em v5 (S7_dictionary->S7b_dictionary); unico novo e S7a',
        not sem_par4 and novos5 == ['S7a_variables_codes_v5_20261009.csv'],
        f'CSV v4={len(v4_csv)}, CSV v5={len(v5_csv)}; sem par={sem_par4}; novos em v5={novos5}')

    tot_cells, tot_pairs = 0, 0
    all_num, all_txt, all_shape, removed_info = [], [], [], {}
    for d, n4, n5 in CSV_PAIRS:
        p4 = V4 / d / f'{n4}_v4_20261009.csv'
        p5 = MS / d / f'{n5}_v5_20261009.csv'
        rows4 = read_csv(p4)
        reord = ''
        if n4 in TAB2_NAMES:
            rows4, mv = white_first(rows4)
            reord = f'reordenacao autorizada aplicada a v4 (White (reference) primeiro em cada bloco): {mv} linhas movidas; '
        r = compare_grid(rows4, read_csv(p5), n5)
        tot_pairs += 1
        tot_cells += r['cells']
        exp_rm = EXPECTED_REMOVED.get(n4, 0)
        ok = (not r['diffs_num'] and not r['diffs_txt'] and not r['shape'] and len(r['removed']) == exp_rm)
        rm_txt = [norm_ws(','.join(x))[:120] for x in r['removed']]
        removed_info[n4] = len(r['removed'])
        add(f'B. CSV {n4} -> {n5}', ok,
            f'{reord}linhas v4={r["nrows4"]}, v5={r["nrows5"]}, celulas comparadas={r["cells"]}; '
            f'linhas Excluding 2024 removidas={len(r["removed"])} (esperado {exp_rm}) {rm_txt}; '
            f'dif. numericas={len(r["diffs_num"])} {r["diffs_num"][:3]}; '
            f'dif. de texto alem das trocas autorizadas={len(r["diffs_txt"])} {r["diffs_txt"][:3]}; forma={r["shape"]}')
        all_num += r['diffs_num']
        all_txt += r['diffs_txt']
        all_shape += r['shape']
    add('B-total. CSVs: numeros identicos celula a celula; texto = v4 + trocas autorizadas; so Excluding 2024 removida',
        not all_num and not all_txt and not all_shape,
        f'{tot_pairs} pares, {tot_cells} celulas; diferencas numericas={len(all_num)}; diferencas de texto={len(all_txt)}; '
        f'problemas de forma={len(all_shape)}; linhas removidas por arquivo (nao zero)='
        f'{ {k: v for k, v in removed_info.items() if v} }')


# ----------------------------------------------------------------------------
# C. xlsx
# ----------------------------------------------------------------------------
def sheet_rows(ws):
    rows = []
    for r in ws.iter_rows(values_only=True):
        rows.append(list(r))
    # aparar colunas vazias a direita de forma consistente: manter max_column
    return rows


def split_sheet(rows):
    """titulo = linhas antes da 1a linha com >=2 celulas; rodape = linhas apos a ultima linha com >=2 celulas."""
    def nn(r):
        return sum(1 for c in r if c not in (None, ''))
    multi = [i for i, r in enumerate(rows) if nn(r) >= 2]
    if not multi:
        return rows, [], []
    first, last = multi[0], multi[-1]
    return rows[:first], rows[first:last + 1], rows[last + 1:]


def text_of(rows):
    return ' '.join(str(c) for r in rows for c in r if c not in (None, ''))


def footer_rule(t4, t5, allowed_texts):
    n4 = collections.Counter(nums_noversion(t4))
    n5 = collections.Counter(nums_noversion(t5))
    lost = n4 - n5
    new = n5 - n4
    allowed = collections.Counter()
    for a in allowed_texts:
        allowed += collections.Counter(nums(a))
    unexpl = new - allowed
    return lost, new, unexpl


REORD_LOG = []
S4B_DEF = 'IC, interaction contrast (per 100 live births).'
S4B_ACCEPT = {'aceito': False}


def allowed_for(name):
    al = [NOTE]
    if 'tab03_knol' in name or name.startswith('Table 3.'):
        al.append(DEF_T3)
    if 'tab02' in name or name.startswith('Table 2.'):
        al.append(EXTENDED)
    if name.startswith('S4b_') and S4B_ACCEPT['aceito']:
        al.append(S4B_DEF)
    return al


def judge_s4b():
    """Rodada 2: julgamento independente do '100' novo no rodape da S4b.
    Aceito como troca de rotulo/documentacao (definicao da sigla IC com a unidade, itens 1/4) somente se:
    (a) o 100 novo esta so na frase de definicao da sigla; (b) a unidade 'per 100 live births' para a mesma
    medida ja estava documentada na v4 (rodape da S4); (c) as linhas IC da S4 estao na S4b com estimativas
    identicas (mesma medida, mesma unidade); (d) a definicao do item 4 (Tab. 3) usa a mesma unidade."""
    wb4 = openpyxl.load_workbook(V4 / 'suplementar/ESM_1_tables_S1_S6_v4_20261009.xlsx', data_only=True)
    wb5 = openpyxl.load_workbook(MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx', data_only=True)
    f4b = text_of(split_sheet(sheet_rows(wb4['S4b_exploratory_family']))[2])
    f5b = text_of(split_sheet(sheet_rows(wb5['S4b_exploratory_family']))[2])
    f4s4 = text_of(split_sheet(sheet_rows(wb4['S4_exploratory_strata']))[2])
    _, new, _ = footer_rule(f4b, f5b, [NOTE])
    a = (S4B_DEF in f5b) and dict(new) == {'100': 1} and \
        collections.Counter(nums(f5b.replace(S4B_DEF, ' '))) == collections.Counter(nums(f4b))
    b = bool(re.search(r'\bICR per 100 live births', f4s4))
    s4 = read_csv(MS / 'suplementar/S4_exploratory_strata_v5_20261009.csv')
    s4b = read_csv(MS / 'suplementar/S4b_exploratory_family_v5_20261009.csv')
    ic4 = {tuple(r[:5]): r[5] for r in s4[1:] if r[3] == 'IC'}
    icb = {tuple(r[:5]): r[5] for r in s4b[1:] if r[3] == 'IC'}
    n_match = sum(1 for k, v in ic4.items() if icb.get(k) == v)
    c = len(ic4) > 0 and n_match == len(ic4)
    wbm = openpyxl.load_workbook(MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', data_only=True)
    d = DEF_T3 in text_of(split_sheet(sheet_rows(wbm['tab03_knol_tercile']))[2])
    S4B_ACCEPT['aceito'] = a and b and c and d
    prefixo = ('ACEITO como troca de rotulo/documentacao autorizada (definicao da sigla IC com a unidade; itens 1 e 4), '
               'nao e resultado: ') if S4B_ACCEPT['aceito'] else 'NAO aceito: '
    add('C-S4b. Julgamento independente: "100" novo no rodape da S4b ("IC, interaction contrast (per 100 live births).")',
        S4B_ACCEPT['aceito'],
        prefixo +
        f'(a) o unico numero novo do rodape e esse 100, dentro da frase de definicao, e os demais numeros sao os da v4={a}; '
        f'(b) a v4 ja documentava a unidade da mesma medida no rodape da S4 ("ICR per 100 live births")={b}; '
        f'(c) as {len(ic4)} linhas IC da S4 aparecem na S4b com estimativa identica ({n_match}/{len(ic4)}; S4b tem {len(icb)} linhas IC), '
        f'logo a S4b reporta a mesma medida na mesma unidade={c}; (d) a definicao do item 4 (rodape da Tab. 3) usa "per 100 live births"={d}. '
        f'Na rodada 1 este 100 foi contado como falha pela regra literal (numeros novos so das notas dos itens 3-4).')


def compare_workbooks(p4, p5, label):
    wb4 = openpyxl.load_workbook(p4, data_only=True)
    wb5 = openpyxl.load_workbook(p5, data_only=True)
    s4, s5 = wb4.sheetnames, wb5.sheetnames
    add(f'C. {label}: mesmas abas', s4 == s5, f'v4={s4}; v5={s5}')
    body_problems, foot_problems, foot_notes, cells = [], [], [], 0
    for name in s4:
        if name not in s5:
            continue
        r4 = sheet_rows(wb4[name])
        r5 = sheet_rows(wb5[name])
        t4, b4, f4 = split_sheet(r4)
        t5, b5, f5 = split_sheet(r5)
        if name in TAB2_NAMES:
            b4, mv = white_first(b4)
            REORD_LOG.append(f'{label}:{name}: {mv} linhas White movidas na v4')
        g = compare_grid(b4, b5, name)
        cells += g['cells']
        exp_rm = EXPECTED_REMOVED.get(name, 0)
        if g['diffs_num'] or g['diffs_txt'] or g['shape'] or len(g['removed']) != exp_rm:
            body_problems.append(f'{name}: num={g["diffs_num"][:3]} txt={g["diffs_txt"][:3]} forma={g["shape"]} '
                                 f'removidas={len(g["removed"])}/{exp_rm}')
        # titulos
        tt4, tt5 = text_of(t4), text_of(t5)
        if nums(tt4) != nums(tt5) or subst(tt4) != tt5:
            foot_problems.append(f'{name} TITULO: {tt4!r} -> {tt5!r}')
        # rodapes
        ft4, ft5 = text_of(f4), text_of(f5)
        lost, new, unexpl = footer_rule(ft4, ft5, allowed_for(name))
        if lost or unexpl:
            foot_problems.append(f'{name} RODAPE: numeros v4 sumidos={dict(lost)}; numeros novos nao explicados por '
                                 f'notas autorizadas={dict(unexpl)}')
        b5txt = ft5
        for rem in (NOTE, DEF_T3):
            b5txt = b5txt.replace(rem, ' ')
        delta = word_delta(norm_ws(subst(ft4)), norm_ws(b5txt))
        if delta:
            foot_notes.append(f'{name}: novos numeros={dict(new)}; delta de texto (v4 c/ trocas vs v5 sem nota/def): {delta}')
    reo = [x for x in REORD_LOG if x.startswith(label + ':')]
    add(f'C. {label}: corpo das abas (celulas) com numeros identicos e texto = v4 + trocas autorizadas',
        not body_problems, f'{cells} celulas comparadas; reordenacao autorizada da Tab. 2 aplicada a v4={reo}; problemas={body_problems}')
    add(f'C. {label}: titulos e rodapes - nenhum numero da v4 sumiu; numeros novos so das notas autorizadas (itens 3-4)',
        not foot_problems, f'problemas={foot_problems}' if foot_problems else 'nenhum problema')
    add(f'C-info. {label}: alteracoes de texto nos rodapes alem da nota de raca/definicao IC (informativo)', True,
        ' || '.join(foot_notes) if foot_notes else 'nenhuma')
    return wb5


def check_C():
    judge_s4b()
    compare_workbooks(V4 / 'tabelas/tabelas_principais_v4_20261009.xlsx',
                      MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', 'xlsx tabelas_principais')
    compare_workbooks(V4 / 'suplementar/ESM_1_tables_S1_S6_v4_20261009.xlsx',
                      MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx', 'xlsx ESM_1 (suplementar)')
    compare_workbooks(SUB4 / 'ESM_1.xlsx', SUB5 / 'ESM_1.xlsx', 'xlsx Submissao/ESM_1.xlsx')
    # copias identicas
    same5 = (SUB5 / 'ESM_1.xlsx').read_bytes() == (MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx').read_bytes()
    same4 = (SUB4 / 'ESM_1.xlsx').read_bytes() == (V4 / 'suplementar/ESM_1_tables_S1_S6_v4_20261009.xlsx').read_bytes()
    add('C. Submissao/ESM_1.xlsx e copia byte a byte do ESM_1 do suplementar (v4 e v5)', same4 and same5,
        f'v4 identico={same4}; v5 identico={same5}')


# ----------------------------------------------------------------------------
# D. docx
# ----------------------------------------------------------------------------
def docx_parts(p):
    d = docx.Document(p)
    tables = [[[c.text for c in row.cells] for row in t.rows] for t in d.tables]
    paras = [pp.text for pp in d.paragraphs if pp.text.strip()]
    hf = []
    for s in d.sections:
        for part in (s.header, s.footer):
            hf += [pp.text for pp in part.paragraphs if pp.text.strip()]
    return d, tables, paras, hf


def check_D():
    _, t4, p4, hf4 = docx_parts(V4 / 'tabelas/tabelas_principais_v4_20261009.docx')
    _, t5, p5, hf5 = docx_parts(MS / 'tabelas/tabelas_principais_v5_20261009.docx')
    add('D. docx: mesmo numero de tabelas e paragrafos', len(t4) == len(t5) and len(p4) == len(p5),
        f'tabelas v4={len(t4)} v5={len(t5)}; paragrafos nao vazios v4={len(p4)} v5={len(p5)}; cabecalho/rodape de secao v4={hf4} v5={hf5}')
    probs, cells, reo = [], 0, []
    names = ['tab01_characteristics', 'tab02_models_m1m3', 'tab03_knol_tercile', 'tab03b_terciles_region', 'tab04_sensitivity']
    for i, (a, b) in enumerate(zip(t4, t5)):
        nm = names[i] if i < len(names) else f'tabela{i + 1}'
        if nm in TAB2_NAMES:
            a, mv = white_first(a)
            reo.append(f'{nm}: {mv} linhas White movidas na v4')
        g = compare_grid(a, b, nm)
        cells += g['cells']
        exp_rm = EXPECTED_REMOVED.get(nm, 0)
        if g['diffs_num'] or g['diffs_txt'] or g['shape'] or len(g['removed']) != exp_rm:
            probs.append(f'{nm}: num={g["diffs_num"][:3]} txt={g["diffs_txt"][:3]} forma={g["shape"]} removidas={len(g["removed"])}/{exp_rm}')
    add('D. docx: tabelas com numeros identicos celula a celula e texto = v4 + trocas autorizadas (so Excluding 2024 removida)',
        not probs, f'{cells} celulas comparadas; reordenacao autorizada da Tab. 2 aplicada a v4={reo}; problemas={probs}')
    fprob, finfo = [], []
    cur_title = ''
    for a, b in zip(p4, p5):
        if b.startswith('Table') or a.startswith('Table'):
            cur_title = b
            if nums(a) != nums(b) or subst(a) != b:
                fprob.append(f'TITULO {a!r} -> {b!r}')
            continue
        lost, new, unexpl = footer_rule(a, b, allowed_for(cur_title) if cur_title else [NOTE])
        if lost or unexpl:
            fprob.append(f'{cur_title[:10] or "cabecalho"}: numeros v4 sumidos={dict(lost)}; novos nao explicados={dict(unexpl)}')
        if VERSION_TAG.search(a) or VERSION_TAG.search(b):
            finfo.append(f'rotulo de versao: {a!r} -> {b!r} (excluido da regra numerica)')
        bb = b
        for rem in (NOTE, DEF_T3):
            bb = bb.replace(rem, ' ')
        dl = word_delta(norm_ws(subst(a)), norm_ws(bb))
        if dl and not VERSION_TAG.search(a):
            finfo.append(f'{cur_title[:10]}: novos numeros={dict(new)}; delta: {dl}')
    add('D. docx: titulos e notas - nenhum numero da v4 sumiu; numeros novos so das notas autorizadas',
        not fprob, f'problemas={fprob}' if fprob else 'nenhum problema')
    add('D-info. docx: alteracoes de texto em titulos/notas (informativo)', True, ' || '.join(finfo) if finfo else 'nenhuma')
    return t5, p5


# ----------------------------------------------------------------------------
# E. PDFs
# ----------------------------------------------------------------------------
def pdf_text(p):
    d = pymupdf.open(p)
    pages = [pg.get_text() for pg in d]
    return d.page_count, pages


def find_split(s, hay):
    if s in hay:
        return True
    for k in range(1, len(s)):
        if s[:k] in hay and s[k:] in hay:
            return True
    return False


def check_E():
    # ESM_3
    n4, pg4 = pdf_text(SUB4 / 'ESM_3.pdf')
    n5, pg5 = pdf_text(SUB5 / 'ESM_3.pdf')
    same = (n4 == n5) and pg4 == pg5
    diff = '' if same else word_delta(norm_ws(' '.join(pg4)), norm_ws(' '.join(pg5)))
    add('E1. ESM_3.pdf v4 x v5: conteudo textual identico', same,
        f'paginas v4={n4} v5={n5}; caracteres v4={sum(map(len, pg4))} v5={sum(map(len, pg5))}; texto pagina a pagina identico={same}; {diff}')
    s3 = (SUB5 / 'ESM_3.pdf').read_bytes() == (MS / 'suplementar/S8_strobe_record_checklist_v5_20261009.pdf').read_bytes()
    add('E1b. Submissao/ESM_3.pdf v5 = suplementar/S8_strobe_record_checklist_v5 (bytes)', s3, f'identico={s3}')

    # ESM_4
    n4, pg4 = pdf_text(SUB4 / 'ESM_4.pdf')
    n5, pg5 = pdf_text(SUB5 / 'ESM_4.pdf')
    t4, t5 = norm_ws(' '.join(pg4)), norm_ws(' '.join(pg5))
    has_note = NOTE in t5
    t5r = norm_ws(t5.replace(NOTE, ' '))
    ok4 = has_note and t5r == t4 and n4 == n5
    add('E2. ESM_4.pdf v4 x v5: so a legenda mudou (nota de raca acrescentada)', ok4,
        f'paginas v4={n4} v5={n5}; nota presente={has_note}; texto v5 sem a nota == texto v4: {t5r == t4}; '
        f'delta={word_delta(t4, t5r) or "nenhum"}')
    # imagens embutidas no ESM_4
    def imgs(p):
        d = pymupdf.open(p)
        out = []
        for pg in d:
            for im in pg.get_images(full=True):
                out.append((im[2], im[3]))
        return out
    i4, i5 = imgs(SUB4 / 'ESM_4.pdf'), imgs(SUB5 / 'ESM_4.pdf')
    add('E2b. ESM_4.pdf: imagem embutida com as mesmas dimensoes em pixels', i4 == i5, f'v4={i4}; v5={i5}')

    # ESM_2
    n4, pg4 = pdf_text(SUB4 / 'ESM_2.pdf')
    n5, pg5 = pdf_text(SUB5 / 'ESM_2.pdf')
    full4 = '\n'.join(pg4)
    full5 = '\n'.join(pg5)
    s2 = (SUB5 / 'ESM_2.pdf').read_bytes() == (MS / 'suplementar/S7_variables_codes_v5_20261009.pdf').read_bytes()
    add('E3a. Submissao/ESM_2.pdf v5 = suplementar/S7_variables_codes_v5 (bytes)', s2, f'identico={s2}; paginas v4={n4}, v5={n5}')
    # separar o v4 em: titulo | dicionario+nota | secao codigo 8
    lines4 = full4.split('\n')
    title4 = lines4[0]
    body4 = '\n'.join(lines4[1:])
    k = body4.find('Gestational age estimation method (TPMETESTIM): code 8')
    dict4, code8_4 = body4[:k], body4[k:]
    h5 = nows(full5.replace(NOTE, ' '))
    # a nota pode quebrar linha no PDF: remover a versao sem espacos
    h5 = h5.replace(nows(NOTE), '')
    ok_dict = nows(subst(dict4)) in h5
    ok_c8 = nows(subst(code8_4)) in h5
    add('E3b. ESM_2: conteudo do antigo dicionario (S7 v4) preservado na v5, com Parda->Brown', ok_dict,
        f'titulo v4="{title4}"; trecho do dicionario v4 ({len(nows(dict4))} caracteres sem espaco, apos Parda->Brown) '
        f'encontrado contiguo no texto v5 (sem a nota de raca)={ok_dict}')
    add('E3c. ESM_2: secao do codigo 8 preservada integralmente', ok_c8,
        f'secao do codigo 8 v4 ({len(nows(code8_4))} caracteres sem espaco) encontrada contigua na v5={ok_c8}')
    # S7a existe e bate com o CSV S7a (colunas em ingles)
    has_s7a = 'Table S7a. Variables and codes' in full5
    rows = read_csv(MS / 'suplementar/S7a_variables_codes_v5_20261009.csv')
    hdr = rows[0]
    pt_col = hdr.index('Official label (Portuguese, data dictionary)') if 'Official label (Portuguese, data dictionary)' in hdr else None
    hay = nows(full5)
    missing, split_found, ncell = [], 0, 0
    for r in rows[1:]:
        for j, c in enumerate(r):
            if j == pt_col or not c.strip():
                continue
            ncell += 1
            s = nows(c)
            if s in hay:
                continue
            if find_split(s, hay):
                split_found += 1
            else:
                missing.append(f'{r[1]}/{hdr[j]}: {c[:70]}')
    add('E3d. ESM_2: nova tabela S7a existe e todas as celulas (exceto coluna em portugues) do CSV S7a aparecem no PDF',
        has_s7a and not missing,
        f'titulo "Table S7a. Variables and codes" presente={has_s7a}; linhas S7a={len(rows) - 1}; celulas checadas={ncell}; '
        f'achadas partidas por quebra de pagina={split_found}; ausentes={missing[:5]}')
    # S7b no PDF bate com o CSV S7b
    rows_b = read_csv(MS / 'suplementar/S7b_dictionary_v5_20261009.csv')
    miss_b = [c[:60] for r in rows_b[1:] for c in r if c.strip() and not find_split(nows(c), hay)]
    has_s7b = 'Table S7b. Operational definitions of derived variables' in full5
    add('E3e. ESM_2: tabela S7b presente e todas as celulas do CSV S7b aparecem no PDF', has_s7b and not miss_b,
        f'titulo S7b presente={has_s7b}; celulas ausentes={miss_b[:5]}')

    # numeros do codigo 8 contra as fontes
    conc = read_csv(SRC / 'tab_e6_02a_concordancia_v1_20261008.csv')
    ch = conc[0]
    row8 = [r for r in conc[1:] if r[ch.index('tp')] == '8' and r[ch.index('sub')] == 'todas validas']
    others = [r for r in conc[1:] if r[ch.index('tp')] in ('1', '2', '9') and r[ch.index('sub')] == 'todas validas']
    tpm = read_csv(SRC / 'tab_e6_02b_tpmetestim_2010_2014_v1_20261008.csv')
    th = tpm[0]
    r13 = [r for r in tpm[1:] if r[th.index('ano')] == '2013' and r[th.index('tp')] == '8']
    first_year8 = min(int(r[th.index('ano')]) for r in tpm[1:] if r[th.index('tp')] == '8')
    r8 = row8[0]
    pct_dum = float(r8[ch.index('pct_dum_valida')])
    pct_ex = float(r8[ch.index('pct_exata')])
    pct_pm1 = float(r8[ch.index('pct_pm1')])
    dmed = float(r8[ch.index('dif_media')])
    ddp = float(r8[ch.index('dif_dp')])
    n13 = int(r13[0][th.index('n')])
    n13d = int(r13[0][th.index('n_dtultmenst')])
    exp = {
        '1,799,677': f'{n13:,}' == '1,799,677' and n13 == n13d,
        '99.998%': f'{pct_dum:.3f}' == '99.998',
        '79.0%': f'{pct_ex:.1f}' == '79.0',
        '99.98%': f'{pct_pm1:.2f}' == '99.98',
        '2013': first_year8 == 2013,
        '0% (codigos 1, 2, 9)': all(float(r[ch.index('pct_dum_valida')]) == 0.0 for r in others) and len(others) == 3,
        '−0.02 / SD 0.47': f'{dmed:.2f}' == '-0.02' and f'{ddp:.2f}' == '0.47',
    }
    # citados na S7a (PDF e CSV), linha TPMETESTIM
    s7a_tp = [r for r in rows[1:] if r[1] == 'TPMETESTIM'][0]
    s7a_txt = ' '.join(s7a_tp)
    cited = {
        '1,799,677': s7a_txt.count('1,799,677') == 2,
        '99.998%': '99.998%' in s7a_txt,
        '79.0%': '79.0%' in s7a_txt,
        '99.98%': '99.98%' in s7a_txt,
        '2013': 'first appears in 2013' in s7a_txt,
    }
    # no PDF: o mesmo trecho
    pdf_s7a = nows(s7a_tp[4]) in hay
    ok8 = all(exp.values()) and all(cited.values()) and pdf_s7a
    add('E4. ESM_2/S7a: numeros da evidencia do codigo 8 conferem com tab_e6_02a (tp 8, todas validas) e tab_e6_02b (2013, tp 8)',
        ok8,
        f'fonte: n 2013 tp8={n13:,}, n_dtultmenst={n13d:,}; 1o ano com tp 8={first_year8}; pct_dum_valida={pct_dum:.5f} -> {pct_dum:.3f}%; '
        f'pct_exata={pct_ex:.4f} -> {pct_ex:.1f}%; pct_pm1={pct_pm1:.4f} -> {pct_pm1:.2f}%; dif_media={dmed:.4f}; dif_dp={ddp:.4f}; '
        f'conferencia fonte={exp}; citados na S7a (CSV)={cited}; celula da S7a presente no PDF={pdf_s7a}. '
        f'Obs.: com sub="IG_DUM 22-44" a concordancia exata seria 79.01% (tambem 79.0%).')


# ----------------------------------------------------------------------------
# F. residuos
# ----------------------------------------------------------------------------
def collect_v5_texts():
    """Lista de (fonte, texto) das saidas v5 em ingles."""
    items = []
    for d in ('tabelas', 'suplementar'):
        for p in sorted((MS / d).glob('*_v5_20261009.csv')):
            rows = read_csv(p)
            hdr = rows[0]
            skip = None
            if p.name.startswith('S7a_'):
                skip = hdr.index('Official label (Portuguese, data dictionary)')
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    if j == skip and i > 0:
                        continue
                    items.append((f'{p.name}:L{i + 1}C{j + 1}', c))
    for p in [MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx',
              SUB5 / 'ESM_1.xlsx']:
        wb = openpyxl.load_workbook(p, data_only=True)
        for ws in wb.worksheets:
            items.append((f'{p.name}:{ws.title}:nome_aba', ws.title))
            for row in ws.iter_rows():
                for c in row:
                    if c.value is not None:
                        items.append((f'{p.name}:{ws.title}:{c.coordinate}', str(c.value)))
    d, t, paras, hf = docx_parts(MS / 'tabelas/tabelas_principais_v5_20261009.docx')
    for i, pp in enumerate(paras):
        items.append((f'docx:par{i + 1}', pp))
    for k, tb in enumerate(t):
        for i, r in enumerate(tb):
            for j, c in enumerate(r):
                items.append((f'docx:tab{k + 1}:L{i + 1}C{j + 1}', c))
    for i, h in enumerate(hf):
        items.append((f'docx:cab/rod{i + 1}', h))
    for p in [SUB5 / 'ESM_2.pdf', SUB5 / 'ESM_3.pdf', SUB5 / 'ESM_4.pdf']:
        _, pages = pdf_text(p)
        for i, pg in enumerate(pages):
            items.append((f'Submissao/{p.name}:p{i + 1}', pg))
    items.append(('legendas_figuras.md', (MS / 'legendas_figuras.md').read_text(encoding='utf-8')))
    items.append(('data_code_availability.md', (MS / 'data_code_availability.md').read_text(encoding='utf-8')))
    return items


def check_F():
    items = collect_v5_texts()
    pats = {'ICR': re.compile(r'\bICR\b'), 'Parda': re.compile(r'Parda'), 'third model': re.compile(r'third model', re.I)}
    hits = {k: [] for k in pats}
    for src, txt in items:
        for k, rx in pats.items():
            for m in rx.finditer(str(txt)):
                s = str(txt)
                hits[k].append(f'{src}: ...{s[max(0, m.start() - 40):m.end() + 40]}...'.replace('\n', ' '))
    amarela = sum(len(re.findall(r'Amarela', str(t))) for _, t in items)
    srcs = sorted(set(s.split(':')[0] for s, _ in items))
    for k in pats:
        add(f'F. Residuo "{k}" nas saidas v5 em ingles', not hits[k],
            f'{len(hits[k])} ocorrencias {hits[k][:5]}; fontes varridas={len(srcs)} ({", ".join(srcs)}); '
            f'excecao aplicada: coluna "Official label (Portuguese, data dictionary)" da S7a')
    add('F-info. "Amarela" (esperado, nao e erro)', True, f'{amarela} ocorrencias')
    # a excecao: confirmar que a coluna em portugues da S7a de fato contem Parda (transcricao do dicionario)
    rows = read_csv(MS / 'suplementar/S7a_variables_codes_v5_20261009.csv')
    j = rows[0].index('Official label (Portuguese, data dictionary)')
    pt = [r[j] for r in rows[1:] if 'Parda' in r[j]]
    add('F-info. Excecao S7a (coluna em portugues) contem "Parda" so como transcricao oficial', True, f'{pt}')


# ----------------------------------------------------------------------------
# G. nota de raca
# ----------------------------------------------------------------------------
def check_G():
    probs, ok_list, broad, info = [], [], [], []
    for p in [MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx',
              SUB5 / 'ESM_1.xlsx']:
        wb = openpyxl.load_workbook(p, data_only=True)
        for ws in wb.worksheets:
            t, b, f = split_sheet(sheet_rows(ws))
            bt, ft = text_of(t + b), text_of(f)
            has_note = NOTE in ft
            if re.search(r'\bBrown\b', bt):
                (ok_list if has_note else probs).append(f'{p.name}:{ws.title}')
            elif re.search(r'\bBrown\b', ft) and not has_note:
                broad.append(f'{p.name}:{ws.title} (Brown so no rodape)')
            elif re.search(r'\b(White|Black|Indigenous)\b', bt) and not has_note:
                info.append(f'{p.name}:{ws.title}')
    # docx: mapear tabela -> nota pela ordem do corpo
    d = docx.Document(MS / 'tabelas/tabelas_principais_v5_20261009.docx')
    body = d.element.body
    seq = []
    for el in body.iterchildren():
        tag = el.tag.split('}')[-1]
        if tag == 'tbl':
            seq.append(('T', el))
        elif tag == 'p':
            txt = ''.join(x.text or '' for x in el.iter() if x.tag.endswith('}t'))
            if txt.strip():
                seq.append(('P', txt))
    tables = d.tables
    ti = 0
    for k, (kind, obj) in enumerate(seq):
        if kind != 'T':
            continue
        tb = tables[ti]
        ti += 1
        cells = ' '.join(c.text for r in tb.rows for c in r.cells)
        nxt = next((o for kk, o in seq[k + 1:] if kk == 'P'), '')
        prev = [o for kk, o in seq[:k] if kk == 'P']
        title = prev[-1][:9] if prev else f'tabela{ti}'
        if re.search(r'\bBrown\b', cells):
            (ok_list if NOTE in nxt else probs).append(f'docx:{title}')
        elif re.search(r'\bBrown\b', nxt) and NOTE not in nxt:
            broad.append(f'docx:{title} (Brown so na nota)')
        elif re.search(r'\b(White|Black|Indigenous)\b', cells) and NOTE not in nxt:
            info.append(f'docx:{title}')
    # ESM_2 (S7a e S7b): nota apos cada tabela
    _, pages = pdf_text(SUB5 / 'ESM_2.pdf')
    t2 = nows(' '.join(pages))
    cnt = t2.count(nows(NOTE))
    if cnt >= 2:
        ok_list.append(f'ESM_2.pdf (nota {cnt}x: S7a e S7b)')
    else:
        probs.append(f'ESM_2.pdf (nota {cnt}x; esperado 2: S7a e S7b)')
    add('G1. Nota de raca no rodape de toda tabela/aba com rotulo Brown no corpo (xlsx, docx, ESM_2)', not probs,
        f'com nota={len(ok_list)} {ok_list}; SEM nota={probs}. CSVs nao tem rodape (nem na v4); avaliados xlsx/docx/PDF.')
    add('G1b. Criterio amplo: "Brown" em qualquer parte da tabela (inclusive so no rodape) exige a nota', not broad,
        f'sem nota sob criterio amplo={broad}; tabelas com outros rotulos de raca (White/Black/Indigenous) sem Brown e sem nota '
        f'(informativo)={info}')
    # legendas
    leg = (MS / 'legendas_figuras.md').read_text(encoding='utf-8')
    entries = re.split(r'\n(?=\*\*(?:Fig\.|Online Resource))', leg)
    entries = [e for e in entries if e.startswith('**')]
    miss = [e[:30] for e in entries if NOTE not in norm_ws(e)]
    _, p4 = pdf_text(SUB5 / 'ESM_4.pdf')
    esm4 = NOTE in norm_ws(' '.join(p4))
    add('G2. Nota de raca em todas as legendas de figuras (legendas_figuras.md e ESM_4.pdf)', not miss and esm4 and len(entries) == 5,
        f'legendas encontradas={len(entries)} ({[e[:28] for e in entries]}); sem nota={miss}; ESM_4.pdf com nota={esm4}')


# ----------------------------------------------------------------------------
# item 4: definicao de IC (Tab 3) e "extended model" (Tab 2, Fig. 2)
# ----------------------------------------------------------------------------
def check_item4():
    wb = openpyxl.load_workbook(MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', data_only=True)
    f3 = text_of(split_sheet(sheet_rows(wb['tab03_knol_tercile']))[2])
    f2 = text_of(split_sheet(sheet_rows(wb['tab02_models_m1m3']))[2])
    _, _, paras, _ = docx_parts(MS / 'tabelas/tabelas_principais_v5_20261009.docx')
    def foot_after(prefix):
        for i, p in enumerate(paras):
            if p.startswith(prefix):
                return paras[i + 1] if i + 1 < len(paras) else ''
        return ''
    d3, d2 = foot_after('Table 3.'), foot_after('Table 2.')
    leg = (MS / 'legendas_figuras.md').read_text(encoding='utf-8')
    fig2 = [e for e in re.split(r'\n(?=\*\*)', leg) if e.startswith('**Fig. 2.')]
    fig2 = fig2[0] if fig2 else ''
    res = {'def IC/RERI rodape Tab3 xlsx': DEF_T3 in f3, 'def IC/RERI nota Tab3 docx': DEF_T3 in d3,
           '"M3 (extended model)" rodape Tab2 xlsx': 'M3 (extended model)' in f2,
           '"M3 (extended model)" nota Tab2 docx': 'M3 (extended model)' in d2,
           '"extended model" legenda Fig. 2': 'extended model' in fig2}
    add('K. Item 4: definicao de IC/RERI no rodape da Tab. 3 e "extended model" na Tab. 2 e na legenda da Fig. 2',
        all(res.values()), str(res))


# ----------------------------------------------------------------------------
# H. figuras
# ----------------------------------------------------------------------------
def check_H():
    pairs = [(SUB4 / f'Fig{i}.tif', SUB5 / f'Fig{i}.tif', f'Fig{i}.tif') for i in range(1, 5)]
    pairs.append((V4 / 'suplementar/S9_maihda_caterpillar_v4_20261009.tif',
                  MS / 'suplementar/S9_maihda_caterpillar_v5_20261009.tif', 'S9_maihda_caterpillar.tif'))
    allok, det = True, []
    for a, b, nm in pairs:
        ia, ib = Image.open(a), Image.open(b)
        dpa, dpb = ia.info.get('dpi'), ib.info.get('dpi')
        sa, sb = ia.size, ib.size
        ok = (sa == sb) and (dpa is not None) and (tuple(round(x) for x in dpa) == tuple(round(x) for x in dpb))
        frac, bbox, bands = None, None, []
        if sa == sb:
            xa = np.asarray(ia.convert('RGB'))
            xb = np.asarray(ib.convert('RGB'))
            dm = np.any(xa != xb, axis=2)
            frac = float(dm.mean())
            bbox = ImageChops.difference(ia.convert('RGB'), ib.convert('RGB')).getbbox()
            # faixas horizontais com diferenca (linhas a <=20 px de distancia agrupadas)
            for y in np.where(dm.any(1))[0]:
                if bands and y - bands[-1][1] <= 20:
                    bands[-1][1] = int(y)
                else:
                    bands.append([int(y), int(y)])
            bands = [(b0, b1, round(100 * (b1 - b0 + 1) / sa[1], 1)) for b0, b1 in bands]
        allok &= ok
        det.append(f'{nm}: px v4={sa} v5={sb}; dpi v4={dpa} v5={dpb}; modo v4={ia.mode} v5={ib.mode}; '
                   f'pixels diferentes={frac * 100:.3f}%; caixa da diferenca={bbox}; '
                   f'faixas y com diferenca (y0, y1, % da altura)={bands}' if frac is not None else
                   f'{nm}: px v4={sa} v5={sb}; dpi v4={dpa} v5={dpb}')
        add(f'H. {nm}: mesma resolucao (dpi) e mesmo tamanho em pixels', ok, det[-1])
    # copias
    cp = []
    names = {1: 'fig01_flowchart', 2: 'fig02_pr_race_m1m3', 3: 'fig03_rd_race_tercile', 4: 'fig04_dating'}
    for i, n in names.items():
        cp.append((SUB5 / f'Fig{i}.tif').read_bytes() == (MS / f'figuras/{n}_v5_20261009.tif').read_bytes())
    add('H-b. Submissao/Fig1-4.tif v5 = figuras/fig0X_*_v5.tif (bytes)', all(cp), f'identicos={cp}')


# ----------------------------------------------------------------------------
# I. data_code_availability
# ----------------------------------------------------------------------------
def env_versions():
    py = subprocess.run([sys.executable, '-c',
                         'import sys,importlib;print("Python", sys.version.split()[0])\n'
                         'for m,n in [("pandas","pandas"),("numpy","numpy"),("scipy","scipy"),("statsmodels","statsmodels"),'
                         '("patsy","patsy"),("pyarrow","pyarrow"),("duckdb","duckdb"),("sklearn","scikit-learn"),("matplotlib","matplotlib")]:\n'
                         '    print(n, importlib.import_module(m).__version__)'],
                        capture_output=True, text=True)
    r = subprocess.run(['Rscript', '-e',
                        'cat("R", paste(R.version$major, R.version$minor, sep="."), "\\n"); '
                        'for (p in c("MASS","growthstandards","arrow","lme4","data.table","gigs")) '
                        'cat(p, packageDescription(p)$Version, "\\n")'],
                       capture_output=True, text=True)
    v = {}
    for line in (py.stdout + r.stdout).splitlines():
        parts = line.split()
        if len(parts) >= 2:
            v[parts[0]] = parts[1]
    return v, py.stderr.strip()[-200:], r.stderr.strip()[-200:]


def check_I():
    t = (MS / 'data_code_availability.md').read_text(encoding='utf-8')
    add('I1. data_code_availability.md v5 nao cita "nnet"', 'nnet' not in t.lower(),
        f'ocorrencias de "nnet"={t.lower().count("nnet")}')
    req = ['MASS 7.3-65', 'growthstandards 0.1.7', 'arrow 21.0.0.1', 'patsy 0.5.6', 'pyarrow 16.1.0', 'duckdb 1.5.6',
           'matplotlib 3.9.2']
    pres = {x: bool(re.search(r'(?<![\w.-])' + re.escape(x) + r'(?![\w.-])', t)) for x in req}
    add('I2. Cita MASS 7.3-65, growthstandards 0.1.7, arrow 21.0.0.1, patsy 0.5.6, pyarrow 16.1.0, duckdb 1.5.6, matplotlib 3.9.2',
        all(pres.values()), str(pres))
    m = re.search(r'Own implementations.*?(?=\n- |\n\n)', t, re.S)
    own = m.group(0) if m else ''
    ok3 = bool(own) and 'AUC' in own and 'DeLong' in own and bool(re.search(r'pROC package is not used', own))
    add('I3. Diz que AUC/DeLong e implementacao propria e que o pROC nao e usado', ok3,
        f'trecho: {norm_ws(own)[-260:]}')
    # frase com 173fecd (o ponto de "7b.2" nao encerra a frase: fim = ponto seguido de espaco/fim)
    m2 = re.search(r'[^\n]*?173fecd.*?\.(?=\s|$)', t, re.S)
    sent = norm_ws(m2.group(0)) if m2 else ''
    add('I4. Diz que 173fecd e o commit da Etapa 7b.2', bool(re.search(r'173fecd.*Etapa 7b\.2 commit', sent)),
        f'frase: {sent!r}')
    # versoes citadas x ambiente instalado
    env, e1, e2 = env_versions()
    cited = {}
    sw = t[t.find('## Software'):t.find('## Draft statement')]
    for name, ver in re.findall(r'([A-Za-z][\w.\-]*) (\d+\.\d+(?:[.\-]\d+)*(?:\.\d+)?)', sw):
        cited[name] = ver
    m3 = re.search(r'R version (\d+\.\d+\.\d+)', sw)
    if m3:
        cited['R'] = m3.group(1)
    cmpres, mism = {}, []
    for k, v in cited.items():
        if k in ('version',):
            continue
        ev = env.get(k)
        if ev is None:
            cmpres[k] = f'{v} (nao checado)'
            continue
        cmpres[k] = f'{v} vs instalado {ev}'
        if ev != v:
            mism.append(f'{k}: citado {v}, instalado {ev}')
    need = ['MASS', 'growthstandards', 'arrow', 'patsy', 'pyarrow', 'duckdb', 'matplotlib']
    miss_env = [k for k in need if k not in env]
    add('I5. Versoes citadas conferem com o ambiente instalado (python3 __version__ / Rscript packageDescription)',
        not mism and not miss_env, f'comparacao={cmpres}; divergencias={mism}; nao encontrados no ambiente={miss_env}')


# ----------------------------------------------------------------------------
# J. ordem das racas
# ----------------------------------------------------------------------------
def _ordered(seq):
    return [RANK[x] for x in seq] == sorted(RANK[x] for x in seq) and len(set(seq)) == len(seq)


def race_order_grid(rows, label, header_row=0):
    """Verifica a ordem das racas: (a) cabecalho; (b) em cada coluna, dentro de grupos definidos pelas
    colunas a esquerda e pela ultima celula nao-raca da propria coluna (linha-secao).
    Retorna (viol_rel, viol_white, grupos): viol_rel = ordem relativa Brown<Black<Indigenous violada;
    viol_white = White (reference) presente mas nao em primeiro."""
    viol_rel, viol_white, groups = [], [], 0
    if not rows:
        return viol_rel, viol_white, groups

    def judge(seq, where):
        nonlocal groups
        if len(seq) < 2:
            return
        groups += 1
        nonw = [x for x in seq if x != 'White']
        if not _ordered(nonw):
            viol_rel.append(f'{where}: {seq}')
        if 'White' in seq and seq[0] != 'White':
            viol_white.append(f'{where}: {seq}')

    hdr = rows[header_row]
    judge([lead_race(c) for c in hdr if lead_race(c)], f'{label} cabecalho')
    ncol = max(len(r) for r in rows)
    for c in range(ncol):
        seqs = collections.OrderedDict()
        section = ''
        for r in rows[header_row + 1:]:
            cell = r[c] if c < len(r) else None
            rc = lead_race(cell)
            if not rc:
                if cell not in (None, '') and str(cell).strip():
                    section = str(cell)   # celula nao-raca na coluna inicia novo bloco
                continue
            key = (section, tuple(str(x) for x in r[:c]))
            seqs.setdefault(key, []).append(rc)
        for key, s in seqs.items():
            col = [s[0]] + [s[k] for k in range(1, len(s)) if s[k] != s[k - 1]]
            judge(col, f'{label} col{c + 1} grupo "{(key[0] or "/".join(key[1])).strip()[:45]}"')
    return viol_rel, viol_white, groups


def inline_lists(texts, label, gap=60):
    """Enumeracoes de >=3 racas no texto: mencoes encadeadas (distancia <= gap caracteres entre mencoes
    consecutivas) dentro de uma mesma oracao (separadores ';' e '. '), sem a nota de raca."""
    v = []
    for src, s in texts:
        s = str(s).replace(NOTE, ' ')
        for clause in re.split(r';|\.\s', s):
            ms = list(re.finditer(r'\b(White|Brown|Black|Indigenous)\b', clause))
            chains, cur = [], []
            for m in ms:
                if cur and m.start() - cur[-1].end() > gap:
                    chains.append(cur)
                    cur = []
                cur.append(m)
            if cur:
                chains.append(cur)
            for ch in chains:
                order = []
                for m in ch:
                    if m.group(1) not in order:
                        order.append(m.group(1))
                if len(order) >= 3 and not _ordered(order):
                    v.append(f'{label}:{src}: {order} em "{norm_ws(clause[ch[0].start():ch[-1].end()])[:120]}"')
    return v


def check_J():
    viol, vwhite, groups, inl = [], [], 0, []
    seqcmp = []
    for d, n4, n5 in CSV_PAIRS + [('suplementar', None, 'S7a_variables_codes')]:
        p5 = MS / d / f'{n5}_v5_20261009.csv'
        rows = read_csv(p5)
        if n5 == 'S7a_variables_codes':
            # colunas de rotulo oficial seguem a ordem dos codigos do dicionario (1 Branca, 2 Preta, 3, 4 Parda, 5)
            hdr = rows[0]
            skip = {hdr.index('Official label (English translation)'), hdr.index('Official label (Portuguese, data dictionary)')}
            rows = [[c for j, c in enumerate(r) if j not in skip] for r in rows]
        vv, vw, g = race_order_grid(rows, n5)
        viol += vv
        vwhite += vw
        groups += g
        inl += inline_lists([(f'L{i + 1}C{j + 1}', c) for i, r in enumerate(rows) for j, c in enumerate(r)], n5)
        if n4:
            r4 = [r for r in read_csv(V4 / d / f'{n4}_v4_20261009.csv') if not is_excl2024(r)]
            if n4 in TAB2_NAMES:   # mudanca autorizada na rodada 2: White (reference) primeiro
                r4, _ = white_first(r4)
            s4 = re.findall(r'\b(?:White|Parda|Brown|Black|Indigenous)\b', ' '.join(' '.join(r) for r in r4))
            s4 = ['Brown' if x == 'Parda' else x for x in s4]
            s5 = re.findall(r'\b(?:White|Brown|Black|Indigenous)\b', ' '.join(' '.join(r) for r in read_csv(p5)))
            if s4 != s5:
                seqcmp.append(n5)
    for p in [MS / 'tabelas/tabelas_principais_v5_20261009.xlsx', MS / 'suplementar/ESM_1_tables_S1_S6_v5_20261009.xlsx']:
        wb = openpyxl.load_workbook(p, data_only=True)
        for ws in wb.worksheets:
            t, b, f = split_sheet(sheet_rows(ws))
            vv, vw, g = race_order_grid(b, f'{p.name}:{ws.title}')
            viol += vv
            vwhite += vw
            groups += g
            inl += inline_lists([('rodape', text_of(f))], f'{p.name}:{ws.title}')
    _, tabs, paras, _ = docx_parts(MS / 'tabelas/tabelas_principais_v5_20261009.docx')
    for k, tb in enumerate(tabs):
        vv, vw, g = race_order_grid(tb, f'docx:tab{k + 1}')
        viol += vv
        vwhite += vw
        groups += g
    inl += inline_lists([(f'par{i + 1}', p) for i, p in enumerate(paras)], 'docx')
    inl += inline_lists([('legendas', (MS / 'legendas_figuras.md').read_text(encoding='utf-8'))], 'md')
    add('J1. Ordem das racas inalterada v4 -> v5 (sequencia de rotulos, com Parda->Brown) em todos os CSVs pareados, '
        'exceto a reordenacao autorizada da Tab. 2',
        not seqcmp, f'arquivos com sequencia diferente={seqcmp} (na Tab. 2 a v4 foi reordenada com White primeiro antes de comparar)')
    add('J2. Ordem relativa Brown, Black, Indigenous (e White antes delas quando listada) em cabecalhos, blocos e listas (CSV, xlsx, docx, legendas)',
        not viol and not inl,
        f'grupos verificados={groups}; violacoes={len(viol)} {viol[:8]}; listas no texto fora de ordem={inl[:5]}. '
        f'Excecao: colunas de rotulo oficial da S7a (seguem a ordem dos codigos 1-5 do dicionario).')
    by_src = collections.Counter(x.split(' col')[0] for x in vwhite)
    add('J3. "White (reference)" em primeiro lugar em todo bloco onde aparece (CSV, xlsx, docx)', not vwhite,
        f'blocos com White fora da 1a posicao={len(vwhite)} por fonte={dict(by_src)}; exemplos={vwhite[:4]}; '
        f'grupos com rotulos de raca verificados={groups}. '
        f'(Rodada 1: 12 blocos da Tab. 2 - CSV, xlsx e docx - com White (reference) por ultimo, ordem herdada da v4.)')


# ----------------------------------------------------------------------------
def main():
    for fn in (check_A, check_B, check_C, check_D, check_E, check_F, check_G, check_item4, check_H, check_I, check_J):
        try:
            fn()
        except Exception as e:  # registrar falha de execucao como verificacao falha
            import traceback
            traceback.print_exc()
            add(f'ERRO ao executar {fn.__name__}', False, repr(e))
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['verificacao', 'ok', 'detalhe'])
        for v, ok, d in RESULTS:
            w.writerow([v, 'True' if ok else 'False', d])
    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    print(f'\n{len(RESULTS)} verificacoes; {n_ok} OK; {len(RESULTS) - n_ok} falhas -> {OUT_CSV}')


if __name__ == '__main__':
    main()
