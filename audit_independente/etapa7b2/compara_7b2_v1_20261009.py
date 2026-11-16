# Comparação auditor × autor — Etapa 7b2 (executado APÓS selar auditor_valores_v1_20261009.csv)
import pandas as pd, numpy as np, sys, importlib.util
ROOT = '/Volumes/Forja/ptb-racial-brasil'
OUT = f'{ROOT}/audit_independente/etapa7b2'
TAB = f'{ROOT}/outputs/tables'
SP = sys.argv[1]
TAG = 'v1_20261009'
a = pd.read_csv(f'{OUT}/auditor_valores_{TAG}.csv')
A = {(r.tarefa, r.subamostra, r.item): r.valor for r in a.itertuples()}

rows = []
def add(tarefa, item, aud, aut):
    dif = aud - aut
    rows.append(dict(tarefa=tarefa, item=item, auditor=aud, autor=aut, dif=dif,
                     dif_rel=(dif / aut) if aut not in (0, None) and not pd.isna(aut) else np.nan))

# ---- A: distribuição
dist = pd.read_csv(f'{TAB}/tab_e7b2_01_dist_v1_20261008.csv')
for r in dist.itertuples():
    add('A', f'TPM{r.codigo}_n_{r.raca}', A[('A', f'TPM{r.codigo}', f'n_{r.raca}')], r.n)
    add('A', f'TPM{r.codigo}_pct_raca_{r.raca}', A[('A', f'TPM{r.codigo}', f'pct_total_raca_{r.raca}')], r.pct_da_raca)
# ---- A: M2 Indígena
m2 = pd.read_csv(f'{TAB}/tab_e7b2_01_m2_v1_20261008.csv')
for r in m2[m2.raca == 'Indigena'].itertuples():
    tpm = r.cenario.split('_')[1]
    for col, suf in [('PR', ''), ('PR_lo', '_lo'), ('PR_hi', '_hi')]:
        add('A', f'TPM{tpm}_M2_{r.desfecho}_{col}_Indigena', A[('A', f'TPM{tpm}', f'M2_{r.desfecho}_PR_Indigena{suf}')], getattr(r, col))
    add('A', f'TPM{tpm}_M2_{r.desfecho}_N', A[('A', f'TPM{tpm}', f'M2_{r.desfecho}_N')], r.N)
# ---- A: ICR Indígena × T1
it = pd.read_csv(f'{TAB}/tab_e7b2_01_interacao_v1_20261008.csv')
for r in it[(it.raca == 'Indigena') & (it.nivel == 'T1')].itertuples():
    tpm = r.sensibilidade.split('_')[1]
    for col, suf in [('ICR_pp', ''), ('ICR_lo', '_lo'), ('ICR_hi', '_hi')]:
        add('A', f'TPM{tpm}_{col}_{r.desfecho}_Indigena_T1', A[('A', f'TPM{tpm}', f'ICR_{r.desfecho}_Indigena_T1{suf}')], getattr(r, col))
# ---- A: Wald
wd = pd.read_csv(f'{TAB}/tab_e7b2_01_wald_v1_20261008.csv')
for r in wd.itertuples():
    tpm = r.sensibilidade.split('_')[1]
    add('A', f'TPM{tpm}_Wald_{r.desfecho}_chi2', A[('A', f'TPM{tpm}', f'Wald_{r.desfecho}_chi2')], r.chi2)
    add('A', f'TPM{tpm}_Wald_{r.desfecho}_p', A[('A', f'TPM{tpm}', f'Wald_{r.desfecho}_p')], r.p)
    add('A', f'TPM{tpm}_3.2_{r.desfecho}_N', A[('A', f'TPM{tpm}', f'3.2_{r.desfecho}_N')], r.N)
# ---- A: casos indígenas por tercil
ci = pd.read_csv(f'{TAB}/tab_e7b2_01_casos_ind_v1_20261008.csv')
for r in ci.itertuples():
    add('A', f'TPM{r.codigo}_casos_ind_{r.desfecho}_{r.tercil}', A[('A', f'TPM{r.codigo}', f'casos_ind_{r.desfecho}_{r.tercil}')], r.casos)
# ---- B: P97 (auditor = tabela oficial; [eq] = sensibilidade com equação gigs)
p97 = pd.read_csv(f'{TAB}/tab_e7b2_01_p97_v1_20261008.csv')
for r in p97.itertuples():
    s = f'TPM{r.codigo}'
    add('B', f'{s}_n_elig_ptb_{r.raca}', A[('B', s, f'n_elig_ptb_{r.raca}')], r.n_prematuros)
    add('B', f'{s}_casos_gt97_{r.raca}', A[('B', s, f'n_gt97_tab_{r.raca}')], r.casos_p97)
    add('B', f'{s}_pct_gt97_{r.raca}', A[('B', s, f'pct_gt97_tab_{r.raca}')], r.pct)
    add('B', f'{s}_pct_gt97_{r.raca}[eq]', A[('B', s, f'pct_gt97_eq_{r.raca}')], r.pct)
# ---- C: reclassificação
add('C', 'n_PTB_reclassificados', A[('C', 'todas', 'reclass_ptb_rc_tab')], 410747)
add('C', 'n_PTBesp_reclassificados', A[('C', 'todas', 'reclass_esp_rc_tab')], 244676)
add('C', 'n_PTB_reclassificados[eq]', A[('C', 'todas', 'reclass_ptb_rc_eq')], 410747)
add('C', 'n_PTBesp_reclassificados[eq]', A[('C', 'todas', 'reclass_esp_rc_eq')], 244676)
rm = pd.read_csv(f'{TAB}/tab_e7b2_02_reclass_m2_v1_20261008.csv')
for r in rm.itertuples():
    lab = 'ptb' if r.desfecho == 'ptb_reclass' else 'ptb_esp'
    for ver, tag in [('tab', ''), ('eq', '[eq]')]:
        for col, suf in [('PR', ''), ('PR_lo', '_lo'), ('PR_hi', '_hi')]:
            add('C', f'M2_{lab}_reclass_{col}_{r.raca}{tag}', A[('C', ver, f'M2_{lab}_PR_{r.raca}{suf}')], getattr(r, col))
    if r.raca == 'Parda':
        for ver, tag in [('tab', ''), ('eq', '[eq]')]:
            add('C', f'M2_{lab}_reclass_casos{tag}', A[('C', ver, f'M2_{lab}_casos')], r.casos)
        add('C', f'M2_{lab}_reclass_N', A[('C', 'tab', f'M2_{lab}_N')], r.N)
ri = pd.read_csv(f'{TAB}/tab_e7b2_02_reclass_interacao_v1_20261008.csv')
for r in ri[(ri.raca == 'Indigena') & (ri.nivel == 'T1')].itertuples():
    lab = 'ptb' if r.desfecho == 'ptb_reclass' else 'ptb_esp'
    for ver, tag in [('tab', ''), ('eq', '[eq]')]:
        for col, suf in [('ICR_pp', ''), ('ICR_lo', '_lo'), ('ICR_hi', '_hi')]:
            add('C', f'{col}_{lab}_reclass_Indigena_T1{tag}', A[('C', ver, f'ICR_{lab}_Indigena_T1{suf}')], getattr(r, col))
rw = pd.read_csv(f'{TAB}/tab_e7b2_02_reclass_wald_v1_20261008.csv')
for r in rw.itertuples():
    lab = 'ptb' if r.desfecho == 'ptb_reclass' else 'ptb_esp'
    for ver, tag in [('tab', ''), ('eq', '[eq]')]:
        add('C', f'Wald_{lab}_reclass_chi2{tag}', A[('C', ver, f'Wald_{lab}_chi2')], r.chi2)
        add('C', f'Wald_{lab}_reclass_p{tag}', A[('C', ver, f'Wald_{lab}_p')], r.p)

# ---- Extras pós-leitura (rotulados): M2 Parda/Preta nas subamostras TPM (o autor também reporta)
spec = importlib.util.spec_from_file_location('mods', f'{OUT}/auditor_7b2_modelos_v1_20261009.py')
cells = pd.read_parquet(f'{SP}/cells_7b2.parquet')
src = open(f'{OUT}/auditor_7b2_modelos_v1_20261009.py').read().split('# ---------------- Tarefa A')[0]
ns = {}; sys.argv = ['x', SP]; exec(src, ns)
for r in m2[m2.raca != 'Indigena'].itertuples():
    tpm = r.cenario.split('_')[1]
    ncol, ycol = ns['OUTC'][r.desfecho]
    res = ns['fit'](cells[cells.tpm == tpm], ncol, ycol, 'M2')
    e, lo, hi, se = ns['pr'](res, f'raca{r.raca}')
    add('A-extra(pos-leitura)', f'TPM{tpm}_M2_{r.desfecho}_PR_{r.raca}', e, r.PR)

cmp = pd.DataFrame(rows)
cmp.to_csv(f'{OUT}/comparacao_7b2_{TAG}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
cmp['absrel'] = cmp.dif_rel.abs()
print('itens:', len(cmp))
print(cmp.groupby('tarefa').absrel.max())
print(cmp[cmp.absrel > 1e-6].to_string())
