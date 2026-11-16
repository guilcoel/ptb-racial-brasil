# Auditoria independente — Etapa 7b2: modelos (M2 e 3.2) sobre células agregadas.
import numpy as np, pandas as pd, sys
from scipy import stats

np.random.seed(42)
ROOT = '/Volumes/Forja/ptb-racial-brasil'
OUT = f'{ROOT}/audit_independente/etapa7b2'
SP = sys.argv[1]
TAG = 'v1_20261009'
cells = pd.read_parquet(f'{SP}/cells_7b2.parquet')

RACAS = ['Preta', 'Parda', 'Indigena']
IDADES = ['<20', '>=35']
ANOS = list(range(2016, 2025))
REGS = ['N', 'NE', 'S', 'CO']
TERCS = ['T1', 'T2']


def design(df, model, raca=None, tercil=None):
    r = df['raca'].values if raca is None else np.repeat(raca, len(df))
    cols, names = [np.ones(len(df))], ['(Intercept)']
    for g in RACAS:
        cols.append((r == g).astype(float)); names.append(f'raca{g}')
    for a in IDADES:
        cols.append((df['idade_cat'].values == a).astype(float)); names.append(f'idade{a}')
    for y in ANOS:
        cols.append((df['ano'].values == y).astype(float)); names.append(f'ano{y}')
    for g in REGS:
        cols.append((df['regiao'].values == g).astype(float)); names.append(f'regiao{g}')
    if model == '3.2':
        t = df['tercil'].values if tercil is None else np.repeat(tercil, len(df))
        for tt in TERCS:
            cols.append((t == tt).astype(float)); names.append(f'tercil{tt}')
        for g in RACAS:
            for tt in TERCS:
                cols.append(((r == g) & (t == tt)).astype(float)); names.append(f'raca{g}:tercil{tt}')
    return np.column_stack(cols), names


def fit(df, ncol, ycol, model):
    df = df[df[ncol] > 0].copy()
    if model == '3.2':
        df = df[df['has_reg']].copy()
        assert df['tercil'].notna().all()
    X, names = design(df, model)
    n = df[ncol].values; y = df[ycol].values
    N = n.sum(); K = X.shape[1]
    beta = np.zeros(K); beta[0] = np.log(y.sum() / N)
    dev_old = np.inf
    for it in range(100):
        eta = X @ beta; mu = np.exp(eta)
        w = n * mu
        z = eta + (y / n - mu) / mu
        XtW = X.T * w
        beta = np.linalg.solve(XtW @ X, XtW @ z)
        mu = np.exp(X @ beta)
        ll = np.sum(y * (X @ beta) - n * mu)
        if abs(ll - dev_old) < 1e-10 * (abs(ll) + 1):
            break
        dev_old = ll
    mu = np.exp(X @ beta)
    A = (X.T * (n * mu)) @ X
    U = X * (y - n * mu)[:, None]
    Ug = pd.DataFrame(U).groupby(df['cl'].values).sum().values
    G = Ug.shape[0]
    M = Ug.T @ Ug
    Ai = np.linalg.inv(A)
    V = Ai @ M @ Ai * (G / (G - 1)) * ((N - 1) / (N - K))
    res = dict(beta=pd.Series(beta, names), V=pd.DataFrame(V, names, names), N=N, G=G, K=K, df=df,
               cases=y.sum(), iters=it, maxscore=np.abs(X.T @ (y - n * mu)).max())
    return res


def pr(res, term):
    b = res['beta'][term]; se = np.sqrt(res['V'].loc[term, term])
    return np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se), se


def icr(res, ncol, g='Indigena', t='T1'):
    df = res['df']; n = df[ncol].values; beta = res['beta'].values; N = n.sum()
    P = {}; D = {}
    for gg in [g, 'Branca']:
        for tt in [t, 'T3']:
            X, _ = design(df, '3.2', raca=gg, tercil=tt)
            mu = np.exp(X @ beta)
            P[(gg, tt)] = (n * mu).sum() / N
            D[(gg, tt)] = (X.T @ (n * mu)) / N
    est = 100 * ((P[(g, t)] - P[('Branca', t)]) - (P[(g, 'T3')] - P[('Branca', 'T3')]))
    grad = 100 * ((D[(g, t)] - D[('Branca', t)]) - (D[(g, 'T3')] - D[('Branca', 'T3')]))
    se = np.sqrt(grad @ res['V'].values @ grad)
    return est, est - 1.96 * se, est + 1.96 * se, se, P


def wald(res):
    terms = [f'raca{g}:tercil{tt}' for g in RACAS for tt in TERCS]
    b = res['beta'][terms].values; V = res['V'].loc[terms, terms].values
    chi2 = float(b @ np.linalg.solve(V, b))
    return chi2, len(terms), stats.chi2.sf(chi2, len(terms))


OUTC = {'ptb': ('n', 'y_ptb'), 'pig': ('n_pig', 'y_pig'), 'ptb_ind': ('n_ind', 'y_ind'),
        'ptb_esp': ('n_esp', 'y_esp'),
        'ptb_rc': ('n', 'y_ptb_rc'), 'ptb_esp_rc': ('n_esp', 'y_esp_rc'),
        'ptb_rceq': ('n', 'y_ptb_rceq'), 'ptb_esp_rceq': ('n_esp', 'y_esp_rceq')}

rows = []
def add(tarefa, sub, item, val, extra=''):
    rows.append(dict(tarefa=tarefa, subamostra=sub, item=item, valor=val, nota=extra))

# ---------------- Tarefa A ----------------
tot_raca = cells.groupby('raca')['n'].sum()
for tpm in ['1', '2']:
    sub = cells[cells.tpm == tpm]
    nr = sub.groupby('raca')['n'].sum()
    for g in ['Branca', 'Preta', 'Parda', 'Indigena']:
        add('A', f'TPM{tpm}', f'n_{g}', nr[g])
        add('A', f'TPM{tpm}', f'pct_total_raca_{g}', 100 * nr[g] / tot_raca[g])
    add('A', f'TPM{tpm}', 'n_total', nr.sum())
    for oc in ['ptb', 'pig', 'ptb_ind']:
        ncol, ycol = OUTC[oc]
        r2 = fit(sub, ncol, ycol, 'M2')
        e, lo, hi, se = pr(r2, 'racaIndigena')
        add('A', f'TPM{tpm}', f'M2_{oc}_PR_Indigena', e, f'IC95 {lo:.4f}-{hi:.4f}; N={r2["N"]:.0f}; G={r2["G"]}; casos={r2["cases"]:.0f}')
        add('A', f'TPM{tpm}', f'M2_{oc}_PR_Indigena_lo', lo); add('A', f'TPM{tpm}', f'M2_{oc}_PR_Indigena_hi', hi)
        add('A', f'TPM{tpm}', f'M2_{oc}_N', r2['N'])
        r3 = fit(sub, ncol, ycol, '3.2')
        ei, lo, hi, se, P = icr(r3, ncol)
        add('A', f'TPM{tpm}', f'ICR_{oc}_Indigena_T1', ei, f'IC95 {lo:.4f} a {hi:.4f}; N={r3["N"]:.0f}; G={r3["G"]}')
        add('A', f'TPM{tpm}', f'ICR_{oc}_Indigena_T1_lo', lo); add('A', f'TPM{tpm}', f'ICR_{oc}_Indigena_T1_hi', hi)
        add('A', f'TPM{tpm}', f'3.2_{oc}_N', r3['N'])
        chi2, dfw, p = wald(r3)
        add('A', f'TPM{tpm}', f'Wald_{oc}_chi2', chi2, f'df={dfw}')
        add('A', f'TPM{tpm}', f'Wald_{oc}_p', p)
        # casos indígenas por tercil (amostra do 3.2)
        d3 = r3['df']
        ci = d3[d3.raca == 'Indigena'].groupby('tercil')[ycol].sum()
        ni = d3[d3.raca == 'Indigena'].groupby('tercil')[ncol].sum()
        for tt in ['T1', 'T2', 'T3']:
            c = ci.get(tt, 0)
            add('A', f'TPM{tpm}', f'casos_ind_{oc}_{tt}', c, ('<30 ' if c < 30 else '') + f'n_ind={ni.get(tt,0):.0f}')
        print(tpm, oc, 'done', flush=True)

# ---------------- Tarefa B ----------------
B = pd.read_csv(f'{SP}/B_raw.csv')
B['tpm'] = B['tpm'].astype(str)
for tpm in ['1', '2', 'todas']:
    sb = B if tpm == 'todas' else B[B.tpm == tpm]
    g = sb.groupby('raca')[['n_elig_ptb', 'n_gt97_tab', 'n_gt97_eq']].sum()
    g.loc['Total'] = g.sum()
    for rc in ['Branca', 'Preta', 'Parda', 'Indigena', 'Total']:
        add('B', f'TPM{tpm}', f'n_elig_ptb_{rc}', g.loc[rc, 'n_elig_ptb'])
        add('B', f'TPM{tpm}', f'n_gt97_tab_{rc}', g.loc[rc, 'n_gt97_tab'])
        add('B', f'TPM{tpm}', f'pct_gt97_tab_{rc}', 100 * g.loc[rc, 'n_gt97_tab'] / g.loc[rc, 'n_elig_ptb'])
        add('B', f'TPM{tpm}', f'pct_gt97_eq_{rc}', 100 * g.loc[rc, 'n_gt97_eq'] / g.loc[rc, 'n_elig_ptb'], 'sensibilidade: equação gigs')

# ---------------- Tarefa C ----------------
recl = pd.read_csv(f'{SP}/recl_raw.csv').iloc[0]
for k, v in recl.items():
    add('C', 'todas', f'reclass_{k}', v)
for version, (o_ptb, o_esp) in {'tab': ('ptb_rc', 'ptb_esp_rc'), 'eq': ('ptb_rceq', 'ptb_esp_rceq'),
                                'orig': ('ptb', 'ptb_esp')}.items():
    for oc in [o_ptb, o_esp]:
        ncol, ycol = OUTC[oc]
        lab = 'ptb' if oc in ('ptb_rc', 'ptb_rceq', 'ptb') else 'ptb_esp'
        r2 = fit(cells, ncol, ycol, 'M2')
        for g in RACAS:
            e, lo, hi, se = pr(r2, f'raca{g}')
            add('C', version, f'M2_{lab}_PR_{g}', e, f'IC95 {lo:.4f}-{hi:.4f}; N={r2["N"]:.0f}; G={r2["G"]}; casos={r2["cases"]:.0f}')
            add('C', version, f'M2_{lab}_PR_{g}_lo', lo); add('C', version, f'M2_{lab}_PR_{g}_hi', hi)
        add('C', version, f'M2_{lab}_N', r2['N']); add('C', version, f'M2_{lab}_casos', r2['cases'])
        r3 = fit(cells, ncol, ycol, '3.2')
        ei, lo, hi, se, P = icr(r3, ncol)
        add('C', version, f'ICR_{lab}_Indigena_T1', ei, f'IC95 {lo:.4f} a {hi:.4f}; N={r3["N"]:.0f}; G={r3["G"]}')
        add('C', version, f'ICR_{lab}_Indigena_T1_lo', lo); add('C', version, f'ICR_{lab}_Indigena_T1_hi', hi)
        chi2, dfw, p = wald(r3)
        add('C', version, f'Wald_{lab}_chi2', chi2, f'df={dfw}')
        add('C', version, f'Wald_{lab}_p', p)
        print('C', version, oc, 'done', flush=True)

out = pd.DataFrame(rows)
out.to_csv(f'{OUT}/auditor_valores_{TAG}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500)
print(out[~out.item.str.endswith(('_lo', '_hi'))].to_string())
