import requests
from requests.exceptions import ProxyError

from selenium.webdriver.edge.webdriver import WebDriver

from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement, NavigableString, ResultSet
from functools import partial

import logging
import asyncio
from asyncio import Queue
from aiofiles import open as aopen
from contextlib import asynccontextmanager

import json
import typing
import time
import os

from utils import get_cookies_dict

import build_logger
logger = build_logger.get_logger(__name__)
logger.setLevel(logging.INFO)

URL = None
CAPTCHA_URL = None
PROXIES = {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}
TOTAL_PROXIES_ERROR = 0
TOTAL_PROXIES_GOOD = -100
DATA_PATH = "result/data.json"
DATA = {}
CURRENT_YEAR = 2023

CERT_PATH = "certificates/burp-suite-certificate.pem"
SEARCH_URL = "/cej/forms/busquedaform.html"
GET_FORM_URL = "/cej/forms/detalleform.html"
DOWNLOAD_URL = "/cej/forms/documentoD.html"

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

id = 0
is_using_driver = False
current_access_id = id
ids_queue = Queue(256)
cookies_queue = Queue(4)

_initialized = False

def init(base_url, captcha_url, proxies={}):
    global URL
    global CAPTCHA_URL
    global PROXIES
    global DATA
    global _initialized
    
    URL = str(base_url)
    CAPTCHA_URL = str(captcha_url)
    for k, v in proxies.items():
        if not k in PROXIES:
            print(f"key {k} is not in both proxies")
        elif v != PROXIES[k]:
            print(f"key {k} has different value in the proxies dicts")
            
    PROXIES  = dict(proxies)
    print("\n")
    print(PROXIES)
    print("")
    
    with open(DATA_PATH, "r") as f:
        DATA = json.load(f)

    _initialized = True

def  stop():
    global _initialized
    _initialized = False

@asynccontextmanager
async def get_lock():
    try:
        id = await get_id()
        await lock(id)
        yield id
    finally:
        pass

@asynccontextmanager
async def cookies_context():
    try:
        page, cookies = await get_cookies()
        yield (page, cookies)
    finally:
        await release_cookies(cookies, page)

async def get_id():
    global id
    id += 1
    return id

async def lock(id):
    global is_using_driver
    global current_access_id
    
    if not is_using_driver:
        current_access_id = id
        is_using_driver = True
        return id
    
    await ids_queue.put(id)
    while current_access_id != id:
        await asyncio.sleep(0)

async def release(id):
    global current_access_id
    global is_using_driver
    
    assert current_access_id == id
    if ids_queue.empty():
        is_using_driver = False
        current_access_id = None
        return
    
    current_access_id = await ids_queue.get()
    

async def send(req: requests.PreparedRequest, timeout=15, reconnection_amount=3, **kwargs) -> requests.Response:
    global TOTAL_PROXIES_ERROR
    global TOTAL_PROXIES_GOOD
    
    if isinstance(req, requests.Request):
        req = req.prepare()
    
    loop = asyncio.get_event_loop()
    
    with requests.Session() as sess:
        if (TOTAL_PROXIES_GOOD + 2) * 2 > TOTAL_PROXIES_ERROR:
            try:
                r = await loop.run_in_executor(None, partial(sess.send, req, verify=False, proxies=PROXIES, timeout=timeout, **kwargs))
                logger.debug("good send with proxy") 
                TOTAL_PROXIES_GOOD += 1
            except ProxyError as e:
                logger.debug("error in proxy reason of " + str(e))
                TOTAL_PROXIES_ERROR += 1
                r = await loop.run_in_executor(None, partial(sess.send, req, verify=False, **kwargs))
            except requests.ReadTimeout as e:
                logger.warning("Timeout error : " + str(e))
                r = None
        else:
            try:
                r = await loop.run_in_executor(None, partial(sess.send, req, verify=False, **kwargs))
            except requests.exceptions.ConnectionError as e:
                if reconnection_amount <= 0:
                    return None
                logger.warning(f"connection error in request : {req.path_url}-{req.url}-{req.headers}")
                logger.warning(e)
                time.sleep(5)
                return await send(req, timeout=timeout, reconnection_amount=reconnection_amount-1, **kwargs)
    return r

async def download_request(req: requests.PreparedRequest, filepath: str, timeout=15, **kwargs) -> requests.Response:
    
    if isinstance(req, requests.Request):
        req.prepare()
    
    try:
        with requests.Session() as sess:
            with sess.send(req, stream=True, timeout=timeout, verify=False, **kwargs) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(8096):
                        if chunk:
                            f.write(chunk)
    except requests.HTTPError as e:
        logger.warning(str(e))
    
    return r

async def get_captcha(cookies) -> str:
    
    #cré une requete avec les paramètres
    req = requests.Request("GET", URL + "/cej/xyhtml", cookies=cookies, headers=HEADERS, params=PARAMS)
    
    # Envoie la requete
    r = await send(req)
    
    # traite la réponse
    if r is None:
        raise AttributeError("None captcha")
    logger.debug(r.text)
    bal = BeautifulSoup(r.text, "html.parser")
    
    
    return str(bal.find("input").get("value"))

async def get_session(driver: WebDriver, force_unsafe = False):
    if force_unsafe:
        driver.delete_all_cookies()
        driver.get(URL + SEARCH_URL)
        cookies = get_cookies_dict(driver=driver)
        page = driver.page_source
        return page, cookies

    async with get_lock() as id:
        driver.delete_all_cookies()
        driver.get(URL + SEARCH_URL)
        cookies = get_cookies_dict(driver=driver)
        page = driver.page_source
    
    return page, cookies

def cookies_creator(driver: WebDriver):
    logger.info("starting getting cookies")
    loop = asyncio.get_event_loop_policy().new_event_loop()
    is_full = False
    while _initialized:
        if not cookies_queue.full():
            is_full = False
            try:
                page, cookies = loop.run_until_complete(get_session(driver=driver, force_unsafe=True))
            except:
                return
            cookies_amount = cookies_queue.qsize()
            loop.run_until_complete(cookies_queue.put((page, cookies)))
        elif not is_full:
            is_full = True
        
async def get_cookies():
    while cookies_queue.empty():
        await asyncio.sleep(0)
    cookies = cookies_queue.get_nowait()
    return cookies

async def release_cookies(cookies, page=None):
    if cookies_queue.empty():
        if page is None:
            req = requests.Request("GET", URL + SEARCH_URL, cookies=cookies)
            r = await send(req=req)
            if not r.status_code in [200, 201, 202]:
                return
            
            page = r.content
        cookies_queue.put_nowait((page, cookies))
    else:
        logger.debug("no empty queue : dumping cookies")

async def get_districts(page: str, cookies) -> typing.Dict[str, int]:
    """Récupère tout les districts dans un dictionnaire

    Args:
        driver (WebDriver): le driver a prendre pour envoyer les données
        
    Returns:
        Retourn un dictionnaire de la forme {"nom du district" : "id actuel du district"}
    """
    
    soup = BeautifulSoup(page, "html.parser")
    districts_list = soup.find(id="distritoJudicial")
    
    # dictionnaire de la forme 'nom du district':'id du district'
    id_name_districts = {}
    
    for i, child in enumerate(districts_list.findChildren(name="option", onmouseover="")):
        if not isinstance(child, Tag):
            continue
        
        id = child.get("value")
        district_name = child.text
        id_name_districts[district_name] = id
    
    return id_name_districts

async def get_instancias_for_district(cookies, district_code: (int, str)) -> dict:
    """Un fonction qui 

    Args:
        driver (WebDriver): Le WebDriver qui pilote le scraping
        district_code (int | str): l'id du district pour lequel on effectue la recherche

    Returns:
        dict: Retourn un dictionnaire de la forme {"nom de l'instance" : "id actuel de l'instance"}
    """
    url_distrito = URL + "/cej/forms/filtrarOrganosPorDistrito.html"
    
    data = {"codDistrito":district_code}
    add_header = HEADERS.copy()
    add_header.update({
        "Origin": "https://cej.pj.gob.pe"
    })
    
    req = requests.Request("POST", url=url_distrito, cookies=cookies, headers=add_header, data=data)
    r = await send(req)
    if r is None:
        raise AttributeError("None response in instancias_for_district")
    soup = BeautifulSoup(r.text, "html.parser")
    instancias = {t.text:t.get("value") for t in soup.find_all("option")}
    
    return instancias

async def get_specialized_per_district_and_instance(
    cookies, 
    district_code: (int, str), 
    instance_code: (int, str)
    ) -> typing.Dict[str, typing.Any]:
    """Une fonction qui retourne les spécialités

    Args:
        driver (WebDriver): Le driver qui pilote le scraping
        district_code (int | str): Le code du district
        instance_code (int | str): Le code de l'instance

    Returns:
        typing.Dict[str, int | str]: Retourn un dictionnaire de la forme {"nom de la spécialité" : "id actuel de la spécialité"}
    """
    
    url_espece = URL + "/cej/forms/filtrarEspecPorOrgano.html"
    
    data = {
        "codDistrito":district_code,
        "codOrgano": instance_code
    }
    add_header = HEADERS.copy()
    add_header.update({
        "Origin": "https://cej.pj.gob.pe"
    })
    
    req = requests.Request("POST", url=url_espece, cookies=cookies, headers=add_header, data=data)
    r = await send(req)
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    
    # récupère les spécialités
    specialized = {t.text:t.get("value") for t in soup.find_all("option")}
    
    return specialized
    

def get_instancias(cookies, overwrite=False):
    global DATA
    
    raise Exception("Uncorrect function")
    # Vérifie la validité du chemin des données et si nécéssaire, cré le fichier / initialize le fichier
    # c'est uniquement pour sauvegarder les données dans un .json
    try:
        with open(DATA_PATH, "r") as f:
            DATA = json.loads(f.read(), object_hook=dict)
    except FileNotFoundError:
        with open(DATA_PATH, "x") as f:
            f.write("{}")
            DATA = {} 
    except json.JSONDecodeError:
        with open(DATA_PATH, "w") as f:
            f.write("{}")
            DATA = {}
    
    # retourne les informations déja enregistré
    # n'a pas lieu si les informations ne sont pas présentes ou que la réécriture est demandée dans 'overwrite'
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
    # print(url_distrito)
    
    # dictionnaire de la forme 'nom du district':'id du district'
    id_name_districts = {}
    
    #dictionnaire de la forme 'nom de l'instance':'id de l'instance'
    id_instancias_dict = {}
    
    #dictionnaire de la forme 'id du district-id de l'instance':'index des spécialités'
    tuple_id_specialized_dict = {}
    
    #liste de dictionnaire de la forme 'nom de la spécialité':'id de la spécialité'
    specialized_dict_list = []
    
    for i, child in enumerate(districts_list.findChildren(name="option", onmouseover="")):
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
            #print("different instancias : ", instancias, " to ", id_instancias_dict)
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
        
        print(i, " : ", len(specialized_dict_list))
    
    print("done looping over childs\n\n")
    with open(DATA_PATH, "w") as f:
        #print(DATA, "\n"*2)
        DATA = {
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




async def validate(
    cookies, 
    district: (str, int), 
    instance: (str, int), 
    specialized: (str, int), 
    year: int, 
    n_expediente: int, 
    captcha: str,
    tries=3
    ):
    
    if tries < 0:
        return False
    
    instances_dict = DATA["id_instancias_dict"]
    
    #vérifie le district
    if district is None:
        logger.warning("District is None")
        return False
    elif not str(district).isalnum():
        logger.warning(f"The district {district} is not alpha numeric")
        return False
    
    
    #Vérifie l'instance
    if instances_dict is None:
        logger.warning("Invalid id for instancias_dict : " + str(district))
        return False
    if instance is None:
        logger.warning("none instance")
        return False
    elif not str(instance).isalnum():
        logger.warning("instance of " + str(instance) + " is not alpha numeric")
        return False
    
    
    if specialized is None:
        logger.warning("none specialized")
        return False
    elif isinstance(specialized, int):
        logger.warning("The string specialized of " + str(specialized) + " is not supported")
    else:
        if not str(specialized).isalnum():
            logger.warning("Specialized not found for " + specialized)
    
    
    # Vérifie la validité de l'année 
    if year and year >= 1977 and year <= CURRENT_YEAR:
        pass
    else:
        logger.warning("Year " + str(year) + " is not valid")
        return False

    # Vérifie la validité du n_expediente
    if n_expediente and n_expediente > 0:
        pass
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
    r = await send(req, timeout=45)
    
    if r is None:
        logger.info("cant validate the filters")
    
    try:
        code = r.text.strip()[0]
        if code == "0" or code == "1":
            return True
        elif len(r.text.strip()) > 10 and tries > 0:
            return await validate(cookies, district, instance, specialized, year, n_expediente, captcha, tries-1)
        else:
            # logger.warning("get false from the server : " + r.text.strip().splitlines()[0])
            return code
    except Exception as e:
        logger.info(type(r))
        logger.info(str(e))
    
    
async def search(
    cookies, 
    district: (str, int), 
    instance: (str, int), 
    specialized: (str, int), 
    year: int, 
    n_expediente: int, 
    captcha: str =None,
    is_validate: bool =False
    ) -> (requests.Response, None):
    
    # vérifie le captcha et les paramètres
    if captcha is None:
        captcha = await get_captcha(cookies)
    
    validate_result = await validate(cookies, district, instance, specialized, year, n_expediente, captcha)
    if not is_validate and not validate_result:
        return validate_result
    
    # Prépare la requete et les paramètres de celle-ci
    request_params = {
        "distritoJudicial": district,
        "organoJurisdiccional": instance,
        "especialidad": specialized,
        "anio": year,
        "numeroExpediente": n_expediente,
    }
    
    req = requests.Request("POST", url=URL+SEARCH_URL, headers=HEADERS, cookies=cookies, data=request_params)
    r = await send(req)
    
    return r

async def compute_result(
    cookies,
    searched_page: requests.Response
    ):
    """
    Retourne tout les formulaires sur la page demandée
    Prend en paramètre le navigateur et la page de la recherche

    Args:
        driver (WebDriver): _description_
        searched_page (requests.Response): _description_
    """
    if searched_page is None:
        print("no searched page")
        return None
    
    all_saved = True
    
    soup = BeautifulSoup(searched_page.text, "html.parser")
    content = soup.find("div", {"id": "divDetalles"})
    ids = {}
    
    if content is None:
        logger.error("No div with id 'divDetalles' found, the script raise an error if continue")
        logger.error(searched_page)
        logger.error(searched_page.text)
        return None, False
    
    for i, child in enumerate(content.findChildren("form", {"id": "command", "action": "detalleform.html", "method": "post"})):
        number = child.get("name", None)
        if number is None:
            continue
        
        ids[i] = int(number)
    
    
    forms = []
    
    coroutines = []
    
    for i, v in ids.items():
        coroutines.append(handle_one_form_id(cookies, v, download=False))
        
    result_list = await asyncio.gather(*coroutines)
    forms = [form for form in result_list if form is not None]
    
    if len(forms) < len(result_list):
        all_saved = False
    
    return forms, all_saved and any(forms)
        
async def handle_one_form_id(cookies, id, retry=True, download=False):
    request_param = {
        "nroRegistro":id
    }
    if cookies is None:
        _, cookies = await get_cookies()
    
    req = requests.Request("POST", url=URL+GET_FORM_URL, headers=HEADERS, cookies=cookies, data=request_param)
    r = await send(req)
    
    if r.status_code != 200:
        logger.warning("status code of " + str(r.status_code))
        r.raise_for_status()
        return None
    
    try:
        form = await get_one_form(text=r.text, id=id, download=download, cookies=cookies)
    except AttributeError:
        if retry:
            return await handle_one_form_id(cookies=None, id=id, retry=False, download=download)
        else:
            raise
    return form
    
async def download_pdf(cookies, infos, pdf_code, number):
    request_param = {
        "nid": pdf_code
    }
    district, instance, specialized, year, n_expediente = infos["trial_id"].split(":")
    
    req = requests.Request("GET", url=URL+DOWNLOAD_URL, headers=HEADERS, cookies=cookies, data=request_param)
    
    folder_path = os.path.join(
        os.getcwd(), 
        "result", 
        str(year),
        str(infos["district"]),
        str(infos["organo"]) + " -- "+str(infos["specialized"])
    )
    
    if not os.path.exists(folder_path):
        logger.warning("creating folder : {}".format(folder_path))
    
    filepath = os.path.join(
        folder_path,
        f"{infos['trial id']}_{infos['fecha de ignicio']}__{number}.pdf"
    )
    
    resp = await download_request(req=req, filepath=filepath)
    
    return resp

async def get_one_form(text: str, id=None, download=True, cookies={}):
    soup = BeautifulSoup(text, "html.parser")
    
    switch_dict = {
        "Expediente N°:": "trial_id",
        "Expediente NÂ°:": "trial_id",
        "Órgano Jurisdiccional:": "organo",
        "Ã“rgano Jurisdiccional:": "organo",
        "Distrito Judicial:": "district",
        "Juez:": "juez",
        "Especialista Legal:": "legal_specialized",
        "Fecha de Inicio:": "fecha de ignicio",
        "Proceso:": "proceso",
        "Observación:": "observation",
        "ObservaciÃ³n:": "observation",
        "Especialidad:": "specialized",
        "Materia(s):": "materials",
        "Estado:": "status",
        "Etapa Procesal:": "step",
        "Fecha Conclusión:": "fecha_conclusion",
        "Fecha ConclusiÃ³n:": "fecha_conclusion",
        "Ubicación:": "ubication",
        "UbicaciÃ³n:": "ubication",
        "Motivo Conclusión:": "motivo_conclusion",
        "Motivo ConclusiÃ³n:": "motivo_conclusion",
        "Sumilla:": "sumilla",
        
    }
    
    infos = {}
    
    #scrap le premier pannel
    pannel_one_values = {}
    pannel_one = soup.find("div", {"id": "collapseOneG"})
    if pannel_one is None:
        print(str(soup), id)
    pannel_one_children = pannel_one.find("div", {"id": "gridRE"}).children
        
    for child in pannel_one_children:
        if not isinstance(child, Tag):
            continue
        
    
        if "".join(list(child.get("class", None))) != "divRepExp":
            logger.info(child.get("class", "Nothing"))
            continue
        
        last = None
        for content in child.children:
            if not isinstance(content, Tag):
                continue
            content_class = "".join(list(content.get("class")))
            # logger.info(content_class)
            if content_class == "celdaGridN":
                last = str(content.text)
            elif last is not None and "celdaGrid" in content_class:
                pannel_one_values[last] = str(content.text)
                last = None
    
    for k, v in pannel_one_values.items():
        value = v
        value = value.replace("\n", "")
        value = value.replace("\r", "")
        value = value.replace("\t", "")
        value = value.replace("\xa0", "")
        values = [val for val in value.split("-") if val]
        value = "-".join(values)
        # value = value.replace("-", "")
        value = value.replace("JUZ.", "JUZGADO")
        infos[switch_dict.get(k, k)] = value
            
    # logger.info("infos : " + str(infos))
    
    pannel_two_switch = {
        "Parte": "parte",
        "Tipo de Persona": "tipo de Persona",
        "Apellido Paterno / Razón Social": "apellido paterno",
        "Apellido Materno": "apellido materno",
        "Nombres": "nombres",
    }
    
    #scrap le second pannel
    pannel_two_categories = []
    pannel_two_values = []
    child_index = 0
    for child in soup.find("div", {"id": "collapseTwo"}).find("div", {"class": "panelGrupo"}).children:
        child_values = {}
        if not isinstance(child, Tag):
            continue
        
        
        if child_index == 0:
            for cat in child.children:
                if not isinstance(child, Tag):
                    continue
                text = cat.get_text(" ").replace("\n", " ")
                text = text.replace("\n", "")
                text = text.replace("\t", "")
                text = text.replace("\r", "")
                if text == " ":
                    continue
                pannel_two_categories.append(pannel_two_switch.get(text, text))
            
            logger.debug("categories" + str(pannel_two_categories))
            child_index += 1
            continue
        
        child_class = child.get("class", "")
        part = ""
        info_index = 0
        
        for info in child.children:
            if (not isinstance(info, Tag)) or (info is None):
                continue
            
            if info is None:
                continue
            else:
                logger.debug(info)
                
            value = info.get_text(" ")
            info_class = " ".join(info.get("class", ""))
            
            child_values[pannel_two_categories[info_index]] = value
            
            info_index += 1
        
        pannel_two_values.append(child_values)
        
        child_index += 1
    
    # pannel_two_dict = dict(map(lambda x: list(zip(pannel_two_categories, x.keys())), pannel_two_values))
    infos["personns"] = pannel_two_values

    #scrap pannel three (descargar)
    downloads_list = soup.find("div", {"id": "collapseThree"}).find_all("a", {"class": "aDescarg"})
    
    downloads_data = {}
    
    if download and len(downloads_list) > 0:
        infos["descargar"] = True
        assert isinstance(downloads_list, ResultSet)
        for i, result in enumerate(downloads_list):
            if not isinstance(result, Tag):
                continue
            result: Tag
            url = result.get("href", None)
            if url is None:
                continue
            
            *_, data_string = url.split("?")
            data_name, data_value = data_string.split("=")
            
            if data_name != "nid":
                continue
            
            dat = await download_pdf(cookies=cookies, infos=info, number=i, pdf_code=data_value)
            
                
    else:
        infos["descargar"] = False
    
    return infos
        