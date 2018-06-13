
"""
RDE Dictionary Builder

File : rde-dictionary-builder.py

Brief : This file contains the definitions and functionalities for generating
        a RDE schema dictionary from a set of standard Redfish CSDL and JSON Schema
        files
"""

from lxml import etree
import argparse
import json
import re
import os.path
from operator import itemgetter
import pprint
from tabulate import tabulate
import urllib.request
import sys
from collections import Counter

# dict to build a list of namespaces that will be used to build the d
includeNamespaces = {}

# OData types
ODATA_ENUM_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EnumType'
ODATA_COMPLEX_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}ComplexType'
ODATA_TYPE_DEFINITION = '{http://docs.oasis-open.org/odata/ns/edm}TypeDefinition'
ODATA_ENTITY_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EntityType'
ODATA_NAVIGATION_PROPERTY = '{http://docs.oasis-open.org/odata/ns/edm}NavigationProperty'
ODATA_ACTION_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}Action'
ODATA_TERM_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}Term'
ODATA_ALL_NAMESPACES = {'edm': 'http://docs.oasis-open.org/odata/ns/edm', 'edmx': 'http://docs.oasis-open.org/odata/ns/edmx'}

# Optimization: check to see if dictionary already contains an entry for the complex type/enum.
# If yes, then just reuse it instead of creating a new set of entries.
OPTIMIZE_REDUNDANT_DICTIONARY_ENTRIES = True

# Dictionary indices
DICTIONARY_ENTRY_INDEX = 0
DICTIONARY_ENTRY_SEQUENCE_NUMBER = 1
DICTIONARY_ENTRY_FORMAT = 2
DICTIONARY_ENTRY_FORMAT_FLAGS = 3
DICTIONARY_ENTRY_FIELD_STRING = 4
DICTIONARY_ENTRY_CHILD_COUNT = 5
DICTIONARY_ENTRY_OFFSET = 6

ENTITY_REPO_TUPLE_TYPE_INDEX = 0
ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX = 1


def get_base_properties(entity_type):
    """
    Constructs a list of base properties that are inherited by entity_type

    Args:
        entity_type: The EntityType or ComplexType whose base properties need to be constructed
    """

    properties = []
    if entity_type.get('BaseType') is not None:
        base_type = entity_type.get('BaseType')
        base_entity = get_base_type(entity_type)
        properties = get_properties(base_entity)
        properties = properties + get_base_properties(base_entity)

    return properties


def strip_version(val):
    """
    Removes version information and returns the Namespace.EntitytypeName

    Args:
        val: string in the format of Namespace.v_Major_Minor_Errata.EntityName
    """

    m = re.compile('(\w+)\.v.*?\.(\w+)').search(val)
    if m:
        return m.group(1) + '.' + m.group(2)
    return val


def get_primitive_type(property_type):
    m = re.compile('Edm\.(.*)').match(property_type)
    if m:  # primitive type?
        primitive_type = m.group(1)
        if primitive_type == "DateTimeOffset" or primitive_type == "Duration" or primitive_type == "TimeOfDay" \
                or primitive_type == "Guid":
            primitive_type = 'String'
        if ((primitive_type == "SByte") or (primitive_type == "Int16") or (primitive_type == "Int32") or
                (primitive_type == "Int64") or (primitive_type == "Decimal")):
            primitive_type = 'Integer'
        return primitive_type
    return ''

PROPERTY_SEQ_NUMBER = 0
PROPERTY_FIELD_STRING = 1
PROPERTY_TYPE = 2
PROPERTY_FLAGS = 3
PROPERTY_OFFSET = 4
PROPERTY_EXPAND = 5


def is_property_nullable(property):
    property_is_nullable = True
    if property.get('Nullable') is not None:
        property_is_nullable = property.get('Nullable') == 'true'
    return property_is_nullable


def get_property_permissions(property):
    permissions = property.xpath('child::edm:Annotation[@Term=\'OData.Permissions\']', namespaces=ODATA_ALL_NAMESPACES)
    if len(permissions) == 1:
        return 'Permission=' + permissions[0].get('EnumMember')[len('OData.Permission/'):]
    return ''


def get_properties(some_type, path='descendant-or-self::edm:Property | edm:NavigationProperty'):
    properties = []
    property_elements = some_type.xpath(path, namespaces=ODATA_ALL_NAMESPACES)
    for property_element in property_elements:
        property_name = property_element.get('Name')

        property_type = property_element.get('Type')

        property_is_nullable_flag = 'Nullable=False'
        if is_property_nullable(property_element):
            property_is_nullable_flag = 'Nullable=True'

        property_permissions = get_property_permissions(property_element)

        property_flags = property_is_nullable_flag + ',' + property_permissions

        is_auto_expand = property_element.tag != ODATA_NAVIGATION_PROPERTY \
            or (property_element.tag == ODATA_NAVIGATION_PROPERTY
                and len(property_element.xpath('child::edm:Annotation[@Term=\'OData.AutoExpand\']',
                                               namespaces=ODATA_ALL_NAMESPACES)))
        is_auto_expand_refs = not is_auto_expand

        primitive_type = get_primitive_type(property_type)
        if primitive_type != '':  # primitive type?
            properties.append([property_name, primitive_type, property_flags, ''])
        else:  # complex type
            complex_type = None
            is_array = re.compile('Collection\((.*?)\)').match(property_type)
            if is_array:
                if is_auto_expand_refs:
                    # TODO fix references
                    # properties.append([propertyName, 'Array', strip_version(m.group(1)), 'AutoExpandRef'])
                    properties.append([property_name, 'Array', property_flags, 'AutoExpandRef'])
                else:  # AutoExpand or not specified
                    array_type = is_array.group(1)

                    if array_type.startswith('Edm.'):  # primitive types
                        properties.append([property_name, 'Array', property_flags, array_type, ''])
                    else:
                        properties.append([property_name, 'Array', property_flags, strip_version(is_array.group(1)), 'AutoExpand'])

            else:
                complex_type = find_element_from_type(property_type)

            if complex_type is not None:
                if complex_type.tag == ODATA_ENUM_TYPE:
                    properties.append([property_name, 'Enum', property_flags, strip_version(property_type)])
                elif complex_type.tag == ODATA_COMPLEX_TYPE or complex_type.tag == ODATA_ENTITY_TYPE:
                    if is_auto_expand_refs:
                        properties.append([property_name, 'ResourceLink', property_flags, ''])
                    else:
                        properties.append([property_name, 'Set', property_flags, strip_version(property_type)])
                elif complex_type.tag == ODATA_TYPE_DEFINITION:
                    assert(re.compile('Edm\..*').match(complex_type.get('UnderlyingType')))
                    m = re.compile('Edm\.(.*)').match(complex_type.get('UnderlyingType'))
                    properties.append([property_name, m.group(1), property_flags, ''])
                else:
                    if args.verbose:
                        print(complex_type.tag)
                    assert False

    return properties


def get_namespace(entity_type):
    namespace = entity_type.xpath('parent::edm:Schema', namespaces=ODATA_ALL_NAMESPACES)[0].get('Namespace')
    if namespace.find('.') != -1:
        m = re.search('(\w*?)\.v.*', namespace)
        if m:
            namespace = m.group(1)
        else:
            namespace = ''
    return namespace


def get_qualified_entity_name(entity):
    return get_namespace(entity) + '.' + entity.get('Name')


def extract_doc_name_from_url(url):
    m = re.compile('http://.*/(.*\.xml)').match(url)
    if m:
        return m.group(1)
    else:
        return ''


def add_annotation_terms(doc, entity_repo):
    for namespace in doc.xpath('//edm:Schema', namespaces=ODATA_ALL_NAMESPACES):
        terms = get_properties(namespace, path='descendant-or-self::edm:Term')

        namespace_name = namespace.get('Namespace')

        # RedfishExtensions is aliased to Redfish. So rename here
        if namespace_name.startswith('RedfishExtensions'):
            namespace_name = 'Redfish'

        if namespace_name not in entity_repo:
            entity_repo[namespace_name] = ('Set', [])

        entity_repo[namespace_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
            [item for item in sorted(terms, key=itemgetter(0))
             if item not in entity_repo[namespace_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]])


def add_entity_and_complex_types(doc, entity_repo):
    for entity_type in doc.xpath('//edm:EntityType | //edm:ComplexType', namespaces=ODATA_ALL_NAMESPACES):
        properties = []
        if is_abstract(entity_type) is not True:
            if is_parent_abstract(entity_type):
                properties = get_base_properties(entity_type)

            properties = properties + get_properties(entity_type)

            # add the entity only if it has at least one property
            if len(properties):
                entity_type_name = get_qualified_entity_name(entity_type)
                if entity_type_name not in entity_repo:
                    entity_repo[entity_type_name] = ('Set', [])

                # sort and add to the map
                # add only unique entries - this is to handle Swordfish vs Redfish conflicting schema (e.g. Volume)
                entity_repo[entity_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
                    [item for item in sorted(properties, key=itemgetter(0))
                     if item not in entity_repo[entity_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
                )

    for enum_type in doc.xpath('//edm:EnumType', namespaces=ODATA_ALL_NAMESPACES):
        enum_type_name = get_qualified_entity_name(enum_type)
        if enum_type_name not in entity_repo:
            entity_repo[enum_type_name] = ('Enum', [])
        entity_repo[enum_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
            [[enum] for enum in enum_type.xpath('child::edm:Member/@Name', namespaces=ODATA_ALL_NAMESPACES)
             if [enum] not in entity_repo[enum_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
        )


def add_actions(doc, entity_repo):
    # Handle Actions
    for actionType in doc.xpath('//edm:Action', namespaces=ODATA_ALL_NAMESPACES):
        # the first parameter is the binding parameter. Skip it
        parameters_iter = iter(actionType.xpath('child::edm:Parameter', namespaces=ODATA_ALL_NAMESPACES))
        binding_parameter = next(parameters_iter)
        action_entity_type = strip_version(binding_parameter.get('Type'))

        if action_entity_type not in entity_repo:
            entity_repo[action_entity_type] = ('Set', [])

        entity_repo[action_entity_type][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append(
            [actionType.get('Name'), 'Set', '', get_qualified_entity_name(actionType)])

        if get_qualified_entity_name(actionType) not in entity_repo:
            entity_repo[get_qualified_entity_name(actionType)] = ('Set', [])

        properties = []

        for parameter in parameters_iter:
            properties = properties + get_properties(parameter, path='descendant-or-self::edm:Parameter')

        # sort and add to the map
        # add only unique entries - this is to handle Swordfish vs Redfish conflicting schema (e.g. Volume)
        entity_repo[get_qualified_entity_name(actionType)][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
            [item for item in sorted(properties, key=itemgetter(0))
             if item not in entity_repo[get_qualified_entity_name(actionType)][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
        )


def add_namespaces(source, doc_list):
    doc_name = source
    schema_string = ''
    if args.source == 'remote':
        doc_name = extract_doc_name_from_url(source)

    # first load the CSDL file as a string
    if doc_name not in doc_list:
        if args.source == 'remote':
            # ignore odata references
            if source.find('http://docs.oasis') == -1:
                try:
                    if args.verbose:
                        print('Opening URL', source)
                    schema_string = urllib.request.urlopen(source).read()
                except:
                    # skip if we cannot bring the file down
                    return
        else:
            with open(source, 'rb') as local_file:
                schema_string = local_file.read()

    if schema_string != '':
        doc = etree.fromstring(schema_string)
        doc_list[doc_name] = doc
        # load all namespaces in the current doc
        for namespace in doc.xpath('descendant-or-self::edm:Schema[@Namespace]', namespaces=ODATA_ALL_NAMESPACES):
            if namespace.get('Namespace') not in includeNamespaces:
                includeNamespaces[namespace.get('Namespace')] = namespace
            else:
                return

        # bring in all dependent documents and their corresponding namespaces
        for ref in doc.xpath('descendant-or-self::edmx:Reference', namespaces=ODATA_ALL_NAMESPACES):
            if args.source == 'remote':
                dependent_source = ref.get('Uri')
            else:
                dependent_source = args.schemaDir + '/metadata/' + extract_doc_name_from_url(ref.get('Uri'))
                if os.path.exists(dependent_source) is False:
                    continue
                if args.verbose:
                    print(dependent_source)
            add_namespaces(dependent_source, doc_list)


def find_enum(key, dictionary):
    for k, v in dictionary.items():
        if k == key and "enum" in v:
            return v
        elif isinstance(v, dict):
            f = find_enum(key, v)
            if f is not None and "enum" in f:
                return f
    return None


def fix_enums(entity_repo, key):
    if entity_repo[key][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
        # build a list of json schema files that need to be scanned for the enum in question
        [base_filename, enum_name] = key.split('.')
        if args.verbose:
            print("Need to look at json schema to fix enums for", key, base_filename)
        enum_values = []
        for file in os.listdir(args.schemaDir + '/json-schema/'):
            if file.startswith(base_filename + '.'):
                json_schema = json.load(open(args.schemaDir + '/json-schema/' + file))
                # search json schema for enum

                if args.verbose:
                    print("Looking for", enum_name, "in", args.schemaDir + '/json-schema/' + file)
                json_enum = find_enum(enum_name, json_schema)
                if json_enum is not None:
                    if args.verbose:
                        print(json_enum["enum"])
                    enum_values = enum_values + list((Counter(json_enum["enum"]) - Counter(enum_values)).elements())
                    if args.verbose:
                        print(enum_values)

        if len(enum_values):
            # entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX] = [[enum] for enum in enum_values]
            del entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX][:]
            entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend([[enum] for enum in enum_values])


def add_all_entity_and_complex_types(doc_list, entity_repo):
    for key in doc_list:
        add_entity_and_complex_types(doc_list[key], entity_repo)
        add_actions(doc_list[key], entity_repo)
        add_annotation_terms(doc_list[key], entity_repo)

    # add special ones for AutoExpandRefs
    #entity_repo['AutoExpandRef'] = ('Set', [['@odata.id', 'String', '']])
    # entity_repo['AutoExpandRef'] = ('Set', [['', 'Set', '']])

    # second pass, add seq numbers
    for key in entity_repo:
        # TODO: Fix enums (works only for local mode currently)
        if args.source == 'local' and entity_repo[key][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
            fix_enums(entity_repo, key)

        for seq, item in enumerate(entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            item.insert(0, seq)


def get_base_type(child):
    if child.get('BaseType') is not None:
        m = re.compile('(.*)\.(\w*)').match(child.get('BaseType'))
        base_namespace = m.group(1)
        base_entity_name = m.group(2)
        return includeNamespaces[base_namespace].xpath(
            'child::edm:EntityType[@Name=\'%s\'] | child::edm:ComplexType[@Name=\'%s\']' % (base_entity_name,
                                                                                            base_entity_name),
            namespaces=ODATA_ALL_NAMESPACES)[0]


def is_parent_abstract(entity_type):
    base_entity = get_base_type(entity_type)
    return (base_entity is not None) and (base_entity.get('Abstract') == 'true')


def is_abstract(entity_type):
    return (entity_type is not None) and (entity_type.get('Abstract') == 'true')


def find_element_from_type(type):
    m = re.compile('(.*)\.(\w*)').match(type)
    namespace = m.group(1)
    entity_name = m.group(2)

    # TODO assert here instead of returning None to let users know that all referenced schema files are not available
    if namespace in includeNamespaces:
        return includeNamespaces[namespace].xpath('child::edm:*[@Name=\'%s\']' % entity_name,
                                                  namespaces=ODATA_ALL_NAMESPACES)[0]
    return None


def print_table_data(data):
    print(tabulate(data, headers="firstrow", tablefmt="grid"))


def add_dictionary_row(dictionary, index, seq_num, format, format_flags, field_string, child_count, offset):
    dictionary.append([index, seq_num, format, format_flags, field_string, child_count, offset])


def add_dictionary_entries(schema_dictionary, entity_repo, entity):
    if entity in entity_repo:
        entity_type = entity_repo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX]
        start = len(schema_dictionary)

        if len(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]) == 0:
            if entity_type not in entity_offset_map:
                add_dictionary_row(schema_dictionary, start, 0, entity_type, '', '', 0, '')

                # store off into the entity offset map to reuse for other entries that use
                # the same entity type
                entity_offset_map[entity_type] = (start, 0)
            else:
                start = entity_offset_map[entity_type][0]

            return 1, start

        index = 0
        for index, property in enumerate(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            if entity_type == 'Enum':  # this is an enum
                add_dictionary_row(schema_dictionary, index + start, property[PROPERTY_SEQ_NUMBER], 'String', '',
                                   property[PROPERTY_FIELD_STRING], 0, '')

            elif property[PROPERTY_TYPE] == 'Array':  # this is an array
                add_dictionary_row(schema_dictionary, index + start, property[PROPERTY_SEQ_NUMBER],
                                   property[PROPERTY_TYPE], property[PROPERTY_FLAGS], property[PROPERTY_FIELD_STRING],
                                   0, property[PROPERTY_OFFSET])

            else:
                add_dictionary_row(schema_dictionary, index + start, property[PROPERTY_SEQ_NUMBER],
                                   property[PROPERTY_TYPE], property[PROPERTY_FLAGS], property[PROPERTY_FIELD_STRING],
                                   0, property[PROPERTY_OFFSET])

        return index + 1, start
    else:
        #  Add a simple entry
        start = len(schema_dictionary)
        simple_type = 'Set'
        primitive_type = get_primitive_type(entity)
        if primitive_type != '':
            simple_type = primitive_type

        if simple_type not in entity_offset_map:
            add_dictionary_row(schema_dictionary, start, 0, simple_type, '', '', 0, '')

            # store off into the entity offset map to reuse for other entries that use
            # the same primitive type
            entity_offset_map[simple_type] = (start, 0)
        else:
            start = entity_offset_map[simple_type][0]

        return 1, start
    return 0, 0


def print_dictionary_summary(schema_dictionary):
    print("Total Entries:", len(schema_dictionary))
    print("Fixed size consumed:", 10 * len(schema_dictionary))
    # calculate size of free form property names:
    total_field_string_size = 0
    for item in schema_dictionary:
        total_field_string_size = total_field_string_size + len(item[DICTIONARY_ENTRY_FIELD_STRING])
    print("Field string size consumed:", total_field_string_size)
    print('Total size:', 10 * len(schema_dictionary) + total_field_string_size)


def to_format(format):
    if format == 'Set':
        return '0x00'
    elif format == 'Array':
        return '0x01'
    elif format == 'Integer':
        return '0x03'
    elif format == 'Enum':
        return '0x04'
    elif format == 'String  ':
        return '0x05'
    elif format == 'Boolean':
        return '0x07'
    elif format == 'ResourceLink':
        return '0x0F'


# TODO
def generate_byte_array(schema_dictionary):
    # first entry is the schema entity
    print('const uint8', schema_dictionary[0][DICTIONARY_ENTRY_FIELD_STRING].split('.')[1]
          + '_schema_dictionary[]= { 0x00, 0x00')

    iter_schema = iter(schema_dictionary)
    next(iter_schema)  # skip the first entry since it is the schema entity
    for item in iter_schema:
        print(to_format(item[DICTIONARY_ENTRY_FORMAT]))
        pass


entity_offset_map = {}


def find_item_offset_and_size(schema_dictionary, item_to_find):
    if item_to_find in entity_offset_map:
        return entity_offset_map[item_to_find][0];
    return 0


def generate_dictionary(dictionary, optimize_duplicate_items=True):
    can_expand = True
    while can_expand:
        tmp_dictionary = dictionary.copy()
        was_expanded = False
        for index, item in enumerate(dictionary):
            if (type(item[DICTIONARY_ENTRY_OFFSET]) == str
                    and item[DICTIONARY_ENTRY_OFFSET] != ''
                    and (item[DICTIONARY_ENTRY_FORMAT] == 'Set'
                         or item[DICTIONARY_ENTRY_FORMAT] == 'Enum'
                         or item[DICTIONARY_ENTRY_FORMAT] == 'Array'
                         or item[DICTIONARY_ENTRY_FORMAT] == 'Namespace')):

                # optimization: check to see if dictionary already contains an entry for the complex type/enum.
                # If yes, then just reuse it instead of creating a new set of entries.
                offset = 0
                num_entries = 0
                if optimize_duplicate_items:
                    if item[DICTIONARY_ENTRY_OFFSET] in entity_offset_map:
                        offset = entity_offset_map[item[DICTIONARY_ENTRY_OFFSET]][0]
                        num_entries = entity_offset_map[item[DICTIONARY_ENTRY_OFFSET]][1]

                if offset == 0:
                    offset = len(tmp_dictionary)

                    item_type = item[DICTIONARY_ENTRY_OFFSET]
                    if item_type in entity_repo:
                        item_type = entity_repo[item[DICTIONARY_ENTRY_OFFSET]][ENTITY_REPO_TUPLE_TYPE_INDEX]

                    num_entries, offset = add_dictionary_entries(tmp_dictionary, entity_repo, item[DICTIONARY_ENTRY_OFFSET])

                    entity_offset_map[item[DICTIONARY_ENTRY_OFFSET]] = (offset, num_entries)

                tmp_dictionary[index][DICTIONARY_ENTRY_OFFSET] = offset
                tmp_dictionary[index][DICTIONARY_ENTRY_CHILD_COUNT] = num_entries
                was_expanded = True
                break
        if was_expanded:
            dictionary = tmp_dictionary.copy()
        else:
            can_expand = False

    return dictionary


def add_redfish_annotations(annotation_dictionary):
    pass


ANNOTATION_DICTIONARY_ODATA_ENTRY = 1
ANNOTATION_DICTIONARY_MESSAGE_ENTRY = 2
ANNOTATION_DICTIONARY_REDFISH_ENTRY = 3
ANNOTATION_DICTIONARY_RESERVED_ENTRY = 4


def add_odata_annotations(annotation_dictionary, odata_annotation_location):
    json_schema = json.load(open(odata_annotation_location))
    offset = len(annotation_dictionary)
    count = 0
    for k, v in json_schema["definitions"].items():
        bej_format = ''
        json_format = v['type']
        if json_format == 'string':
            bej_format = 'String'
        elif json_format == 'number':
            bej_format = 'Integer'
        elif json_format == 'object':
            # TODO expand object
            bej_format = 'Set'
        else:
            print('Unknown format')

        add_dictionary_row(annotation_dictionary, offset, offset - 5, bej_format, '', k, 0, '')
        offset = offset + 1
        count = count + 1

    return count


def fix_annotations_sequence_numbers(annotation_dictionary, annotation_index, stripe_factor):
    start_of_annotation_dictionary = annotation_dictionary[annotation_index][DICTIONARY_ENTRY_OFFSET]
    num_annotation_dictionary_entries = annotation_dictionary[annotation_index][DICTIONARY_ENTRY_CHILD_COUNT]
    for index in range(start_of_annotation_dictionary,
                       start_of_annotation_dictionary+num_annotation_dictionary_entries):
        annotation_dictionary[index][DICTIONARY_ENTRY_SEQUENCE_NUMBER] = \
            (annotation_dictionary[index][DICTIONARY_ENTRY_SEQUENCE_NUMBER] << 2) | stripe_factor

def generate_annotation_dictionary():
    annotation_dictionary = []
    # TODO: Currently only local is supported
    if args.source == 'local':
        # first 4 entries
        odata_row_index = 1
        message_row_index = 2
        redfish_row_index = 3
        add_dictionary_row(annotation_dictionary, 0, 0, "Set", '', "annotation", 4, 1)
        add_dictionary_row(annotation_dictionary, odata_row_index, 0, "Set", '', "odata", 0, 5)
        add_dictionary_row(annotation_dictionary, message_row_index, 0, "Set", '', "Message", 0, 'Message')
        add_dictionary_row(annotation_dictionary, redfish_row_index, 0, "Set", '', "Redfish", 0, 'Redfish')
        add_dictionary_row(annotation_dictionary, 4, 0, "Set", '', "reserved", 0, '')

        odata_annotation_location = args.schemaDir + '/json-schema/' + 'odata.v4_0_2.json'
        annotation_dictionary[1][DICTIONARY_ENTRY_CHILD_COUNT] = \
            add_odata_annotations(annotation_dictionary, odata_annotation_location)

        annotation_dictionary = generate_dictionary(annotation_dictionary, False)

        # In order to present annotations as a flat namespace, sequence numbers for elements from the
        # odata, Message and Redfish schema shall have their two low-order bits set to 00b, 01b and 10b
        # respectively
        fix_annotations_sequence_numbers(annotation_dictionary, odata_row_index,   0)
        fix_annotations_sequence_numbers(annotation_dictionary, message_row_index, 1)
        fix_annotations_sequence_numbers(annotation_dictionary, redfish_row_index, 2)

    return annotation_dictionary


if __name__ == '__main__':
    # rde_schema_dictionary parse --schemaDir=directory --schemaFilename=filename
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    subparsers = parser.add_subparsers(dest='source')

    remote_parser = subparsers.add_parser('remote')
    remote_parser.add_argument('--schemaURL', type=str, required=True)
    remote_parser.add_argument('--entity', type=str, required=True)
    remote_parser.add_argument('--outputFile', type=str, required=False)

    local_parser = subparsers.add_parser('local')
    local_parser.add_argument('--schemaDir', type=str, required=True)
    local_parser.add_argument('--schemaFilename', type=str, required=True)
    local_parser.add_argument('--entity', type=str, required=True)
    local_parser.add_argument('--oemSchemaFilenames', nargs='*', type=str, required=False)
    local_parser.add_argument('--oemEntities', nargs='*', type=str, required=False)
    local_parser.add_argument('--outputFile', type=str, required=False)

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.source is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # bring in all dependent documents and their corresponding namespaces
    doc_list = {}
    source = ''
    oemSources = []
    if args.source == 'local':
        source = args.schemaDir + '/' + 'metadata/' + args.schemaFilename
        if args.oemSchemaFilenames:
            for schemaFilename in args.oemSchemaFilenames:
                oemSources.append(args.schemaDir + '/' + 'metadata/' + schemaFilename)
    elif args.source == 'remote':
        source = args.schemaURL

    add_namespaces(source, doc_list)
    for oemSource in oemSources:
        add_namespaces(oemSource, doc_list)

    entity = args.entity
    if args.verbose:
        pprint.PrettyPrinter(indent=3).pprint(doc_list)

    entity_repo = {}
    if args.oemSchemaFilenames:
        oemEntityType = entity + '.Oem'
        # create a special entity for OEM and set the major entity's oem section to it
        entity_repo[oemEntityType] = ('Set', [])
        for oemEntityPair in args.oemEntities:
            oemName, oemEntity = oemEntityPair.split('=')
            entity_repo[oemEntityType][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append([oemName, 'Set', '', oemEntity])

    add_all_entity_and_complex_types(doc_list, entity_repo)
    if args.verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    # set the entity oem entry to the special OEM entity type
    if args.oemSchemaFilenames:
        for property in entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
            if property[PROPERTY_FIELD_STRING] == 'Oem':
                property[PROPERTY_OFFSET] = oemEntityType

    # search for entity and build dictionary
    if entity in entity_repo:
        schema_dictionary = []
        add_dictionary_row(schema_dictionary, index=0, seq_num=0, format='Set', format_flags='', field_string=entity,
                           child_count=0, offset=1)
        num_entries, offset = add_dictionary_entries(schema_dictionary, entity_repo, entity)
        schema_dictionary[0][DICTIONARY_ENTRY_CHILD_COUNT] = num_entries
        schema_dictionary = generate_dictionary(schema_dictionary)

        print_table_data(
            [["Row", "Sequence#", "Format", "Flags", "Field String", "Child Count", "Offset"]]
            +
            schema_dictionary
        )

        print_dictionary_summary(schema_dictionary)

        entity_offset_map = {}
        annotation_dictionary = generate_annotation_dictionary()
        print_table_data(
            [["Row", "Sequence#", "Format", "Flags", "Field String", "Child Count", "Offset"]]
            +
            annotation_dictionary
        )
        print_dictionary_summary(annotation_dictionary)

        # TODO: Generate
        # generate_byte_array(schema_dictionary)

        if args.outputFile:
            file = open(args.outputFile, 'w')
            file.write(json.dumps(schema_dictionary))
            file.close()

            file = open(args.outputFile, 'r')
            dict = json.load(file)
            print(dict)
    else:
        print('Error, cannot find entity:', entity)
