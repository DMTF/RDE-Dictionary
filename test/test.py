import json
import os

SPEC_INDEX_SCHEMA_FILENAME = 0
SPEC_INDEX_SCHEMA_ENTITY = 1
SPEC_INDEX_OEM_SCHEMA_FILENAMES = 2
SPEC_INDEX_OEM_ENTITIES = 3
SPEC_INDEX_DICTIONARY_FILENAME = 4
SPEC_INDEX_JSONFILE_TO_ENCODE = 5
SPEC_INDEX_BEJ_ENCODED_FILE = 6

MAJOR_SCHEMA_DICTIONARY_LIST = [('Drive_v1.xml',
                                 'Drive.Drive',
                                 'OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml',
                                 'OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt',
                                 'drive.bin',
                                 'drive.json',      # file to encode
                                 'drive_bej.bin'),  # encoded bej file

                                ('Storage_v1.xml',
                                 'Storage.Storage',
                                 '',
                                 '',
                                 'storage.bin',
                                 'storage.json',
                                 'storage_bej.bin')
                                ]

if __name__ == '__main__':

    # Generate the annotation dictionary
    print('Generating annotation dictionary...')
    os.system('python rde_schema_dictionary_gen.py annotation --schemaDir "test/schema" --outputFile annotation.bin')

    # Generate the major schema dictionaries
    for major_schema in MAJOR_SCHEMA_DICTIONARY_LIST:
        dict_cmd = 'python rde_schema_dictionary_gen.py local --schemaDir "test/schema"  ' \
              '--schemaFilename ' + major_schema[SPEC_INDEX_SCHEMA_FILENAME] + \
              ' --entity ' + major_schema[SPEC_INDEX_SCHEMA_ENTITY] + \
              (' --oemSchemaFilenames ' if  (major_schema[SPEC_INDEX_OEM_SCHEMA_FILENAMES] is not '')  else '') + \
                 major_schema[SPEC_INDEX_OEM_SCHEMA_FILENAMES] + \
              (' --oemEntities ' if (major_schema[SPEC_INDEX_OEM_ENTITIES] is not '') else '') + \
                 major_schema[SPEC_INDEX_OEM_ENTITIES] + \
              ' --outputFile ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME]
        print(dict_cmd)
        os.system(dict_cmd)

        # Run the encode/decode
        encode_cmd = 'python pldm_bej_encoder_decoder.py encode '\
                     '--schemaDictionary ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME] + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --jsonFile test/' + major_schema[SPEC_INDEX_JSONFILE_TO_ENCODE] + \
                     ' --bejOutputFile ' + major_schema[SPEC_INDEX_BEJ_ENCODED_FILE] + \
                     ' --pdrMapFile pdr.txt'
        print(encode_cmd)
        os.system(encode_cmd)

        decode_cmd = 'python pldm_bej_encoder_decoder.py decode '\
                     '--schemaDictionary ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME] + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --bejEncodedFile ' + major_schema[SPEC_INDEX_BEJ_ENCODED_FILE] + \
                     ' --pdrMapFile pdr.txt'
        decode_file = os.popen(decode_cmd).read()

        # compare the decode with the original
        print('Decoded JSON:')
        print(json.dumps(json.loads(decode_file), indent=3))
        assert(json.loads(decode_file) == json.load(open('test/'+major_schema[SPEC_INDEX_JSONFILE_TO_ENCODE])))
    exit(code=0)