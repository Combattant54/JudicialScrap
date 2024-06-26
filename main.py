import argparse, logging, os

from saver import Saver
import scraper
import urllib3
import traceback
import sys
import platform
from sql_saver import SQLSaver
import asyncio
import keyboard
import datetime

import sqliteORM.logger_builder
sqliteORM.logger_builder.set_level(logging.DEBUG)
import build_logger
import api
import signal

PROXIES = [("127.0.0.1", 8080)]
for proxy in PROXIES:
    try:
        #delay = ping.Ping('www.wikipedia.org', timeout=2000).do()
        pass
    except Exception as e:
        print(e)
        PROXIES.remove(proxy)
    else:
        #print("Delai to", proxy, "=", delay)
        pass
    
urllib3.disable_warnings()
ALPHABET = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "w", "X", "Y", "Z",
]

COLUMNS = [
    "Distrito Judicial",
    "Instancia",
    "Especialidad",
    "Año",
    "N expediente",
    "trial ID",
    "Juzgado",
    "Juez",
    "Fecha de Inicio",
    "Fecha Conclusión",
    "Materia(s)",
    "Sumilla",
    "Especialista legal",
    "Proceso",
    "Estado",
    "DEMANDADO (Tipo de Persona)",
    "DEMANDADO (Apellido Paterno + Apellido Materno)",
    "DEMANDADO (Nombres)",
    "DEMANDANTE (Tipo de Persona)",
    "DEMANDANTE (Apellido Paterno + Apellido Materno)",
    "DEMANDANTE (Nombres)",
    "AGRAVIADO (Tipo de Persona)",
    "AGRAVIADO (Apellido Paterno + Apellido Materno)",
    "AGRAVIADO (Nombres)",
    "DESCARGAR",
]

COLUMNS_MAP = {ALPHABET[i]:COLUMNS[i] for i in range(len(COLUMNS))}

#On définit les paramètre des loggers (fichier de sortie et format)
FORMAT = "%(levelname)s:[%(asctime)s]:%(name)s-%(lineno)s : %(msg)s"
LOGS_FILE = "logs.txt"
if not os.path.exists(LOGS_FILE):
    with open(LOGS_FILE, "x"):
        pass

DESCRIPTION = """Un programme de scraping internet : 
Un programme qui scrape le site 'cej.cj.gob.pe' (un site contenant des informations sur des procès au Pérou)
"""

MAIN_TASK = None

async def main(mode="INFO", logs_file=LOGS_FILE, save_file="result/output.xlxs", overwrite=False, **kwargs):
    global MAIN_TASK
    # définit le fichier de log
    global LOGS_FILE
    LOGS_FILE = logs_file
    global LOGGER
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "x"):
            pass
    
    build_logger.set_level(mode)
    LOGGER = build_logger.get_logger(__name__)
    
    # cré le saver
    path, name = os.path.split(save_file)
    name = "db.db"
    saver = (path, name, COLUMNS_MAP)
    
    # lance le scraping
    try:
        scraper.init(**kwargs)
        api.start()
        scraper_task = asyncio.create_task(scraper.scrap(saver=saver, overwrite=overwrite, **kwargs))
        starting_time = datetime.datetime.now()
        MAIN_TASK = scraper_task
        await asyncio.sleep(2)
        LOGGER.critical(api.get_json())
        LOGGER.info("starting_time :" + str(starting_time))
        
        LOGGER.debug("starting awaiting MAIN TASK")
        await MAIN_TASK
        print("main task finished")
        LOGGER.critical("main task finished")
    except Exception as e:
        extype, value, tb = sys.exc_info()
        for ligne in traceback.format_exception(extype, value, tb):
            LOGGER.error(ligne)
        LOGGER.exception("Getting an exception : " + str(e))
    finally:
        LOGGER.critical(api.get_json())
        ending_time = datetime.datetime.now()
        running_time = ending_time - starting_time
        LOGGER.critical("starting_time :" + str(starting_time))
        LOGGER.critical("ending_time :" + str(ending_time))
        LOGGER.critical("exiting after running_time : " + str(running_time))
        try:
            MAIN_TASK.cancel()
        except:
            LOGGER.warning("Can't cancell the task " + str(MAIN_TASK))
        exit()
        LOGGER.critical("exit system")
        sys.exit(4)

def exit():
    traceback.print_stack(limit=30)
    extyp, value, tb = sys.exc_info()
    LOGGER.critical("\n".join(traceback.format_exception(extyp, value, tb, limit=30)))
    global stop
    logger = build_logger.get_logger(__name__)
    try:
        stop = True
        try:
            MAIN_TASK.cancel()
            scraper.stop()
        except Exception as e:
            logger.warning("Can't cancell the task " + str(MAIN_TASK) + " ; " + str(e))
        try:
            asyncio.run(api.stop())
        except Exception as e:
            print(type(e))
            print(e)
            asyncio.get_event_loop().run_until_complete(api.stop())
    except:
        pass
    finally:
        if platform.system() == "Windows":
            os.system("taskkill /IM python.exe /F")
        else:
            logger.info("pkill running")
            os.system("pkill -e -c -f python.exe; pkill -e -c -f python3.9; pkill -e -c -f bash")
            logger.info("kill running")
            os.system("kill -9 $(pidof python3.9); echo 'first kill done'; kill -9 $(pidof java)")
            logger.info("os.kill running")
            os.kill(os.getpid(), signal.SIGKILL)

def get_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    help_years = "All scraped years, one by one separated by ';' (1997;1998;2023) or in range separated by '-' (2007-2017;2020)"
    help_years += f", valid years are in range {1977}-{datetime.date.today().year}"
    parser.add_argument("years", type=str, help=help_years)
    parser.add_argument("districts", type=str, help="All disctricts scraped")
    parser.add_argument("instances", type=str, help="All instances scraped")
    parser.add_argument("specialized", type=str, help="All specialized scraped")
    
    parser.add_argument("-o", "--output", type=str, default="result/output.xlxs", help="Le fichier de sortie du document")
    
    #parser.add_argument("-m", "--mode", type=str, default="WARNING", choices=logging.getLevelNamesMapping().keys(), help="Le niveau a partir duquel les messages vont être loggés")
    parser.add_argument("-m", "--mode", default="INFO", help="Le niveau a partir duquel les messages vont être loggés")
    
    parser.add_argument("--logs-file", type=str, default=LOGS_FILE, help="Le fichier dans lequel vont être écrits les logs")
    
    parser.add_argument("--overwrite", action="store_true", help="Si présent, réécrit le fichier data.json")
    
    parser.add_argument("--just_init", action="store_true", help="Si présent, initialise les scripts sans lancer le scraping")
    
    return parser.parse_args()

if __name__ == "__main__":
    namespace = get_args()
    params_dict = {k:v for (k, v) in namespace._get_kwargs()}
    
    keyboard.add_hotkey("ctrl+q", exit)
    
    asyncio.run(main(**params_dict))
