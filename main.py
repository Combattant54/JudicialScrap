import argparse, logging, os

from saver import Saver
import scraper
import urllib3
import traceback
import sys
from sql_saver import SQLSaver

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
Un programme qui scrape le site 'cej.cj.gob.pe'(un site contenant des informations sur des procès)
"""



def main(mode="WARNING", logs_file=LOGS_FILE, save_file="result/output.xlxs", overwrite=False, **kwargs):
    # définit le fichier de log
    global LOGS_FILE
    LOGS_FILE = logs_file
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "x"):
            pass
    
    logging.basicConfig(filename=LOGS_FILE, filemode="w", level=mode, format=FORMAT)
    
    # cré le saver
    if kwargs.get("sql_saver", False):
        path, name = os.path.split(save_file)
        name = "db.db"
        saver = SQLSaver(name, path, COLUMNS_MAP)
    else:
        saver = Saver(*os.path.split(save_file), COLUMNS_MAP)
    
    # lance le scraping
    try:
        scraper.init()
        scraper.scrap(saver=saver)
    except Exception as e:
        traceback.print_exc()
    finally:
        scraper.exit()
        sys.exit()

def get_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-o", "--output", type=str, default="result/output.xlxs", help="Le fichier de sortie du document")
    
    #parser.add_argument("-m", "--mode", type=str, default="WARNING", choices=logging.getLevelNamesMapping().keys(), help="Le niveau a partir duquel les messages vont être loggés")
    parser.add_argument("-m", "--mode", default="WARNING", help="Le niveau a partir duquel les messages vont être loggés")
    
    parser.add_argument("--logs-file", type=str, default=LOGS_FILE, help="Le fichier dans lequel vont être écrits les logs")
    
    parser.add_argument("--overwrite", action="store_true", help="Si présent, réécrit le fichier data.json")
    
    parser.add_argument("--sql_saver", action="store_true", help="Si présent, utilise le saver SQLsaver (expérimental)")
    
    return parser.parse_args()

if __name__ == "__main__":
    namespace = get_args()
    params_dict = {k:v for (k, v) in namespace._get_kwargs()}
    
    main( **params_dict)