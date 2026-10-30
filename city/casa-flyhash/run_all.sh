#!/usr/bin/env bash
# Reproduce TODOS los experimentos de casa-flyhash (los comandos exactos que se ejecutaron). Ejecutar desde la raiz de la casa.
# Variables: PY (python con numpy/scipy/numba/pandas/pyarrow/sklearn/torch), FLYHASH_DL (MNIST/Fashion/news; ver src/fetch_datasets.sh).
# ATENCION: los .jsonl se ANADEN (append); ejecutar en una copia limpia (sin out/raw) o se duplicaran filas.
# Usa a lo sumo 2 procesos si se lanzan en 2 carriles (aqui van en serie: ~5 h de CPU compartida; los dos primeros bloques son los pesados).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}; export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
SRC=src; OUT=out/raw; mkdir -p $OUT
SZ=3000,3000,400,2000
exp() { "$PY" -B -I $SRC/exp.py "$@"; }
# ---- E1: digits/proyeccion, todos los comparadores, 30 replicas (seed0=1000)
exp --dataset digits --mapper proj --reps 0:30 --frac 0.05 --variants real_b,real_w,null_b,null_w,nullsh_w,realtop_shw,nullbl_b,null_nb_b,f6,kcdeg_b,gauss,sgauss,sgauss_f6,sim_k,sim_st,sim_m,noexp,raw --tag E1 --out $OUT/E1_digits_proj_all.jsonl

# ---- laneA.sh
# E2 MNIST nucleo (proyeccion), 12 replicas
exp --dataset mnist --mapper proj --reps 0:12 --seed0 1000 --frac 0.05 --sizes 3000,3000,400,2000 --variants real_b,real_w,null_b,null_w,f6,kcdeg_b,gauss,sim_k,sim_st,sim_m,noexp,raw --tag E2 --out $OUT/E2_mnist_proj_A.jsonl

# ---- laneB.sh
# E9 potencia: ventaja inyectada (+e % KC extra) sobre el real, digits/proyeccion, mismas semillas que E1 (real_b y null_b se reutilizan de E1)
exp --dataset digits --mapper proj --reps 0:30 --seed0 1000 --frac 0.05 --tasks ret --variants plus10_b,plus25_b,plus50_b,plus100_b --tag E9 --out $OUT/E9_power.jsonl
# E3 barrido de dispersion
for f in 0.01 0.02 0.1 0.2 0.35 0.5; do
  exp --dataset digits --mapper proj --reps 0:10 --seed0 1000 --frac $f --variants real_b,null_b,f6,gauss,sim_k,sim_m,noexp --tag E3 --out $OUT/E3_f$f.jsonl
done

# ---- laneA2.sh
for mp in pca pca_deg pca_rdeg select glom; do
  exp --dataset mnist --mapper $mp --reps 0:12 --seed0 1000 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,null_b,real_w,null_w,f6,kcdeg_b,null_nb_b,gauss,raw --tag E7 --out $OUT/E7_mnist_$mp.jsonl
done
for mp in select glom; do
  exp --dataset digits --mapper $mp --reps 0:12 --seed0 1000 --frac 0.05 --variants real_b,null_b,real_w,null_w,f6,kcdeg_b,null_nb_b,gauss,sim_m,raw --tag E7 --out $OUT/E7_digits_$mp.jsonl
done
exp --dataset digits --mapper proj --reps 0:12 --seed0 1000 --frac 0.05 --norm 1 --variants real_b,real_w,null_b,null_w,f6,kcdeg_b,gauss,sim_m --tag E8 --out $OUT/E8_digits_norm.jsonl
exp --dataset mnist --mapper pca_deg --reps 0:10 --seed0 1000 --norm 1 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,real_w,null_b,null_w,f6,kcdeg_b --tag E8 --out $OUT/E8_mnist_pcadeg_norm.jsonl
exp --dataset fmnist --mapper proj --reps 0:8 --seed0 1000 --frac 0.05 --sizes $SZ --variants real_b,null_b,real_w,null_w,f6,gauss,sim_k,sim_st,sim_m,noexp,raw --tag E2f --out $OUT/E2f_fmnist_proj.jsonl
exp --dataset news --mapper proj --reps 0:8 --seed0 1000 --frac 0.05 --sizes $SZ --variants real_b,null_b,real_w,null_w,f6,gauss,sim_k,sim_st,sim_m,noexp,raw --tag E2n --out $OUT/E2n_news_proj.jsonl
for mp in pca pca_deg pca_rdeg; do
  exp --dataset news --mapper $mp --reps 0:8 --seed0 1000 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,null_b,f6,kcdeg_b,gauss,raw --tag E7n --out $OUT/E7n_news_$mp.jsonl
done

# ---- laneB2.sh
exp --dataset digits --mapper proj --reps 0:8 --seed0 1000 --frac 0.05 --conds clean,gnoise:0.5,gnoise:1,gnoise:2,mask:0.3,mask:0.6,lesion:0.3,lesion:0.6 --variants real_b,null_b,f6,sim_k,sim_m,raw --tag E5 --out $OUT/E5_digits_noise.jsonl
for st in 0 1 2; do
  exp --dataset digits --mapper proj --reps 0:20 --seed0 1000 --frac 0.05 --subtype $st --m_cap 650 --variants real_b,null_b,f6,gauss --tag E6_$st --out $OUT/E6_sub$st.jsonl
done
exp --dataset digits --mapper proj --reps 0:20 --seed0 1000 --frac 0.05 --mfrac 0.1705 --variants real_b,null_b,f6,gauss --tag E6_all --out $OUT/E6_suball.jsonl
"$PY" -B -I $SRC/exp_rank.py --mappings 0:12 --K 30 --K2 10 --out $OUT/E11_rank.jsonl
"$PY" -B -I $SRC/exp_scale.py --dataset digits --reps 0:6 --seed0 3000 --factors 0.0625,0.125,0.25,0.5,1,2,4,8,16,32,100 --tag E4 --out $OUT/E4_scale.jsonl

# ---- laneC.sh
for nm in 0 1; do
  for mp in pca pca_deg pca_rdeg; do
    exp --dataset mnist --mapper $mp --reps 0:12 --seed0 1000 --frac 0.05 --norm $nm --sizes $SZ --tasks ret --variants real_b,null_b,nulljdd_b,nullbl_b,f6,kcdeg_b,real_w,null_w --tag E7b --out $OUT/E7b_mnist_${mp}_norm$nm.jsonl
  done
done
for nm in 0 1; do
  exp --dataset mnist --mapper glom --reps 0:12 --seed0 1000 --frac 0.05 --norm $nm --sizes $SZ --tasks ret --variants real_b,null_b,nulljdd_b,nullbl_b,f6,kcdeg_b,null_nb_b --tag E7b --out $OUT/E7b_mnist_glom_norm$nm.jsonl
  exp --dataset mnist --mapper proj --reps 0:12 --seed0 1000 --frac 0.05 --norm $nm --sizes $SZ --tasks ret --variants real_b,null_b,nulljdd_b,f6,kcdeg_b,real_w,null_w --tag E7b --out $OUT/E7b_mnist_proj_norm$nm.jsonl
done

# ---- laneD.sh
# E13 las 252 KC sin PN cuentan (m=4064): ¿cambia la comparacion?
exp --dataset digits --mapper proj --reps 0:12 --seed0 1000 --frac 0.05 --keep_dead 1 --variants real_b,null_b,f6,gauss,sim_k,sim_m --tag E13 --out $OUT/E13_digits_keepdead.jsonl
# E14 control de mecanismo: real sin entradas repetidas del mismo tipo de PN
for mp in glom proj; do
  exp --dataset mnist --mapper $mp --reps 0:12 --seed0 1000 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,realdd_b,null_b,f6 --tag E14 --out $OUT/E14_mnist_$mp.jsonl
done
exp --dataset digits --mapper glom --reps 0:12 --seed0 1000 --frac 0.05 --tasks ret --variants real_b,realdd_b,null_b,f6 --tag E14 --out $OUT/E14_digits_glom.jsonl
# E12 compensacion presinaptica de PN (hubs): digits y MNIST, mapeos proj y pca/pca_deg/glom
exp --dataset digits --mapper proj --reps 0:12 --seed0 1000 --frac 0.05 --variants real_b,null_b,real_w,null_w,real_b_pn,null_b_pn,real_w_pn,null_w_pn,nulljdd_b_pn,f6,kcdeg_b,gauss --tag E12 --out $OUT/E12_digits_proj.jsonl
for mp in proj pca pca_deg glom; do
  exp --dataset mnist --mapper $mp --reps 0:12 --seed0 1000 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,null_b,real_w,null_w,real_b_pn,null_b_pn,real_w_pn,null_w_pn,nulljdd_b_pn,f6,kcdeg_b --tag E12 --out $OUT/E12_mnist_$mp.jsonl
done
"$PY" -B -I $SRC/exp_net.py --seeds 2:3 --out $OUT/E10_net.jsonl

# ---- laneE.sh
"$PY" -B -I $SRC/exp_net.py --seeds 0:2 --out $OUT/E10_net.jsonl
"$PY" -B -I $SRC/exp_net.py --seeds 0:2 --mapper pca_deg --budgets 10000,20000,40000 --archs fly_lin_real,fly_lin_null,fly_lin_f6,rf_lin --out $OUT/E10_net_pcadeg.jsonl

# ---- E7n replica (32 replicas nuevas de la senal exploratoria del texto con PCA)
for mp in pca pca_deg pca_rdeg; do exp --dataset news --mapper $mp --reps 8:40 --seed0 1000 --frac 0.05 --sizes $SZ --tasks ret --variants real_b,null_b,f6,kcdeg_b --tag E7n_rep --out $OUT/E7nrep_news_$mp.jsonl; done
# ---- E3: el punto frac=0.05 reutiliza E1 (reps 0-9); ver out/COMANDOS.txt
# ---- E15 regresion logistica (comprobacion de la lectura)
"$PY" -B -I $SRC/exp_logreg.py --dataset digits --reps 0:12 --out $OUT/E15_logreg_digits.jsonl
# ---- analisis
"$PY" -B -I $SRC/analyze_all.py
