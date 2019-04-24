
"""
RDE Dictionary Builder

File : rde-dictionary-builder.py

Brief : This file contains the definitions and functionalities for generating
        a RDE schema dictionary from a set of standard Redfish CSDL and JSON Schema
        files
"""

import argparse
import sys
from rdebej.dictionary import *


if __name__ == '__main__':
    # rde_schema_dictionary parse --schemaDir=directory --schemaFilename=filename
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--silent", help="no output prints unless errors", action="store_true")
    subparsers = parser.add_subparsers(dest='source')

    # TODO: Fix remote for json fixups
    # remote_parser = subparsers.add_parser('remote')
    # remote_parser.add_argument('--schemaURL', type=str, required=True)
    # remote_parser.add_argument('--entity', type=str, required=True)
    # remote_parser.add_argument('--outputFile', type=str, required=False)

    local_parser = subparsers.add_parser('local')
    local_parser.add_argument('-c', '--csdlSchemaDirectories', nargs='*', type=str, required=True)
    local_parser.add_argument('-j', '--jsonSchemaDirectories', nargs='*', type=str, required=True)
    local_parser.add_argument('-s', '--schemaFilename', type=str, required=True)
    local_parser.add_argument('-e', '--entity', type=str, required=True)
    local_parser.add_argument('-o', '--oemSchemaFilenames', nargs='*', type=str, required=False)
    local_parser.add_argument('-t', '--oemEntities', nargs='*', type=str, required=False)
    local_parser.add_argument('-r', '--copyright', type=str, required=False)
    local_parser.add_argument('-p', '--profile', type=str, required=False)
    local_parser.add_argument('-d', '--outputFile', type=argparse.FileType('wb'), required=False)
    local_parser.add_argument('-f', '--outputJsonDictionaryFile', type=argparse.FileType('w'), required=False)

    annotation_v2_parser = subparsers.add_parser('annotation')
    annotation_v2_parser.add_argument('-c', '--csdlSchemaDirectories', nargs='*', type=str, required=True)
    annotation_v2_parser.add_argument('-j', '--jsonSchemaDirectories', nargs='*', type=str, required=True)
    annotation_v2_parser.add_argument('-v', '--version', type=str, required=True)
    annotation_v2_parser.add_argument('-r', '--copyright', type=str, required=False)
    annotation_v2_parser.add_argument('-d', '--outputFile', type=argparse.FileType('wb'), required=False)
    annotation_v2_parser.add_argument('-f', '--outputJsonDictionaryFile', type=argparse.FileType('w'), required=False)

    error_parser = subparsers.add_parser('error')
    error_parser.add_argument('-c', '--csdlSchemaDirectories', nargs='*', type=str, required=True)
    error_parser.add_argument('-j', '--jsonSchemaDirectories', nargs='*', type=str, required=True)
    error_parser.add_argument('-r', '--copyright', type=str, required=False)
    error_parser.add_argument('-d', '--outputFile', type=argparse.FileType('wb'), required=False)
    error_parser.add_argument('-f', '--outputJsonDictionaryFile', type=argparse.FileType('w'), required=False)

    dictionary_dump = subparsers.add_parser('view')
    dictionary_dump.add_argument('-f', '--file', type=str, required=True)

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.source is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set the verbose flag.
    verbose = args.verbose
    silent = args.silent
    if verbose and silent:  # override silent if verbose is set
        verbose = True
        silent = False

    # view an existing binary dictionary
    if args.source == 'view':
        # load the binary dictionary file
        file = open(args.file, 'rb')
        contents = file.read()
        print_binary_dictionary(list(contents))
        sys.exit()

    # Generate the schema dictionary.
    schema_dictionary = None
    if args.source == 'local':
        schema_dictionary = generate_schema_dictionary(args.source, args.csdlSchemaDirectories,
                                                       args.jsonSchemaDirectories, args.entity,
                                                       args.schemaFilename, args.oemEntities,
                                                       args.oemSchemaFilenames, args.profile,
                                                       None,
                                                       args.copyright)
    elif args.source == 'remote':
        schema_dictionary = generate_schema_dictionary(args.source, None, None, args.entity, None,
                                                       None, None, None, args.schemaURL)
    elif args.source == 'annotation':
        # Just choose a dummy complex entity type to start the annotation dictionary generation process.
        schema_dictionary = generate_annotation_schema_dictionary(args.csdlSchemaDirectories,
                                                                  args.jsonSchemaDirectories, args.version,
                                                                  args.copyright)
    elif args.source == 'error':
        schema_dictionary = generate_error_schema_dictionary(args.csdlSchemaDirectories,
                                                             args.jsonSchemaDirectories, args.copyright)

    # Print table data.
    if schema_dictionary is not None and schema_dictionary.dictionary:
        if not silent:
            print_table_data(
                          [["Row", "Sequence#", "Format", "Flags", "Field String", "Child Count", "Offset"]]
                          +
                          schema_dictionary.dictionary)

        # Print dictionary summary.
        if not silent:
            print_dictionary_summary(schema_dictionary.dictionary, schema_dictionary.dictionary_byte_array)

        # Generate binary dictionary file
        if args.outputFile:
            args.outputFile.write(bytes(schema_dictionary.dictionary_byte_array))

        if args.outputJsonDictionaryFile:
            args.outputJsonDictionaryFile.write(schema_dictionary.json_dictionary)
    else:
        print('Error, dictionary could not be generated')
