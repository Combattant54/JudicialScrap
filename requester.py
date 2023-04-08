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
SEARCH_URL = ""

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

def send(req: requests.PreparedRequest, **kwargs) -> requests.Response:
    if isinstance(req, requests.request):
        req = req.prepare()
    
    with requests.Session() as sess:
        try:
            r = sess.send(req, PROXIES, verify=False, **kwargs)
        except ProxyError:
            r = sess.send(req, verify=False, **kwargs)
            
    return r

def get_captcha(driver: WebDriver) -> str:
    COOKIES = get_cookies_dict(driver.get_cookies())
    
    #cré une requete avec les paramètres
    req = requests.Request("GET", URL + "/cej/xyhtml", cookies=COOKIES, headers=HEADERS, params=PARAMS)
    
    # Envoie la requete
    r = send(req)
    
    # traite la réponse
    logger.debug(r.text)
    bal = BeautifulSoup(r.text, "html.parser")
    
    
    return str(bal.find("input").get("value"))

def get_instancias(driver: WebDriver, overwrite=False):
    global DATA
    with open(DATA_PATH, "r") as f:
        DATA = json.loads(f.read(), object_hook=dict)
    if not overwrite and "id_name_districts" in DATA and "id_instancias_dict" in DATA and "tuple_id_specialized_dict" in DATA and "specialized_dict_list" in DATA:
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
    
    # dictionnaire de la forme 'nom du district':'id du district'
    id_name_districts = {}
    
    #dictionnaire de la forme 'nom de l'instance':'id de l'instance'
    id_instancias_dict = {}
    
    #dictionnaire de la forme 'id du district-id de l'instance':'index des spécialités'
    tuple_id_specialized_dict = {}
    
    #liste de dictionnaire de la forme 'nom de la spécialité':'id de la spécialité'
    specialized_dict_list = []
    
    for child in districts_list.findChildren(name="option", onmouseover=""):
        if not isinstance(child, Tag):
            continue
        
        id = child.get("value")
        district_name = child.text
        id_name_districts[district_name] = id
        data = {"codDistrito":id}
        add_header = HEADERS.copy()
        add_header.update({
            "Origin": "https://cej.pj.gob.pe"
        })
        
        req = requests.Request("POST", url=url_distrito, cookies=cookies, headers=add_header, data=data)
        r = send(req)
    
        soup = BeautifulSoup(r.text, "html.parser")
        instancias = {t.text:t.get("value") for t in soup.find_all("option")}
        if instancias != id_instancias_dict:
            print("different instancias : ", instancias, " to ", id_instancias_dict)
            id_instancias_dict = instancias.copy()
        
        
        for k, v in instancias.items():
            data["codOrgano"] = v
            
            
            # envoie la requeteet la parse
            req = requests.Request("POST", url=url_espece, cookies=cookies, headers=add_header, data=data)
            r = send(req)
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            
            # récupère les spécialités
            specialized = {t.text:t.get("value") for t in soup.find_all("option")}
            
            if not specialized in specialized_dict_list:
                specialized_dict_list.append(specialized)
            
            tuple_id_specialized_dict[str(district_name)+"-"+str(k)] = specialized_dict_list.index(specialized)
        
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
            last_instancias = k
        else:
            if last_instancias != v:
                print(f"{last_instancias} is different of {k} from {v} with name {id_instancias_dict[k]}")
    
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
    instances_dict = DATA["id_instancias_dict"]
    district_name = ""
    instance_name = ""
    
    
    #vérifie le district
    if district is None:
        return False
    elif isinstance(district, int):
        val = False
        for k, v in districts_dict.items():
            if v == district:
                district_name = k
                district = v
                val = True
                break
        if not val:
            logger.warning("Invalid district id of " + str(district))
            return False
    else:
        district_name = district
        district = districts_dict.get(district, None)
        if district is None:
            logger.warning(district + " not found in data")
            return False
    
    
    #Vérifie l'instance
    if instances_dict is None:
        logger.warning("Invalid id for instancias_dict : " + str(district))
        return False
    if instance is None:
        return False
    elif isinstance(instance, int):
        val = False
        for k, v in instances_dict.items():
            if instance == k:
                instance_name = k
                instance = v
                val = True
                break
        if not val:
            logger.warning("Invalid instance of id " + str(instance))
            return False
    else:
        instance_name = instance
        instance = instances_dict.get(instance, None)
        if instance is None:
            logger.warning(instance + " not found in instance dict of district " + districts_dict.get(district))
            return False
    
    
    # Définit la spécialité
    specializeds_dicts = DATA["tuple_id_specialized_dict"]
    specializeds_lists = DATA["specialized_dict_list"]
    
    specialized_key = str(district_name) + "-" + str(instance_name)
    specialized_index = specializeds_dicts.get(specialized_key, {})
    
    if specialized_index is not None and specialized_index < len(specializeds_lists):
        specialized_dict = specializeds_lists[specialized_index]
    else:
        logger.error(f"specialized_index of {specialized_key} is not found")
        return False
    
    if specialized_dict is None:
        logger.error(f"Index of {specialized_index} is not found or is unset")
        return False
    
    if specialized is None:
        return False
    elif isinstance(specialized, int):
        val = False
        for k, v in specialized_dict.items():
            if specialized == k:
                specialized = int(v)
                val = True
                break
        if not val:
            logger.warning("Invalid specialized id at " + str(specialized))
            return False
    else:
        specialized = int(specialized_dict.get(specialized, None))
        if specialized is None:
            logger.warning("Specialized not found for " + specialized)
    
    
    # Vérifie la validité de l'année 
    if year and year >= 1977 and year <= CURRENT_YEAR:
        logger.info("Year " + str(year) + " is valid")
    else:
        logger.warning("Year " + str(year) + " is not valid")
        return False

    # Vérifie la validité du n_expediente
    if n_expediente and n_expediente > 0:
        logger.info("N_expediente " + str(n_expediente) + " is valid")
    else:
        logger.warning("N_expediente " + str(n_expediente) + " is not valid")
        return False
    
    # Vérifie la validité du captcha
    if len(captcha) < 4:
        logger.warning("Invalid captcha : " + captcha)
        return False
    if len(captcha) > 4:
        logger.info("Captcha invalid : " + captcha + ", transformed to " + captcha[:4])
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
    req = requests.Request("POST", url=validate_url, cookies=cookies, headers=add_header, data=request_params)
    r = send(req)
    
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
    ) -> bool:
    
    
    # vérifie le captcha et les paramètres
    if captcha is None:
        captcha = get_captcha(driver)
    
    if not is_validate and not validate(driver, district, instance, specialized, year, n_expediente, captcha):
        return False
    
    
    # Prépare la requete et les paramètres de celle-ci
    cookies = get_cookies_dict(driver.get_cookies())    
    request_params = {
        "distritoJudicial": district,
        "organoJurisdiccional": instance,
        "especialidad": specialized,
        "anio": year,
        "numeroExpediente": n_expediente,
        "codigoCaptcha": captcha,
        "divKcha": 0
    }
    
    req = requests.Request("GET", url=URL+SEARCH_URL, headers=HEADERS, cookies=cookies, data=request_params)
    r = send(req)
    
    return True