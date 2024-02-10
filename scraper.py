import json
import asyncio
import threading
import datetime
from .sql_saver import SQLSaver

from webdriver import get_driver

with open("errored.txt", "w"):
    pass

from sql_saver import SQLSaver
import requester
from datetime import date

# définit le logger de ce fichier
import build_logger
logger = build_logger.get_logger(__name__)

today = date.today()
DATA_PATH = "result/data.json"
with open(DATA_PATH, "r") as f:
    DATA = json.loads(f.read())

PROXIES = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080"
}

#définie l'url du site, du formulaire et le cookie (généré avec un navigateur classique parce que sinon ca marche pas)
URL = "https://cej.pj.gob.pe"
FORM_URL = "/cej/forms/busquedaform.html"
CAPTCHA_URL = "/cej/Captcha.jpg"

PROXIES.clear()

ALL_YEARS = set(range(1977, today.year+1))
ALL_DISTRICTS = set(DATA["id_name_districts"].keys())
ALL_INSTANCES = set(DATA["id_instancias_dict"].keys())
ALL_SPECIALIZED = set()
for d in DATA["specialized_dict_list"]:
    ALL_SPECIALIZED.update(d.keys())
print(ALL_YEARS)
print(ALL_DISTRICTS)
print(ALL_INSTANCES)
print("specialized : ")
print(ALL_SPECIALIZED)

YEARS = {2015}
DISTRICTS = {"AMAZONAS"}
SPECIALIZED = {"FAMILIA CIVIL", "FAMILIA TUTELAR"}

YEARS = {2018}
DISTRICTS = {"AMAZONAS"}
INSTANCES = {"JUZGADO DE PAZ LETRADO", "JUZGADO ESPECIALIZADO", "JUZGADO MIXTO", "SALA SUPERIOR"}
SPECIALIZED = {"FAMILIA CIVIL"}
N_EXPEDIENTES = list(range(1, 5000, 1))
page_scraped = 0

DIRECT_SAVER = False
SYNCRONOUS_AMOUNT = 10
BREAKS_AMOUNT = 20

# driver = None
initialized = False
isStopped = False

scraping_years = set()
scraping_districts = set()
scraping_instances = set()
scraping_specialized = set()
scraping_n_expedientes = set()

scraped_years = set()
scraped_districts = set()
scraped_instances = set()
scraped_specialized = set()
scraped_n_expedientes = set()

def init(proxy_addr="127.0.0.1:8080", **kwargs):
    global driver
    global initialized
    
    PROXIES["http"] = "http://" + proxy_addr
    PROXIES["https"] = "http://" + proxy_addr
    
    requester.init(URL, CAPTCHA_URL, PROXIES)
    
    driver = get_driver(proxy_addr=proxy_addr)

    initialized = True

async def get_saver(path, year, columns_map) -> SQLSaver:
    saver = SQLSaver(f"db_{year}.db", path, columns_map)
    await saver.create_tables()
    return saver

async def scrap_n_expediente(saver: SQLSaver, year, district_name, instance_name, specialized_name, n_expediente, tries=3):
    if isStopped or tries < 0:
        return False
    
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
            code = f"{district_name}:{instance_name}:{specialized_name}:{year}:{n_expediente}"
            with open("errored.txt", "a") as f:
                f.write(f"{datetime.datetime.now()} - error during getting (nothing searched) {code}\n")
            return False
        elif r == "2":
            logger.warning(f"No data ({r}) get for {district_name}:{district_code} {instance_name}:{instance_code} {specialized_name}:{specialized_code} {year} {n_expediente}")
            return 2
        else:
            forms_infos = await requester.compute_result(cookies, searched_page=r)
    
    if forms_infos is None or not forms_infos:
        if tries > 0:
            return await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, n_expediente, tries-1)
        code = f"{district_name}:{instance_name}:{specialized_name}:{year}:{n_expediente}"
        with open("errored.txt", "a") as f:
            f.write(f"{datetime.datetime.now()} - error during getting forms infos (max tries reach) {code}\n")
        return False
    
    # compute the result
    # print(forms_infos)
    
    # print(f"computing datas for {district_name}:{instance_name}:{specialized_name}:{year}:{n_expediente}")
    await saver.compute_informations(forms_infos, district_name=district_name, instance_name=instance_name, specialized_name=specialized_name)
    
    return True
    

async def scrap_specialized(saver, year, district_name, instance_name, specialized_name):
    if isStopped:
        return
    
    global page_scraped
    
    scraping_specialized.add(specialized_name)
    
    errored = []
    were_broken = []
    
    current_n_expediente = 0
    was_broken_at = None
    while True:
        current_n_expediente += 1
        
        if DIRECT_SAVER:
            coroutines = []
            n_expedientes = list(range(current_n_expediente, current_n_expediente + SYNCRONOUS_AMOUNT))
            scraping_n_expedientes.update(n_expedientes)
            for i in n_expedientes:
                logger.info("adding for n_expediente = " + str(i))
                coroutines.append(scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, i))
            
            results = await asyncio.gather(*coroutines)
            
            scraping_n_expedientes.difference_update(n_expedientes)
            scraped_n_expedientes.update(n_expedientes)
            
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
        
        # starting script if this is not in direct saver (currently what is selected)
        try:
            scraping_n_expedientes.add(current_n_expediente)
            r = await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, current_n_expediente)
        except AttributeError as e:
            if "has no attribute 'findChildren'" in str(e):
                r = await scrap_n_expediente(saver, year, district_name, instance_name, specialized_name, current_n_expediente)
            else:
                current_str = f"{year}:{district_name}:{instance_name}:{specialized_name}:{current_n_expediente}"
                logger.exception(f"an unhandled exception occured when scraping " + current_str)
                r = None
        scraping_n_expedientes.remove(current_n_expediente)
        
        if r:
            for n in were_broken:
                errored.append((year, district_name, instance_name, specialized_name, n))
                with open("errored.txt", "a") as f:
                    f.write(f"{datetime.datetime.now()} - error during scraping n_expediente {year}:{district_name}:{instance_name}:{specialized_name} -> {n} \n")
            were_broken.clear()
            page_scraped += 1
            scraped_n_expedientes.add(current_n_expediente)
            continue
        elif len(were_broken) + 1 == BREAKS_AMOUNT:
            were_broken.append(current_n_expediente)
            for error in errored.copy():
                if error[-1] in were_broken:
                    errored.remove(error)
            break
        elif len(were_broken) + 1 < BREAKS_AMOUNT:
            were_broken.append(current_n_expediente)
        else:
            scraped_n_expedientes.add(current_n_expediente)
            with open("errored.txt", "a") as f:
                f.write(f"{datetime.datetime.now()} - error during scraping n_expediente {year}:{district_name}:{instance_name}:{specialized_name} -> {was_broken_at}\n")
            logger.warning(f"error in scraping  {year}  {district_name}  {instance_name}  {specialized_name}  {was_broken_at}")
    
    scraped_specialized.add(specialized_name)
    scraping_specialized.remove(specialized_name)
    scraped_n_expedientes.clear()
    
    return errored


async def scrap_instance(saver, year, district_name, instance_name):
    errored = []
    if isStopped:
        return
    
    scraping_instances.add(instance_name)
    
    specialized_list_id = DATA["tuple_id_specialized_dict"][district_name + "--" + instance_name]
    
    specialized_dict = DATA["specialized_dict_list"][specialized_list_id]
    
    coroutines = []
    
    for specialized_name in specialized_dict.keys():
        if not specialized_name.upper() in SPECIALIZED:
            logger.debug(f"specialized {specialized_name} not in {str(SPECIALIZED)}")
            continue
        
        if not DIRECT_SAVER:
            logger.info("awaiting specialized of " + specialized_name)
            r = await scrap_specialized(saver, year, district_name, instance_name, specialized_name)
            errored.extend(r)
            continue
        
        coroutines.append(scrap_specialized(saver, year, district_name, instance_name, specialized_name))
    
    if DIRECT_SAVER:
        r_list = await asyncio.gather(*coroutines)
        for r in r_list:
            errored.extend(r)
    
    scraped_instances.add(instance_name)
    scraping_instances.remove(instance_name)
    scraping_specialized.clear()
    
    return errored

async def scrap_district(saver, year, district_name):
    errored = []
    if isStopped:
        return
    
    scraping_districts.add(district_name)
    
    # récupère le nom du district et le nom de chaque instance dans le format "district_name--instance_name"
    districts_instances_names = [name for name in DATA["tuple_id_specialized_dict"].keys() if name.startswith(district_name)]
    
    coroutines = []
    for district_instance_name in districts_instances_names:
        instance_name = str(district_instance_name.split("--")[1])
        
        if not instance_name.upper() in INSTANCES:
            continue
        
        if not DIRECT_SAVER:
            logger.info("awaiting instance of " + instance_name)
            r = await scrap_instance(saver, year, district_name, instance_name)
            errored.extend(r)
            continue
        else:
            coroutines.append(scrap_instance(saver, year, district_name, instance_name))
    
    if DIRECT_SAVER:
        logger.error("not supposed to be in direct saver")
        r_list = await asyncio.gather(*coroutines)
        for r in r_list:
            errored.extend(r)
    
    scraped_districts.add(district_name)
    scraping_districts.remove(district_name)
    scraping_instances.clear()
    
    return errored

async def scrap_year(saver, year):
    errored = []
    if isStopped:
        print("stopping because isStopped is True")
        return
    
    districts_names = DATA["id_name_districts"].keys()
    scraping_years.add(year)
    
    for district_name in districts_names:
        if not district_name.upper() in DISTRICTS:
            continue
        
        logger.info("awaiting district of " + district_name)
        r = await scrap_district(saver, year, district_name)
        errored.extend(r)
    
    scraped_years.add(year)
    scraping_years.remove(year)
    scraped_districts.clear()
    
    return errored

async def scrap(saver: tuple, overwrite=False, just_init=False, **kwargs):
    if not initialized:
        logger.critical("This script havn't been initialized : exiting script")
        return
    
    path, name, columns_map = saver
    
    # SETTING SCRAPING PARAMETERS !

    global YEARS
    global DISTRICTS
    global INSTANCES
    global SPECIALIZED
    
    print("setting years")
    #setting years
    years = kwargs.get("years", ALL_YEARS)
    if (isinstance(years, str) and years.strip() == "ALL") or years is None:
        YEARS = ALL_YEARS
    elif isinstance(years, str):
        YEARS = []
        years = years.split(";")
        for year_arg in years:
            if str(year_arg).find("-") != -1:
                start_year, stop_year = year_arg.split("-")
                start_year = int(start_year)
                stop_year = int(stop_year)
                YEARS.extend(list(range(start_year, stop_year, 1)))
            else:
                YEARS.append(int(year_arg.strip()))
    else:
        logger.warning("invalid years parameter : " + str(years))
        YEARS = ALL_YEARS
    print("years set as : " + str(YEARS))
    #setting districts
    districts = kwargs.get("districts", ALL_DISTRICTS)
    if (isinstance(districts, str) and districts.strip() == "ALL") or districts is None:
        DISTRICTS = {district.upper() for district in ALL_DISTRICTS}
    elif isinstance(districts, str):
        DISTRICTS = set()
        districts = districts.split(";")
        for district_arg in districts:
            DISTRICTS.add(str(district_arg).upper())
    else:
        logger.warning("invalid districts parameters : " + str(districts))
        DISTRICTS = {district.upper() for district in ALL_DISTRICTS}
    print("districts set as : " + str(DISTRICTS))
    
    # setting instances
    instances = kwargs.get("instances", ALL_INSTANCES)
    if (isinstance(instances, str) and instances.strip() == "ALL") or instances is None:
        INSTANCES = {instance.upper() for instance in ALL_INSTANCES}
    elif isinstance(instances, str):
        INSTANCES = set()
        instances = instances.split(";")
        for instance_arg in instances:
            INSTANCES.add(str(instance_arg).upper())
    else:
        logger.warning("invalid instances parameters : " + str(instances))
        INSTANCES = {instance.upper() for instance in ALL_INSTANCES}
    print("setting instances as " + str(INSTANCES))
    
    #setting specialized 
    specialized = kwargs.get("specialized", ALL_SPECIALIZED)
    if (isinstance(specialized, str) and specialized.strip() == "ALL") or specialized is None:
        SPECIALIZED = {specialized.upper() for specialized in ALL_SPECIALIZED}
    elif isinstance(specialized, str):
        SPECIALIZED = set()
        specialized = specialized.split(";")
        for specialized_arg in specialized:
            SPECIALIZED.add(str(specialized_arg).upper())
    else:
        logger.warning("invalid specialized parameters : " + str(specialized))
        SPECIALIZED = {specialized.upper() for specialized in ALL_SPECIALIZED}
    print("setting specilized as " + str(SPECIALIZED))
    
    # END SETTING SCRAPING PARAMETERS ! 
    
    
    thread = threading.Thread(target=requester.cookies_creator, kwargs={"driver": driver})
    thread.start()
    
    if just_init:
        print("exiting after a just init, may be an exception")
        stop()
        return
    
    tasks = []
    errors_list = []
    for year in YEARS:
        saver = await get_saver(path, year, columns_map)
        print("awaiting year " + str(year))
        err = await scrap_year(saver, year)
        print("years awaited, errors are : " + str(err))
        errors_list.append(err)
    # unworking code : the target server return false
    # errors_list = await asyncio.gather(*tasks)
    
    
    errored = []
    for errors in errors_list:
        if errors is None:
            continue
        errored.extend(errors)
        with open("errored.txt", "a") as f:
            f.write(f"{datetime.datetime.now()} - Starting final errors computing -> \n")
            for e in errors:
                f.write(":".join(e) + "\n")
            
    
    logger.debug(errored)
    stop()
    
    
def get_iterator(driver, saver: SQLSaver):
    saver.get_filtrer()

def stop():
    logger.critical("stoping the script")
    global isStopped
    isStopped = True
    requester.stop()
    driver.close()
    