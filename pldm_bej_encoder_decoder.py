
"""
PLDM BEJ Encoder/Decoder

File : pldm_bej_encoder_decoder.py

Brief : This file allows encoding a JSON file to PLDM Binary encoded JSON (BEJ) and
        decoding a PLDM BEJ file back into JSON.
"""

import argparse
import json
import io
import sys
from rdebej import encode, decode


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--silent", help="no output prints unless errors", action="store_true")
    subparsers = parser.add_subparsers(dest='operation')

    encode_parser = subparsers.add_parser('encode')
    encode_parser.add_argument('-s',  '--schemaDictionary', type=argparse.FileType('rb'), required=True)
    encode_parser.add_argument('-a',  '--annotationDictionary', type=argparse.FileType('rb'), required=True)
    encode_parser.add_argument('-j',  '--jsonFile', type=argparse.FileType('r'), required=False)
    encode_parser.add_argument('-o',  '--bejOutputFile', type=argparse.FileType('wb'), required=False)
    encode_parser.add_argument('-op', '--pdrMapFile', type=argparse.FileType('w'), required=False)

    decode_parser = subparsers.add_parser('decode')
    decode_parser.add_argument('-s', '--schemaDictionary', type=argparse.FileType('rb'), required=True)
    decode_parser.add_argument('-a', '--annotationDictionary', type=argparse.FileType('rb'), required=True)
    decode_parser.add_argument('-b', '--bejEncodedFile', type=argparse.FileType('rb'), required=True)
    decode_parser.add_argument('-p', '--pdrMapFile', type=argparse.FileType('r'), required=False)

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set the verbose flag.
    verbose = args.verbose
    silent = args.silent
    if verbose and silent:  # override silent if verbose is set
        verbose = True
        silent = False

    # Read the binary schema dictionary into a byte array
    schema_dictionary = list(args.schemaDictionary.read())

    # Read the binary annotation dictionary into a byte array
    annotation_dictionary = list(args.annotationDictionary.read())

    if args.operation == 'encode':
        json_str = {}

        # Read the json file
        if args.jsonFile:
            json_str = args.jsonFile.read()
        else:  # read from stdin
            json_str = sys.stdin.read()

        json_to_encode = json.loads(json_str)

        # create a byte stream
        output_stream = io.BytesIO()
        success, pdr_map = encode.bej_encode(output_stream, json_to_encode, schema_dictionary, annotation_dictionary)
        if success:
            encoded_bytes = output_stream.getvalue()
            if not silent:
                encode.print_encode_summary(json_to_encode, encoded_bytes)

            if args.bejOutputFile:
                args.bejOutputFile.write(encoded_bytes)

            if args.pdrMapFile:
                args.pdrMapFile.write(json.dumps(pdr_map))
        else:
            if not silent:
                print('Failed to encode JSON')

    elif args.operation == 'decode':
        # Read the encoded bytes
        bej_encoded_bytes = list(args.bejEncodedFile.read())

        pdr_map = {}
        if args.pdrMapFile:
            pdr_map = json.loads(args.pdrMapFile.read())

        input_stream = io.BytesIO(bytes(bej_encoded_bytes))
        output_stream = io.StringIO()
        success = decode.bej_decode(output_stream, input_stream, schema_dictionary, annotation_dictionary, {}, pdr_map,
                                    {})
        if success:
            if not silent:
                print(json.dumps(json.loads(output_stream.getvalue()), indent=3))
        else:
            if not silent:
                print('Failed to decode JSON')
