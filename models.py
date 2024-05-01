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