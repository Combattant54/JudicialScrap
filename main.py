import argparse, logging, os

from saver import Saver
import scraper
import urllib3

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
print(len(COLUMNS), COLUMNS_MAP)

#On définit les paramètre des loggers (fichier de sortie et format)
FORMAT = "%(levelname)s:[%(asctime)s]:%(name)s-%(lineno)s : %(msg)s"
LOGS_FILE = "logs.txt"
if not os.path.exists(LOGS_FILE):
    with open(LOGS_FILE, "x"):
        pass

DESCRIPTION = """Un programme de scraping internet : 
Un programme qui scrape le site 'cej.cj.gob.pe'(un site contenant des informations sur des procès)
"""



def main(mode="WARNING", logs_file=LOGS_FILE, save_file="result/output.xlxs"):
    # définit 
    global LOGS_FILE
    LOGS_FILE = logs_file
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "x"):
            pass
    
    logging.basicConfig(filename=LOGS_FILE, filemode="w", level=mode, format=FORMAT)
    
    saver = Saver(*os.path.split(save_file), COLUMNS_MAP)
    scraper.init()
    scraper.scrap(saver=saver)
    

def get_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-o", "--output", type=str, default="result/output.xlxs", help="Le fichier de sortie du document")
    
    #parser.add_argument("-m", "--mode", type=str, default="WARNING", choices=logging.getLevelNamesMapping().keys(), help="Le niveau a partir duquel les messages vont être loggés")
    parser.add_argument("-m", "--mode", default="WARNING", help="Le niveau a partir duquel les messages vont être loggés")
    
    parser.add_argument("--logs-file", type=str, default=LOGS_FILE, help="Le fichier dans lequel vont être écrits les logs")
    
    
    return parser.parse_args()

if __name__ == "__main__":
    namespace = get_args()
    mode = namespace.mode
    logs_file = namespace.logs_file
    
    main(mode=mode, logs_file=logs_file)