from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver import DesiredCapabilities
import platform

def load_capabilities(
        path: str, 
        capability: dict, 
        service
    ):
    
    path = str(path)
    print(path)
    service = service(path)
    capabilities = capability.copy()
    capabilities["plateform"] = platform.system().upper()
    capabilities["version"] = platform.version().split(".")[0]
    
    return service, capabilities
    

def get_windows_driver(*args, **kwargs):
    from selenium.webdriver.edge.service import Service
    proxy_addr = kwargs.get("proxy_addr", None)
    from selenium.webdriver import Edge
    path = kwargs.get("path", "driver/msedgedriver.exe")
    service, capabilities = load_capabilities(path=path, capability=DesiredCapabilities.EDGE, service=Service)
    if proxy_addr is not None:
        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = proxy_addr
        
        proxy.add_to_capabilities(capabilities)
    
    driver = Edge(capabilities=capabilities, service=service)
    
    return driver

def get_linux_driver(*args, **kwargs):
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    
    proxy_addr = kwargs.get("proxy_addr", None)
    from selenium.webdriver import Chrome
    path: str = kwargs.get("path", "/usr/bin/chromedriver")
    service, capabilities = load_capabilities(path=path, capability=DesiredCapabilities.EDGE, service=Service)
    
    WINDOW_SIZE = "1920,1080"

    # Options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=%s" % WINDOW_SIZE)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    if proxy_addr is not None:
        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = proxy_addr
        
        proxy.add_to_capabilities(capabilities)
    
    driver = Chrome(service=service, options=chrome_options)
    
    return driver

FUNCTIONS_DICT = {
    "Windows": get_windows_driver,
    "Linux": get_linux_driver
}

def get_driver(*args, **kwargs):
    return FUNCTIONS_DICT.get(platform.system(), lambda *args, **kwargs: None)(*args, **kwargs)