from bs4 import BeautifulSoup
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver import Edge, DesiredCapabilities
from selenium.webdriver.edge.service import Service
import requester
import logging

PROXIES = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080"
}

#définie l'url du site, du formulaire et le cookie (généré avec un navigateur classique parce que sinon ca marche pas)
URL = "https://cej.pj.gob.pe"
FORM_URL = "/cej/forms/busquedaform.html"
CAPTCHA_URL = "/cej/Captcha.jpg"

COOKIES = {
    "JSESSIONID": "ATDDKKHS4Qytm15i5l-Dct9S.jvmr-scomunes22", 
    "_gid": "GA1.3.967327814.1679388211",
    "_ga": "GA1.3.1330425668.1679388211"
}
PROXIES.clear()
COOKIES.clear()

# définit le logger de ce fichier
logger = logging.getLogger(__name__)
driver = None

def init(proxy_addr="127.0.0.1:8080"):
    global driver
    
    PROXIES["http"] = "http://" + proxy_addr
    PROXIES["https"] = "http://" + proxy_addr
    
    service = Service("driver/edgedriver.exe")
    proxy = Proxy()
    proxy.proxy_type = ProxyType.MANUAL
    proxy.http_proxy = proxy_addr
    
    capabilities = DesiredCapabilities.EDGE
    proxy.add_to_capabilities(capabilities)
    driver = Edge(capabilities=capabilities, service=service)


    requester.init(URL, CAPTCHA_URL, PROXIES)

def scrap(saver):
    if driver is None:
        logger.critical("This script havn't been initialized : exiting script")
        exit(1)
    
    #requete d'initialisation
    driver.get(URL + FORM_URL)
    
    # Récupère le captcha
    captcha = requester.get_captcha(driver)
    print("captcha :", captcha)
    
    requester.get_instancias(driver)
    
    #transformation en soupe de bs4 (pour la manipulation)
    soup = BeautifulSoup(driver.page_source, features="html.parser")
