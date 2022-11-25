#!/bin/bash

# don't forget to set the --all flag for md trajs

# load dirs
source env.sh

# set python path
PYTHONPATH="/home/rhjvanworkum/caschnet/:/home/rhjvanworkum/schnetpack/src/:$PYTHONPATH"
export PYTHONPATH

# variables
# test_geometry_folder=geometries/fulvene_geom_scan_250/
# db_name=fulvene_geom_scan_250.db
# split_name=fulvene_gs_250.npz
# mo_model=fulvene_gs250_MO
# f_model=fulvene_gs250_F
# phisnet_model=fulvene_gs250_phisnet
# basis=sto_6g

test_geometry_folder=geometries/fulvene_md_traj_25/
db_name=fulvene_md_250.db
split_name=fulvene_md_250.npz
mo_model=fulvene_md_250_MO
f_model=fulvene_md_250_F
phisnet_model=fulvene_md250_phisnet
basis=sto_6g

# run evaluation scripts
python evaluation/evaluate_model_loss.py --db_name $db_name --split_name $split_name --mo_model $mo_model --F_model $f_model --phisnet_model $phisnet_model
python evaluation/evaluate_orbital_guesses_convergence.py --geometry_folder $test_geometry_folder --split_name $split_name --mo_model $mo_model --F_model $f_model --phisnet_model $phisnet_model --basis $basis --all true
python evaluation/evaluate_orbital_guesses_energies.py --geometry_folder $test_geometry_folder --split_name $split_name --mo_model $mo_model --F_model $f_model --phisnet_model $phisnet_model --basis $basis --all true