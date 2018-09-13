import json
import os
import re
from collections import namedtuple
import importlib
import sys
import argparse

rde_lib_name = "rde_schema_dictionary_gen"

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_bej", help="test only BEJ", action="store_true")

    args = parser.parse_args()

    # Import the RDE dictionary builder script.
    try:
        sys.path.append('./')
        rde_dictionary_module = importlib.import_module(rde_lib_name)
    except Exception as ex:
        print("Error: Failed to import RDE dictionary builder library:", rde_lib_name)
        print("Error: Exception type: {0}, message: {1}".format(ex.__class__.__name__, str(ex)))
        sys.exit(1)

    schema_test_dir = 'test/schema'
    if not args.test_bej:
        # go thru every csdl and attempt creating a dictionary
        skip_list = ['AttributeRegistry_v1.xml']  # TODO: find and fix why these are failing
        for filename in os.listdir(schema_test_dir + '/metadata'):
            if filename not in skip_list:
                # strip out the _v1.xml
                m = re.compile('(.*)_v1.xml').match(filename)
                if m:
                    entity = m.group(1) + '.' + m.group(1)

                try:
                    schema_dictionary = rde_dictionary_module.generate_schema_dictionary(
                        'local',
                        [schema_test_dir + '/metadata'],
                        [schema_test_dir + '/json-schema'],
                        entity,
                        filename
                    )

                    if schema_dictionary and schema_dictionary.dictionary and schema_dictionary.json_dictionary:
                        print(filename, 'Entries:', len(schema_dictionary.dictionary), 'Size:', len(schema_dictionary.dictionary_byte_array) )
                    else:
                        print(filename, "Missing entities")

                except Exception as ex:
                    print("Error: Could not generate JSON schema dictionary for schema:", filename)
                    print("Error: Exception type: {0}, message: {1}".format(ex.__class__.__name__, str(ex)))
                    exit(1)


    # Generate the annotation dictionary
    print('Generating annotation dictionary...')
    try:
        annotation_dictionary = rde_dictionary_module.generate_schema_dictionary(
            'annotation',
            [schema_test_dir + '/metadata'],
            [schema_test_dir + '/json-schema'],
            'RedfishExtensions.PropertyPattern',
            'RedfishExtensions_v1.xml'
        )

        if annotation_dictionary and annotation_dictionary.dictionary \
                and annotation_dictionary.dictionary_byte_array and annotation_dictionary.json_dictionary:
            print('Entries:', len(annotation_dictionary.dictionary), 'Size:',
                  len(annotation_dictionary.dictionary_byte_array))
            with open('annotation.bin', 'wb') as annotaton_bin:
                annotaton_bin.write(bytearray(annotation_dictionary.dictionary_byte_array))

    except Exception as ex:
        print("Error: Could not generate JSON schema dictionary for schema annotation")
        print("Error: Exception type: {0}, message: {1}".format(ex.__class__.__name__, str(ex)))
        exit(1)


    # Generate the major schema dictionaries
    for major_schema in MAJOR_SCHEMA_DICTIONARY_LIST:

        try:
            schema_dictionary = rde_dictionary_module.generate_schema_dictionary(
                'local',
                major_schema.csdl_directories.split(),
                ['test/schema/json-schema'],
                major_schema.entity,
                major_schema.schema_filename,
                major_schema.oem_entities.split(),
                major_schema.oem_schema_filenames.split(),
                major_schema.profile
            )

            if schema_dictionary and schema_dictionary.dictionary and schema_dictionary.json_dictionary:
                print('Entries:', len(schema_dictionary.dictionary), 'Size:',
                      len(schema_dictionary.dictionary_byte_array))
                with open(major_schema.dictionary_filename, 'wb') as dictionary_bin:
                    dictionary_bin.write(bytearray(schema_dictionary.dictionary_byte_array))
                rde_dictionary_module.print_binary_dictionary(schema_dictionary.dictionary_byte_array)

        except Exception as ex:
            print("Error: Could not generate JSON schema dictionary for schema:", major_schema.schema_filename)
            print("Error: Exception type: {0}, message: {1}".format(ex.__class__.__name__, str(ex)))
            exit(1)

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

        # cleanup
        os.remove('pdr.txt')
        os.remove(major_schema.output_encoded_filename)
        os.remove(major_schema.dictionary_filename)
        
    # cleanup
    os.remove('annotation.bin')

    exit(code=0)