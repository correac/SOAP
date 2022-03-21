#!/bin/bash

module purge
module load gnu_comp/11.1.0 openmpi/4.1.1 python/3.10.1

#swift_filename="/cosma8/data/dp004/jlvc76/FLAMINGO/ScienceRuns/L1000N1800/HYDRO_FIDUCIAL/snapshots/flamingo_0077/flamingo_0077.0.hdf5"
#vr_basename="/cosma8/data/dp004/jlvc76/FLAMINGO/ScienceRuns/L1000N1800/HYDRO_FIDUCIAL/VR/catalogue_0077/vr_catalogue_0077"
#outfile="/cosma8/data/dp004/jch/tmp/test.hdf5"
#
#mpirun -np 8 python3 -u -m mpi4py \
#    ./vr_group_membership.py ${swift_filename} ${vr_basename} ${outfile}

swift_filename="/cosma8/data/dp004/jch/FLAMINGO/BlackHoles/200_w_lightcone/snapshots/flamingo_0013.hdf5"
vr_basename="/cosma8/data/dp004/jch/FLAMINGO/BlackHoles/200_w_lightcone/vr/catalogue_0013/vr_catalogue_0013"
outfile="/cosma8/data/dp004/jch/tmp/test.hdf5"

mpirun -np 8 python3 -u -m mpi4py \
    ./vr_group_membership.py ${swift_filename} ${vr_basename} ${outfile}