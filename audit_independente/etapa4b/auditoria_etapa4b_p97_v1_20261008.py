# Extrai P10 e P97 INTERGROWTH-21st (kg) das tabelas oficiais em PDF (pypdf); dias = 7*sem + d
# Estende o extrator da etapa 4 (que só lia P10). Confere com o CSV oficial já existente em docs/referencias.
import pypdf, re, csv
REF = '/Volumes/Forja/ptb-racial-brasil/docs/referencias'
OUT = '/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4b'
pat = re.compile(r'^\s*(\d{2})\+(\d)\s+' + r'\s+'.join([r'([\d.]+)'] * 7) + r'\s*$')
seen = {}
for f, sexo in [('grow_newborn-ct-boys_bw_table.pdf', 1), ('grow_newborn-ct-girls_bw_table.pdf', 2),
                ('grow_verypreterm-ct-boys_bw_table.pdf', 1), ('grow_verypreterm-ct-girls_bw_table.pdf', 2)]:
    for p in pypdf.PdfReader(f'{REF}/{f}').pages:
        for ln in p.extract_text().splitlines():
            m = pat.match(ln)
            if m:
                v = tuple(float(m[i]) for i in range(3, 10))
                assert all(v[i] <= v[i + 1] for i in range(6)), ln
                seen.setdefault((sexo, 7 * int(m[1]) + int(m[2])), set()).add(v)
assert all(len(v) == 1 for v in seen.values()), 'duplicatas conflitantes'
# conferência cruzada com o CSV oficial (P10 e P97)
ofi = {}
with open(f'{REF}/intergrowth21_bw_centis_oficial.csv') as fh:
    for r in csv.DictReader(fh):
        if r['centil'] in ('10', '97'):
            ofi[(1 if r['sexo'] == 'M' else 2, int(r['gest_days']), r['centil'])] = float(r['peso_kg'])
dif = 0
with open(f'{OUT}/p97_intergrowth_tabela_v1_20261008.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['sexo', 'dias', 'p10_kg', 'p97_kg'])
    for (s, d), v in sorted(seen.items()):
        v = v.pop()
        dif += (ofi.get((s, d, '10')) != v[2]) + (ofi.get((s, d, '97')) != v[6])
        w.writerow([s, d, v[2], v[6]])
print('linhas', len(seen), 'dias min/max', min(k[1] for k in seen), max(k[1] for k in seen),
      'divergências com CSV oficial (P10+P97):', dif)
need = [(s, 7 * g + 3) for s in (1, 2) for g in range(24, 37)]
print('dias 7*sg+3 (24-36) ausentes:', [k for k in need if k not in seen])
