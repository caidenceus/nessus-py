# nessus-py

A script for overcoming the limitations of the Nessus Rest APIs.

## Start a scan called "Example scan name"

Use the following `if __name__ == '__main__'` code.

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

    # Use a Playwright context manager for web interface interaction
    with sync_playwright() as cm:
        nessus = NessusEssentials(url, username, password, api_access_key, api_secret_key, cm)

        nessus.start_scan("Example scan name")
        scan_complete = nessus.block_until_scan_completes("Example scan name")
        
        print('This string prints after the scan finishes')
```

## Usage
1) Install the required packages

```bash
pip install -r requirements.txt
playwright install
```

2) Replace variables with your Nessus information at the bottom of `nessus.py`
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
