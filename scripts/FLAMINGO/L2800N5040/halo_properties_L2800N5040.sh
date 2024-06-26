#!/bin/bash -l
#
# Compute halo properties for a snapshot. Must run the group_membership
# script first.
#
# Output locations are specified by enviroment variables. E.g.
#
# export FLAMINGO_SCRATCH_DIR=/snap8/scratch/dp004/${USER}/FLAMINGO/ScienceRuns/
# export FLAMINGO_OUTPUT_DIR=/cosma8/data/dp004/${USER}/FLAMINGO/ScienceRuns/
#
# Job name determines which of the L2800N5040 runs we process.
# Array job index is the snapshot number to do. Submit with (for example):
#
# cd SOAP
# mkdir logs
# sbatch -J HYDRO_FIDUCIAL --array=0-78%4 ./scripts/FLAMINGO/L2800N5040/halo_properties_L2800N5040_HYDRO.sh
#
#SBATCH --nodes=16
#SBATCH --cpus-per-task=1
#SBATCH -o ./logs/halo_properties_L2800N5040_%x.%a.out
#SBATCH -p cosma8
#SBATCH -A dp004
#SBATCH --exclusive
#SBATCH -t 48:00:00
#

module purge
module load gnu_comp/11.1.0 openmpi/4.1.1 python/3.10.1

# Get location for temporary output
if [[ "${FLAMINGO_SCRATCH_DIR}" ]] ; then
  scratch_dir="${FLAMINGO_SCRATCH_DIR}"
else
  echo Please set FLAMINGO_SCRATCH_DIR
  exit 1
fi

# Get location for final output
if [[ "${FLAMINGO_OUTPUT_DIR}" ]] ; then
  output_dir="${FLAMINGO_OUTPUT_DIR}"
else
  echo Please set FLAMINGO_OUTPUT_DIR
  exit 1
fi

# Which simulation to do
sim="L2800N5040/${SLURM_JOB_NAME}"

# Input simulation location
basedir="/cosma8/data/dp004/flamingo/Runs/${sim}/"

# Where to write the uncompressed output
outbase="${scratch_dir}/${sim}/SOAP_uncompressed/"

# Location for temporary chunk output
chunkdir="${scratch_dir}/SOAP-tmp/${sim}/"

# Generate file names for this snapshot
swift_filename="${basedir}/snapshots/flamingo_%(snap_nr)04d/flamingo_%(snap_nr)04d.%(file_nr)d.hdf5"
extra_filename="${outbase}/membership_%(snap_nr)04d/membership_%(snap_nr)04d.%(file_nr)d.hdf5"
vr_basename="${basedir}/VR/catalogue_%(snap_nr)04d/vr_catalogue_%(snap_nr)04d"
outfile="${outbase}/halo_properties_%(snap_nr)04d.hdf5"

# Check for DMO run
dmo_flag=""
if [[ $sim == *DMO_* ]] ; then
  dmo_flag="--dmo"
fi

nr_chunks=80

# Create output directory
outdir=`dirname "${outfile}"`
mkdir -p "${outdir}"
lfs setstripe --stripe-count=-1 --stripe-size=32M ${outdir}

mpirun python3 -u -m mpi4py ./compute_halo_properties.py \
    ${swift_filename} ${chunkdir} ${vr_basename} ${outfile} ${SLURM_ARRAY_TASK_ID} \
    --chunks=${nr_chunks} ${dmo_flag} \
    --extra-input=${extra_filename} \
    --reference-snapshot=78 \
    --parameters parameter_files/flamingo_SOAP_params.yml
