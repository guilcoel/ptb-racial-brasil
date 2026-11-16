# Extrai P10 INTERGROWTH-21st (kg) das tabelas oficiais em PDF (pypdf), dias = 7*sem + d
import pypdf, re, csv
REF = '/Volumes/Forja/ptb-racial-brasil/docs/referencias'
OUT = '/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa4'
rows = []
for f, sexo in [('grow_newborn-ct-boys_bw_table.pdf', 1), ('grow_newborn-ct-girls_bw_table.pdf', 2),
                ('grow_verypreterm-ct-boys_bw_table.pdf', 1), ('grow_verypreterm-ct-girls_bw_table.pdf', 2)]:
    for p in pypdf.PdfReader(f'{REF}/{f}').pages:
        for ln in p.extract_text().splitlines():
            m = re.match(r'^\s*(\d{2})\+(\d)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s', ln)
            if m:
                rows.append((sexo, 7 * int(m[1]) + int(m[2]), float(m[5]), f))
seen = {}
for s, d, p, f in rows:
    seen.setdefault((s, d), set()).add(p)
assert all(len(v) == 1 for v in seen.values()), 'duplicatas conflitantes'
with open(f'{OUT}/p10_intergrowth_tabela_v1_20261008.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['sexo', 'dias', 'p10_kg'])
    for (s, d), v in sorted(seen.items()):
        w.writerow([s, d, v.pop()])
print('linhas', len(seen), 'por sexo', {s: sum(1 for k in seen if k[0] == s) for s in (1, 2)},
      'dias min/max', min(k[1] for k in seen), max(k[1] for k in seen))
