from bs4 import BeautifulSoup
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver import Edge, DesiredCapabilities
from selenium.webdriver.edge.service import Service
import logging
import json
import asyncio
import threading

from sql_saver import SQLSaver
import requester
from datetime import date

# définit le logger de ce fichier
import build_logger
logger = build_logger.get_logger(__name__)

today = date.today()
with open("data.json", "r") as f:
    DATA = json.loads(f.read())

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

YEARS = set(range(1977, today.year))
DISTRICTS = set(DATA["id_name_districts"].keys())
INSTANCES = set(DATA["id_instancias_dict"].keys())
SPECIALIZED = set()
for d in DATA["specialized_dict_list"]:
    SPECIALIZED.update(d.keys())
print(YEARS)
print(DISTRICTS)
print(INSTANCES)
print("specialized : ")
print(SPECIALIZED)

YEARS = {2015}
DISTRICTS = {"AMAZONAS"}
SPECIALIZED = {"FAMILIA CIVIL", "FAMILIA TUTELAR"}

YEARS = {2018}
DISTRICTS = {"AMAZONAS"}
INSTANCES = {"JUZGADO DE PAZ LETRADO"}
SPECIALIZED = {"FAMILIA CIVIL"}
N_EXPEDIENTES = list(range(1, 757, 1))

DIRECT_SAVER = False
SYNCRONOUS_AMOUNT = 10

# driver = None
initialized = False
isStopped = False


def init(proxy_addr="127.0.0.1:8080", **kwargs):
    global driver
    global initialized
    
    PROXIES["http"] = "http://" + proxy_addr
    PROXIES["https"] = "http://" + proxy_addr
    
    requester.init(URL, CAPTCHA_URL, PROXIES)
    
    service = Service("driver/msedgedriver.exe")
    proxy = Proxy()
    proxy.proxy_type = ProxyType.MANUAL
    proxy.http_proxy = proxy_addr
    
    capabilities = DesiredCapabilities.EDGE.copy()
    capabilities["plateform"] = "WINDOWS"
    capabilities["version"] = "11"
    proxy.add_to_capabilities(capabilities)
    driver = Edge(capabilities=capabilities, service=service)

    initialized = True

async def scrap_n_expediente(saver: SQLSaver, year, district_name, instance_name, specialized_name, n_expediente, tries=3):
    if isStopped:
        return
    
    logger.debug(f"scraping {year} {district_name} {instance_name} {specialized_name} {n_expediente}")
    forms_infos = None
    
    async with requester.cookies_context() as (page, cookies):
    
        districts = await requester.get_districts(page, cookies)
        district_code = districts.get(district_name)
        if district_code is None:
            logger.warning("district " + district_name + " not found in " + str(districts))
            return -1
        
        instancias = await requester.get_instancias_for_district(cookies, district_code)
        instance_code = instancias.get(instance_name)
        if instance_code is None:
            logger.warning("instance " + instance_name + " not found in " + str(instancias))
            return -1
        
        specialized = await requester.get_specialized_per_district_and_instance(cookies, district_code, instance_code)
        specialized_code = specialized.get(specialized_name, None)
        if specialized_code is None:
            logger.warning("specialized " + specialized_name + " not found in " + str(specialized))
            return -1
        
        r = await requester.search(
            cookies, 
            district_code,
            instance_code, 
            specialized_code,
            year,
            n_expediente
        )
        
        if not r:
            logger.debug("False returned")
            return False
        elif r == "2":
            logger.warning(f"No data ({r}) get for {district_name}:{district_code} {instance_name}:{instance_code} {specialized_name}:{specialized_code} {year} {n_expediente}")
            return 2
        else:
            forms_infos = await requester.compute_result(cookies, searched_page=r)
    
    if forms_infos is None or not forms_infos:
        if tries > 0:
            return await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, n_expediente, tries-1)
        return False
    
    # compute the result
    # print(forms_infos)
    
    print(f"computing datas for {district_name}:{instance_name}:{specialized_name}:{year}:{n_expediente}")
    await saver.compute_informations(forms_infos, district_name=district_name, instance_name=instance_name, specialized_name=specialized_name)
    
    return True
    

async def scrap_specialized(saver, year, district_name, instance_name, specialized_name):
    if isStopped:
        return
    
    errored = []
    
    current_n_expediente = 0
    was_broken_at = None
    while True:
        current_n_expediente += 1
        
        if DIRECT_SAVER:
            coroutines = []
            for i in range(current_n_expediente, current_n_expediente + SYNCRONOUS_AMOUNT):
                logger.info("adding for n_expediente = " + str(i))
                coroutines.append(scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, i))
            
            results = await asyncio.gather(*coroutines)
            
            for i, r in enumerate(results):
                if r == True:
                    continue
                elif r == -1:
                    errored.append((year, district_name, instance_name, specialized_name, current_n_expediente + i))
                elif was_broken_at is None:
                    was_broken_at = current_n_expediente + i
                elif was_broken_at + 1 == current_n_expediente + i:
                    break
                else:
                    logger.warning(f"error in scraping  {year}  {district_name}  {instance_name}  {specialized_name}  {was_broken_at}")
            
            current_n_expediente += SYNCRONOUS_AMOUNT - 1
            continue
        
        try:
            r = await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, current_n_expediente)
        except AttributeError as e:
            if "has no attribute 'findChildren'" in str(e):
                r = await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, current_n_expediente)
        if r:
            logger.debug("continuing scraping")
            continue
        if was_broken_at is None:
            was_broken_at = current_n_expediente
        elif was_broken_at + 1 == current_n_expediente:
            break
        else:
            logger.warning(f"error in scraping  {year}  {district_name}  {instance_name}  {specialized_name}  {was_broken_at}")
    
    return errored


async def scrap_instance(saver, year, district_name, instance_name):
    errored = []
    if isStopped:
        return
    
    specialized_list_id = DATA["tuple_id_specialized_dict"][district_name + "--" + instance_name]
    
    specialized_dict = DATA["specialized_dict_list"][specialized_list_id]
    
    coroutines = []
    
    for specialized_name in specialized_dict.keys():
        if not specialized_name in SPECIALIZED:
            continue
        
        if DIRECT_SAVER:
            logger.info("awaiting specialized of " + specialized_name)
            r = await scrap_specialized(saver, year, district_name, instance_name, specialized_name)
            errored.extend(r)
            continue
        
        coroutines.append(scrap_specialized(saver, year, district_name, instance_name, specialized_name))
    
    if not DIRECT_SAVER:
        r_list = await asyncio.gather(*coroutines)
        for r in r_list:
            errored.extend(r)
    
    return errored

async def scrap_district(saver, year, district_name):
    errored = []
    if isStopped:
        return
    
    # récupère le nom du district et le nom de chaque instance dans le format "district_name--instance_name"
    districts_instances_names = [name for name in DATA["tuple_id_specialized_dict"].keys() if name.startswith(district_name)]
    
    coroutines = []
    for district_instance_name in districts_instances_names:
        instance_name = district_instance_name.split("--")[1]
        
        if not instance_name in INSTANCES:
            continue
        
        if DIRECT_SAVER:
            logger.info("awaiting instance of " + instance_name)
            r = await scrap_instance(saver, year, district_name, instance_name)
            errored.extend(r)
            continue
        coroutines.append(scrap_instance(saver, year, district_name, instance_name))
    
    if not DIRECT_SAVER:
        r_list = await asyncio.gather(*coroutines)
        for r in r_list:
            errored.extend(r)

async def scrap_year(saver, year):
    errored = []
    if isStopped:
        return
    
    districts_names = DATA["id_name_districts"].keys()
    
    for district_name in districts_names:
        if not district_name in DISTRICTS:
            continue
        
        logger.info("awaiting district of " + district_name)
        r = await scrap_district(saver, year, district_name)
        errored.extend(r)

async def scrap(saver: SQLSaver, overwrite=False, just_init=False, **kwargs):
    if not initialized:
        logger.critical("This script havn't been initialized : exiting script")
        return
    
    thread = threading.Thread(target=requester.cookies_creator, kwargs={"driver": driver})
    thread.start()
    
    if just_init:
        stop()
        return
    
    tasks = []
    for year in YEARS:
        tasks.append(scrap_year(saver, year))
    
    errors_list = await asyncio.gather(*tasks)
    errored = []
    for errors in errors_list:
        if errors is None:
            continue
        errored.extend(errors)
    
    print(errored)
    stop()
    
    
def get_iterator(driver, saver: SQLSaver):
    saver.get_filtrer()

def stop():
    global isStopped
    isStopped = True
    requester.stop()
    driver.close()
    

# def exit():
#     if driver is None:
#         return
    
#     driver.quit()