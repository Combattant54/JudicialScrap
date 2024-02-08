from openpyxl import Workbook
from openpyxl.cell import Cell
import os
import logging
logger = logging.getLogger(__name__)
import sql_saver
from datetime import date
import json
import asyncio
import sys

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
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "AA",
    "AB",
    "AC",
    "AD",
    "AE",
    "AF",
    "AG",
    "AH"
]

demandantes = [
    "AI",
    "AJ",
    "AK",
    "AL",
    "AM",
    "AN",
    "AO",
    "AP",
    "AQ",
    "AR",
    "AS",
    "AT"
]

agraviados = [
    "AU",
    "AV",
    "AW",
    "AX",
    "AY",
    "AZ",
    "BA",
    "BB",
    "BC"
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
    "DEMANDADO",
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
SPECIALIZED = set(((k) for k in d.keys()) for d in DATA["specialized_dict_list"])
print(YEARS)
print(DISTRICTS)
print(INSTANCES)
print(SPECIALIZED)

YEARS = {2018}
DISTRICTS = {"AMAZONAS"}
SPECIALIZED = {"FAMILIA CIVIL"}
INSTANCES = {
    "JUZGADO DE PAZ LETRADO",
    # "JUZGADO ESPECIALIZADO", 
    # "JUZGADO MIXTO", 
    # "SALA SUPERIOR"
}
active_saver = None

async def init(path, saver: sql_saver.SQLSaver =None):
    global DB_PATH
    global TARGET_PATH
    global wb
    global active_page
    global current_line
    global active_saver
    
    name, ext = os.path.splitext(path)
    if not ext:
        ext = ".db"
    
    DB_PATH = name + ext
    TARGET_PATH = name + ".xlsx"
    logger.info(DB_PATH)
    logger.info(TARGET_PATH)
    
    if saver is None:
        folder, filename = os.path.split(DB_PATH)
        active_saver = sql_saver.SQLSaver(filename, folder)
        await active_saver.create_tables()
    else:
        active_saver = saver
    
    wb = Workbook()
    active_page = wb.active
    
    for k, v in DATA_BASE.items():
        active_page[f"{k}{current_line}"] = v
    current_line += 1

def fill_0(number, number_of_zeros):
    string = str(number)
    string = "0" * (number_of_zeros - len(string)) + string
    return string

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
def to_excel(save_path: str):
    global current_line
    district_id = sql_saver.Districts.get_by(name=DISTRICTS.pop()).id
    instance_id = sql_saver.Instances.get_by(name=INSTANCES.pop()).id
    specialized_id = sql_saver.Specialized.get_by(name=SPECIALIZED.pop()).id
    cursor = active_saver.db.execute(get_all_query, (YEARS.pop(), district_id, instance_id, specialized_id))
    last_n_expediente = 1
    for record_tuple in cursor.fetchall():
        record = sql_saver.Records.get_by(id=record_tuple[0])
        assert isinstance(record, sql_saver.Records)
        
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
        
        district = sql_saver.Districts.get_by(id=record.district_id)
        active_page[f"A{current_line}"] = str(district.name).capitalize()
        
        instance = sql_saver.Instances.get_by(id=record.instance_id)
        active_page[f"B{current_line}"] = str(instance.name).capitalize()
        
        specialized = sql_saver.Specialized.get_by(id=record.specialized_id)
        active_page[f"C{current_line}"] = str(specialized.name).capitalize()
        
        active_page[f"D{current_line}"] = year
        active_page[f"E{current_line}"] = int(n_expediente)
        active_page[f"F{current_line}"] = trial_ID
        
        juzgado = sql_saver.Juzgado.get_by(id=record.juzgado_id)
        juzgado_val = str(juzgado.value)
        # if juzgado_val.startswith("1º"):
        #     juzgado_val = juzgado_val[len("1º"):]
        # juzgado_val = juzgado_val.strip()
        active_page[f"G{current_line}"] = juzgado_val
        
        juez = sql_saver.Personns.get_by(id=record.juez_id)
        active_page[f"H{current_line}"] = juez.name
        
        active_page[f"I{current_line}"] = fecha_ignicio
        
        conclusion = sql_saver.Fecha_conclusion.get_by(id=record.conclusion_id)
        active_page[f"J{current_line}"] = conclusion.value
        
        materias = sql_saver.Materias.get_by(id=record.materias_id)
        active_page[f"K{current_line}"] = materias.value
        
        summilla = sql_saver.Summilla.get_by(id=record.summilla_id)
        active_page[f"L{current_line}"] = summilla.value
        
        especialista_legal = sql_saver.Personns.get_by(id=record.especialista_legal_id)
        active_page[f"M{current_line}"] = especialista_legal.name
        
        proceso = sql_saver.Proceso.get_by(id=record.proceso_id)
        active_page[f"N{current_line}"] = proceso.value
        
        estado = sql_saver.Estado.get_by(id=record.estado_id)
        active_page[f"O{current_line}"] = estado.value
        
        active_page[f"P{current_line}"] = 1 if descargar else 0
        
        # récupère les personnes
        personns_records = sql_saver.PersonnRecord.get_all(record_id=record.id)
        personns_records.sort(key = lambda pers: pers.partes_id)
        demandados_pers, demandantes_pers, agraviados_pers = [], [], []
        for i, personn_record in enumerate(personns_records):
            col_number = NO_PERSONNS_AMOUNT + i*4
            partes = sql_saver.Partes.get_by(id=personn_record.partes_id)
            personn = sql_saver.Personns.get_by(id=personn_record.personn_id)
            if SAVER_PARTES_TYPE == 0:
                partes_name = str(partes.name).strip().upper()
                if partes_name in demandados_aliases:
                    demandados_pers.append(personn)
                elif partes_name == "DEMANDANTE":
                    demandantes_pers.append(personn)
                elif partes_name == "AGRAVIADO":
                    agraviados_pers.append(personn)
            elif SAVER_PARTES_TYPE == 1:
                active_page[f"{xl_col_to_name(col_number + 0)}{current_line}"] = str(partes.name).strip()
                active_page[f"{xl_col_to_name(col_number + 1)}{current_line}"] = str(sql_saver.PersonnType.get_by(id=personn.type).value).strip()
                active_page[f"{xl_col_to_name(col_number + 2)}{current_line}"] = str(personn.appelido_paterno + " " + personn.appelido_materno).strip()
                active_page[f"{xl_col_to_name(col_number + 3)}{current_line}"] = str(personn.nombres).strip()
        
        if SAVER_PARTES_TYPE == 0:
            for i, personn in enumerate(demandados_pers):
                active_page[f"{demandados[i*3]}{current_line}"] = str(sql_saver.PersonnType.get_by(id=personn.type).value).strip()
                active_page[f"{demandados[i*3+1]}{current_line}"] = str(personn.appelido_paterno + " " + personn.appelido_materno).strip()
                active_page[f"{demandados[i*3+2]}{current_line}"] = str(personn.nombres).strip()
            
            for i, personn in enumerate(demandantes_pers):
                active_page[f"{demandantes[i*3]}{current_line}"] = str(sql_saver.PersonnType.get_by(id=personn.type).value).strip()
                active_page[f"{demandantes[i*3+1]}{current_line}"] = str(personn.appelido_paterno + " " + personn.appelido_materno).strip()
                active_page[f"{demandantes[i*3+2]}{current_line}"] = str(personn.nombres).strip()
            
            for i, personn in enumerate(agraviados_pers):
                active_page[f"{agraviados[i*3]}{current_line}"] = str(sql_saver.PersonnType.get_by(id=personn.type).value).strip()
                active_page[f"{agraviados[i*3+1]}{current_line}"] = str(personn.appelido_paterno + " " + personn.appelido_materno).strip()
                active_page[f"{agraviados[i*3+2]}{current_line}"] = str(personn.nombres).strip()
                
        
        current_line += 1
    
    wb.save(save_path)
        
if __name__ == "__main__":
    
    db_path = "result/db.db"
    save_path = os.path.join("result", sys.argv[1])
    asyncio.run(init(db_path))
    to_excel(save_path)