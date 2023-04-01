import json
import sqlite3
from bs4 import BeautifulSoup

import requests
from saver import Saver
import os, logging
import math

logger = logging.getLogger(__name__)
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
        if not force and self.conn is not None:
            return self.conn
            
        try:
            self.conn = sqlite3.connect(self.path)
        except Exception as e:
            logger.exception("Error in getting connection, force = " + str(force))
        
        return self.conn

    def execute(self, command, params_tuple=(), many=False, force_new=False):
        conn = self.get_conn(force=force_new)
        r = None
        
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
        c = """SELECT * FROM Specialized ORDER BY id"""
        result = self.execute(c).fetchall()
        bool_table = {}
        print(result)
        for r in result:
            i = r[0]
            id = r[1]
            if (str(id) in specialized_map) and (specialized_map[str(id)] == True):
                bool_table[i] = True
            else:
                bool_table[i] = False
        
        current = 0
        i = 0
        for id, bool in bool_table.items():
            if bool:
                i += 2**current
            current += 1
            print(current, i)
        
        return i

    def get_combinaison_from_int(self, value):
        c = """SELECT * FROM Specialized ORDER BY id"""
        result = self.execute(c).fetchall()
        
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
                
    
    def get_filtrer(self, json_data_filter_path="data.json"):
        with open(json_data_filter_path, "r") as f:
            data = json.loads(f.read())
        assert isinstance(data, dict)
        
        c = """CREATE TABLE IF NOT EXISTS Districts (
            id integer PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        
        self.execute(c)
        
        c = """INSERT INTO Districts (val, name) VALUES (?, ?)"""
        districts = data.get("id_name_districts", {})
        self.execute(c, districts.items(), many=True)
        
        c = """CREATE TABLE IF NOT EXISTS Instances (
            id integer PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
        
        c = """INSERT INTO Instances (val, name) VALUES (?, ?)"""
        # récupère le dictionnaire contenant toutes les régions avec leur code (en key) et leur nom (en value)
        instances_dict = next(iter(data.get("id_instancias_dict", {}).values()))
        logger.info("instances_dict = " + str(instances_dict))
        self.execute(c, instances_dict.items(), many=True)
        
        c = """CREATE TABLE IF NOT EXISTS Specialized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            val TEXT UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
        
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
        
        c = f"""CREATE TABLE IF NOT EXISTS SpecializedRecords (
            id integer PRIMARY KEY AUTOINCREMENT,
            district smallint NOT NULL,
            instance smallint NOT NULL,
            val bit({bytes_amount}) NOT NULL
        )"""
        self.execute(c)
        
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
    print("\n"*2)
    for id, val in result:
        print(id, val, saver.get_combinaison_from_int(val))
        print("\n")
        

if __name__ == "__main__":
    test()
    exit(1)
    saver = SQLSaver("db", "result")
    saver.get_filtrer()