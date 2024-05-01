IF "%~8"=="" (
    ECHO "To call this script you need to run '%0 start_year end_year start_district end_district start_instance end_instance start_specialized end_sepcialized'"
    GOTO exit
)

FOR /L %%A IN (%1,1,%2) DO (
    FOR /L %%B IN (%3,1,%4) DO (
        FOR /L %%C IN (%5,1,%6) DO (
            FOR /L %%D IN (%7,1,%8) DO (
                python to_excel.py %%A %%B %%C %%D
            )
        )
    )
)
:exit