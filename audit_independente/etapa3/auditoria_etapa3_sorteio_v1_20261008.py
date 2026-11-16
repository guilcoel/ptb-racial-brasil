# Sorteio do bootstrap (numpy só para índices). Grava contagens por município x réplica 1..20.
import numpy as np, duckdb
OUT='/Volumes/Forja/ptb-racial-brasil/audit_independente/etapa3'
muns=[r[0] for r in duckdb.sql(f"select mun from read_csv('{OUT}/clusters_boot_v1_20261008.csv', all_varchar=true) order by mun").fetchall()]
G=len(muns); assert G==5593
idx=np.random.default_rng(42).integers(0,G,size=(500,G))
with open(f'{OUT}/boot_contagens_r1a20_v1_20261008.csv','w') as f:
    f.write('replica,mun,k\n')
    for b in range(1,21):
        cnt=np.bincount(idx[b-1],minlength=G)
        for j in np.nonzero(cnt)[0]:
            f.write(f'{b},{muns[j]},{cnt[j]}\n')
print('ok G',G, 'distintos r1', len(np.unique(idx[0])))
