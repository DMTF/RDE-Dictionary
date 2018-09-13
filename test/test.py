import json
import os
import re
from collections import namedtuple

TestSpecification = namedtuple('TestSpecification', 'csdl_directories '
                                                    'schema_filename '
                                                    'entity '
                                                    'oem_schema_filenames '
                                                    'oem_entities '
                                                    'profile '
                                                    'dictionary_filename '
                                                    'input_encode_filename '
                                                    'output_encoded_filename')
MAJOR_SCHEMA_DICTIONARY_LIST = [
                                TestSpecification(
                                    'test/schema/dummysimple/csdl',
                                    'DummySimple_v1.xml',
                                    'DummySimple.DummySimple',
                                    '',
                                    '',
                                    '',
                                    'DummySimple.bin',
                                    'test/dummysimple.json',
                                    'DummySimple_bej.bin'),

                                TestSpecification(
                                    'test/schema/metadata test/schema/oem-csdl',
                                    'Drive_v1.xml',
                                    'Drive.Drive',
                                    'OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml',
                                    'OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt',
                                    '',                # profile
                                    'drive.bin',
                                    'test/drive.json',      # file to encode
                                    'drive_bej.bin'),  # encoded bej file

                                TestSpecification(
                                    'test/schema/metadata',
                                    'Storage_v1.xml',
                                    'Storage.Storage',
                                    '',
                                    '',
                                    '',
                                    'storage.bin',
                                    'test/storage.json',
                                    'storage_bej.bin'),

                                TestSpecification(
                                    'test/schema/metadata',
                                    'Storage_v1.xml',
                                    'Storage.Storage',
                                    '',
                                    '',
                                    'test/example_profile_for_truncation.json',
                                    'storage.bin',
                                    'test/storage_profile_conformant.json',
                                    'storage_bej.bin')
                                ]

if __name__ == '__main__':
    # go thru every csdl and attempt creating a dictionary
    skip_list = ['AttributeRegistry_v1.xml']  # TODO: find and fix why these are failing
    schema_test_dir = 'test/schema'
    for filename in os.listdir(schema_test_dir + '/metadata'):
        if filename not in skip_list:
            # strip out the _v1.xml
            m = re.compile('(.*)_v1.xml').match(filename)
            if m:
                entity = m.group(1) + '.' + m.group(1)

            dict_cmd = 'python rde_schema_dictionary_gen.py --silent local ' \
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
                   '--csdlSchemaDirectories ' + major_schema.csdl_directories + \
                   ' --jsonSchemaDirectories test/schema/json-schema ' \
                   '--schemaFilename ' + major_schema.schema_filename + \
                   ' --entity ' + major_schema.entity + \
                   (' --oemSchemaFilenames ' if (major_schema.oem_schema_filenames is not '') else '') + \
                   major_schema.oem_schema_filenames + \
                   (' --oemEntities ' if (major_schema.oem_entities is not '') else '') + \
                   major_schema.oem_entities + \
                   (' --profile ' if (major_schema.profile is not '') else '') + \
                   major_schema.profile + \
                   ' --outputFile ' + major_schema.dictionary_filename
        print(dict_cmd)
        error_code = os.system(dict_cmd)
        if error_code != 0:
            exit(error_code)

        # Run the encode/decode
        encode_cmd = 'python pldm_bej_encoder_decoder.py encode '\
                     '--schemaDictionary ' + major_schema.dictionary_filename + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --jsonFile ' + major_schema.input_encode_filename + \
                     ' --bejOutputFile ' + major_schema.output_encoded_filename + \
                     ' --pdrMapFile pdr.txt'
        print(encode_cmd)
        error_code = os.system(encode_cmd)
        if error_code != 0:
            exit(error_code)

        decode_cmd = 'python pldm_bej_encoder_decoder.py decode '\
                     '--schemaDictionary ' + major_schema.dictionary_filename + \
                     ' --annotationDictionary annotation.bin ' \
                     ' --bejEncodedFile ' + major_schema.output_encoded_filename + \
                     ' --pdrMapFile pdr.txt'
        print(decode_cmd)
        decode_file = os.popen(decode_cmd).read()

        # compare the decode with the original
        print('Decoded JSON:')
        print(json.dumps(json.loads(decode_file), indent=3))
        assert(json.loads(decode_file) == json.load(open(major_schema.input_encode_filename)))

        # TODO: cleanup

    exit(code=0)