"""Module containing utilities for PCI subsystem."""


class PCIUtilException(Exception):
    """Exception thrown by :class:`PCIUtil` class methods."""


class PCIUtil:
    """Wrapper for retrieving information about PCI devices."""

    @staticmethod
    def get_vendor_id(bus_id: str) -> str:
        """Retrieve vendor ID by BCI bus ID.

        :param bus_id: PCI bus ID
        :return: PCI vendor ID (e.g. `10de`)
        :raises: :class:`PCIUtilException` on failure
        """
        vendor = None
        try:
            with open(f'/sys/bus/pci/devices/{bus_id}/vendor', encoding='utf-8') as file:
                vendor = file.read().removeprefix('0x').rstrip()
        except FileNotFoundError as err:
            raise PCIUtilException(err) from err

        return vendor

    @staticmethod
    def get_device_id(bus_id) -> str:
        """Retrieve device ID by BCI bus ID.

        :param bus_id: PCI bus ID
        :return: PCI device ID (e.g. `1c20`)
        :raises: :class:`PCIUtilException` on failure
        """
        device = None
        try:
            with open(f'/sys/bus/pci/devices/{bus_id}/device', encoding='utf-8') as file:
                device = file.read().removeprefix('0x').rstrip()
        except FileNotFoundError as err:
            raise PCIUtilException(err) from err

        return device

    @staticmethod
    def get_device_info(vendor, device) -> (str, str):
        """Retrieve vendor and device names by PCI vendor and device IDs.

        :param vendor: Vendor ID (e.g. `10de`)
        :param device: Device ID (e.g. `1c20`)
        :return: Tuple of PCI vendor and device names,
                 e.g. `('NVIDIA Corporation', 'GP106M [GeForce GTX 1060 Mobile]')`
        :raises: :class:`PCIUtilException` on failure
        """
        ids_lib = {}
        try:
            with open('/usr/share/hwdata/pci.ids', encoding='utf-8') as file:
                for line in file:
                    # If line is tabbed or contains an hashtag skips
                    if line[:3] == '\t\t' or line[0] == '#':
                        continue

                    # If line isn't tabbed and isn't a newline create a :
                    if not line[:1] in ['\t', '\n']:
                        temp_vendor = line.split()[0]
                        ids_lib[temp_vendor] = {'name': line[6:-1]}

                    if line.startswith('\t\t') or line.startswith('\n'):
                        continue
                    if line.startswith('\t'):
                        ids_lib[temp_vendor][line.split()[0]] = {'name': ' '.join(line.split()[1:])}
        except FileNotFoundError as err:
            raise PCIUtilException(err) from err

        if vendor not in ids_lib or device not in ids_lib[vendor]:
            raise PCIUtilException(f'Name not found for PCI device {vendor}:{device}')

        return ids_lib[vendor]['name'], ids_lib[vendor][device]['name']
