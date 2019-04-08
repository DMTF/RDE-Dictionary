from behave import *
import re
import os
import sys
from ctypes import *
import io
import json
#sys.path.append('../..')
import rdebej.dictionary
import rdebej.encode
import rdebej.decode


class DictionaryHeader(LittleEndianStructure):
    _pack_ = 1

    _fields_ = [
        ('VersionTag', c_uint8),
        ('DictionaryFlags', c_uint8),
        ('EntryCount', c_uint16),
        ('SchemaVersion', c_uint32),
        ('DictionarySize', c_uint32)
    ]


@given('a CSDL schema file {Schema} and entity {Entity}')
def step_impl(context, Schema, Entity):
    context.Schema = Schema
    context.Entity = Entity
    is_found = False
    for dir in context.csdl_dirs:
        if os.path.isfile(dir + '//' + Schema):
            is_found = True

    assert is_found, "Could not find %s" % (Schema)


@given('a list of schema files')
def step_impl(context):
    context.schemas = []
    for dir in context.csdl_dirs:
        context.schemas += os.listdir(dir)
    assert context.schemas and len(context.schemas) > 0


@when('the dictionary is generated')
def step_impl(context):
    dict = rdebej.dictionary.generate_schema_dictionary(
        'local',
        context.csdl_dirs,
        context.json_schema_dirs,
        context.Entity, context.Schema,
        oem_entities=None,
        oem_schema_file_names=None,
        profile=None,
        schema_url=None,
        copyright=None)

    assert dict.dictionary, "Could not generate dictionary for %s:%s" % (context.Schema, context.Entity)
    assert dict.dictionary_byte_array, "Could not generate byte array dictionary for %s:%s" % (context.Schema, context.Entity)
    assert dict.json_dictionary, "Could not generate json dictionary for %s:%s" % (context.Schema, context.Entity)

    context.dictionary = dict


@then('the dictionary header shall have the {Property} {Comparison} {Value:h}')
def step_impl(context, Property, Comparison, Value):
    header = DictionaryHeader.from_buffer_copy(bytearray(context.dictionary.dictionary_byte_array))

    if Comparison == 'not equal to':
        assert getattr(header, Property) != Value, "Expected %s, Actual %s" % (Value, getattr(header, Property))
    if Comparison == 'equal to':
        assert getattr(header, Property) == Value, "Expected %s, Actual %s" % (Value, getattr(header, Property))
    elif Comparison == 'greater than':
        assert getattr(header, Property) > Value, "Expected %s, Actual %s" % (Value, getattr(header, Property))


@then('the resulting dictionaries have valid header information')
def step_impl(context):
    skip_list = ['IPAddresses_v1.xml', 'Privileges_v1.xml', 'RedfishExtensions_v1.xml', 'Resource_v1.xml']
    for filename in context.schemas:
        if filename not in skip_list:
            # strip out the _v1.xml
            m = re.compile('(.*)_v1.xml').match(filename)
            entity = ''
            if m:
                entity = m.group(1) + '.' + m.group(1)

            context.execute_steps(u'''
                Given a CSDL schema file %s and entity %s
                When the dictionary is generated
                Then the dictionary header shall have the VersionTag equal to 0x00
                And the dictionary header shall have the DictionaryFlags equal to 0x00
                And the dictionary header shall have the EntryCount greater than 0x00
                And the dictionary header shall have the SchemaVersion greater than 0x00
                And the dictionary header shall have the DictionarySize greater than 0x00
                ''' % (filename, entity))


@then('the following JSON is encoded using the dictionary successfully')
def step_impl(context):
    bej_stream = io.BytesIO()
    context.json_to_encode = json.loads(context.text)

    context.annotation_dictionary = rdebej.dictionary.generate_annotation_schema_dictionary(
        context.csdl_dirs,
        context.json_schema_dirs,
        'v1_0_0'
    )

    encode_success, pdr_map = rdebej.encode.bej_encode(bej_stream, context.json_to_encode,
                                                       context.dictionary.dictionary_byte_array,
                                                       context.annotation_dictionary.dictionary_byte_array,
                                                       verbose=True)

    assert encode_success, 'Encode failure'

    context.bej_encoded_bytes = bej_stream.getvalue()
    context.pdr_map = pdr_map


@then('the BEJ can be successfully decoded back to JSON')
def step_impl(context):

    # build the deferred binding strings from the pdr_map
    deferred_binding_strings = {}
    for url, pdr_num in context.pdr_map.items():
        deferred_binding_strings['%L' + str(pdr_num)] = url

    decode_stream = io.StringIO()
    decode_success = rdebej.decode.bej_decode(
        decode_stream,
        io.BytesIO(bytes(context.bej_encoded_bytes)),
        context.dictionary.dictionary_byte_array,
        context.annotation_dictionary.dictionary_byte_array,
        [], context.pdr_map, deferred_binding_strings
        )

    assert decode_success, 'Decode failure'
    decode_file = decode_stream.getvalue()
    assert json.loads(decode_file) == context.json_to_encode, 'Mismatch in original JSON and decoded JSON'
