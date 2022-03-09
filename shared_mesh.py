#!/bin/env python

import numpy as np
import shared_array
import virgo.mpi.parallel_sort as ps
from mpi4py import MPI

class SharedMesh:

    def __init__(self, comm, pos, resolution):
        """
        Build a mesh in shared memory which can be used to find
        particles in a particular region. Input is assumed to
        already be wrapped so we don't need to consider the periodic
        boundary.

        Input positions are stored in a SharedArray instance. Setting
        up the mesh is a collective operation over communicator comm.
        """
        
        comm_rank = comm.Get_rank()

        # First, we need to establish a bounding box for the particles
        pos_min_local = np.amin(pos.local.value, axis=0)
        pos_max_local = np.amax(pos.local.value, axis=0)
        self.pos_min = pos_min_local.copy()
        comm.Allreduce(pos_min_local, self.pos_min, op=MPI.MIN)
        self.pos_max = pos_max_local.copy()
        comm.Allreduce(pos_max_local, self.pos_max, op=MPI.MAX)

        # Determine the cell size
        self.resolution = int(resolution)
        nr_cells = self.resolution**3
        self.cell_size = (self.pos_max-self.pos_min)/self.resolution

        # Determine which cell each particle in the local part of pos belongs to
        cell_idx = np.floor((pos.local.value-self.pos_min[None,:])/self.cell_size[None,:]).astype(np.int32)
        cell_idx = np.clip(cell_idx, 0, self.resolution-1)
        cell_idx = cell_idx[:,0] + self.resolution*cell_idx[:,1] + (self.resolution**2)*cell_idx[:,2]

        # Count local particles per cell
        local_count = np.bincount(cell_idx, minlength=nr_cells)
        # Allocate a shared array to store the global count
        shape = (nr_cells,) if comm_rank==0 else (0,)
        self.cell_count = shared_array.SharedArray(shape, local_count.dtype, comm)
        # Accumulate local counts to the shared array
        if comm_rank == 0:
            global_count = np.empty_like(local_count)
        else:
            global_count = None
        comm.Reduce(local_count, global_count, op=MPI.SUM, root=0)
        if comm_rank == 0:
            self.cell_count.full[:] = global_count
        comm.barrier()
        self.cell_count.sync()

        # Compute offset to each cell
        self.cell_offset = shared_array.SharedArray(shape, local_count.dtype, comm)
        if comm_rank == 0:
            self.cell_offset.full[0] = 0
            if len(self.cell_offset.full) > 1:
                np.cumsum(self.cell_count.full[:-1], out=self.cell_offset.full[1:])
        comm.barrier()
        self.cell_offset.sync()

        # Compute sorting index to put particles in order of cell
        sort_idx_local = ps.parallel_sort(cell_idx, comm=comm, return_index=True)
        del cell_idx

        # Merge local sorting indexes into a single shared array
        self.sort_idx = shared_array.SharedArray(sort_idx_local.shape, sort_idx_local.dtype, comm)
        self.sort_idx.local[:] = sort_idx_local
        comm.barrier()
        self.sort_idx.sync()

    def free(self):
        self.cell_count.free()
        self.cell_offset.free()
        self.sort_idx.free()

    def query(self, pos_min, pos_max):
        """
        Return indexes of particles which might be in the region defined
        by pos_min and pos_max. This can be called independently on
        different MPI ranks since it only reads the shared data.
        """
        
        if hasattr(pos_min, "value"):
            pos_min = pos_min.value
        if hasattr(pos_max, "value"):
            pos_max = pos_max.value

        # Find range of cells involved
        cell_min_idx = np.floor((pos_min-self.pos_min)/self.cell_size).astype(np.int32)
        cell_min_idx = np.clip(cell_min_idx, 0, self.resolution-1)
        cell_max_idx = np.floor((pos_max-self.pos_min)/self.cell_size).astype(np.int32)
        cell_max_idx = np.clip(cell_max_idx, 0, self.resolution-1)

        # Get the indexes of particles in the required cells
        idx = []
        for k in range(cell_min_idx[2], cell_max_idx[2]+1):
            for j in range(cell_min_idx[1], cell_max_idx[1]+1):
                for i in range(cell_min_idx[0], cell_max_idx[0]+1):
                    cell_nr = i+self.resolution*j+(self.resolution**2)*k
                    start = self.cell_offset.full[cell_nr]
                    count = self.cell_count.full[cell_nr]
                    if count > 0:
                        idx.append(self.sort_idx.full[start:start+count])
        
        # Return a single array of indexes
        if len(idx) > 0:
            return np.concatenate(idx)
        else:
            return np.ndarray(0, dtype=int)

    def query_radius(self, centre, radius, pos):
        """
        Return indexes of particles which are in a sphere defined by
        centre and radius. pos should be the coordinates used to build
        the mesh. This can be called independently on different MPI ranks
        since it only reads the shared data.
        """
        
        pos_min = centre - radius
        pos_max = centre + radius

        if hasattr(pos_min, "value"):
            pos_min = pos_min.value
        if hasattr(pos_max, "value"):
            pos_max = pos_max.value

        # Find range of cells involved
        cell_min_idx = np.floor((pos_min-self.pos_min)/self.cell_size).astype(np.int32)
        cell_min_idx = np.clip(cell_min_idx, 0, self.resolution-1)
        cell_max_idx = np.floor((pos_max-self.pos_min)/self.cell_size).astype(np.int32)
        cell_max_idx = np.clip(cell_max_idx, 0, self.resolution-1)

        # Get the indexes of particles in the required cells
        idx = []
        for k in range(cell_min_idx[2], cell_max_idx[2]+1):
            for j in range(cell_min_idx[1], cell_max_idx[1]+1):
                for i in range(cell_min_idx[0], cell_max_idx[0]+1):
                    cell_nr = i+self.resolution*j+(self.resolution**2)*k
                    start = self.cell_offset.full[cell_nr]
                    count = self.cell_count.full[cell_nr]
                    if count > 0:
                        idx_in_cell = self.sort_idx.full[start:start+count]
                        r2 = np.sum((pos.full[idx_in_cell, :] - centre[None,:])**2, axis=1)
                        keep = (r2 <= radius*radius)
                        if np.sum(keep) > 0:
                            idx.append(idx_in_cell[keep])
        
        # Return a single array of indexes
        if len(idx) > 0:
            return np.concatenate(idx)
        else:
            return np.ndarray(0, dtype=int)