#! /usr/bin/python3
# Copyright Notice:
# Copyright 2018-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/RDE-Dictionary/blob/master/LICENSE.md

"""
PLDM BEJ Decoder

File : decode.py

Brief : This file defines APIs to decode a PLDM Binary encoded JSON (BEJ) to JSON
"""

import os
import re
from ._internal_utils import *


def bej_unpack_nnint(stream):
    # read num bytes
    num_bytes = int.from_bytes(stream.read(1), 'little')
    return int.from_bytes(stream.read(num_bytes), 'little')


def bej_unpack_sfl(stream):
    # unpack seq
    seq = bej_unpack_nnint(stream)

    # unpack format
    format = int.from_bytes(stream.read(1), 'little') >> 4

    # unpack length
    length = bej_unpack_nnint(stream)

    return seq, format, length


def bej_decode_sequence_number(seq):
    """
    Returns the sequence number and the dictionary selector
    """
    return seq >> 1, seq & 0x01


def bej_unpack_sflv_string(stream):
    seq, format, length = bej_unpack_sfl(stream)
    val = stream.read(length).decode()

    # the last byte in a string decode is the null terminator, remove that and return
    return bej_decode_sequence_number(seq), val[:length-1]


def bej_unpack_sflv_boolean(stream):
    seq, format, length = bej_unpack_sfl(stream)
    val = stream.read(length)

    bool_val = 'false'
    if val[0] == 0x01:
        bool_val = 'true'

    # the last byte in a string decode is the null terminator, remove that and return
    return bej_decode_sequence_number(seq), bool_val


def bej_unpack_sflv_integer(stream):
    seq, format, length = bej_unpack_sfl(stream)
    int_array = stream.read(length)
    return bej_decode_sequence_number(seq), int.from_bytes(int_array, 'little', signed=True)


def bej_unpack_sflv_real(stream):
    seq, format, length = bej_unpack_sfl(stream)
    length_of_whole = bej_unpack_nnint(stream)
    whole_array = stream.read(length_of_whole)
    whole = int.from_bytes(whole_array, 'little', signed=True)
    leading_zero_count = bej_unpack_nnint(stream)
    fract = bej_unpack_nnint(stream)
    length_of_exponent = bej_unpack_nnint(stream)
    exponent = 0
    if length_of_exponent > 0:
        exponent_array = stream.read(length_of_exponent)
        exponent =  int.from_bytes(exponent_array, 'little', signed=True)

    real_str = str(whole) + '.'
    for i in range(0, leading_zero_count):
       real_str += '0'
    real_str += str(fract)
    real_str += 'e' + str(exponent)
    return bej_decode_sequence_number(seq), float(real_str)


def bej_unpack_sflv_enum(stream):
    seq, format, length = bej_unpack_sfl(stream)
    value = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), value


def bej_unpack_sflv_resource_link(stream):
    seq, format, length = bej_unpack_sfl(stream)
    value = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), value


def bej_unpack_sflv_null(stream):
    seq, format, length = bej_unpack_sfl(stream)
    return bej_decode_sequence_number(seq)


def bej_unpack_set_start(stream):
    '''
    :param stream:
    :return: [sequence_num, selector], length, count
    '''

    # move the stream to point to the first element in the set
    seq, format, length = bej_unpack_sfl(stream)

    # unpack the count
    count = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), length, count


def bej_unpack_array_start(stream):
    '''
    :param stream:
    :return: [sequence_num, selector], length, count
    '''

    # move the stream to point to the first element in the array
    seq, format, length = bej_unpack_sfl(stream)

    # unpack the count
    count = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), length, count


def bej_unpack_property_annotation_start(stream):
    '''
    :param stream:
    :return:
    '''

    # move the stream to point to the first element in the set
    seq, format, length = bej_unpack_sfl(stream)
    prop_seq, selector = bej_decode_sequence_number(seq)
    annot_seq, selector = bej_decode_sequence_number(bej_sequenceof(stream))
    return annot_seq, prop_seq


    pass


def bej_unpack_array_done():
    pass


def bej_unpack_property_annotation_done():
    pass


def bej_typeof(stream):
    current_pos = stream.tell()

    # skip seq
    bej_unpack_nnint(stream)

    format = int.from_bytes(stream.read(1), 'little') >> 4
    stream.seek(current_pos, os.SEEK_SET)

    return format


def bej_is_deferred_binding(stream):
    current_pos = stream.tell()

    # skip seq
    bej_unpack_nnint(stream)

    is_deferred_binding = int.from_bytes(stream.read(1), 'little') & 0x01 == 0x01
    stream.seek(current_pos, os.SEEK_SET)

    return is_deferred_binding


def bej_sequenceof(stream):
    current_pos = stream.tell()

    # get seq
    seq = bej_unpack_nnint(stream)

    stream.seek(current_pos, os.SEEK_SET)

    return seq


def get_stream_size(stream):
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    final_pos = stream.tell()
    stream.seek(current_pos, os.SEEK_SET)
    return final_pos


current_available_pdr = 0


def get_link_from_pdr_map(pdr, pdr_map):
    for key, value in pdr_map.items():
        if value == pdr:
            return key
    return ''


def load_dictionary_subset_by_key_sequence(schema_dict, offset, child_count):
    schema_dict_stream = DictionaryByteArrayStream(schema_dict, offset, child_count)

    entry_dict = {}
    while schema_dict_stream.has_entry():
        entry = schema_dict_stream.get_next_entry()
        entry_dict[entry[DICTIONARY_ENTRY_SEQUENCE_NUMBER]] = entry

    return entry_dict


def get_full_annotation_name_from_sequence_number(seq, annot_dict):
    # TODO: cache the main annotations
    base_entry = DictionaryByteArrayStream(annot_dict, 0, -1).get_next_entry()
    annotation_entries = load_dictionary_subset_by_key_sequence(annot_dict,
                                                                base_entry[DICTIONARY_ENTRY_OFFSET],
                                                                base_entry[DICTIONARY_ENTRY_CHILD_COUNT])

    return annotation_entries[seq][DICTIONARY_ENTRY_NAME]


def bej_decode_enum_value(dict_to_use, dict_entry, value):
    # get the value for the enum sequence number from the dictionary
    enum_dict_stream = DictionaryByteArrayStream(dict_to_use, dict_entry[DICTIONARY_ENTRY_OFFSET],
                                                 dict_entry[DICTIONARY_ENTRY_CHILD_COUNT])
    enum_value = ''
    while enum_dict_stream.has_entry():
        enum_entry = enum_dict_stream.get_next_entry()

        if enum_entry[DICTIONARY_ENTRY_SEQUENCE_NUMBER] == value:
            enum_value = enum_entry[DICTIONARY_ENTRY_NAME]
            break
    return enum_value


def bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream):
    if selector == entries_by_seq_selector:
        name = entries_by_seq[seq][DICTIONARY_ENTRY_NAME]
    elif selector == BEJ_DICTIONARY_SELECTOR_ANNOTATION:
        name = get_full_annotation_name_from_sequence_number(seq, annot_dict)
    else:
        name = entries_by_seq[seq][DICTIONARY_ENTRY_NAME]

    if name != '':
        output_stream.write('"' + name + '":')


def bej_decode_property_annotation_name(annot_dict, annot_seq, prop_seq, entries_by_seq, output_stream):
    prop_name = entries_by_seq[prop_seq][DICTIONARY_ENTRY_NAME]
    annot_name = get_full_annotation_name_from_sequence_number(annot_seq, annot_dict)

    output_stream.write('"' + prop_name + annot_name + '":')


def get_annotation_dictionary_entries_by_seq(annotation_dictionary):
    base_entry = DictionaryByteArrayStream(annotation_dictionary, 0, -1).get_next_entry()
    return load_dictionary_subset_by_key_sequence(annotation_dictionary, base_entry[DICTIONARY_ENTRY_OFFSET],
                                              base_entry[DICTIONARY_ENTRY_CHILD_COUNT])


def validate_complex_type_length(input_stream, complex_type_start_pos, length):
    current_pos = input_stream.tell()
    input_stream.seek(complex_type_start_pos, os.SEEK_SET)
    bej_unpack_sfl(input_stream)
    set_value_start_pos = input_stream.tell()
    input_stream.seek(current_pos, os.SEEK_SET)
    return current_pos - set_value_start_pos == length


def bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict, entries_by_seq, entries_by_seq_selector,
                      prop_count, is_seq_array_index, add_name, deferred_binding_strings):
    index = 0
    success = True
    while success and input_stream.tell() < get_stream_size(input_stream) and index < prop_count:
        format = bej_typeof(input_stream)

        if format == BEJ_FORMAT_SET:
            # record the stream pos so we can validate the length later
            set_start_pos = input_stream.tell()
            [seq, selector], length, count = bej_unpack_set_start(input_stream)
            if is_seq_array_index:
                seq = 0
            entry = entries_by_seq[seq]

            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            dict_to_use = schema_dict if selector is BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA else annot_dict
            output_stream.write('{')

            success = bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict,
                                        load_dictionary_subset_by_key_sequence(
                                            dict_to_use, entry[DICTIONARY_ENTRY_OFFSET], entry[DICTIONARY_ENTRY_CHILD_COUNT]),
                                        selector,
                                        count, is_seq_array_index=False, add_name=True, deferred_binding_strings=deferred_binding_strings)
            output_stream.write('}')

            # validate the length
            if not validate_complex_type_length(input_stream, set_start_pos, length):
                print('BEJ decoding error: Invalid length/count for set. Current stream contents:',
                      output_stream.getvalue())
                return False

        elif format == BEJ_FORMAT_STRING:
            is_deferred_binding = bej_is_deferred_binding(input_stream)
            [seq, selector], value = bej_unpack_sflv_string(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            if is_deferred_binding:
                bindings_to_resolve = re.findall('(%M|%[LTPI][0-9]+)\.?[0-9]*.*?', value)
                for binding in bindings_to_resolve:
                    if binding in deferred_binding_strings:
                        value = value.replace(binding, deferred_binding_strings[binding])

            output_stream.write('"' + value + '"')

        elif format == BEJ_FORMAT_INTEGER:
            [seq, selector], value = bej_unpack_sflv_integer(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write(str(value))

        elif format == BEJ_FORMAT_REAL:
            [seq, selector], value = bej_unpack_sflv_real(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write(str(value))

        elif format == BEJ_FORMAT_BOOLEAN:
            [seq, selector], value = bej_unpack_sflv_boolean(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write(value)

        elif format == BEJ_FORMAT_RESOURCE_LINK:
            [seq, selector], pdr = bej_unpack_sflv_resource_link(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write('"' + get_link_from_pdr_map(pdr) + '"')

        elif format == BEJ_FORMAT_ENUM:
            [seq, selector], value = bej_unpack_sflv_enum(input_stream)
            if is_seq_array_index:
                seq = 0

            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            dict_to_use = schema_dict if selector is BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA else annot_dict
            enum_value = bej_decode_enum_value(dict_to_use, entries_by_seq[seq], value)
            output_stream.write('"' + enum_value + '"')

        elif format == BEJ_FORMAT_NULL:
            [seq, selector] = bej_unpack_sflv_null(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write('null')

        elif format == BEJ_FORMAT_ARRAY:
            array_start_pos = input_stream.tell()
            [seq, selector], length, array_member_count = bej_unpack_array_start(input_stream)
            if is_seq_array_index:
                seq = 0

            dict_to_use = schema_dict if selector is BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA else annot_dict

            # if we are changing dictionary context, we need to load entries for the new dictionary
            if entries_by_seq_selector != selector:
                base_entry = DictionaryByteArrayStream(dict_to_use, 0, -1).get_next_entry()
                entries_by_seq = load_dictionary_subset_by_key_sequence(dict_to_use,
                                                                            base_entry[DICTIONARY_ENTRY_OFFSET],
                                                                            base_entry[DICTIONARY_ENTRY_CHILD_COUNT])

            entry = entries_by_seq[seq]

            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, entries_by_seq_selector, output_stream)

            output_stream.write('[')
            for i in range(0, array_member_count):
                success = bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict,
                                            load_dictionary_subset_by_key_sequence(dict_to_use, entry[DICTIONARY_ENTRY_OFFSET],
                                                                                   entry[DICTIONARY_ENTRY_CHILD_COUNT]),
                                            selector,
                                            prop_count=1, is_seq_array_index=True, add_name=False,
                                            deferred_binding_strings=deferred_binding_strings)
                if i < array_member_count-1:
                    output_stream.write(',')

            output_stream.write(']')

            # validate the length
            if not validate_complex_type_length(input_stream, array_start_pos, length):
                print('BEJ decoding error: Invalid length/count for array. Current stream contents:',
                      output_stream.getvalue())
                return False


        elif format == BEJ_FORMAT_PROPERTY_ANNOTATION:
            # Seq(property sequence #)
            #    Format(bejPropertyAnnotation)
            #        Length
            #            Seq(Annotation_name)
            #                Format(format of annotation value)
            #                    Length
            #                        Value(value: can be a complex type)
            # e.g Status@Message.ExtendedInfo

            annot_seq, prop_seq = bej_unpack_property_annotation_start(input_stream)
            bej_decode_property_annotation_name(annot_dict, annot_seq, prop_seq, entries_by_seq,
                                                output_stream)

            success = bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict,
                                        get_annotation_dictionary_entries_by_seq(annot_dict),
                                        BEJ_DICTIONARY_SELECTOR_ANNOTATION,
                                        prop_count=1, is_seq_array_index=False, add_name=False,
                                        deferred_binding_strings=deferred_binding_strings)
        else:
            success = False

        if index < prop_count-1:
            output_stream.write(',')
        index += 1

    return success


def bej_decode(output_stream, input_stream, schema_dictionary, annotation_dictionary,
               error_dictionary, pdr_map, def_binding_strings):
    """
    Decode a BEJ stream into JSON

    Args:
        output_stream:
        input_stream:
        schema_dictionary:
        annotation_dictionary:
        error_dictionary:
        pdr_map:
        def_binding_strings:

    Returns:
    """
    resource_link_to_pdr_map = pdr_map
    # strip off the headers
    version = input_stream.read(4)
    assert(version == bytes([0x00, 0xF0, 0xF0, 0xF1]))
    flags = input_stream.read(2)
    assert (flags == bytes([0x00, 0x00]))
    schemaClass = input_stream.read(1)
    assert(schemaClass in [bytes([0x00]), bytes([0x04])])

    if schemaClass == bytes([0x00]): # Major schema class
        return bej_decode_stream(output_stream, input_stream, schema_dictionary, annotation_dictionary,
                                 load_dictionary_subset_by_key_sequence(schema_dictionary, 0, -1),
                                 BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA,
                                 1, is_seq_array_index=False, add_name=False,
                                 deferred_binding_strings=def_binding_strings)
    else: # Error schema class
        return bej_decode_stream(output_stream, input_stream, error_dictionary, annotation_dictionary,
                                 load_dictionary_subset_by_key_sequence(error_dictionary, 0, -1),
                                 BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA,
                                 1, is_seq_array_index=False, add_name=False,
                                 deferred_binding_strings=def_binding_strings)

