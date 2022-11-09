#!/bin/env python

class SnapshotDatasets:
    def __init__(self, file_handle):
        self.datasets_in_file = {}
        for group in file_handle:
            if group.startswith("PartType"):
                self.datasets_in_file[group] = []
                for dset in file_handle[group]:
                     self.datasets_in_file[group].append(dset)

        # Read named columns
        self.named_columns = {}
        for name in file_handle["SubgridScheme"]["NamedColumns"]:
                column_names = file_handle["SubgridScheme"]["NamedColumns"][name][:]
                self.named_columns[name] = {}
                for iname, colname in enumerate(column_names):
                   self.named_columns[name][colname.decode("utf-8")] = iname

    def setup_aliases(self, aliases):
       self.dataset_map = {}
       for ptype in self.datasets_in_file:
         for dset in self.datasets_in_file[ptype] + ["GroupNr_all", "GroupNr_bound"]:
           snap_name = f"{ptype}/{dset}"
           self.dataset_map[snap_name] = (ptype, dset)
       for alias in aliases:
           SOAP_ptype, SOAP_dset = alias.split("/")
           snap_ptype, snap_dset = aliases[alias].split("/")
           self.dataset_map[alias] = (snap_ptype, snap_dset)
           if (snap_dset in self.named_columns) and (SOAP_dset not in self.named_columns):
             self.named_columns[SOAP_dset] = dict(self.named_columns[snap_dset])

    def get_dataset(self, name, data_dict):
        try:
          ptype, dset = self.dataset_map[name]
        except KeyError as e:
          print(f"Dataset \"{name}\" not found!")
          print("Available datasets:")
          for key in self.dataset_map:
            print(f"  {key}")
          raise e
        return data_dict[ptype][dset]

    def get_dataset_column(self, name, column_name, data_dict):
        ptype, dset = self.dataset_map[name]
        column_index = self.named_columns[dset][column_name]
        return data_dict[ptype][dset][:,column_index]

    def get_column_index(self, dset, column_name):
        return self.named_columns[dset][column_name]
