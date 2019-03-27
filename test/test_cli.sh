#!/usr/bin/env bash

pipenv run python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --outputFile drive.bin
pipenv run python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --outputFile drive.bin -f drive.json
pipenv run python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --oemSchemaFilenames OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml --oemEntities OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt --outputFile drive.bin
pipenv run python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --profile test/example_profile_for_truncation.json
pipenv run python rde_schema_dictionary_gen.py annotation --csdlSchemaDirectories test/schema/metadata --jsonSchemaDirectories test/schema/json-schema -v v1_0_0 --outputFile annotation.bin
pipenv run python rde_schema_dictionary_gen.py annotation --csdlSchemaDirectories test/schema/metadata --jsonSchemaDirectories test/schema/json-schema -v v1_0_0 --outputFile annotation.bin -f annotation.json
pipenv run python rde_schema_dictionary_gen.py error -c test/schema/metadata -j test/schema/json-schema
pipenv run python pldm_bej_encoder_decoder.py encode --schemaDictionary drive.bin --annotationDictionary annotation.bin --jsonFile test/drive.json --bejOutputFile drive_bej.bin --pdrMapFile pdr.txt  
pipenv run python pldm_bej_encoder_decoder.py decode --schemaDictionary drive.bin --annotationDictionary annotation.bin --bejEncodedFile drive_bej.bin --pdrMapFile pdr.txt
