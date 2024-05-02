from openpyxl import Workbook
from openpyxl.cell import Cell
import os
import logging
logger = logging.getLogger(__name__)
import sql_saver, models
from datetime import date
import json
import asyncio
import sys
import threading

from letters_ops import num_to_letters
from xlsxwriter.utility import xl_col_to_name

get_all_query = """SELECT * FROM Records
WHERE 
    year = ? AND
    district_id = ? AND
    instance_id = ? AND
    specialized_id = ?
ORDER BY 
    year ASC, 
    district_id ASC, 
    instance_id ASC, 
    specialized_id ASC, 
    n_expediente ASC, 
    juzgado_id ASC, 
    materias_id ASC, 
    fecha_ignicio
"""

select_max_amount = """SELECT """
SAVER_PARTES_TYPE = 0

NO_PERSONNS_AMOUNT = 16
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
    "P": "DESCARGAR",
}
demandados = [
]

demandantes = [
]

agraviados = [
]

MAX_PERS_YEARS = 8
if SAVER_PARTES_TYPE == 1:
    for i in range(MAX_PERS_YEARS):
        current_number = NO_PERSONNS_AMOUNT + i*4
        DATA_BASE[xl_col_to_name(current_number + 0)] = f"PERSONN {i + 1} (Partes)"
        DATA_BASE[xl_col_to_name(current_number + 1)] = f"PERSONN {i + 1} (Tipo de Persona)"
        DATA_BASE[xl_col_to_name(current_number + 2)] = f"PERSONN {i + 1} (Apellido Paterno + Apellido Materno)"
        DATA_BASE[xl_col_to_name(current_number + 3)] = f"PERSONN {i + 1} (Nombres)"
elif SAVER_PARTES_TYPE == 0:
    for i in range(len(demandados) // 3):
        DATA_BASE[demandados[i*3]] = f"DEMANDADOS {i + 1} (Tipo de Persona)"
        DATA_BASE[demandados[i*3 + 1]] = f"DEMANDADOS {i + 1} (Apellido Paterno + Apellido Materno)"
        DATA_BASE[demandados[i*3 + 2]] = f"DEMANDADOS {i + 1} (Nombres)"
    for i in range(len(demandantes) // 3):
        DATA_BASE[demandantes[i*3]] = f"DEMANDANTES {i + 1} (Tipo de Persona)"
        DATA_BASE[demandantes[i*3 + 1]] = f"DEMANDANTES {i + 1} (Apellido Paterno + Apellido Materno)"
        DATA_BASE[demandantes[i*3 + 2]] = f"DEMANDANTES {i + 1} (Nombres)"
    for i in range(len(agraviados) // 3):
        DATA_BASE[agraviados[i*3]] = f"AGRAVIADOS {i + 1} (Tipo de Persona)"
        DATA_BASE[agraviados[i*3 + 1]] = f"AGRAVIADOS {i + 1} (Apellido Paterno + Apellido Materno)"
        DATA_BASE[agraviados[i*3 + 2]] = f"AGRAVIADOS {i + 1} (Nombres)"

demandados_aliases = [
    "DENUNCIADO"
]

DATA_MAPPING = {}

current_line = 1

DB_PATH = None
TARGET_PATH = None
today = date.today()

with open("result/data.json", "r") as f:
    DATA = json.load(f)

YEARS = set(range(1977, today.year))
DISTRICTS = set(DATA["id_name_districts"].keys())
INSTANCES = set(DATA["id_instancias_dict"].keys())
SPECIALIZED = set()
for d in DATA["specialized_dict_list"]:
    SPECIALIZED.update([k for k in d.keys()])
    
YEARS = {2018}
# DISTRICTS = {"AMAZONAS"}
SPECIALIZED = {"FAMILIA CIVIL"}
INSTANCES = {
    # "JUZGADO DE PAZ LETRADO",
    "JUZGADO ESPECIALIZADO", 
    # "JUZGADO MIXTO", 
    # "SALA SUPERIOR"
}

print(YEARS)
print(DISTRICTS)
print(INSTANCES)
print(SPECIALIZED)

active_saver = None

def init(path, save_dir):
    global DB_PATH
    global TARGET_PATH
    global SAVE_DIR
    global active_saver
    
    name, ext = os.path.splitext(path)
    if not ext:
        ext = ".db"
    
    DB_PATH = name + ext
    TARGET_PATH = name + ".xlsx"
    SAVE_DIR = str(save_dir)
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    logger.info(DB_PATH)
    logger.info(TARGET_PATH)

def fill_0(number, number_of_zeros):
    string = str(number)
    string = "0" * (number_of_zeros - len(string)) + string
    return string

def get_file_path(year, district, instance, specialized):
    year = str(year).lower()
    district = str(district).lower().replace(" - ", "_").replace(" ", "_")
    specialized = str(specialized).lower().replace(" - ", "_").replace(" ", "_")
    instance = str(instance).lower().replace(" - ", "_").replace(" ", "_")
    filename = f"{year}_{district}_{specialized}_{instance}.xlsx"
    
    directory = os.path.join(SAVE_DIR, year)
    if not os.path.exists(directory):
        os.makedirs(directory)
    path = os.path.join(directory, filename)
    
    return path
    

district_id = 1
instance_id = 1
specialized_id = 1

test_command = "SELECT * FROM sqlite_master WHERE type='table'"

command = """SELECT * FROM records
WHERE
	year = ? AND
	specialized_id = ? AND
	instance_id = ?
ORDER BY n_expediente ASC
"""

async def load_saver(db_filename) -> sql_saver.SQLSaver:
    folder, filename = os.path.split(DB_PATH)
    active_saver = sql_saver.SQLSaver(db_filename, folder)
    with active_saver.DBLock:
        await active_saver.create_tables()

async def year_to_excel(year, district_arg:str ="", instance_arg: str ="", specialized_arg: str =""):
    saver = await load_saver(f"db_{year}.db")
    initialize(saver)
    
    if district_arg == "ALL" or district_arg == "":
        districts = list(map(lambda x: x.id, saver.Districts.get_all()))
    elif "-" in district_arg:
        districts = range(*map(lambda x: saver.Districts.get_by(name=x.upper()).id, district_arg.split("-")))
        districts.stop += 1
        districts = list(districts)
    elif ";" in district_arg:
        districts = list(map(lambda x: saver.Districts.get_by(name=x.upper()).id, district_arg.split(";")))
    else:
        districts = [saver.Districts.get_by(name=district_arg).id]
        
    
    if instance_arg == "ALL" or instance_arg == "":
        instances = list(map(lambda x: x.id, saver.Instances.get_all()))
    elif "-" in instance_arg:
        instances = range(*map(lambda x: saver.Instances.get_by(name=x.upper()).id, instance_arg.split("-")))
        instances.stop += 1
        instances = list(instances)
    elif ";" in instance_arg:
        instances = list(map(lambda x: saver.Instances.get_by(name=x.upper()).id, instance_arg.split(";")))
    else:
        instances = [saver.Instances.get_by(name=instance_arg).id]
        
    if specialized_arg == "ALL" or specialized_arg == "":
        specialized = list(map(lambda x: x.id, saver.Specialized.get_all()))
    elif "-" in specialized_arg:
        specialized = range(*map(lambda x: saver.Specialized.get_by(name=x.upper()).id, specialized_arg.split("-")))
        specialized.stop += 1
        specialized = list(specialized)
    elif ";" in specialized_arg:
        specialized = list(map(lambda x: saver.Specialized.get_by(name=x.upper()).id, specialized_arg.split(";")))
    else:
        specialized = [saver.Specialized.get_by(name=specialized_arg).id]
        
    for district_id in districts:
        for instance_id in instances:
            for specialized_id in specialized:
                to_excel(saver, year, district_id, instance_id, specialized_id)
                

def initialize(saver: sql_saver.SQLSaver) -> None:
    print("initalization")
    demandados_id = saver.Partes.get_by(name="DEMANDADO").id
    demandados_al = []
    for aliase in demandados_aliases:
        partes =  saver.Partes.get_by(name=aliase)
        demandados_al.append(partes.id)
    params = {demandados_id: tuple(demandados_al)}
    print(params)
    print(tuple(params.items()))
    
    for k, v in params.items():
        active_saver.db.execute(
            models.search_max_table_initating.format(",".join(map(str, v))), 
            [k]
        )

def to_excel(saver:sql_saver.SQLSaver, year, district_id, instance_id, specialized_id):
    print(year, district_id, instance_id, specialized_id)
    
    wb = Workbook()
    active_page = wb.active
    
    current_line = 1
    for k, v in DATA_BASE.items():
        active_page[f"{k}{current_line}"] = v
    
    col_offset = len(DATA_BASE)
    print(col_offset)
    
    current_line += 1
    cursor = saver.db.execute(get_all_query, (year, district_id, instance_id, specialized_id))
    record_tuple = cursor.fetchone()
    print("first_fetched")
    while record_tuple:
        record = saver.Records.get_by(id=record_tuple[0])
        assert isinstance(record, saver.Records)
        
        #saut de ligne a chaque n_expediente
        # if last_n_expediente != record.n_expediente:
        #     current_line += 1
        # last_n_expediente = record.n_expediente
        
        n_expediente = fill_0(record.n_expediente, 5)
        year = record.year
        digit_1 = fill_0(record.digit_1, 1)
        digit_2 = fill_0(record.digit_2, 4)
        code_1 = record.instance_code
        code_2 = record.specialized_code
        last_digit = fill_0(record.last_digit, 2)
        trial_ID = f"{n_expediente}-{year}-{digit_1}-{digit_2}-{code_1}-{code_2}-{last_digit}"
        
        fecha_ignicio = record.fecha_ignicio
        descargar = record.descargar == 1
        
        district = saver.Districts.get_by(id=record.district_id)
        active_page[f"A{current_line}"] = str(district.name).capitalize()
        
        instance = saver.Instances.get_by(id=record.instance_id)
        active_page[f"B{current_line}"] = str(instance.name).capitalize()
        
        specialized = saver.Specialized.get_by(id=record.specialized_id)
        active_page[f"C{current_line}"] = str(specialized.name).capitalize()
        
        active_page[f"D{current_line}"] = year
        active_page[f"E{current_line}"] = int(n_expediente)
        active_page[f"F{current_line}"] = trial_ID
        
        juzgado = saver.Juzgado.get_by(id=record.juzgado_id)
        juzgado_val = str(juzgado.value)
        # if juzgado_val.startswith("1º"):
        #     juzgado_val = juzgado_val[len("1º"):]
        # juzgado_val = juzgado_val.strip()
        active_page[f"G{current_line}"] = juzgado_val
        
        juez = saver.Personns.get_by(id=record.juez_id)
        active_page[f"H{current_line}"] = juez.name
        
        active_page[f"I{current_line}"] = fecha_ignicio
        
        conclusion = saver.Fecha_conclusion.get_by(id=record.conclusion_id)
        active_page[f"J{current_line}"] = conclusion.value
        
        materias = saver.Materias.get_by(id=record.materias_id)
        active_page[f"K{current_line}"] = materias.value
        
        summilla = saver.Summilla.get_by(id=record.summilla_id)
        active_page[f"L{current_line}"] = summilla.value
        
        especialista_legal = saver.Personns.get_by(id=record.especialista_legal_id)
        active_page[f"M{current_line}"] = especialista_legal.name
        
        proceso = saver.Proceso.get_by(id=record.proceso_id)
        active_page[f"N{current_line}"] = proceso.value
        
        estado = saver.Estado.get_by(id=record.estado_id)
        active_page[f"O{current_line}"] = estado.value
        
        active_page[f"P{current_line}"] = 1 if descargar else 0
        
        # récupère les personnes
        personns_records = saver.PersonnRecord.get_all(record_id=record.id)
        personns_records.sort(key = lambda pers: pers.partes_id)
        if current_line % 500 == 0:
            print("starting getting personnes on line " + str(current_line))
        
        for i, personn_record in enumerate(personns_records):
            col_number = col_offset + i*4
            partes = sql_saver.Partes.get_by(id=personn_record.partes_id)
            personn = sql_saver.Personns.get_by(id=personn_record.personn_id)
            active_page[f"{xl_col_to_name(col_number + 0)}{current_line}"] = str(partes.name).strip()
            active_page[f"{xl_col_to_name(col_number + 1)}{current_line}"] = str(saver.PersonnType.get_by(id=personn.type).value).strip()
            active_page[f"{xl_col_to_name(col_number + 2)}{current_line}"] = str(personn.appelido_paterno + " " + personn.appelido_materno).strip()
            active_page[f"{xl_col_to_name(col_number + 3)}{current_line}"] = str(personn.nombres).strip()
        
        current_line += 1
        record_tuple = cursor.fetchone()
    
    district_name = saver.Districts.get_by(id=district_id)
    instance_name = saver.Instances.get_by(id=instance_id)
    specialized_name = saver.Specialized.get_by(id=specialized_id)
    save_path = get_file_path(year, district_name, instance_name, specialized_name)
    wb.save(save_path)
    wb.close()
    print("file saved at " + save_path)

def main(db_path, save_dir, year, district, instance, specialized):
    init(db_path, save_dir)
    
    years = []
    if "-" in year:
        years = range(*map(int, year.split("-")))
    elif ";" in year:
        years = map(int, year.split(";"))
    else:
        years = [int(year)]
    
    threads = []
    for year in years:
        t = threading.Thread(target=asyncio.run, args=(year_to_excel(year, district_id, instance_id, specialized_id)))
        t.start()
        threads.append(t)

if __name__ == "__main__":
    args = sys.argv[1:]
    year = int(args[0])
    district_id = int(args[1])
    instance_id = int(args[2])
    specialized_id = int(args[3])
    
    db_path = "result/db_{}.db"
    save_dir = "result/DATA/excel files"
    main(db_path, save_dir, args)
    