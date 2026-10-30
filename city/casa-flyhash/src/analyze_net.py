"""E10: tabla y figura de la red entrenada a igual nº de parametros entrenables. n=3 semillas: se dan media, sd y rango de las diferencias pareadas (sin p-valores)."""
import os, sys, json, numpy as np, pandas as pd
import matplotlib; matplotlib.use('svg'); matplotlib.rcParams['svg.fonttype'] = 'none'
import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'); RAW = os.path.join(OUT, 'raw')
def rd(f): return pd.DataFrame([json.loads(l) for l in open(os.path.join(RAW, f))]) if os.path.exists(os.path.join(RAW, f)) else pd.DataFrame()
df = rd('E10_net.jsonl'); pdg = rd('E10_net_pcadeg.jsonl')
def table(d, name):
    t = d.groupby(['budget', 'arch']).acc.agg(['mean', 'std', 'count']).round(4).reset_index(); t.to_csv(os.path.join(OUT, f'{name}_summary.csv'), index=False)
    P = d.pivot_table(index=['seed', 'budget'], columns='arch', values='acc'); rows = []
    for a, b in (('fly_lin_real', 'fly_lin_null'), ('fly_lin_f6', 'fly_lin_real'), ('dense', 'fly_lin_f6'), ('rf_lin', 'fly_lin_f6'), ('dense', 'rf_lin'), ('fly_hid_f6', 'fly_hid_real'), ('fly_hid_real', 'fly_hid_null'), ('dense', 'fly_hid_f6')):
        if a in P and b in P:
            for B, g in P.groupby(level='budget'):
                x = (g[a] - g[b]).dropna()
                if len(x): rows.append(dict(a=a, b=b, budget=B, n=len(x), mean_pp=100 * x.mean(), min_pp=100 * x.min(), max_pp=100 * x.max()))
    R = pd.DataFrame(rows).round(2); R.to_csv(os.path.join(OUT, f'{name}_paired.csv'), index=False); return t, R
if len(df):
    t, R = table(df, 'E10'); pd.set_option('display.width', 220)
    print(df.groupby(['budget', 'arch']).acc.mean().unstack(1).round(4).to_string()); print(R.to_string(index=False))
    fig, ax = plt.subplots(figsize=(5.4, 3.6)); col = {'dense': 'k', 'rf_lin': '#66a61e', 'fly_lin_real': '#d95f02', 'fly_lin_null': '#7570b3', 'fly_lin_f6': '#1b9e77', 'fly_hid_f6': '#1b9e77', 'fly_hid_real': '#d95f02', 'fly_hid_null': '#7570b3'}
    for arch, g in df.groupby('arch'):
        s = g.groupby('budget').acc.agg(['mean', 'std']); ax.errorbar(s.index, s['mean'], s['std'], label=arch, color=col.get(arch), ls='--' if 'hid' in arch else '-', marker='o', ms=3, capsize=2, lw=1)
    ax.set_xscale('log'); ax.set_xlabel('parametros entrenables'); ax.set_ylabel('exactitud test (MNIST)'); ax.legend(fontsize=6); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'fig_net.svg')); plt.close(fig)
if len(pdg):
    t, R = table(pdg, 'E10pcadeg'); print(pdg.groupby(['budget', 'arch']).acc.mean().unstack(1).round(4).to_string()); print(R.to_string(index=False))
