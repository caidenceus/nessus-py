# Python imports
import requests
import time
import urllib3

# Third-party imports
from playwright._impl._api_types import TimeoutError as PwTimeoutError
from playwright.sync_api import sync_playwright


class ElementNotVisibleError(Exception):
    """HTML element is not found."""
    pass


def assert_valid_http_response(
        response, url, expected_status=200, expecting_json=True):
    """Helper method to assert an HTTP response object is valid.

    :param response: requests.Reponse object returned by calling a reqest
                     method.
    :param url: The URL used to make the request. This is used for logging.
    :param expected_status: The expected status code of the response.
    :param expecting_json: Whether we are expecting json in the response.
    """
    code = response.status_code
    print(f'Asserting valid HTTP response from {url}')
    if code != expected_status:
        print(f'Aborting: expected status code {expected_status} not {code}')
        exit()

    if expecting_json:
        try:
            response.json()
        except:
            print('Aborting: Unable to find/decode response JSON')
            exit()


def block_until_element_is_visible(playwright_page, locator_str, timeout=5):
    """Block program executeion until a web element is visible.

    :param playwright_page: A playwright page instance created from a browser
                            context.
    :param locator_string: String used to locate the element to wait for.
    :param timeout: How long to wait for element to become visible in seconds.
    """
    retries = timeout

    # Locator object can hang; reload it each time before calling wait_for
    while retries > 0:
        try:
            element = playwright_page.locator(locator_str)
            # One second timeout
            element.wait_for(timeout=1000, state='visible')
            return
        except PwTimeoutError:
            retries -= 1
    raise ElementNotVisibleError(f'Unable to locate "{locator_str}"')


class NessusEssentialssWebInterface(object):
    def __init__(
            self, url, username, password, context_manager, headless=False):
        """Helper class to separate web dirty hacks from Rest API calls.

        :param url: The base URL of the Nessus host.
        :param username: The web interface username of the Nessus host.
        :param password: The web interface password of the Nessus host.
        :param context_manager: Playwright sync API contect manager.
        :param headless: If True, the web browser will not display.
        """
        self._url = url

        # Credentials for web interface
        self.username = username
        self.password = password

        # Session instance variables for dirty hacks
        self.browser = context_manager.chromium.launch(headless=headless)
        context = self.browser.new_context(**{'ignore_https_errors': True})
        self.page = context.new_page()

    def _assert_scan_exists(self, scan_name):
        """Helper method to assert that a scan exists before operating on it.

        This function will print an error message and exit the program if the
        scan in question is not found.

        :param scan_name: The name of the scan to assert exists.
        """
        for scan in self.get_on_demand_scans():
            if scan['name'] == scan_name:
                return
        print(f'Aborting: Unable to locate the scan {scan_name}')
        exit()

    def _login_web_interface(self, resource='/#/scans/folders/all-scans'):
        """Login to Nessus using the web credentials passed to __init__.

        Note: This is used as a last resort for dirty hacks to work around
              Nessus Rest API bugs and feature locks.

        :param resource: The resource to navigate to after logging in.
        """
        print('Attempting to login to the Nessus web interface')

        # Assert location is valid before trying to open it
        location = self._url + resource
        response = requests.get(location, verify=False)
        assert_valid_http_response(response, location, expecting_json=False)
        self.page.goto(location)

        try:
            block_until_element_is_visible(self.page, '.login-username')
            self.page.fill('.login-username', self.username)
            self.page.fill('.login-password', self.password)
            block_until_element_is_visible(self.page, 'text=Sign In')
            self.page.click('text=Sign In')
        except ElementNotVisibleError:
            # TODO: (check this) Probably already logged in
            print('Unable to login to the Nessus web interface')
            return
        print('Successfully logged in to the Nessus web interface')

    def _start_scan_web_interface(self, scan_name, folder_name, targets=[]):
        """Start a scan from the Nessus web interface.

        Note: This is used as a last resort for dirty hacks to work around
              Nessus Rest API bugs and feature limitations.

        :param scan_name: Name of the Nessus scan to start.
        :param folder_name: The name of the folder the scan lives in.
        :param targets: Optionally, scan listed targets rather than default.
        """
        self._assert_scan_exists(scan_name)

        # Folder names must be lowercase with hyphens in places of spaces
        folder_name = folder_name.lower().replace(' ', '-')
        scan_folder_location = '/#/scans/folders/' + folder_name
        self._login_web_interface(resource=scan_folder_location)

        try:
            block_until_element_is_visible(self.page, f'text={scan_name}')
            self.page.click(f'text={scan_name}')
        except ElementNotVisibleError:
            print(f'FATAL: failed to start the scan "{scan_name}".')
            return

        # Manually start the scan from the Nessus web interface
        block_until_element_is_visible(self.page, '#launch-dropdown')
        self.page.click('text=Launch')

        if len(targets) == 0:
            self.page.click('text=Default')
        else:
            self.page.click('text=Custom')

            target_str = ''
            for target in targets:
                target_str += target + ', '
            target_str = target_str[:-2]  # Truncate the last adjunct ', '

            self.page.fill('#custom-launch-targets', target_str)
            self.page.click('#custom-targets-launch')

        time.sleep(10)  # Wait for scan to start
        print('Scan started successfully')


class NessusEssentials(NessusEssentialssWebInterface):
    def __init__(
            self, url, username, password, api_access_key, api_secret_key,
            context_manager, headless=False):
        """Nessus object for managing and polling scans.

        Generating Rest API keys:
        https://docs.tenable.com/nessus/Content/GenerateAnAPIKey.htm

        Note: When possible, the Rest API is used; however, due to bugs in the
              API and feature locks, if a Rest API resource does not work,
              member functions of this class will retry the operation through
              the web interface.

              We refer to bypassing feature locks as "dirty hacks." Dirty hack
              methods will start with two underscores, as they should be private
              member functions.

              Similarly, protected member functions start with one underscore.

        :param url: The base URL of the Nessus host.
        :param username: The web interface username of the Nessus host.
        :param password: The web interface password of the Nessus host.
        :param api_access_key: The Nessus Rest API access key.
        :param api_secret_key: The Nessus Rest API secret key.
        :param context_manager: Playwright sync API contect manager.
        :param headless: If True, the web browser will not display.
        """
        super().__init__(url, username, password, headless, context_manager)

        # Rest API authentication
        api_auth = f'accessKey={api_access_key}; secretKey={api_secret_key}'
        self._default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'pyscan/1.0',
            'X-ApiKeys': api_auth
        }

    def get_scan_folders(self):
        """Get a list of scan folder names and their IDs.

        Example:
            >>> NessusEssentials.get_scan_folders()
            >>> [{'name': 'My Scans', 'id': 1}, {'name': 'All Scans', 'id': 2}]

        :return: List of dictionaries of scan names and their corresponding
                 folder IDs.
        """
        url = self._url + '/scans'
        resp = requests.get(url, headers=self._default_headers, verify=False)
        assert_valid_http_response(resp, url)

        folders = resp.json()
        return [{
            'name': folder['name'],
            'id': folder['id']
        } for folder in folders['folders']]

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
        url = self._url + '/scans'
        resp = requests.get(url, headers=self._default_headers, verify=False)
        assert_valid_http_response(resp, url)

        scans = resp.json()
        scan_dict = [{
            'name': scan['name'],
            'id': scan['id'],
            'folder_id': scan['folder_id'],
            'status': scan['status']
        } for scan in scans['scans']]

        # Now we get the scan folder name for dirty hacks
        for scan in scan_dict:
            folder_id = scan['folder_id']

            for folder in self.get_scan_folders():
                if folder['id'] == folder_id:
                    scan.update({'folder_name': folder['name']})
                    break
        return scan_dict

    def get_scan_status(self, scan_name: str) -> str:
        """Get the status of a scan.

        :param scan_name: The name of the scan to get the status of.
        :return: The current status of the scan.
        """
        self._assert_scan_exists(scan_name)
        for scan in self.get_on_demand_scans():
            if scan['name'] == scan_name:
                return scan['status']

    def get_scan_information(self, scan_name):
        """Get a specific scan's information from self.get_on_demand_scans

        :param scan_name: The name of the scan's information to retrieve.
        :return: Dictionary of the scan's information, or None if scan does not
                 exist.
        """
        self._assert_scan_exists(scan_name)
        for scan in self.get_on_demand_scans():
            if scan['name'] == scan_name:
                return scan

    def block_until_scan_completes(self, scan_name, timeout=360, interval=5):
        """Block script execution until scan completes.

        :param scan_name: The scan to block execution on.
        :param timeout: Maximum time to block execution for in minutes.
        :param interval: How often to check the scan status in minutes.
        :return: True if scan completes within timeout, False otherwise.
        """
        self._assert_scan_exists(scan_name)
        scan_status = self.get_scan_status(scan_name)

        # First, we wait until the scan starts running. Timeout is 15 minutes
        start_running_timeout = 900
        while scan_status != 'running':
            if start_running_timeout == 0:
                print('ERROR: Scan unable to start')
                exit()
            print(f'Waiting for "{scan_name}" to start, sleeping 15 seconds')
            time.sleep(15)
            start_running_timeout -= 15
            scan_status = self.get_scan_status(scan_name)

        # Block until the scan finishes or aborts
        time_left = timeout
        while scan_status == 'running':
            if timeout == 0:
                print('ERROR: Scann timed out')
                return False

            print(f'"{scan_name}" is running, sleeping {interval} minutes')
            time.sleep(interval*60)
            time_left -= interval
            scan_status = self.get_scan_status(scan_name)

        print('Scan completed successfully')
        return True

    def start_scan(self, scan_name, targets=[]):
        """Start a Nessus scan.

        Note: This endpoint is only available on Nessus Manager, we use
              a dirty hack to bypass this feature limitation if applicable.

        :param scan_name: The name of the scan to start.
        :param targets: The target IP address(es) to pass to the scan.
        """
        self._assert_scan_exists(scan_name)
        invalid_scan_states = [
            'running', 'stopping', 'imported', 'pausing', 'paused', 'pending',
            'resuming']
        curr_state = self.get_scan_status(scan_name)
        if curr_state in invalid_scan_states:
            print(f'Cannot start scan: {scan_name} currently in {curr_state}')
            exit()

        scan_id = self.get_scan_information(scan_name)['id']
        url = self._url + f'/scans/{scan_id}/launch'
        if len(targets) == 0:
            resp = requests.post(
                url, headers=self._default_headers, verify=False)
        else:
            resp = requests.post(
                url, headers=self._default_headers, json={'targets': targets},
                verify=False)

        # Do not call assert_valid_http_response because API may return 200
        # or 412. In the case of a 412 code, we try our dirty hacks
        if resp.status_code == 200:
            print('Scan started successfully')
        elif resp.status_code == 412:
            # If error response, we are probably not running Nessus Manager
            print('/scans/{id}/launch is only available on Nessus manager.')
            print('Attempting dirty hack to work around this feature lock')

            scan_dict = self.get_scan_information(scan_name)
            self._start_scan_web_interface(
                scan_name, scan_dict['folder_name'], targets)
        else:
            print(f'Unexpected error when trying to start"{scan_name}"')
            print(f'return code from {url} was {resp.status_code}')
            exit()



# Your code goes below this line
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
        
        # Start the Nessus scan called "Example scan name"
        nessus.start_scan("Example scan name")
        
        # Block scrip execution until "Example scan name" finishes
        nessus.block_until_scan_completes("Example scan name")
        
        print('This string prints after the scan finishes')

