
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
import os
import re
import string

BEJ_FORMAT_SET = 0x00
BEJ_FORMAT_ARRAY = 0x01
BEJ_FORMAT_NULL = 0x02
BEJ_FORMAT_INTEGER = 0x03
BEJ_FORMAT_ENUM = 0x04
BEJ_FORMAT_STRING = 0x05
BEJ_FORMAT_REAL = 0x06
BEJ_FORMAT_BOOLEAN = 0x07
BEJ_FORMAT_BYTE_STRING = 0x08
BEJ_FORMAT_CHOICE = 0x09
BEJ_FORMAT_PROPERTY_ANNOTATION = 0x0A
BEJ_FORMAT_RESOURCE_LINK = 0x0E
BEJ_FORMAT_RESOURCE_LINK_EXPANSION = 0x0F
BEJ_FORMAT_UNKNOWN = 0xFF

BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA = 0x00
BEJ_DICTIONARY_SELECTOR_ANNOTATION = 0x01

NUM_BYTES_FOR_INTEGER = 8

VALID_ASCII_PRINT_CHARS = string.ascii_letters + string.hexdigits + string.punctuation


def print_hex(byte_buf, max_size=None, add_line_number=True, show_ascii=True):
    """
    Prints a byte array as hex dump

    Args:
        byte_buf: byte array to be printed as a hex dump
        max_size: Number of bytes to print, None indicates to print all bytes
        add_line_number: Set to True to show line numbers
        show_ascii: Set to True to print ASCII
    """

    ascii_print = ''
    limit_size = True if max_size else False
    for ii, byte in enumerate(byte_buf):
        if limit_size and ii >= max_size:
            break
        mod = ii % 16
        next_mod = (ii + 1) % 16
        if add_line_number and mod == 0:
            print(format(ii, '#08X')+': ', end="")
        print(format(byte, '02X'), end=" ")
        byte_char = format(byte, 'c')
        if show_ascii:
            ascii_print += (byte_char if byte_char in VALID_ASCII_PRINT_CHARS else '.')

        if next_mod == 0:
            # Print the ascii line
            if show_ascii:
                print(ascii_print, end="")
                ascii_print = ''
            print('')

    # Add a newline to seperate
    print('')


def twos_complement(value, nbits):
    return (value + (1 << nbits)) % (1 << nbits)


def find_num_bytes_and_msb(value):
    if value == 0:
        return 1, 0x00
    if value == -1:
        return 1, 0xff

    # use a big endian byte array (MSB is at index 0) as it is easier to eliminate the padding
    if value > 0:
        value_byte_array = twos_complement(value, 64).to_bytes(NUM_BYTES_FOR_INTEGER, 'big')
        for index, val in enumerate(value_byte_array):
            if val != 0x00:
                return NUM_BYTES_FOR_INTEGER - index, val
    else:
        value_byte_array = twos_complement(value, 64).to_bytes(NUM_BYTES_FOR_INTEGER, 'little')
        for index, val in enumerate(value_byte_array):
            if val & 0x80:
                return index+1, val


def num_bytes_for_unsigned_integer(value):
    num_bytes = 1 if value == 0 else 0
    while value != 0:
        value >>= 8
        num_bytes = num_bytes + 1

    return num_bytes


def bej_pack_nnint(stream, value, num_bytes):
    """
    The nnint type captures the BEJ encoding of Non-Negative Integers via the following encoding:
    The first byte shall consist of metadata for the number of bytes needed to encode the numeric
    value in the remaining bytes. Subsequent bytes shall contain the encoded value in
    little-endian format. As examples, the value 65 shall be encoded as 0x01 0x41; the value 130
    shall be encoded as 0x01 0x82; and the value 1337 shall be encoded as 0x02 0x39 0x05.

    Args:
        stream:
        value:
        num_bytes: indicates number of bytes (length) to use to represent the value, if 0 is specified, the most
        optimal size is used
    Return: -1 if error or no bytes written, >= 0 indicates number of bytes packed
    """
    num_bytes_for_value = num_bytes_for_unsigned_integer(value)
    if num_bytes and (num_bytes < num_bytes_for_value):
        return -1

    if num_bytes:
        num_bytes_for_value = num_bytes

    num_bytes_packed = stream.write(num_bytes_for_value.to_bytes(1, 'little'))
    num_bytes_packed += stream.write(value.to_bytes(num_bytes_for_value, 'little'))

    return num_bytes_packed


def bej_unpack_nnint(stream):
    # read num bytes
    num_bytes = int.from_bytes(stream.read(1), 'little')
    return int.from_bytes(stream.read(num_bytes), 'little')


def bej_pack_sfl(stream, seq_num, format, length):
    # pack seq num as nnint
    num_bytes = bej_pack_nnint(stream, seq_num, 0)

    # pack format
    format = format << 4
    num_bytes += stream.write(format.to_bytes(1, 'little'))

    # pack length as nnint
    num_bytes += bej_pack_nnint(stream, length, 0)

    return num_bytes


def bej_unpack_sfl(stream):
    # unpack seq
    seq = bej_unpack_nnint(stream)

    # unpack format
    format = int.from_bytes(stream.read(1), 'little') >> 4

    # unpack length
    length = bej_unpack_nnint(stream)

    return seq, format, length


def bej_pack_sflv_string(stream, seq_num, str):
    num_bytes_packed = bej_pack_sfl(stream, seq_num, BEJ_FORMAT_STRING, len(str) + 1)

    # pack str
    null = 0
    num_bytes_packed += stream.write(str.encode())
    num_bytes_packed += stream.write(null.to_bytes(1, 'little'))  # null termination

    return num_bytes_packed


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


def bej_pack_sflv_boolean(stream, seq_num, val):
    num_bytes_packed = bej_pack_sfl(stream, seq_num, BEJ_FORMAT_BOOLEAN, 1)

    # pack val
    if val == True:
        num_bytes_packed += stream.write(0x01.to_bytes(1, 'little'))
    else:
        num_bytes_packed += stream.write(0x00.to_bytes(1, 'little'))

    return num_bytes_packed


def bej_unpack_sflv_boolean(stream):
    seq, format, length = bej_unpack_sfl(stream)
    val = stream.read(length)

    bool_val = 'false'
    if val[0] == 0x01:
        bool_val = 'true'

    # the last byte in a string decode is the null terminator, remove that and return
    return bej_decode_sequence_number(seq), bool_val


def bej_pack_sflv_integer(stream, seq_num, value):
    num_bytes_for_value, msb = find_num_bytes_and_msb(value)

    # determine if padding is required to guarantee 2's complement
    is_padding_required = False
    if value > 0 and (msb & 0x80):
        # add one more byte to the msb to guarantee highest MSb is zero
        is_padding_required = True

    num_bytes_packed = bej_pack_sfl(stream, seq_num, BEJ_FORMAT_INTEGER,
                 num_bytes_for_value+1 if is_padding_required else num_bytes_for_value)

    # pack the value
    num_bytes_packed += stream.write(twos_complement(value, 64).to_bytes(8, 'little')[:num_bytes_for_value])
    # add padding if needed
    if is_padding_required:
        pad = 0
        num_bytes_packed += stream.write(pad.to_bytes(1, 'little'))

    return num_bytes_packed


def bej_unpack_sflv_integer(stream):
    seq, format, length = bej_unpack_sfl(stream)
    int_array = stream.read(length)
    return bej_decode_sequence_number(seq), int.from_bytes(int_array, 'little', signed=True)


def bej_pack_sflv_enum(stream, seq_num, value):
    num_bytes_packed = bej_pack_sfl(stream, seq_num, BEJ_FORMAT_ENUM, 1)
    num_bytes_packed += bej_pack_nnint(stream, value, 0)

    return num_bytes_packed


def bej_unpack_sflv_enum(stream):
    seq, format, length = bej_unpack_sfl(stream)
    value = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), value


def bej_pack_sflv_resource_link(stream, seq_num, pdr):
    num_bytes_packed = bej_pack_sfl(stream, seq_num, BEJ_FORMAT_RESOURCE_LINK, num_bytes_for_unsigned_integer(pdr)+1)
    num_bytes_packed += bej_pack_nnint(stream, pdr, 0)

    return num_bytes_packed


def bej_unpack_sflv_resource_link(stream):
    seq, format, length = bej_unpack_sfl(stream)
    value = bej_unpack_nnint(stream)

    return bej_decode_sequence_number(seq), value


def bej_unpack_sflv_null(stream):
    seq, format, length = bej_unpack_sfl(stream)
    return bej_decode_sequence_number(seq)

# Globals for bej set - Warning! not thread safe
bej_set_stream_stack = []


def bej_pack_set_start(stream, count):
    bej_set_stream_stack.append(stream)

    # construct a new stream to start adding set data and pack the count
    tmp_stream = io.BytesIO()
    bej_pack_nnint(tmp_stream, count, 0)

    return tmp_stream


def bej_pack_set_done(stream, seq_num):
    # pop the last stream from the stack and add the s, f and l. Length can now be determined from the current stream
    length = len(stream.getvalue())
    prev_stream = bej_set_stream_stack.pop()
    num_bytes_packed = bej_pack_sfl(prev_stream, seq_num, BEJ_FORMAT_SET, length)

    # append the current stream to the prev and return prev
    prev_stream.write(stream.getvalue())

    return num_bytes_packed + len(stream.getvalue())


def bej_pack_array_start(stream, count):
    bej_set_stream_stack.append(stream)

    # construct a new stream to start adding array data and pack the count
    tmp_stream = io.BytesIO()
    bej_pack_nnint(tmp_stream, count, 0)

    return tmp_stream


def bej_pack_array_done(stream, seq_num):
    # pop the last stream from the stack and add the s, f and l. Length can now be determined from the current stream
    length = len(stream.getvalue())
    prev_stream = bej_set_stream_stack.pop()
    num_bytes_packed = bej_pack_sfl(prev_stream, seq_num, BEJ_FORMAT_ARRAY, length)

    # append the current stream to the prev and return prev
    prev_stream.write(stream.getvalue())

    return num_bytes_packed + len(stream.getvalue())


def bej_pack_property_annotation_start(stream):
    bej_set_stream_stack.append(stream)

    # construct a new stream to start adding annotation data
    tmp_stream = io.BytesIO()
    return tmp_stream


def bej_pack_property_annotation_done(stream, annotation_seq):
    # pop the last stream from the stack and add the s, f and l. Length can now be determined from the current stream
    length = len(stream.getvalue())
    prev_stream = bej_set_stream_stack.pop()
    num_bytes_packed = bej_pack_sfl(prev_stream, annotation_seq, BEJ_FORMAT_PROPERTY_ANNOTATION, length)

    # append the current stream to the prev and return prev
    prev_stream.write(stream.getvalue())

    return num_bytes_packed + len(stream.getvalue())


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


DICTIONARY_ENTRY_FORMAT = 0
DICTIONARY_ENTRY_SEQUENCE_NUMBER = 1
DICTIONARY_ENTRY_OFFSET = 2
DICTIONARY_ENTRY_CHILD_COUNT = 3
DICTIONARY_ENTRY_NAME = 4


class DictionaryByteArrayStream:
    def __init__(self, byte_array, offset=0, child_count=-1):
        self._byte_array = byte_array
        self._current_index = offset
        self._child_count = child_count
        self._current_entry = 0

        if self._current_index == 0:
            # skip thru the header
            self.get_int(1)  # VersionTag
            self.get_int(1)  # DictionaryFlags
            self.get_int(4)  # SchemaVersion
            self._total_entries = self.get_int(2)  # EntryCount
            self.get_int(4)  # DictionarySize

            self._child_count = 1

    def get_offset(self):
        return self._current_index

    def get_child_count(self):
        return self._child_count

    def get_int(self, size):
        value = int.from_bytes(self._byte_array[self._current_index:self._current_index+size], 'little')
        self._current_index += size
        return value

    def has_entry(self):
        return self._current_entry < self._child_count

    def get_next_entry(self):
        entry = []
        current_entry = 0
        if self._current_entry < self._child_count or self._child_count == -1:

            entry.append(self.get_int(1) >> 4)  # format
            entry.append(self.get_int(2))  # sequence
            entry.append(self.get_int(2))  # offset
            entry.append(self.get_int(2))  # child_count

            name_length = self.get_int(1)
            name_offset = self.get_int(2)

            # fetch the name
            name = ''
            if name_length > 0:
                name = "".join(map(chr, self._byte_array[name_offset:name_offset+name_length-1])) # -1 to skip null terminator

            entry.append(name)

            if self._child_count != -1:
                self._current_entry += 1

        return entry


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


resource_link_to_pdr_map = {}
current_available_pdr = 0


def get_link_from_pdr_map(pdr):
    for key, value in resource_link_to_pdr_map.items():
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


def load_dictionary_subset_by_key_name(schema_dict, offset, child_count):
    schema_dict_stream = DictionaryByteArrayStream(schema_dict, offset, child_count)

    entry_dict = {}
    while schema_dict_stream.has_entry():
        entry = schema_dict_stream.get_next_entry()
        entry_dict[entry[DICTIONARY_ENTRY_NAME]] = entry

    return entry_dict


def is_payload_annotation(property):
    if '@' in property:
        return True
    return False


def get_annotation_parts(property):
    """
    Returns the schema property name (if present) and the annotation property name

    Returns: schema property name, annotation property name
    """
    m = re.compile('(.*)(@.*\..*)').match(property)

    return m.group(1), m.group(2)


def get_annotation_name(annotation_property):
    m = re.compile('.*@.*\.(.*)').match(annotation_property)
    return m.group(1)


odata_dictionary_entries = {}


def get_annotation_dictionary_entries(annot_dict):
    # TODO: cache the main annotations
    base_entry = DictionaryByteArrayStream(annot_dict, 0, -1).get_next_entry()
    return load_dictionary_subset_by_key_name(annot_dict, base_entry[DICTIONARY_ENTRY_OFFSET],
                                              base_entry[DICTIONARY_ENTRY_CHILD_COUNT])


def bej_encode_enum(output_stream, dict_to_use, dict_entry, sequence_number_with_dictionary_selector, enum_value):
    # get the sequence number for the enum value from the dictionary
    enum_dict_stream = DictionaryByteArrayStream(dict_to_use, dict_entry[DICTIONARY_ENTRY_OFFSET],
                                                 dict_entry[DICTIONARY_ENTRY_CHILD_COUNT])
    value = None
    while enum_dict_stream.has_entry():
        enum_entry = enum_dict_stream.get_next_entry()

        if enum_entry[DICTIONARY_ENTRY_NAME] == enum_value:
            value = enum_entry[DICTIONARY_ENTRY_SEQUENCE_NUMBER]
            break

    bej_pack_sflv_enum(output_stream, sequence_number_with_dictionary_selector, value)


def bej_encode_sflv(output_stream, schema_dict, annot_dict, dict_to_use, dict_entry, seq, format, json_value):
    success = True
    if format == BEJ_FORMAT_STRING:
        bej_pack_sflv_string(output_stream, seq, json_value)

    elif format == BEJ_FORMAT_INTEGER:
        bej_pack_sflv_integer(output_stream, seq, json_value)

    elif format == BEJ_FORMAT_BOOLEAN:
        bej_pack_sflv_boolean(output_stream, seq, json_value)

    elif format == BEJ_FORMAT_ENUM:
        bej_encode_enum(output_stream, dict_to_use, dict_entry, seq, json_value)

    elif format == BEJ_FORMAT_RESOURCE_LINK:
        global current_available_pdr
        # add an entry to the PDR
        if json_value not in resource_link_to_pdr_map:
            resource_link_to_pdr_map[json_value] = current_available_pdr
            current_available_pdr += 1
        new_pdr_num = resource_link_to_pdr_map[json_value]
        bej_pack_sflv_resource_link(output_stream, seq, new_pdr_num)

    elif format == BEJ_FORMAT_SET:
        nested_set_stream = bej_pack_set_start(output_stream, len(json_value))
        success = bej_encode_stream(nested_set_stream, json_value, schema_dict,
                                    annot_dict, dict_to_use, dict_entry[DICTIONARY_ENTRY_OFFSET],
                                    dict_entry[DICTIONARY_ENTRY_CHILD_COUNT])
        bej_pack_set_done(nested_set_stream, seq)

    elif format == BEJ_FORMAT_ARRAY:
        count = len(json_value)
        array_dict_stream = DictionaryByteArrayStream(dict_to_use, dict_entry[DICTIONARY_ENTRY_OFFSET],
                                                      dict_entry[DICTIONARY_ENTRY_CHILD_COUNT])
        array_dict_entry = array_dict_stream.get_next_entry()

        nested_stream = bej_pack_array_start(output_stream, count)
        tmp_seq, selector = bej_decode_sequence_number(seq)
        for i in range(0, count):
            success = bej_encode_sflv(nested_stream, schema_dict, annot_dict, dict_to_use, array_dict_entry,
                                      (i << 1) | selector, array_dict_entry[DICTIONARY_ENTRY_FORMAT],
                                      json_value[i])
            if not success:
                break

        bej_pack_array_done(nested_stream, seq)

    else:
        if verbose:
            print('Failed to encode value:', json_value)
        success = False

    return success


def bej_encode_stream(output_stream, json_data, schema_dict, annot_dict, dict_to_use, offset=0, child_count=-1):
    global current_available_pdr
    dict_entries = load_dictionary_subset_by_key_name(dict_to_use, offset, child_count)
    success = True

    for prop in json_data:
        if prop in dict_entries or is_payload_annotation(prop):
            tmp_dict_to_use = dict_to_use
            entry = []
            # dict_to_use = schema_dict
            dictionary_selector_bit_value = BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA

            if is_payload_annotation(prop):
                # two kinds - property annotation (e.g. Status@Message.ExtendedInfo) or payload annotation
                schema_property, annotation_property = get_annotation_parts(prop)
                entry = get_annotation_dictionary_entries(annot_dict)[annotation_property]
                dictionary_selector_bit_value = BEJ_DICTIONARY_SELECTOR_ANNOTATION
                tmp_dict_to_use = annot_dict

                if schema_property != '':  # this is a property annotation (e.g. Status@Message.ExtendedInfo)
                    prop_format = BEJ_FORMAT_PROPERTY_ANNOTATION
                else:
                    prop_format = entry[DICTIONARY_ENTRY_FORMAT]

            else:
                entry = dict_entries[prop]
                dictionary_selector_bit_value = BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA
                prop_format = entry[DICTIONARY_ENTRY_FORMAT]

            sequence_number_with_dictionary_selector = (entry[DICTIONARY_ENTRY_SEQUENCE_NUMBER] << 1) \
                                                       | dictionary_selector_bit_value

            if prop_format == BEJ_FORMAT_PROPERTY_ANNOTATION:
                # Seq(Annotation_name)
                #    Format(bejPropertyAnnotation)
                #        Length
                #            Seq(property sequence #)
                #                Format(format of annotation value)
                #                    Length
                #                        Value(value: can be a complex type)
                # e.g Status@Message.ExtendedInfo
                schema_property, annotation_property = get_annotation_parts(prop)
                prop_seq = (dict_entries[schema_property][DICTIONARY_ENTRY_SEQUENCE_NUMBER] << 1) \
                           | BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA

                nested_stream = bej_pack_property_annotation_start(output_stream)

                success = bej_encode_sflv(nested_stream, schema_dict, annot_dict, tmp_dict_to_use, entry,
                                          sequence_number_with_dictionary_selector, entry[DICTIONARY_ENTRY_FORMAT],
                                          json_data[prop])

                bej_pack_property_annotation_done(nested_stream, prop_seq)
            else:
                success = bej_encode_sflv(output_stream, schema_dict, annot_dict, tmp_dict_to_use, entry,
                                          sequence_number_with_dictionary_selector, prop_format, json_data[prop])
        else:
            if verbose:
                print('Property cannot be encoded - missing dictionary entry', prop)
            success = False

        if not success:
            break

    return success


def bej_encode(output_stream, json_data, schema_dict, annot_dict):
    # Add header info
    output_stream.write(0xF1F0F000.to_bytes(4, 'little'))  # BEJ Version
    output_stream.write(0x0000.to_bytes(2, 'little'))  # BEJ flags
    output_stream.write(0x00.to_bytes(1, 'little'))  # schemaClass - MAJOR only for now

    # Encode the bejTuple
    new_stream = bej_pack_set_start(output_stream, len(json_data))
    dict_stream = DictionaryByteArrayStream(schema_dict)
    entry = dict_stream.get_next_entry()
    success = bej_encode_stream(new_stream, json_data, schema_dict, annot_dict, schema_dict, entry[DICTIONARY_ENTRY_OFFSET],
                                entry[DICTIONARY_ENTRY_CHILD_COUNT])
    if success:
        bej_pack_set_done(new_stream, 0)
    return success, resource_link_to_pdr_map


def get_seq_and_dictionary_selector(seq):
    return seq >> 1, seq & 0x01


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


def bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream):
    if selector == BEJ_DICTIONARY_SELECTOR_ANNOTATION:
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


def bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict, entries_by_seq, prop_count,
                      is_seq_array_index, add_name, deferred_binding_strings):
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
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            dict_to_use = schema_dict if selector is BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA else annot_dict
            output_stream.write('{')

            success = bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict,
                                        load_dictionary_subset_by_key_sequence(
                                            dict_to_use, entry[DICTIONARY_ENTRY_OFFSET], entry[DICTIONARY_ENTRY_CHILD_COUNT]),
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
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            if is_deferred_binding:
                bindings_to_resolve = re.findall('%.*?%', value)
                for binding in bindings_to_resolve:
                    if binding in deferred_binding_strings:
                        value = value.replace(binding, deferred_binding_strings[binding])

            output_stream.write('"' + value + '"')

        elif format == BEJ_FORMAT_INTEGER:
            [seq, selector], value = bej_unpack_sflv_integer(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            output_stream.write(str(value))

        elif format == BEJ_FORMAT_BOOLEAN:
            [seq, selector], value = bej_unpack_sflv_boolean(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            output_stream.write(value)

        elif format == BEJ_FORMAT_RESOURCE_LINK:
            [seq, selector], pdr = bej_unpack_sflv_resource_link(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            output_stream.write('"' + get_link_from_pdr_map(pdr) + '"')

        elif format == BEJ_FORMAT_ENUM:
            [seq, selector], value = bej_unpack_sflv_enum(input_stream)
            if is_seq_array_index:
                seq = 0

            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            enum_value = bej_decode_enum_value(schema_dict, entries_by_seq[seq], value)
            output_stream.write('"' + enum_value + '"')

        elif format == BEJ_FORMAT_NULL:
            [seq, selector] = bej_unpack_sflv_null(input_stream)
            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            output_stream.write('null')

        elif format == BEJ_FORMAT_ARRAY:
            array_start_pos = input_stream.tell()
            [seq, selector], length, array_member_count = bej_unpack_array_start(input_stream)
            if is_seq_array_index:
                seq = 0

            entry = entries_by_seq[seq]

            if add_name:
                bej_decode_name(annot_dict, seq, selector, entries_by_seq, output_stream)

            dict_to_use = schema_dict if selector is BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA else annot_dict
            output_stream.write('[')
            for i in range(0, array_member_count):
                success = bej_decode_stream(output_stream, input_stream, schema_dict, annot_dict,
                                            load_dictionary_subset_by_key_sequence(dict_to_use, entry[DICTIONARY_ENTRY_OFFSET],
                                                                                   entry[DICTIONARY_ENTRY_CHILD_COUNT]),
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
                                        prop_count=1, is_seq_array_index=False, add_name=False,
                                        deferred_binding_strings=deferred_binding_strings)
        else:
            if verbose:
                print('Unable to decode')
            success = False

        if index < prop_count-1:
            output_stream.write(',')
        index += 1

    return success


def bej_decode(output_stream, input_stream, schema_dictionary, annotation_dictionary, pdr_map,
               def_binding_strings):
    global resource_link_to_pdr_map
    resource_link_to_pdr_map = pdr_map
    # strip off the headers
    version = input_stream.read(4)
    assert(version == bytes([0x00, 0xF0, 0xF0, 0xF1]))
    flags = input_stream.read(2)
    assert (flags == bytes([0x00, 0x00]))
    schemaClass = input_stream.read(1)
    assert(schemaClass == bytes([0x00]))

    return bej_decode_stream(output_stream, input_stream, schema_dictionary, annotation_dictionary,
                             load_dictionary_subset_by_key_sequence(schema_dictionary, 0, -1),
                             1, is_seq_array_index=False, add_name=False,
                             deferred_binding_strings=def_binding_strings)


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
        total_json_size = len(json.dumps(json_to_encode, separators=(',', ':')))

        # create a byte stream
        output_stream = io.BytesIO()
        success, pdr_map = bej_encode(output_stream, json_to_encode, schema_dictionary, annotation_dictionary)
        if success:
            encoded_bytes = output_stream.getvalue()
            if not silent:
                print_hex(encoded_bytes)
                print('JSON size:', total_json_size)
                print('Total encode size:', len(encoded_bytes))
                print('Compression ratio(%):', (1.0 - len(encoded_bytes)/total_json_size)*100)

            if args.bejOutputFile:
                args.bejOutputFile.write(encoded_bytes)

            if args.pdrMapFile:
                args.pdrMapFile.write(json.dumps(resource_link_to_pdr_map))
        else:
            if not silent:
                print('Failed to encode JSON')

    elif args.operation == 'decode':
        # Read the encoded bytes
        bej_encoded_bytes = list(args.bejEncodedFile.read())

        pdr_map = resource_link_to_pdr_map
        if args.pdrMapFile:
            pdr_map = json.loads(args.pdrMapFile.read())

        input_stream = io.BytesIO(bytes(bej_encoded_bytes))
        output_stream = io.StringIO()
        success = bej_decode(output_stream, input_stream, schema_dictionary, annotation_dictionary, pdr_map, {})
        if success:
            if not silent:
                print(json.dumps(json.loads(output_stream.getvalue()), indent=3))
        else:
            if not silent:
                print('Failed to decode JSON')

