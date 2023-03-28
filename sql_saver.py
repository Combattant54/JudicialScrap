import json
import sqlite3
from bs4 import BeautifulSoup

import requests
from saver import Saver
import os, logging

logger = logging.getLogger(__name__)

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
        
        try:
            if not many:
                r = conn.execute(command, params_tuple)
            else:
                r = conn.executemany(command, params_tuple)
        except sqlite3.ProgrammingError as e:
            conn.rollback()
            if "Cannot operate on a closed database." in str(e):
                self.execute(command, params_tuple, many, force_new=True)
            else:
                raise e
        except Exception as e:
            conn.rollback()
            logger.exception("Unhandled error in execute for " + command + " with parameters " + str(params_tuple))
    
    def get_filtrer(self, json_data_filter_path="data.json"):
        with open(json_data_filter_path, "r") as f:
            data = json.loads(f.read())
        
        c = """CREATE TABLE IF NOT EXISTS Districts (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )"""
        
        self.execute(c)
        
        c = """INSERT INTO Districts (id, name) VALUES (?, ?)"""
        self.execute(c, data.get("id_name_districts", {}).items(), many=True)
        
        c = """CREATE TABLE IF NOT EXISTS Instances (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )"""
        self.execute(c)
        
        c = """INSERT INTO Instances (id, name) VALUES (?, ?)"""
        instances_dict = next(iter(data.get("id_instancias_dict", {}).values()))
        logger.info("instances_dict = " + str(instances_dict))
        self.execute(c, instances_dict.items(), many=True)
        
        
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

if __name__ == "__main__":
    saver = SQLSaver("db", "result")
    saver.get_filtrer()