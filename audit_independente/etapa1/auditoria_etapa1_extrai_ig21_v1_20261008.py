# Extrai centis oficiais INTERGROWTH-21st de peso ao nascer dos PDFs (pypdf). Nao usa o CSV do autor.
import re, csv, pypdf
D='/Volumes/Forja/ptb-racial-brasil/docs/referencias/'
arqs={('newborn','M'):'grow_newborn-ct-boys_bw_table.pdf',('newborn','F'):'grow_newborn-ct-girls_bw_table.pdf',
      ('verypreterm','M'):'grow_verypreterm-ct-boys_bw_table.pdf',('verypreterm','F'):'grow_verypreterm-ct-girls_bw_table.pdf'}
pat=re.compile(r'^\s*(\d{2})\+(\d)\s+'+r'\s+'.join([r'(\d\.\d{2})']*7)+r'\s*$')
rows=[]
for (tab,sx),f in arqs.items():
    n=0
    for p in pypdf.PdfReader(D+f).pages:
        for ln in p.extract_text().splitlines():
            m=pat.match(ln)
            if m:
                w,d=int(m[1]),int(m[2]); v=[float(x) for x in m.groups()[2:]]
                rows.append([tab,sx,w,d,7*w+d]+v); n+=1
    print(tab,sx,n,'linhas')
# checagens: dias contiguos, centis monotonos
from collections import defaultdict
g=defaultdict(list)
for r in rows: g[(r[0],r[1])].append(r)
for k,v in g.items():
    ds=sorted(r[4] for r in v); assert ds==list(range(ds[0],ds[-1]+1)),k
    for r in v: assert all(r[5+i]<=r[6+i] for i in range(6)),r
    print(k,ds[0],ds[-1])
with open('ig21_bw_centis_extraidos_pdf_v1_20261008.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['tabela','sexo','sem','dia','ig_dias','p3','p5','p10','p50','p90','p95','p97']); w.writerows(rows)
