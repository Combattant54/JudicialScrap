from openpyxl import Workbook
from openpyxl.cell import Cell
import os
import logging
logger = logging.getLogger(__name__)
import sql_saver
from datetime import date
import json
import sqliteORM

get_all_query = """SELECT * FROM Records
ORDER BY year, district_id, instance_id, specialized_id, n_expediente, juzgado_id, materias_id, fecha_ignicio
"""

DATA_BASE = {
    "A": "Distrito Judicial",
    "B": "Instancia",
    "C": "Especialidad",
    "D": "Año",
    "E": "N expediente",
    "F": "trial ID", 
    "G": "Juzgado", 
    "H": "Juez",
    "I": "Fecha de Inicio",
    "J": "Fecha Conclusión",
    "K": "Materia(s)",
    "L": "Sumilla",
    "M": "Especialista legal",
    "N": "Proceso",
    "O": "Estado",
    "P": "DEMANDADO (Tipo de Persona)",
    "Q": "DEMANDADO (Apellido Paterno + Apellido Materno)",
    "R": "DEMANDADO (Nombres)",
    "S": "DEMANDANTE (Tipo de Persona)",
    "T": "DEMANDANTE (Apellido Paterno + Apellido Materno)",
    "U": "DEMANDANTE (Nombres)",
    "V": "AGRAVIADO (Tipo de Persona)",
    "w": "AGRAVIADO (Apellido Paterno + Apellido Materno)",
    "X": "AGRAVIADO (Nombres)",
    "Y": "DESCARGAR",
}

DATA_MAPPING = {}

current_line = 1

DB_PATH = None
TARGET_PATH = None
today = date.today()

with open("data.json", "r") as f:
    DATA = json.load(f)

YEARS = set(range(1977, today.year))
DISTRICTS = set(DATA["id_name_districts"].keys())
INSTANCES = set(DATA["id_instancias_dict"].keys())
SPECIALIZED = {(k for k in d.keys()) for d in DATA["specialized_dict_list"]}
print(YEARS)
print(DISTRICTS)
print(INSTANCES)
print(SPECIALIZED)

YEARS = {2015}
DISTRICTS = {"AMAZONAS"}
SPECIALIZED = {"FAMILIA CIVIL", "FAMILIA TUTELAR"}

def init(path, saver: sql_saver.SQLSaver =None):
    global DB_PATH
    global TARGET_PATH
    global wb
    global active_page
    
    name, ext = os.path.splitext(path)
    if not ext:
        ext = "db"
    
    DB_PATH = name + "." + ext
    TARGET_PATH = name + ".xlsx"
    logger.log(DB_PATH, TARGET_PATH)
    
    if saver is None:
        saver = sql_saver.SQLSaver(*os.path.split(DB_PATH))
    
    wb = Workbook()
    active_page = wb.active
    
    for k, v in DATA_BASE.items():
        active_page[f"{k}{current_line}"] = v
    current_line += 1

def fill_0(number, number_of_zeros):
    string = str(number)
    string = "0" * (number_of_zeros - len(number)) + string

def to_excel():
    for record in sql_saver.Records.iter_rows():
        assert isinstance(record, sql_saver.Record)
        
        district = record()
        
        n_expediente = fill_0(record.n_expediente, 5)
        year = record.year
        digit_1 = fill_0(record.digit_1, 1)
        digit_2 = fill_0(record.digit_2, 2)
        code_1 = record.instance_code
        code_2 = record.specialized_code
        last_digit = fill_0(record.last_digit, 2)
        trial_ID = f"{n_expediente}-{year}-{digit_1}-{digit_2}-{code_1}-{code_2}-{last_digit}"
        