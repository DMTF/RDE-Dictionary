from behave import *
import re
import os
import sys
from ctypes import *

#sys.path.append('../..')
import rdebej.dictionary


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
    assert os.path.isfile(context.schema_dir + '/metadata/' + Schema), \
        "Could not find %s" % (context.schema_dir + '/metadata/' + Schema)


@given('a list of schema files')
def step_impl(context):
    context.schemas = os.listdir(context.schema_dir + '/metadata/')
    assert context.schemas and len(context.schemas) > 0


@when('the dictionary is generated')
def step_impl(context):
    dict = rdebej.dictionary.generate_schema_dictionary(
        'local',
        [context.schema_dir + '/metadata/'],
        [context.schema_dir + '/json-schema/'],
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
