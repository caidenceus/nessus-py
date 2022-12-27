# Nessus Essentials 10.4

Bypass feature limitations of the Rest API, such as starting a scan, by crawling the web interface.

### Currently supported methods
```python
# Scan interaction
start_scan(self, scan_name, targets=[])
export_scan(self, scan_name, format='nessus', file_name='export')

# Information
get_scan_folders(self)
get_on_demand_scans(self)
get_scan_status(self, scan_name: str) -> str
get_scan_information(self, scan_name)

# Script execution
block_until_scan_completes(self, scan_name, timeout=360, interval=5)
```

### Usage
1) Install the required packages

```bash
pip install -r requirements.txt
playwright install
```

2) Replace variables with your Nessus information at the bottom of `nessus_essentials.py`
```python
if __name__ == '__main__':
    urllib3.disable_warnings()

    # Initialize global variables
    url = "<URL to Nessus web interface>"
    username = "<Nessus web interface username>"
    password = "<Nessus web interface password>"
    
    # See https://docs.tenable.com/nessus/Content/GenerateAnAPIKey.htm 
    api_access_key = "<Nessus API access key>"
    api_secret_key = "<Nessus API secret key>"
```

3) Run `python3 nessus.py`


### Method details
```python
def start_scan(self, scan_name, targets=[]):
    """Start a Nessus scan.

    Note: This endpoint is only available on Nessus Manager, we use
          a dirty hack to bypass this feature limitation if applicable.

    :param scan_name: The name of the scan to start.
    :param targets: The target IP address(es) to pass to the scan.
    """


def export_scan(self, scan_name, format='nessus', file_name='export'):
    """Export a Nessus scan.

    Note: This request requires can view scan permissions.

    :param scan_name: The name of the scan to export.
    :param format: Export format. One of [nessus:html:pdf:csv:db].
    :param file_name: What to name the export file.
    """


def get_scan_folders(self):
    """Get a list of scan folder names and their IDs.

    Example:
        >>> NessusEssentials.get_scan_folders()
        >>> [{'name': 'My Scans', 'id': 1}, {'name': 'All Scans', 'id': 2}]

    :return: List of dictionaries of scan names and their corresponding
             folder IDs.
    """


def get_on_demand_scans(self):
    """Get a list of dictionaries that contains scan information.

    This Rest API resource is not feature locked, so no corresponding
    get_on_demand_scans method is provided.

    The scan information will include all data neccessary to run a scan as
    well as the scan name.

    Example:
        >>> NessusEssentials.get_on_demand_scans()
        >>> [{'name': 'scan_1', 'id': 1, 'folder_id': 1,
              'status': 'running', 'folder_name': 'All Scans'},
             {'name': 'scan_2', 'id': 2, 'folder_id': 2, 'status':
              'running', 'folder_name': 'My Scans'}]

    :return: A list of dictionaries of each scan, its name, folder id, and
             its id.
    """


def get_scan_status(self, scan_name: str) -> str:
    """Get the status of a scan.

    :param scan_name: The name of the scan to get the status of.
    :return: The current status of the scan.
    """


def get_scan_information(self, scan_name):
    """Get a specific scan's information from self.get_on_demand_scans

    :param scan_name: The name of the scan's information to retrieve.
    :return: Dictionary of the scan's information, or None if scan does not
             exist.
    """


def block_until_scan_completes(self, scan_name, timeout=360, interval=5):
    """Block script execution until scan completes.

    :param scan_name: The scan to block execution on.
    :param timeout: Maximum time to block execution for in minutes.
    :param interval: How often to check the scan status in minutes.
    :return: True if scan completes within timeout, False otherwise.
    """
```