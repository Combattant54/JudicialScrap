import requests
from requests.exceptions import ProxyError
from selenium.webdriver.remote.webdriver import WebDriver
from bs4 import BeautifulSoup
from bs4.element import Tag
import logging
import json
from utils import get_cookies_dict

logger = logging.getLogger(__name__)

URL = None
CAPTCHA_URL = None
PROXIES = {}
DATA_PATH = "data.json"
DATA = {}
CURRENT_YEAR = 2023

CERT_PATH = "certificates/burp-suite-certificate.pem"

HEADERS = {
    "Host":"cej.pj.gob.pe",
    "Accept-Encoding": "gzip, deflate", 
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://cej.pj.gob.pe/cej/forms/busquedaform.html"
}
PARAMS = {
    "Method": "GET",
    "Path": "/cej/xyhtml"
}

def init(base_url, captcha_url, proxies={}):
    global URL
    global CAPTCHA_URL
    global PROXIES
    
    URL = str(base_url)
    CAPTCHA_URL = str(captcha_url)
    PROXIES  = dict(proxies)
    print(PROXIES)

def get_captcha(driver: WebDriver) -> str:
    COOKIES = get_cookies_dict(driver.get_cookies)
    
    
    #cré une session de requests
    with requests.Session() as s:    
    
        #cré une requete avec les paramètres
        req = requests.Request("GET", URL + "/cej/xyhtml", cookies=COOKIES, headers=HEADERS, params=PARAMS)
        #regarde le contenue de la requete
        print("Request inspection")
        print(req.params, req.headers, req.cookies, req.url)
        print(req.data, req.auth, req.method, req.files, req.hooks)
        print(dir(req))
        #prépare la requete a l'envoit
        
        req = req.prepare()
        #affiche les headers de la requete
        print(req.headers)
        
        #envoie la requete et affiche la réponse
        try:
            r = s.send(req, proxies=PROXIES, verify=False)
        except ProxyError:
            logger.error("Invalid proxy, using no proxy instead")
            r = s.send(req, verify=False)
        
        print(r)
        print(r.text)
        bal = BeautifulSoup(r.text, "html.parser")
        return bal.find("input").get("value")

def get_instancias(driver: WebDriver):
    global DATA
    with open(DATA_PATH, "r") as f:
        DATA = json.loads(f.read(), object_hook=dict)
    if "id_name_districts" in DATA and "id_instancias_dict" in DATA and "tuple_id_specialized_dict" in DATA and "specialized_dict_list" in DATA:
        id_name_districts = DATA["id_name_districts"]
        id_instancias_dict = DATA["id_instancias_dict"]
        tuple_id_specialized_dict = DATA["tuple_id_specialized_dict"]
        specialized_dict_list = DATA["specialized_dict_list"]
        return id_name_districts, id_instancias_dict, tuple_id_specialized_dict, specialized_dict_list
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    districts_list = soup.find(id="distritoJudicial")
    
    temp_cookies = driver.get_cookies()
    cookies = {}
    if isinstance(temp_cookies, list):
        cookies = {d["name"]:d["value"] for d in temp_cookies}
    else:
        cookies = temp_cookies
    
    url_distrito = URL + "/cej/forms/filtrarOrganosPorDistrito.html"
    url_espece = URL + "/cej/forms/filtrarEspecPorOrgano.html"
    print(url_distrito)
    
    id_name_districts = {}
    id_instancias_dict = {}
    tuple_id_specialized_dict = {}
    specialized_dict_list = []
    
    for child in districts_list.findChildren(name="option", onmouseover=""):
        if not isinstance(child, Tag):
            continue
        
        id = child.get("value")
        id_name_districts[id] = child.text
        data = {"codDistrito":id}
        add_header = HEADERS.copy()
        add_header.update({
            "Origin": "https://cej.pj.gob.pe"
        })
        
        req = requests.Request("POST", url=url_distrito, cookies=cookies, headers=add_header, data=data)
        req = req.prepare()
        with requests.Session() as s:
            try:
                r = s.send(req, proxies=PROXIES, verify=False)
            except ProxyError:
                logger.error("Invalid proxy, using no proxy instead")
                r = s.send(req, verify=False)
    
        soup = BeautifulSoup(r.text, "html.parser")
        instancias = {t.get("value"):t.text for t in soup.find_all("option")}
        id_instancias_dict[id] = instancias
        
        
        for k, v in instancias.items():
            data["codOrgano"] = k
            req = requests.Request("POST", url=url_espece, cookies=cookies, headers=add_header, data=data)
            req = req.prepare()
            
            with requests.Session() as s:
                try:
                    r = s.send(req, proxies=PROXIES, verify=False)
                except ProxyError:
                    logger.error("Invalid proxy, using no proxy instead")
                    r = s.send(req, verify=False) 
            
            soup = BeautifulSoup(r.text, "html.parser")
            specialized = {t.get("value"):t.text for t in soup.find_all("option")}
            
            if not specialized in specialized_dict_list:
                specialized_dict_list.append(specialized)
            
            tuple_id_specialized_dict[str(id)+"-"+str(k)] = specialized_dict_list.index(specialized)
        
        print(specialized_dict_list)
    with open(DATA_PATH, "w") as f:
        data = {
            "id_name_districts": id_name_districts,
            "id_instancias_dict": id_instancias_dict,
            "tuple_id_specialized_dict": tuple_id_specialized_dict,
            "specialized_dict_list": specialized_dict_list,
        }
        json.dump(data, f, indent=2)
            
    last_instancias = None
    for k, v in id_instancias_dict.items():
        if not last_instancias:
            last_instancias = v
        else:
            if last_instancias != v:
                print(f"{last_instancias} is different of {v} from {k} with name {id_name_districts[k]}")
    
    return id_name_districts, id_instancias_dict, tuple_id_specialized_dict, specialized_dict_list




def validate(
    driver: WebDriver, 
    district: str|int, 
    instance: str|int, 
    specialized: str|int, 
    year: int, 
    n_expediente: int, 
    captcha: str
    ):
    
    
    districts_dict = DATA["id_name_districts"]
    instances_dicts = DATA["id_instancias_dict"]
    
    if district is None:
        return False
    elif isinstance(district, str):
        val = False
        for k, v in districts_dict.items():
            if v == district:
                district = k
                val = True
                break
        if not val:
            logger.warning(district + " not found in data")
            return False
    else:
        if districts_dict.get(district, None) is None:
            logger.warning("Invalid district id of " + str(district))
            return False
    
    instance_dict = instances_dicts.get(district, None)
    if instance_dict is None:
        logger.warning("Invalid id for instancias_dict : " + str(district))
        return False
    if instance is None:
        return False
    elif isinstance(instance, str):
        
        val = False
        for k, v in instance_dict.items():
            if instance == v:
                instance = k
                val = True
                break
        if not val:
            logger.warning(instance + " not found in instance dict of district " + districts_dict.get(district))
            return False
    else:
        if instance_dict.get(instance, None) is None:
            logger.warning("Invalid instance of id " + str(instance))
            return False
    
    
    # Définit la spécialité
    specializeds_dicts = DATA["tuple_id_specialized_dict"]
    specializeds_lists = DATA["specialized_dict_list"]
    
    specialized_index = specializeds_dicts.get(str(district) + "-" + str(instance))
    if specialized_index is not None and specialized_index < len(specializeds_lists):
        specialized_dict = specializeds_lists[specialized_index]
    else:
        logger.error(f"specialized_index of {str(district) + '-' + str(instance)} is not found")
        return False
    
    if specialized_dict is None:
        logger.error(f"Index of {specialized_index} is not found or is unset")
        return False
    
    if specialized is None:
        return False
    elif isinstance(specialized, str):
        val = False
        for k, v in specialized_dict.items():
            if v == specialized:
                specialized = int(k)
                val = True
                break
        if not val:
            logger.warning("Specialized not found for " + specialized)
            return False
    else:
        if specialized_dict.get(str(specialized), None) is None:
            logger.warning("Invalid specialized id at " + str(specialized))
    
    
    # Vérifie la validité de l'année 
    if year and year >= 1977 and year <= CURRENT_YEAR:
        logger.debug("Year " + str(year) + " is valid")
    else:
        logger.warning("Year " + str(year) + " is not valid")
        return False

    # Vérifie la validité du n_expediente
    if n_expediente and n_expediente > 0:
        logger.debug("N_expediente " + str(n_expediente) + " is valid")
    else:
        logger.warning("N_expediente " + str(n_expediente) + " is not valid")
        return False
    
    # Vérifie la validité du captcha
    if len(captcha) < 4:
        logger.info("Invalid captcha : " + captcha)
        return False
    if len(captcha) > 4:
        logger.debug("Captcha invalid : " + captcha + ", transformed to " + captcha[:4])
        captcha = captcha[4:]
    
    validate_url = URL + "/cej/forms/ValidarFiltros.htm"
    cookies = driver.get_cookies()
    request_params = {
        "distritoJudicial": district,
        "organoJurisdiccional": instance,
        "especialidad": specialized,
        "anio": year,
        "numeroExpediente": n_expediente,
        "codigoCaptcha": captcha,
        "divKcha": 0
    }
    add_header = HEADERS.copy()
    req = requests.Request("POST", url=validate_url, headers=add_header, data=request_params)
    req = req.prepare()
    with requests.Session() as s:
        try:
            r = s.send(req, proxies=PROXIES)
        except ProxyError:
            r = s.send(req)
    
    if r.text.strip().startswith("1"):
        return True
    
    
def search(
    driver:WebDriver, 
    district: str|int, 
    instance: str|int, 
    specialized: str|int, 
    year: int, 
    n_expediente: int, 
    captcha: str =None,
    is_validate: bool =False
    ):
    
    if captcha is None:
        captcha = get_captcha(driver)