# MODELS CREATION

records_create_command = """CREATE TABLE records (
id INTEGER NOT NULL, 
n_expediente INTEGER NOT NULL, 
year smallint NOT NULL, 
digit_1 tinyint NOT NULL, 
digit_2 smallint NOT NULL, 
instance_code TEXT(2) NOT NULL, 
specialized_code TEXT(2) NOT NULL, 
last_digit tyniint NOT NULL, 
fecha_ignicio TEXT(10) NOT NULL, 
descargar BIT(1) NOT NULL, 
district_id INTEGER NOT NULL, 
instance_id INTEGER NOT NULL, 
specialized_id INTEGER NOT NULL, 
juzgado_id INTEGER NOT NULL, 
juez_id INTEGER NOT NULL, 
conclusion_id INTEGER, 
materias_id INTEGER, 
summilla_id INTEGER, 
especialista_legal_id INTEGER NOT NULL, 
estado_id INTEGER, 
proceso_id INTEGER, 
PRIMARY KEY(id, n_expediente, year, digit_1, digit_2, instance_code, specialized_code, last_digit, fecha_ignicio, descargar),
UNIQUE(n_expediente, year, digit_1, digit_2, instance_code, specialized_code, last_digit),
FOREIGN KEY (district_id) REFERENCES Districts(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (instance_id) REFERENCES Instances(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (specialized_id) REFERENCES Specialized(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (juzgado_id) REFERENCES Juzgado(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (juez_id, especialista_legal_id) REFERENCES Personns(id, id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (conclusion_id) REFERENCES Fecha_conclusion(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (materias_id) REFERENCES Materias(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (summilla_id) REFERENCES Summilla(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (estado_id) REFERENCES Estado(id ) ON UPDATE CASCADE ON DELETE RESTRICT, 
FOREIGN KEY (proceso_id) REFERENCES Proceso(id ) ON UPDATE CASCADE ON DELETE RESTRICT),"""



# SEARCH REQUESTS

search_max_table_initating = """UPDATE personnrecord SET partes_id = ? WHERE partes_id IN ({})"""

search_max_partes_request = """WITH Result AS (
    SELECT
        records.year,
        records.district_id,
        records.instance_id,
        records.specialized_id ,
        partes_id,
        COUNT(*) as pers_count 
	FROM personnrecord
    INNER JOIN records ON records.id = record_id
	WHERE 
        records.year = ? AND
        records.district_id = ? AND
        records.instance_id = ? AND
        records.specialized_id = ?
    GROUP BY 
        record_id,
        partes_id
)
SELECT partes_id, MAX(pers_count) as max_pers_count
FROM Result
GROUP BY 
	year, district_id, instance_id, specialized_id, partes_id
    
"""
search_record = """SELECT * FROM records 
WHERE 
    n_expediente = ? AND
    year = ? AND
    digit_1 = ? AND
    digit_2 = ? AND
    instance_code = ? AND
    specialized_code = ? AND
    last_digit = ? AND
    district_id = ? AND
    instance_id = ? AND
    specialized_id = ? AND
    juzgado_id = ? AND
    juez_id = ? AND
    fecha_ignicio = ? AND
    conclusion_id = ? AND
    materias_id = ? AND
    summilla_id = ? AND
    especialista_legal_id = ? AND
    estado_id = ? AND
    proceso_id = ? AND
    descargar = ?"""




