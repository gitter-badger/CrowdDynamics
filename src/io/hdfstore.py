import datetime
import logging
import os

import h5py
import numpy as np


class ListBuffer(list):
    def __init__(self, start=0, end=0):
        """Buffer that tracks start and end indices of added items."""
        super(ListBuffer, self).__init__()
        self.start = start
        self.end = end

    def append(self, p_object):
        super(ListBuffer, self).append(p_object)
        self.end += 1

    def clear(self):
        super(ListBuffer, self).clear()
        self.start = self.end


class HDFStore(object):
    """Class for saving object's array or scalar data in hdf5 file."""
    # TODO: Threading, Locks
    ext = ".hdf5"

    def __init__(self, filepath):
        # Path to the HDF5 file
        self.filepath, _ = os.path.splitext(filepath)  # Remove extension
        self.filepath += self.ext  # Set extension
        self.group_name = None

        # Appending data
        self.buffers = []  # (struct, buffers)

        # Configuration
        self.configure_file()

    @staticmethod
    def create_dataset(group: h5py.Group, name, values, resizable=False):
        """

        :param group: h5py.Group
        :param name: Name
        :param values: Values to be stored. Goes through np.array(value).
        :param resizable: If true values can be added to the dataset.
        :return:
        """
        values = np.array(values)
        kw = {}
        if resizable:
            values = np.array(values)
            maxshape = (None,) + values.shape
            kw.update(maxshape=maxshape)
            values = np.expand_dims(values, axis=0)
        group.create_dataset(name, data=values, **kw)

    @staticmethod
    def append_buffer_to_dataset(dset: h5py.Dataset, buffer: ListBuffer):
        """Append values to resizable h5py dataset."""
        if len(buffer):  # Buffer is not empty
            values = np.array(buffer)
            new_shape = ((buffer.end + 1),) + values.shape[1:]
            dset.resize(new_shape)
            dset[buffer.start:] = values

    def configure_file(self):
        """Configure and creates new HDF5 File."""
        logging.info("")

        timestamp = str(datetime.datetime.now())
        with h5py.File(self.filepath, mode='a') as file:
            self.group_name = timestamp.replace(" ", "_")  # HDF group name
            group = file.create_group(self.group_name)  # Create Group
            group.attrs["timestamp"] = timestamp  # Metadata

        logging.info(self.filepath)
        logging.info(self.group_name)

    def add_dataset(self, struct, attributes, overwrite=False):
        logging.info("")

        with h5py.File(self.filepath, mode='a') as file:
            name = struct.__class__.__name__.lower()
            base = file[self.group_name]  # New group for structure
            if overwrite and (name in base):
                del base[name]  # Delete existing dataset
            group = base.create_group(name)

            # Create new datasets
            for attr in attributes:
                value = np.copy(getattr(struct, attr.name))
                self.create_dataset(group, attr.name, value, attr.is_resizable)

        logging.info("")

    def add_buffers(self, struct, attributes):
        """
        struct
        buffers:
          attr.name: buffer1
          attr.name: buffer2
          ...
        """
        logging.info("")

        buffers = {attr.name: ListBuffer(start=1, end=1) for attr in attributes}
        self.buffers.append((struct, buffers))

        logging.info("")

    def update_buffers(self):
        for struct, buffers in self.buffers:
            logging.debug("Struct: {}".format(struct))
            for attr, buffer in buffers:
                logging.debug("Attr: {}, Buffer: {}".format(attr, buffer))
                value = getattr(struct, attr)
                value = np.copy(value)
                buffer.append(value)

    def dump_buffers(self):
        logging.debug("")
        # TODO: Swap old buffers to new cleared one
        with h5py.File(self.filepath, mode='a') as file:
            grp = file[self.group_name]
            for struct, buffers in self.buffers:
                name = struct.__class__.__name__.lower()
                for attr, buffer in buffers:
                    dset = grp[name][attr.name]
                    self.append_buffer_to_dataset(dset, buffer)
                    buffer.clear()
