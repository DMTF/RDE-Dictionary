import json
import os
import re

SPEC_INDEX_SCHEMA_FILENAME = 0
SPEC_INDEX_SCHEMA_ENTITY = 1
SPEC_INDEX_OEM_SCHEMA_FILENAMES = 2
SPEC_INDEX_OEM_ENTITIES = 3
SPEC_INDEX_PROFILE = 4
SPEC_INDEX_DICTIONARY_FILENAME = 5
SPEC_INDEX_JSONFILE_TO_ENCODE = 6
SPEC_INDEX_BEJ_ENCODED_FILE = 7


MAJOR_SCHEMA_DICTIONARY_LIST = [('Drive_v1.xml',
                                 'Drive.Drive',
                                 'OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml',
                                 'OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt',
                                 '',                # profile
                                 'drive.bin',
                                 'drive.json',      # file to encode
                                 'drive_bej.bin'),  # encoded bej file

                                ('Storage_v1.xml',
                                 'Storage.Storage',
                                 '',
                                 '',
                                 '',
                                 'storage.bin',
                                 'storage.json',
                                 'storage_bej.bin'),

                                ('Storage_v1.xml',
                                 'Storage.Storage',
                                 '',
                                 '',
                                 'test/example_profile_for_truncation.json',
                                 'storage.bin',
                                 'storage_profile_conformant.json',
                                 'storage_bej.bin'),
                                ]

if __name__ == '__main__':
    # go thru every csdl and attempt creating a dictionary
    skip_list = ['AttributeRegistry_v1.xml'] # TODO: find and fix why these are failing
    schema_test_dir = 'test/schema'
    for filename in os.listdir(schema_test_dir + '/metadata'):
        if filename not in skip_list:
            # strip out the _v1.xml
            m = re.compile('(.*)_v1.xml').match(filename)
            if m:
                entity = m.group(1) + '.' + m.group(1)

            dict_cmd = 'python rde_schema_dictionary_gen.py local ' \
                       '--csdlSchemaDirectories ' + schema_test_dir + '/metadata ' \
                       '--jsonSchemaDirectories ' + schema_test_dir + '/json-schema ' \
                       '--schemaFilename ' + filename + \
                       ' --entity ' + entity + \
                       ' --outputFile ' + 'tmp_dict.bin'
            print(dict_cmd)
            error_code = os.system(dict_cmd)
            if error_code != 0:
                exit(error_code)

    # Generate the annotation dictionary
    print('Generating annotation dictionary...')
    error_code = os.system('python rde_schema_dictionary_gen.py annotation '
                           '--csdlSchemaDirectories test/schema/metadata '
                           '--jsonSchemaDirectories test/schema/json-schema '
                           '--outputFile annotation.bin')
    if error_code != 0:
        exit(error_code)

    # Generate the major schema dictionaries
    for major_schema in MAJOR_SCHEMA_DICTIONARY_LIST:
        dict_cmd = 'python rde_schema_dictionary_gen.py local ' \
                   '--csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl ' \
                   '--jsonSchemaDirectories test/schema/json-schema ' \
                   '--schemaFilename ' + major_schema[SPEC_INDEX_SCHEMA_FILENAME] + \
                   ' --entity ' + major_schema[SPEC_INDEX_SCHEMA_ENTITY] + \
                   (' --oemSchemaFilenames ' if  (major_schema[SPEC_INDEX_OEM_SCHEMA_FILENAMES] is not '')  else '') + \
                   major_schema[SPEC_INDEX_OEM_SCHEMA_FILENAMES] + \
                   (' --oemEntities ' if (major_schema[SPEC_INDEX_OEM_ENTITIES] is not '') else '') + \
                   major_schema[SPEC_INDEX_OEM_ENTITIES] + \
                   (' --profile ' if (major_schema[SPEC_INDEX_PROFILE] is not '') else '') + \
                   major_schema[SPEC_INDEX_PROFILE] + \
                   ' --outputFile ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME]
        print(dict_cmd)
        error_code = os.system(dict_cmd)
        if error_code != 0:
            exit(error_code)

        # Run the encode/decode
        encode_cmd = 'python pldm_bej_encoder_decoder.py encode '\
                     '--schemaDictionary ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME] + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --jsonFile test/' + major_schema[SPEC_INDEX_JSONFILE_TO_ENCODE] + \
                     ' --bejOutputFile ' + major_schema[SPEC_INDEX_BEJ_ENCODED_FILE] + \
                     ' --pdrMapFile pdr.txt'
        print(encode_cmd)
        error_code = os.system(encode_cmd)
        if error_code != 0:
            exit(error_code)

        decode_cmd = 'python pldm_bej_encoder_decoder.py decode '\
                     '--schemaDictionary ' + major_schema[SPEC_INDEX_DICTIONARY_FILENAME] + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --bejEncodedFile ' + major_schema[SPEC_INDEX_BEJ_ENCODED_FILE] + \
                     ' --pdrMapFile pdr.txt'
        print(decode_cmd)
        decode_file = os.popen(decode_cmd).read()

        # compare the decode with the original
        print('Decoded JSON:')
        print(json.dumps(json.loads(decode_file), indent=3))
        assert(json.loads(decode_file) == json.load(open('test/'+major_schema[SPEC_INDEX_JSONFILE_TO_ENCODE])))

    exit(code=0)