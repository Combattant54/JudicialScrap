import json
import sqlite3
from typing import Iterable
from bs4 import BeautifulSoup

import asyncio
import requests
from saver import Saver
import os, logging
import math

from sqliteORM import db, rows
from sqliteORM.types import INTEGER, TEXT, BIT, DATE
import build_logger

logger = build_logger.get_logger(__name__)

PARTES = set()
DBLock = asyncio.Lock()

class Districts(db.DBTable):
    @classmethod
    def create(cls):
        Districts.add_row(rows.DBRow.build_id_row())
        Districts.add_row(rows.DBRow("value", TEXT(10), unique=True))
        Districts.add_row(rows.DBRow("name", TEXT(45), unique=True))

class Instances(db.DBTable):
    @classmethod
    def create(cls):
        Instances.add_row(rows.DBRow.build_id_row())
        Instances.add_row(rows.DBRow("value", TEXT(10), unique=True))
        Instances.add_row(rows.DBRow("name", TEXT(45), unique=True))

class Specialized(db.DBTable):
    @classmethod
    def create(cls):
        Specialized.add_row(rows.DBRow.build_id_row())
        Specialized.add_row(rows.DBRow("value", TEXT(10), unique=True))
        Specialized.add_row(rows.DBRow("name", TEXT(75), unique=True))

class SpecializedRecords(db.DBTable):
    @classmethod
    def create(cls):
        SpecializedRecords.add_row(rows.DBRow.build_id_row())
        SpecializedRecords.add_row(rows.DBRow("district", INTEGER, foreign_key=Districts.get_row("id")))
        SpecializedRecords.add_row(rows.DBRow("Specialized", INTEGER, foreign_key=Specialized.get_row("id")))
        SpecializedRecords.add_row(rows.DBRow("value", INTEGER))

class Juzgado(db.DBTable):
    @classmethod
    def create(cls):
        Juzgado.add_row(rows.DBRow.build_id_row())
        Juzgado.add_row(rows.DBRow("value", TEXT(80), unique=True))

class PersonnType(db.DBTable):
    @classmethod
    def create(cls):
        PersonnType.add_row(rows.DBRow.build_id_row())
        PersonnType.add_row(rows.DBRow("value", TEXT(50), unique=True))

class Personns(db.DBTable):
    @classmethod
    def create(cls):
        Personns.add_row(rows.DBRow.build_id_row())
        Personns.add_row(rows.DBRow("name", TEXT(300), unique=True))
        Personns.add_row(rows.DBRow("nombres", TEXT(70), nullable=True, default=None))
        Personns.add_row(rows.DBRow("appelido_paterno", TEXT(100), nullable=True, default=None))
        Personns.add_row(rows.DBRow("appelido_materno", TEXT(100), nullable=True, default=None))
        Personns.add_row(rows.DBRow("type", INTEGER, foreign_key=PersonnType.get_row("id"), nullable=True, default=None))

class Proceso(db.DBTable):
    @classmethod
    def create(cls):
        Proceso.add_row(rows.DBRow.build_id_row())
        Proceso.add_row(rows.DBRow("value", TEXT(30), unique=True))

class Estado(db.DBTable):
    @classmethod
    def create(cls):
        Estado.add_row(rows.DBRow.build_id_row())
        Estado.add_row(rows.DBRow("value", TEXT(60), unique=True))

class Materias(db.DBTable):
    @classmethod
    def create(cls):
        Materias.add_row(rows.DBRow.build_id_row())
        Materias.add_row(rows.DBRow("value", TEXT(75), unique=True))

class Summilla(db.DBTable):
    @classmethod
    def create(cls):
        Summilla.add_row(rows.DBRow.build_id_row())
        Summilla.add_row(rows.DBRow("value", TEXT(250), unique=True))
        
class Fecha_conclusion(db.DBTable):
    @classmethod
    def create(cls):
        Fecha_conclusion.add_row(rows.DBRow.build_id_row())
        Fecha_conclusion.add_row(rows.DBRow("value", TEXT(250), unique=True))

class Partes(db.DBTable):
    @classmethod
    def create(cls):
        Partes.add_row(rows.DBRow.build_id_row())
        Partes.add_row(rows.DBRow("name", TEXT(40), unique=True))


class Records(db.DBTable):
    @classmethod
    def create(cls):
        Records.add_row(rows.DBRow.build_id_row())
        Records.add_row(rows.DBRow("n_expediente", INTEGER, primary=True))
        Records.add_row(rows.DBRow("year", "smallint", primary=True))
        Records.add_row(rows.DBRow("digit_1", "tinyint", primary=True))
        Records.add_row(rows.DBRow("digit_2", "smallint", primary=True))
        Records.add_row(rows.DBRow("instance_code", TEXT(2), primary=True))
        Records.add_row(rows.DBRow("specialized_code", TEXT(2), primary=True))
        Records.add_row(rows.DBRow("last_digit", "tyniint", primary=True))
        Records.add_row(rows.DBRow("fecha_ignicio", DATE, nullable=False, primary=True))
        Records.add_row(rows.DBRow("descargar", BIT(1), default=0, primary=True))
        
        Records.add_row(rows.DBRow("district_id", INTEGER, foreign_key=Districts.get_row("id")))
        Records.add_row(rows.DBRow("instance_id", INTEGER, foreign_key=Instances.get_row("id")))
        Records.add_row(rows.DBRow("specialized_id", INTEGER, foreign_key=Specialized.get_row("id")))
        Records.add_row(rows.DBRow("juzgado_id", INTEGER, foreign_key=Juzgado.get_row("id")))
        Records.add_row(rows.DBRow("juez_id", INTEGER, nullable=False, foreign_key=Personns.get_row("id")))
        Records.add_row(rows.DBRow("conclusion_id", INTEGER, nullable=True, foreign_key=Fecha_conclusion.get_row("id")))
        Records.add_row(rows.DBRow("materias_id", INTEGER, nullable=True, foreign_key=Materias.get_row("id")))
        Records.add_row(rows.DBRow("summilla_id", INTEGER, nullable=True, foreign_key=Summilla.get_row("id")))
        Records.add_row(rows.DBRow("especialista_legal_id", INTEGER, nullable=False, foreign_key=Personns.get_row("id")))
        Records.add_row(rows.DBRow("estado_id", INTEGER, nullable=True, foreign_key=Estado.get_row("id")))
        Records.add_row(rows.DBRow("proceso_id", INTEGER, nullable=True, foreign_key=Proceso.get_row("id")))
        # Records.add_row(rows.DBRow("demando_id", INTEGER, nullable=True, foreign_key=Personns.get_row("id")))
        # Records.add_row(rows.DBRow("demandante_id", INTEGER, nullable=True, foreign_key=Personns.get_row("id")))
        # Records.add_row(rows.DBRow("agraviado_id", INTEGER, nullable=True, foreign_key=Personns.get_row("id")))
        
class PersonnRecord(db.DBTable):
    @classmethod
    def create(cls):
        PersonnRecord.add_row(rows.DBRow.build_id_row())
        PersonnRecord.add_row(rows.DBRow("personn_id", INTEGER, foreign_key=Personns.get_row("id")))
        PersonnRecord.add_row(rows.DBRow("record_id", INTEGER, foreign_key=Records.get_row("id")))
        PersonnRecord.add_row(rows.DBRow("partes_id", INTEGER, foreign_key=Partes.get_row("id")))

class Trial(db.DBTable):
    pass

def int_to_bytes(i: int, length:int =1) -> bytes:
    b = i.to_bytes(length=length)
    return b
def bytes_to_int(s:str) -> int:
    i = int.from_bytes(s)
    return i

class SQLSaver(Saver):
    DB_FOLDER = "result"
    def __init__(self, name: str, folders, columns_map={}, debug=True) -> None:
        super().__init__(name, folders, columns_map)
        self.db_folder = os.path.join(folders)
        
        if not name.endswith(".db"):
            name = name + ".db"
        
        self.name = name
        self.path = os.path.join(self.db_folder, self.name)
        self.db = db.DB(path=self.path, debug=debug)
        self.debug = debug
        
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
        logger.error("using get combinaison from int, not verified")
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
            if 2**i <= value:
                value -= 2**i
                bool_table[i] = True
            else:
                bool_table[i] = False
        
        return bool_table
    
    async def create_tables(self):
        self.db.add_table(Districts)
        self.db.add_table(Instances)
        self.db.add_table(Specialized)
        self.db.add_table(SpecializedRecords)
        self.db.add_table(Juzgado)
        self.db.add_table(PersonnType)
        self.db.add_table(Personns)
        self.db.add_table(Proceso)
        self.db.add_table(Estado)
        self.db.add_table(Materias)
        self.db.add_table(Summilla)
        self.db.add_table(Fecha_conclusion)
        self.db.add_table(Records)
        self.db.add_table(Partes)
        self.db.add_table(PersonnRecord)
        
        self.db.create_tables()
        
    async def get_filtrer(self, json_data_filter_path="data.json"):
        await self.create_tables()
        return 
        
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
        c = """UPDATE Districts (val, name) VALUES (?, ?)"""
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
            print("commiting for : " + str(msg))
            logger.info("Commiting for : " + str(msg))

    async def save_informations(self, informations: dict | list, district_name="", instance_name="", specialized_name="", ):
        if isinstance(informations, list):
            print("saving informations of type : " + type(informations))
            for info in informations:
                await self.save_informations(info)
            return
        
        logger.debug(f"starting saving info (with descargar {informations.get('descargar', False)}) : {informations} ")
        
        # l'identifiant
        n_expediente, year, digit_one, digit_two, code_one, code_two, last_digit = informations["trial_id"].split("-")
        
        # descargar
        if informations.get("descargar", False):
            descargar_value = 1
        else:
            descargar_value = 0
        
        # la date
        fecha_ignicio = informations["fecha de ignicio"]
        
        record_id_string = f"n°{n_expediente}-{year}-{digit_one}-{digit_two}-{code_one}-{code_two}-{last_digit}"
        record_additional_string = f"{fecha_ignicio}-{descargar_value}-{informations.get('organo', '')}-{informations.get('materials', '')}"
        record_id_string = record_id_string + " / " + record_additional_string
        logger.debug(f"saving record " + record_id_string)
        
        # l'instance
        instance = Instances.get_by(name=instance_name)
        if instance is None:
            instance = Instances(name=instance_name)
            instance.create_new()
        instance_id = instance.id
        
        # l'organe de justice
        organo_name = informations["organo"]
        organo_name = str(organo_name.split("°")[-1]).strip()
        organo = Juzgado.get_by(value=organo_name)
        if organo is None:
            organo = Juzgado(value=organo_name)
            organo.create_new()
        organo_id = organo.id
        
        # le district
        district_name = informations["district"]
        district = Districts.get_by(name=district_name)
        if district is None:
            district = Districts(name=district_name)
            district.create_new()
        district_id = district.id
        
        # le juge
        juez_name = informations["juez"]
        juez = Personns.get_by(name=juez_name)
        if juez is None:
            juez = Personns(name=juez_name)
            juez.create_new()
        logger.info(juez)
        juez_id = juez.id
        
        # psécialité légale
        legal_specialized_name = informations["legal_specialized"]
        legal_specialized = Personns.get_by(name=legal_specialized_name)
        if legal_specialized is None:
            legal_specialized = Personns(name=legal_specialized_name)
            legal_specialized.create_new()
        legal_specialized_id = legal_specialized.id
        
        # proceso
        proceso_name = informations["proceso"]
        proceso = Proceso.get_by(value=proceso_name)
        if proceso is None:
            proceso = Proceso(value=proceso_name)
            proceso.create_new()
        proceso_id = proceso.id
        
        # specialized
        specialized_name = informations["specialized"]
        specialized = Specialized.get_by(name=specialized_name)
        if specialized is None:
            specialized = Specialized(name=specialized_name)
            specialized.create_new()
        specialized_id = specialized.id
        
        # le sujet
        materias_name = informations["materials"]
        materias = Materias.get_by(value=materias_name)
        if materias is None:
            materias = Materias(value=materias_name)
            materias.create_new()
        materias_id = materias.id
        
        # le status
        status_name = informations["status"]
        status = Estado.get_by(value=status_name)
        if status is None:
            status = Estado(value=status_name)
            status.create_new()
        status_id = status.id
        
        # il y a peut etre informations["step"] qui correspond au Etapa Procesal
        
        # la conclusion
        conclusion_name = informations["fecha_conclusion"]
        conclusion = Fecha_conclusion.get_by(value=conclusion_name)
        if conclusion is None:
            conclusion = Fecha_conclusion(value=conclusion_name)
            conclusion.create_new()
        conclusion_id = conclusion.id
        logger.info(str(conclusion.value))
        
        # il y a peut etre informations["ubication"] qui correspond à 'Ubicación'
        
        # la motivo_conclusion
        # motivo_conclusion_name = informations["motivo_conclusion"]
        # motivo_conclusion = await 
        
        # sumilla
        summilla_name = informations["sumilla"]
        summilla = Summilla.get_by(value=summilla_name)
        if summilla is None:
            summilla = Summilla(value=summilla_name)
            summilla.create_new()
        summilla_id = summilla.id
        
        # le record avec les valeurs
        datas_dict = {
            "n_expediente": n_expediente,
            "year": year,
            "digit_1": digit_one,
            "digit_2": digit_two,
            "instance_code": code_one,
            "specialized_code": code_two,
            "last_digit": last_digit,
            "district_id": district_id,
            "instance_id": instance_id,
            "specialized_id": specialized_id,
            "juzgado_id": organo_id,
            "juez_id": juez_id,
            "fecha_ignicio": fecha_ignicio,
            "conclusion_id": conclusion_id,
            "materias_id": materias_id,
            "summilla_id": summilla_id,
            "especialista_legal_id": legal_specialized_id,
            "estado_id": status_id,
            "proceso_id": proceso_id,
            "descargar": descargar_value
        }
        
        logger.info(datas_dict)
        
        record = Records.get_by(**datas_dict)
        
        if record is not None:
            logger.debug(f"record already saved : {record_id_string} not saving a second time")
            return
        
        record = Records(
            **datas_dict
        )
        
        record.create_new()
        
        
        # crés les PersonnRecord
        for i, personn in enumerate(informations["personns"]):
            if personn is None:
                logger.warning("personn at index " + str(i) + " is None in informations " + str(informations["personns"]))
            kwargs = {}
            
            
            # récupère les informations d=sur la personne
            personn_paterno = personn.get("apellido paterno", "")
            if personn_paterno:
                kwargs["appelido_paterno"] = personn_paterno
                
            personn_materno = personn.get("apellido materno", "")
            if personn_materno:
                kwargs["appelido_materno"] = personn_materno
            
            personn_nombres = personn.get("nombres", "")
            if personn_nombres: #not implemented
                # kwargs[""] = ""
                pass
            
            
            # récupèrz=e le type de la personne
            type_name = personn["tipo de Persona"]
            personn_type = PersonnType.get_by(value=type_name)
            if personn_type is None:
                personn_type = PersonnType(value=type_name)
                personn_type.create_new()
            personn_type_id = personn_type.id
            kwargs["type"] = personn_type_id
            
            assert len(kwargs) > 0
            
            # cré l'objet de la personne
            personn_object = Personns.get_by(**kwargs)
            if personn_object is None:
                personn_object = Personns(
                    appelido_paterno=personn_paterno, 
                    appelido_materno=personn_materno, 
                    nombres=personn_nombres, 
                    type=personn_type_id
                )
                
                personn_object.create_new()
            
            partes_name = personn["parte"]
            personn_partes = Partes.get_by(name=partes_name)
            if personn_partes is None:
                personn_partes = Partes(name=partes_name)
                personn_partes.create_new()
            partes_id = personn_partes.id
            
            personn_record = PersonnRecord.get_by(
                
                personn_id=personn_object.id, 
                record_id=record.id, 
                partes_id=partes_id
            )
            
            if personn_record is None:
                personn_record = PersonnRecord(
                    personn_id=personn_object.id,
                    record_id=record.id,
                    partes_id=partes_id
                )
                personn_record.create_new()
        
        logger.debug("record " + record_id_string + " saved")
        print("record " + record_id_string + " saved")

    async def compute_informations(self, informations, district_name, instance_name, specialized_name):
        print("computing informations : " + str(len(informations)))
        for info in informations:
            try:
                async with DBLock:
                    await self.save_informations(
                        info, 
                        district_name=district_name, 
                        instance_name=instance_name, 
                        specialized_name=specialized_name
                    )
            except:
                logger.exception("Error during saving informations : " + str(info))
        self.db.commit("adding records")
        logger.debug("saved datas")
        
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