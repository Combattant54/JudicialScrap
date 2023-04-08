import json
import sqlite3
from bs4 import BeautifulSoup

import requests
from saver import Saver
import os, logging
import math



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def int_to_bytes(i: int, length:int =1) -> bytes:
    b = i.to_bytes(length=length)
    return b
def bytes_to_int(s:str) -> int:
    i = int.from_bytes(s)
    return i

class SQLSaver(Saver):
    DB_FOLDER = "result"
    def __init__(self, name: str, folders, columns_map={}) -> None:
        super().__init__(name, folders, columns_map)
        self.db_folder = os.path.join(folders)
        
        if not name.endswith(".db"):
            name = name + ".db"
        
        self.name = name
        self.path = os.path.join(self.db_folder, self.name)
        self.conn = self.get_conn(force=True)
        
    def get_conn(self, force=False):
        # La connection existe déja et une nouvelle n'est pas demandée
        if (not force) and (self.conn is not None):
            return self.conn
        
        #cré une nouvelle connection
        try:
            self.conn = sqlite3.connect(self.path)
        except Exception as e:
            logger.exception("Error in getting connection, force = " + str(force))
        
        return self.conn

    def execute(self, command, params_tuple=(), many=False, force_new=False):
        params_tuple = tuple(params_tuple)
        conn = self.get_conn(force=force_new)
        r = None
        
        logger.info(f"executing {command} for {len(params_tuple)} args and force_new of {force_new} and many of {many}")
        logger.debug(str(params_tuple))
        
        try:
            if not many:
                r = conn.execute(command, params_tuple)
            else:
                r = conn.executemany(command, params_tuple)
        except sqlite3.ProgrammingError as e:
            conn.rollback()
            if "Cannot operate on a closed database." in str(e):
                r = self.execute(command, params_tuple, many, force_new=True)
            else:
                raise e
        except Exception as e:
            conn.rollback()
            logger.exception("Unhandled error in execute for " + command + " with parameters " + str(params_tuple))
        return r
        
    def get_int_from_combinaison(self, specialized_map: dict[int, bool]):
        # Récupère les spécialités
        c = """SELECT * FROM Specialized ORDER BY id"""
        result = self.execute(c).fetchall()
        bool_table = {}

        # Itère dans les valeurs récupérées pour celles du dictionnaire
        # Les données sont stockées sous le format
        # 00010100 (exemple sans sens)
        # Qui signifirait que la 4ème et la 6ème valeurs sont True
        # Soit un dictionnaire comme {'4':True, '6':True}
        for element in result:
            i = element[0]
            id = element[1]
            
            bool_table[i] = specialized_map.get(str(id), False)
        
        # GLOBALEMENT :
        # 
        # transforme la table avec les boolens en integer pour etre transformer en int
        # 
        # EXPLICATION DU PROCESSUS :
        # 
        # la 3ème valeur est sur le troisième bit encodant la valeur 2^(3-1) soit 2^2 soit 4
        # En effet 0010 est bien 4 avec la 3ème valeur en 1 donc true
        # Ce qui donne un int (pour le dictionnaire {'4':True, '6':True}) égal à 2^(4-1) + 2^(6-1)
        # Soit 2^3 + 2^5 = 8 + 32 = 40
        # Soit 0001 0000 + 0000 0100 = 0001 0100 ont a bien la 4ème et la 6ème valeur qui valent 1 (True)
        # La valeur 40 est donc retournée pour etre stockée 
        current = 0
        i = 0
        for id, bool in bool_table.items():
            if bool:
                i += 2**current
            current += 1        
        return i

    def get_combinaison_from_int(self, value):
        # Récupère les spécialités
        c = """SELECT * FROM Specialized ORDER BY id"""
        result = self.execute(c).fetchall()
        
        # GOLBALEMENT:
        #
        # transforme l'integer donné en dictionnaire de booleens (fait l'inverse de la méthode 'get_int_from_combinaison')
        # les données sont structurées de la forme 0001 0100 (soit 40) pour un dictionnaire {'4':True, '6':True}
        # 
        # EXPLICATIONS DU PROCESSUS:
        #
        # Itère dans les indexs de la longueur du résultat (ex: 7 spécialités) mais en arrière
        # Ce qui donne un ordre d'appel du plus grand au plus petit ex: 7, 6, 5, 4, 3, 2, 1, 0
        # L'ordre décroissant des index parmet de traiter les grand nombres en premier
        # En effet, 16 qui correspond a 0001 0000 est >= à 1(2^0), 2(2^1), 4(2^2), 8(2^3) et 16(2^4)
        # Pour trouver la valeur initiale, il faut donc commencer par la fin et on tombe bien sur 4 (2^4 = 16)
        # Donc la 4ème valeur était True et il suffit de regarder dans la liste des spécialités dans l'ordre pour la retrouver
         
        bool_table = {}
        current = len(result) - 1
        for i in range(current, 0, -1):
            print(current, i, value, 2**i)
            if 2**i <= value:
                value -= 2**i
                bool_table[i] = True
            else:
                bool_table[i] = False
        
        return bool_table
    
    def create_tables(self, bytes_amount=1):
        c = """CREATE TABLE IF NOT EXISTS Districts (
            id integer PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
        
        c = """CREATE TABLE IF NOT EXISTS Instances (
            id integer PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
                
        c = """CREATE TABLE IF NOT EXISTS Specialized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
        
        c = f"""CREATE TABLE IF NOT EXISTS SpecializedRecords (
            id integer PRIMARY KEY AUTOINCREMENT,
            district smallint NOT NULL,
            instance smallint NOT NULL,
            val bit({bytes_amount}) NOT NULL
        )"""
        self.execute(c)
    
    def get_filtrer(self, json_data_filter_path="data.json"):
        self.create_tables()
        
        with open(json_data_filter_path, "r") as f:
            data = json.loads(f.read())
        assert isinstance(data, dict)
        
        
        districts = data.get("id_name_districts", {})
        
        check  = """SELECT id, name, val FROM Districts WHERE name IN ("""
        added_check =  "?, " * len(districts)
        added_check = added_check[:-2] + ")"
        check += added_check
        
        result = self.execute(check, params_tuple=(v for v in districts.values()))
        add_districts = []
        update_districts = []
        
        # récupère les district déja présent pour ne pas faire de key error sur ceux-ci en essayant de les ajouter
        for id, name, val, *rest in result.fetchall():
            print((id, name, val, *rest))
            if name in districts.values():
                update_districts.append(id)
        
        
        # Séléctionne les districts pas présents et les ajoute
        for k, v in districts.items():
            if not k in districts.values():
                add_districts.append((k, v))
        
        c = """INSERT INTO Districts (val, name) VALUES (?, ?)"""
        self.execute(c, add_districts, many=True)
        
        
        # récupère le dictionnaire contenant toutes les régions avec leur nom (en value) et leur code (en key)
        c = "INSERT INTO Instances (name, val) VALUES (?, ?)"
        instances_dict = data.get("id_instancias_dict", {})
        
        logger.info("instances_dict = " + str(instances_dict))

        self.execute(c, instances_dict.items(), many=True)
        
        specialized_dict = {}
        specialized = data.get("specialized_dict_list", [])
        for spec in specialized:
            for k, v in spec.items():
                if k in specialized_dict:
                    continue
                specialized_dict[k] = v
        
        
        # trie les spécialités 
        specialized_params_tuple = [( str(k), str(specialized_dict[k]) ) for k in sorted(specialized_dict.keys())]
        
        c = """INSERT INTO Specialized (val, name) VALUES (?, ?)"""
        self.execute(c, specialized_params_tuple, many=True)
        self.commit()
        
        bytes_amount = math.ceil(len(specialized_params_tuple)/8)
        
        params_tuple = []
        tuple_id_specialized = data.get("tuple_id_specialized_dict")
        for district in districts.keys():
            for instance in instances_dict.keys():
                # Récupère les valeurs associées
                index = tuple_id_specialized[f"{district}-{instance}"]
                spec = specialized[index]
                
                # Crée la table des boolens avec spécialités
                bool_table = {k:True for k in spec.keys()}
                
                # récupère la valeur pour la table fournie
                i = self.get_int_from_combinaison(bool_table)
                logger.warning(f"index : {index} and int_value : {i}")
                
                # Ajoute la valeur dans la liste qui sera utilisée par executemany
                params_tuple.append((district, instance, i))
        c = """INSERT INTO SpecializedRecords (district, instance, val) VALUES (?, ?, ?)"""
        self.execute(c, params_tuple, many=True)
        
        
        self.commit()
    
    def get_categories(self, page: requests.Response):
        soup = BeautifulSoup(page.text, "html.parser")
            
    def commit(self, msg=""):
        conn = self.get_conn()
        if not msg:
            msg = conn.total_changes
        if conn.total_changes > 0:
            conn.commit()
            logger.debug("Commiting for : " + str(msg))

def test():
    saver = SQLSaver("db", "result")
    c = "SELECT id, val FROM SpecializedRecords"
    result = saver.execute(c).fetchmany(5)
    
    saver.get_filtrer()
        

LOGS_FILE = "logs.txt"
if __name__ == "__main__":
    FORMAT = "%(levelname)s:[%(asctime)s]:%(name)s-%(lineno)s : %(msg)s"
    
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "x"):
            pass
    
    logging.basicConfig(filename=LOGS_FILE, filemode="w", level=logging.DEBUG, format=FORMAT)
    
    test()
    exit(1)
    saver = SQLSaver("db", "result")
    saver.get_filtrer()