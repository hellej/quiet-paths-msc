#!/bin/bash
#SBATCH -J nw_nois
#SBATCH -o out.txt
#SBATCH -e err.txt
#SBATCH -n 1
#SBATCH --nodes=1
#SBATCH --cpus-per-task=15
#SBATCH --mem-per-cpu=4000
#SBATCH -p test
#SBATCH -t 00:20:00
#SBATCH --mail-type=END
#

export OMP_NUM_THREADS=15
module load geoconda
srun python noise_ext.py
