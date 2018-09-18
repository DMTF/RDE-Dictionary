
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
from collections import namedtuple
from copy import deepcopy
import binascii
import os.path


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

ENTITY_REPO_ENTRY_SEQUENCE_NUMBER = 0
ENTITY_REPO_ENTRY_PROPERTY_NAME = 1
ENTITY_REPO_ENTRY_TYPE = 2
ENTITY_REPO_ENTRY_FLAGS = 3
ENTITY_REPO_ENTRY_REFERENCE = 4
ENTITY_REPO_ENTRY_AUTO_EXPAND = 5

# Global variable to set verbosity.
includeNamespaces = {} # Dict to build a list of namespaces that will be used to build the dictionary
verbose = False
silent = False

EntityOffsetMapTuple = namedtuple('EntityOffsetMapTuple', 'offset offset_to_array')


def get_base_properties(entity_type):
    """
    Constructs a list of base properties that are inherited by entity_type

    Args:
        entity_type: The EntityType or ComplexType whose base properties need to be constructed
    """

    properties = []
    if entity_type.get('BaseType') is not None:
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
        if primitive_type == "DateTimeOffset" or primitive_type == "Duration" or primitive_type == "TimeOfDay" or primitive_type == "Guid":
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
    global verbose

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
                        properties.append([property_name, 'Set', property_flags, ''])
                    else:
                        properties.append([property_name, 'Set', property_flags, strip_version(property_type)])
                elif complex_type.tag == ODATA_TYPE_DEFINITION:
                    assert(re.compile('Edm\..*').match(complex_type.get('UnderlyingType')))
                    primitive_type = get_primitive_type(complex_type.get('UnderlyingType'))
                    properties.append([property_name, primitive_type, property_flags, ''])
                else:
                    if verbose:
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


def find_csdl_source(csdl_schema_dirs, filename):
    for csdl_dir in csdl_schema_dirs:
        if os.path.isfile(csdl_dir + '/' + filename):
            return os.path.join(csdl_dir, filename)
    return ''


def find_json_schema_source(json_schema_dirs, filename):
    for json_schema_dir in json_schema_dirs:
        if os.path.isfile(json_schema_dir + '/' + filename):
            return os.path.join(json_schema_dir, filename)
    return ''


def add_namespaces(csdl_schema_dirs, source_type, source, doc_list):
    global includeNamespaces
    global verbose

    doc_name = source
    schema_string = ''
    if source_type == 'remote':
        doc_name = extract_doc_name_from_url(source)

    # first load the CSDL file as a string
    if doc_name not in doc_list:
        if source_type == 'remote':
            # ignore odata references
            if source.find('http://docs.oasis') == -1:
                try:
                    if verbose:
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
            if source_type == 'remote':
                dependent_source = ref.get('Uri')
            else:
                dependent_source = find_csdl_source(csdl_schema_dirs, extract_doc_name_from_url(ref.get('Uri')))

                if os.path.exists(dependent_source) is False:
                    continue
                if verbose:
                    print(dependent_source)
            add_namespaces(csdl_schema_dirs, source_type, dependent_source, doc_list)


def get_latest_version(entity):
    global includeNamespaces

    # search the namespaces for all 'entity.vMajor_Minor_Errata'
    result = [key for key, value in includeNamespaces.items() if key.startswith(entity.split('.')[1]+'.')]

    # The last item in result will have the latest version
    if len(result) > 1:  # This is a versioned namespace
        return result[len(result) - 1].split('.')[1]
    else:  # This is unversioned, return v0_0_0
        return 'v0_0_0'


def get_latest_version_as_ver32(entity):
    """
    Returns the latest version of the entity as a PLDM ver32 array of bytes

    Args:
        entity: The EntityType or ComplexType in the format Namespace.Entity (e.g. Drive.Drive)
    """

    version = get_latest_version(entity)

    # The last item in result will have the latest version
    if version != 'v0_0_0':  # This is a versioned namespace
        ver_array = version[1:].split('_')   # skip the 'v' and split the major, minor and errata
        ver_number = ((int(ver_array[0]) | 0xF0) << 24) | ((int(ver_array[1]) | 0xF0) << 16) | ((int(ver_array[2]) | 0xF0) << 8)
        return ver_number
    else:  # This is an un-versioned entity, return v0_0_0
        return 0xFFFFFFFF


def find_enum(key, dictionary):
    for k, v in dictionary.items():
        if k == key and "enum" in v:
            return v
        elif isinstance(v, dict):
            f = find_enum(key, v)
            if f is not None and "enum" in f:
                return f
    return None


def fix_enums(json_schema_dirs, entity_repo, key):
    global verbose

    if entity_repo[key][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
        # build a list of json schema files that need to be scanned for the enum in question
        [base_filename, enum_name] = key.split('.')
        if verbose:
            print("Need to look at json schema to fix enums for", key, base_filename)
        enum_values = []
        for json_schema_dir in json_schema_dirs:
            for file in os.listdir(json_schema_dir):
                if file.startswith(base_filename + '.'):
                    json_schema = json.load(open(json_schema_dir + '/' + file))
                    # search json schema for enum

                    if verbose:
                        print("Looking for", enum_name, "in", json_schema_dir + '/' + file)
                    json_enum = find_enum(enum_name, json_schema)
                    if json_enum is not None:
                        if verbose:
                            print(json_enum["enum"])
                        enum_values = enum_values + list((Counter(json_enum["enum"]) - Counter(enum_values)).elements())
                        if verbose:
                            print(enum_values)

        if len(enum_values):
            # entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX] = [[enum] for enum in enum_values]
            del entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX][:]
            entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend([[enum] for enum in enum_values])


def add_all_entity_and_complex_types(json_schema_dirs, source_type, doc_list, entity_repo):
    for key in doc_list:
        add_entity_and_complex_types(doc_list[key], entity_repo)
        add_actions(doc_list[key], entity_repo)
        add_annotation_terms(doc_list[key], entity_repo)

    # add special ones for AutoExpandRefs
    # entity_repo['AutoExpandRef'] = ('Set', [['@odata.id', 'String', '']])
    # entity_repo['AutoExpandRef'] = ('Set', [['', 'Set', '']])

    # second pass, add seq numbers
    for key in entity_repo:
        # TODO: Fix enums (works only for local mode currently)
        if source_type == 'local' and entity_repo[key][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
            fix_enums(json_schema_dirs, entity_repo, key)

        for seq, item in enumerate(entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            item.insert(0, seq)


def get_base_type(child):
    global includeNamespaces
    global verbose

    if child.get('BaseType') is not None:
        m = re.compile('(.*)\.(\w*)').match(child.get('BaseType'))
        base_namespace = m.group(1)
        base_entity_name = m.group(2)
        try:
            return includeNamespaces[base_namespace].xpath(
                'child::edm:EntityType[@Name=\'%s\'] | child::edm:ComplexType[@Name=\'%s\']' % (base_entity_name,
                                                                                                base_entity_name),
                namespaces=ODATA_ALL_NAMESPACES)[0]
        except:
            if verbose:
                print(base_namespace, base_entity_name)
            sys.exit()

def is_parent_abstract(entity_type):
    base_entity = get_base_type(entity_type)
    return (base_entity is not None) and (base_entity.get('Abstract') == 'true')


def is_abstract(entity_type):
    return (entity_type is not None) and (entity_type.get('Abstract') == 'true')


def find_element_from_type(type):
    global includeNamespaces

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


def add_dictionary_entries(schema_dictionary, entity_repo, entity, entity_offset_map, is_parent_array):
    if entity in entity_repo:
        entity_type = entity_repo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX]
        start = len(schema_dictionary)

        # Check to see if dictionary entries for the entity has already been generated and use the cached offsets
        # if yes.
        if entity in entity_offset_map:
            offset = entity_offset_map[entity].offset
            array_offset = entity_offset_map[entity].offset_to_array
            if is_parent_array:
                # If this is the first time we found a usage of this entity in the context of an array, we need to add
                # a dummy dictionary entry and update the entity_offset_map
                if array_offset == 0:
                    add_dictionary_row(schema_dictionary, start, 0, entity_type, '', '',
                                       len(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]), offset)
                    entity_offset_map[entity] = EntityOffsetMapTuple(offset, start)

                return entity_offset_map[entity].offset_to_array, len(entity_repo[entity][
                                                                          ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX])

            return offset, len(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX])

        # For a set or enum add a row indicating this is a set or enum if used in the context of an array
        offset = start
        if is_parent_array and (entity_type == 'Set' or entity_type == 'Enum'):
            add_dictionary_row(schema_dictionary, start, 0, entity_type, '', '',
                               len(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]), start + 1)
            start = start + 1

        child_count = 0
        for index, property in enumerate(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            if entity_type == 'Enum':  # this is an enum
                add_dictionary_row(schema_dictionary, index + start, property[PROPERTY_SEQ_NUMBER], 'String', '',
                                   property[PROPERTY_FIELD_STRING], 0, '')
            else:  # all other types
                add_dictionary_row(schema_dictionary, index + start, property[PROPERTY_SEQ_NUMBER],
                                   property[PROPERTY_TYPE], property[PROPERTY_FLAGS], property[PROPERTY_FIELD_STRING],
                                   0, property[PROPERTY_OFFSET])
            child_count = child_count + 1

        # If we are here, then this is a new set of entries added to the dictionary. Let's update the entity_offset_map
        # to cache the offsets.
        if is_parent_array:
            entity_offset_map[entity] = EntityOffsetMapTuple(offset+1, offset)
        else:
            entity_offset_map[entity] = EntityOffsetMapTuple(offset, 0)

        return offset, child_count

    # This case is for empty complex types (Set) that don't have any additional definition in the CSDL (e.g. Oem)
    # but are being used in the context of an array
    elif is_parent_array:
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
            entity_offset_map[simple_type] = EntityOffsetMapTuple(start, 0)
        else:
            start = entity_offset_map[simple_type].offset

        return start, 0

    # This case is for empty complex types (Set) that don't have any additional definition in the CSDL (e.g. Oem)
    else:
        return 0, 0


def generate_json_dictionary(dictionary, dictionary_byte_array, entity, ver):
    summary = {}

    summary['schema_name'] = entity
    summary['schema_version'] = ver
    summary['schema_url'] = 'https://redfish.dmtf.org/schemas/' + entity.split('.')[0] + '.' + get_latest_version(entity) + '.json'

    assert(dictionary_binary_size(dictionary) == len(dictionary_byte_array))
    summary['schema_dictionary_length_bytes'] = dictionary_binary_size(dictionary)
    summary['schema_dictionary_crc_32'] = binascii.crc32(bytes(dictionary_byte_array))
    summary['schema_dictionary_bytes'] = dictionary_byte_array
    assert(len(summary['schema_dictionary_bytes']) == summary['schema_dictionary_length_bytes'])

    return (json.dumps(summary))


def print_dictionary_summary(dictionary, dictionary_byte_array):
    print("Total Entries:", len(dictionary))
    print("Fixed size consumed (bytes):", dictionary_binary_header_size() + dictionary_binary_entry_size() * len(dictionary))
    # calculate size of free form property names:
    total_field_string_size = 0
    for item in dictionary:
        total_field_string_size = total_field_string_size + len(item[DICTIONARY_ENTRY_FIELD_STRING])
    print("Field string size consumed (bytes):", total_field_string_size)
    print('Total size (bytes):', dictionary_binary_size(dictionary))
    print('Signature:', hex(binascii.crc32(bytes(dictionary_byte_array))))


def generate_dictionary(dictionary, entity_repo, entity_offset_map, optimize_duplicate_items=True):
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

                # Add dictionary entries
                offset, child_count = add_dictionary_entries(tmp_dictionary, entity_repo,
                                                             item[DICTIONARY_ENTRY_OFFSET],
                                                             entity_offset_map,
                                                             item[DICTIONARY_ENTRY_FORMAT] == 'Array')

                tmp_dictionary[index][DICTIONARY_ENTRY_OFFSET] = ''
                if offset != 0:
                    tmp_dictionary[index][DICTIONARY_ENTRY_OFFSET] = offset
                    # Use child_count only if this is a complex type or enum
                    if item[DICTIONARY_ENTRY_FORMAT] == 'Set' or item[DICTIONARY_ENTRY_FORMAT] == 'Enum':
                        tmp_dictionary[index][DICTIONARY_ENTRY_CHILD_COUNT] = child_count
                    else:
                        tmp_dictionary[index][DICTIONARY_ENTRY_CHILD_COUNT] = 1

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
    global verbose

    json_schema = json.load(open(odata_annotation_location))
    offset = len(annotation_dictionary)
    count = 0
    for k, v in json_schema["definitions"].items():
        bej_format = ''
        json_format = v['type']
        if json_format == 'string':
            if k == 'id':  # special case odata.id to be a resource link
                bej_format = 'ResourceLink'
            else:
                bej_format = 'String'
        elif json_format == 'number':
            bej_format = 'Integer'
        elif json_format == 'object':
            # TODO expand object
            bej_format = 'Set'
        else:
            if verbose:
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


def generate_annotation_dictionary(json_schema_dirs, entity_repo, entity_offset_map):
    annotation_dictionary = []

    # first 4 entries
    odata_row_index = 1
    message_row_index = 2
    redfish_row_index = 3
    add_dictionary_row(annotation_dictionary, 0, 0, "Set", '', "annotation", 4, 1)
    add_dictionary_row(annotation_dictionary, odata_row_index, 0, "Set", '', "odata", 0, 5)
    add_dictionary_row(annotation_dictionary, message_row_index, 0, "Set", '', "Message", 0, 'Message')
    add_dictionary_row(annotation_dictionary, redfish_row_index, 0, "Set", '', "Redfish", 0, 'Redfish')
    add_dictionary_row(annotation_dictionary, 4, 0, "Set", '', "reserved", 0, '')

    odata_annotation_location = find_json_schema_source(json_schema_dirs, 'odata.v4_0_2.json')
    annotation_dictionary[1][DICTIONARY_ENTRY_CHILD_COUNT] = \
        add_odata_annotations(annotation_dictionary, odata_annotation_location)

    annotation_dictionary = generate_dictionary(annotation_dictionary, entity_repo, entity_offset_map, False)

    # In order to present annotations as a flat namespace, sequence numbers for elements from the
    # odata, Message and Redfish schema shall have their two low-order bits set to 00b, 01b and 10b
    # respectively
    fix_annotations_sequence_numbers(annotation_dictionary, odata_row_index,   0)
    fix_annotations_sequence_numbers(annotation_dictionary, message_row_index, 1)
    fix_annotations_sequence_numbers(annotation_dictionary, redfish_row_index, 2)

    return annotation_dictionary


def truncate_entity_repo(entity_repo, entity, required_properties, is_truncated, enum_key = ""):
    """Truncate the entity repository baseed on the required_properties dictionary."""
    if entity in entity_repo:
        if entity_repo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Set':
            # The entity type is 'Set'.
            # Recursively search for each member in the property list of the entity in the required
            # properties dictionary. If the property does not exist in the required properties dictionary,
            # remove it from the entity repo.
            for property in reversed(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
                is_required = False
                if property[ENTITY_REPO_ENTRY_PROPERTY_NAME] in required_properties:
                    is_required = True
                    truncate_entity_repo(entity_repo, property[ENTITY_REPO_ENTRY_REFERENCE], required_properties,
                                         is_truncated, property[ENTITY_REPO_ENTRY_PROPERTY_NAME])
                if is_required == False:
                    entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].remove(property)
                    is_truncated = True
        if entity_repo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
            # The entity type is 'Enum'.
            # No recursion is necessary, but the enum list must be trimmed such that it is a union of
            # all valid values of all properties that use this enum.

            # First, create an untruncated reference version of the entity if it does not exist and
            # clear the 'real' entity which will be used to generate the dictionary.
            untruncated_entity = entity + ".Untruncated"
            if untruncated_entity not in entity_repo:
                entity_repo[untruncated_entity] = deepcopy(entity_repo[entity])
                entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].clear()
            # If the required property does not have an specified list of values, assume that all enum
            # values are valid.
            add_all = True if len(required_properties[enum_key]) == 0 else False
            if not add_all:
                is_truncated = True
            # Traverse the untrunctaed entity entry. If the entry exists in the required properties value
            # list, add it to the 'real' entity.
            for enum_val in entity_repo[untruncated_entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
                if add_all or enum_val[ENTITY_REPO_ENTRY_PROPERTY_NAME] in required_properties[enum_key]:
                    if enum_val not in entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
                        entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append(enum_val)


def process_profile(json_profile, entity):
    """Validate that the provided profile has a 'Resources' key and the target entity.

    If the provided profile is valid, create a dictionary of required properties used to truncate the entity repo.
    """
    json_resource = None
    required_properties = None
    if "Resources" in json_profile:
        profile_key = entity.split('.')[1]
        if profile_key in json_profile["Resources"]:
            json_resource = json_profile["Resources"][profile_key]
    if json_resource:
        required_properties = {}
        build_requirements(json_resource, required_properties)
    return required_properties


def build_requirements(obj, required_properties):
    """Generate a required_properties dictionary used to truncate the entity repository.

    The required_properties dictionary is generated in a way such that every property specified in the
    profile is converted into a key-value pair where:
    - key = property name
    - value = list of valid enums
    For properties that are not enums, or that do not have valid enums specified, the value in the
    key-value pair is an empty list.
    """
    for key in obj:
        if key == 'PropertyRequirements':
            for prop in obj[key].items():
                enum_values = []
                for child in prop[1]:
                    if child == 'Values':
                        enum_values = prop[1][child]
                if prop[0] in required_properties:
                    full_enum_values = required_properties[prop[0]] + [val for val in enum_values if val not in required_properties[prop[0]]]
                    required_properties[prop[0]] = full_enum_values
                else:
                    required_properties[prop[0]] = enum_values
    for val in obj.values():
        if isinstance(val, dict):
            build_requirements(val, required_properties)


def dictionary_binary_header_size():
    version_tag_size = 1
    dictionary_flags_size = 1
    schema_version_size = 4
    entry_count_size = 2
    dictionary_size_size = 4

    return version_tag_size + dictionary_flags_size + schema_version_size + entry_count_size + dictionary_size_size


def dictionary_binary_entry_size():
    entry_format_size = 1
    entry_sequence_number_size = 2
    entry_child_pointer_offset_size = 2
    entry_child_count_size = 2
    entry_name_length_size = 1
    entry_format_length_size = 1
    entry_name_offset_size = 2
    entry_format_offset_size = 2

    return entry_format_size + entry_sequence_number_size + entry_child_pointer_offset_size + entry_child_count_size + \
           entry_name_length_size + entry_format_length_size + entry_name_offset_size + entry_format_offset_size


def dictionary_binary_size(dictionary):
    total_field_string_size = 0
    for item in dictionary:
        if len(item[DICTIONARY_ENTRY_FIELD_STRING]):
            total_field_string_size = total_field_string_size + len(item[DICTIONARY_ENTRY_FIELD_STRING]) \
                                   + 1  # for null termination
    return dictionary_binary_header_size() + len(dictionary) * dictionary_binary_entry_size() + total_field_string_size


def binary_offset_from_dictionary_offset(offset):
    return dictionary_binary_header_size() + (offset * dictionary_binary_entry_size())


def dictionary_offset_from_binary_offset(offset):
    if offset:
        return int((offset - dictionary_binary_header_size() + 1)/dictionary_binary_entry_size())
    else:
        return offset

bej_format_table = {
    'Set':          0x00,
    'Array':        0x01,
    'Integer':      0x03,
    'Enum':         0x04,
    'String':       0x05,
    'Boolean':      0x07,
    'ResourceLink': 0x0E
}


def to_bej_format(format, is_nullable, is_readonly):
    format = bej_format_table[format] << 4
    if is_readonly:
        format |= 0x02
    if is_nullable:
        format |= 0x04

    return format


bej_format_table_reverse_map = dict((reversed(item) for item in bej_format_table.items()))


def from_bej_format(format):
    return bej_format_table_reverse_map[format >> 4]


def is_nullable(format):
    return (format & 0x04) != 0


def is_readonly(format):
    return (format & 0x02) != 0


def generate_byte_array(dictionary, version, is_truncated):
    binary_data = []
    binary_data.append(0x00)  # VersionTag

    # DictionaryFlags
    if is_truncated:
        binary_data.append(0x01)
    else:
        binary_data.append(0x00)

    binary_data.extend(len(dictionary).to_bytes(2, 'little', signed=False))  # EntryCount

    binary_data.extend(version.to_bytes(4, 'little', signed=False))  # SchemaVersion

    binary_data.extend(dictionary_binary_size(dictionary).to_bytes(4, 'little', signed=False))  # DictionarySize

    # track property name offsets, this is initialized to the first property name
    name_offset = dictionary_binary_header_size() + (len(dictionary) * dictionary_binary_entry_size())

    # Add the fixed sized entries
    for item in dictionary:
        # Format
        format = to_bej_format(item[DICTIONARY_ENTRY_FORMAT],
                               is_nullable='Nullable=True' in item[DICTIONARY_ENTRY_FORMAT_FLAGS],
                               is_readonly=('Permission=Read' in item[DICTIONARY_ENTRY_FORMAT_FLAGS] and 'Permission=ReadWrite' not in item[DICTIONARY_ENTRY_FORMAT_FLAGS]))
        binary_data.extend(format.to_bytes(1, 'little'))

        binary_data.extend(item[DICTIONARY_ENTRY_SEQUENCE_NUMBER].to_bytes(2, 'little'))  # SequenceNumber

        # ChildPointerOffset
        if item[DICTIONARY_ENTRY_OFFSET]:
            binary_data.extend(binary_offset_from_dictionary_offset(int(item[DICTIONARY_ENTRY_OFFSET])).to_bytes(2, 'little'))
        else:
            binary_data.extend([0x00, 0x00])

        # ChildCount
        if item[DICTIONARY_ENTRY_FIELD_STRING] == 'Array':
            binary_data.extend([0xFF, 0xFF])
        else:
            binary_data.extend(item[DICTIONARY_ENTRY_CHILD_COUNT].to_bytes(2, 'little'))

        # NameLength
        if item[DICTIONARY_ENTRY_FIELD_STRING]:
            binary_data.append(len(item[DICTIONARY_ENTRY_FIELD_STRING]) + 1)
        else:
            binary_data.append(0x00)

        # TODO: FormatLength
        binary_data.append(0x00)

        # NameOffset
        if item[DICTIONARY_ENTRY_FIELD_STRING]:
            binary_data.extend(name_offset.to_bytes(2, 'little'))
            name_offset += len(item[DICTIONARY_ENTRY_FIELD_STRING]) + 1
        else:
            binary_data.extend([0x00, 0x00])

        # TODO: FormatOffset
        binary_data.extend([0x00, 0x00])

    # Add the property names
    for item in dictionary:
        if item[DICTIONARY_ENTRY_FIELD_STRING]:
            binary_data.extend([ord(elem) for elem in item[DICTIONARY_ENTRY_FIELD_STRING]])
            binary_data.append(0x00)

    return binary_data


def get_int_from_byte_array(byte_array, start_index, size):
    return int.from_bytes(byte_array[start_index:start_index+size], 'little'), start_index + size


class DictionaryByteArrayStream:
    def __init__(self, byte_array):
        self._byte_array = byte_array
        self._current_index = 0

    def get_int(self, size):
        value = int.from_bytes(self._byte_array[self._current_index:self._current_index+size], 'little')
        self._current_index += size
        return value


    def get_current_offset(self):
        return self._current_index


def print_binary_dictionary(byte_array):
    stream = DictionaryByteArrayStream(byte_array)

    # print header
    print('VersionTag: ', stream.get_int(1))
    print('DictionaryFlags: ', stream.get_int(1))
    total_entries = stream.get_int(2)
    print('EntryCount: ', total_entries)
    print('SchemaVersion: ', hex(stream.get_int(4)))
    print('DictionarySize: ', stream.get_int(4))

    # print each entry
    table = []
    current_entry = 0
    while current_entry < total_entries:
        current_offset = stream.get_current_offset()
        format = stream.get_int(1)
        format_str = from_bej_format(format)
        format_flags = ''
        if is_nullable(format):
            format_flags = 'Nullable=True'
        if is_readonly(format):
            format_flags += ',Permission=Read'

        sequence = stream.get_int(2)
        offset = stream.get_int(2)
        child_count = stream.get_int(2)
        name_length = stream.get_int(1)
        format_length = stream.get_int(1)
        name_offset = stream.get_int(2)
        format_offset = stream.get_int(2)

        name = ''
        if name_length > 0:
            name = "".join(map(chr, byte_array[name_offset:name_offset+name_length]))

        table.append([str(current_entry)+'('+str(current_offset)+')', sequence, format_str, format_flags, name,
                      str(dictionary_offset_from_binary_offset(offset))+'('+str(offset)+')', child_count])
        current_entry += 1

    print_table_data(
        [["Row", "Sequence#", "Format", "Flags", "Field String", "Offset", "Child Count"]]
        +
        table
    )


# Named tuple to return schema dictionary.
SchemaDictionary = namedtuple('SchemaDictionary', 'dictionary dictionary_byte_array json_dictionary')

def generate_schema_dictionary(source_type, csdl_schema_dirs, json_schema_dirs,
                               entity, schema_file_name, oem_entities=None,
                               oem_schema_file_names=None, profile=None, schema_url=None):
    """ Generate the schema dictionary.

    Args:
        source_type: Type of schema file. local, annotation or remote.
        csdl_schema_dirs: List of CSDL schema directories.
        json_schema_dirs: List of JSON schema directories.
        entity: Schema entity name.
        schema_file_name: Schema file name.
        oem_entities: List of oem entities (default None).
        oem_schema_file_names: List of OEM schema file names (default None).
        profile: Schema profile (default None)
        schema_url: Schema URL. Used when source_type is remote (default None).

    Return:
        SchemaDictionary: Named tuple which has the following fields:
                          dictionary - The schema dictionary.
                          dictionary_byte_array - The schema dictionary in byte array.
                          json_dictionary - Schema dictionary in JSON format.
    """
    global includeNamespaces
    global verbose

    # Initialize the global variables.
    doc_list = {}
    source = ''
    oemSources = []
    oemEntityType = ''
    entity_repo = {}
    entity_offset_map = {}
    includeNamespaces = {}

    # Validate source type.
    if source_type not in ['local', 'annotation', 'remote']:
        if verbose:
            print('Error, invalid source_type: {0}'.format(source_type))
        return (SchemaDictionary(dictionary=None,
                                 dictionary_byte_array=None,
                                 json_dictionary=None))

    # Set the source variable. If source_type is remote set source to schema_url.
    if source_type == 'remote':
        source = schema_url
    else:
        # compute source starting with the first csdl directory. The first one wins
        source = schema_file_name
        for csdl_dir in csdl_schema_dirs:
            if os.path.isfile(os.path.join(csdl_dir, schema_file_name)):
                source = os.path.join(csdl_dir, schema_file_name)
                break

    # Set oem sources and entity repo for oem schema file names.
    if oem_schema_file_names:
        for oem_schema_file in oem_schema_file_names:
            for csdl_dir in csdl_schema_dirs:
                if os.path.isfile(os.path.join(csdl_dir, oem_schema_file)):
                    oemSources.append(os.path.join(csdl_dir, oem_schema_file))

        oemEntityType = entity + '.Oem'
        # create a special entity for OEM and set the major entity's oem section to it
        entity_repo[oemEntityType] = ('Set', [])
        for oemEntityPair in oem_entities:
            oemName, oemEntity = oemEntityPair.split('=')
            entity_repo[oemEntityType][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append(
               [oemName, 'Set', '', oemEntity])

    # Add namespaces.
    add_namespaces(csdl_schema_dirs, source_type, source, doc_list)
    for oemSource in oemSources:
        add_namespaces(csdl_schema_dirs, source_type, oemSource, doc_list)

    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(doc_list)

    add_all_entity_and_complex_types(json_schema_dirs, source_type, doc_list, entity_repo)
    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    # set the entity oem entry to the special OEM entity type
    if source_type == 'local' and oem_schema_file_names:
        for property in entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
            if property[PROPERTY_FIELD_STRING] == 'Oem':
                property[PROPERTY_OFFSET] = oemEntityType

    # search for entity and build dictionary
    if entity in entity_repo:
        ver = ''
        dictionary = []
        if source_type == 'local':
            # truncate the entity_repo first if a profile is specified
            is_truncated = False
            if profile:
                with open(profile) as file:
                    json_profile = json.load(file)
                # Fix up the profile
                profile_requirements = process_profile(json_profile, entity)
                if profile_requirements:
                    truncate_entity_repo(entity_repo, entity, profile_requirements, is_truncated)
                else:
                    if verbose:
                        print('Error parsing profile')
                    sys.exit(1)

            add_dictionary_entries(dictionary, entity_repo, entity, entity_offset_map, is_parent_array=True)
            dictionary = generate_dictionary(dictionary, entity_repo, entity_offset_map)
            ver = get_latest_version_as_ver32(entity)
            if verbose:
                print(entity_offset_map)

        if source_type == 'annotation':
            dictionary = generate_annotation_dictionary(json_schema_dirs, entity_repo, entity_offset_map)
            ver = 0xF1F0F000  # TODO: fix version for annotation dictionary (maybe add cmd line param)

        # Generate dictionary_byte_array.
        dictionary_byte_array = generate_byte_array(dictionary, ver, False)

        # Generate JSON dictionary.
        json_dictionary = generate_json_dictionary(dictionary, dictionary_byte_array, entity, ver)
        # Return the named tuple.
        return (SchemaDictionary(dictionary=dictionary,
                                 dictionary_byte_array=dictionary_byte_array,
                                 json_dictionary=json_dictionary))

    # Reached here means something went wrong. Return an empty named tuple.
    else:
        if verbose:
            print('Error, cannot find entity:', entity)
        return (SchemaDictionary(dictionary=None,
                                 dictionary_byte_array=None,
                                 json_dictionary=None))


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
    #local_parser.add_argument('--schemaDir', type=str, required=False)
    local_parser.add_argument('-cd', '--csdlSchemaDirectories', nargs='*', type=str, required=True)
    local_parser.add_argument('-jd', '--jsonSchemaDirectories', nargs='*', type=str, required=True)
    local_parser.add_argument('-f', '--schemaFilename', type=str, required=True)
    local_parser.add_argument('-e', '--entity', type=str, required=True)
    local_parser.add_argument('-oemf', '--oemSchemaFilenames', nargs='*', type=str, required=False)
    local_parser.add_argument('-oem', '--oemEntities', nargs='*', type=str, required=False)
    local_parser.add_argument('-p', '--profile', type=str, required=False)
    local_parser.add_argument('-o', '--outputFile', type=argparse.FileType('wb'), required=False)
    local_parser.add_argument('-oj', '--outputJsonDictionaryFile', type=argparse.FileType('w'), required=False)


    annotation_parser = subparsers.add_parser('annotation')
    annotation_parser.add_argument('-cd', '--csdlSchemaDirectories', nargs='*', type=str, required=True)
    annotation_parser.add_argument('-jd', '--jsonSchemaDirectories', nargs='*', type=str, required=True)
    annotation_parser.add_argument('-o', '--outputFile', type=argparse.FileType('wb'), required=False)
    annotation_parser.add_argument('-oj', '--outputJsonDictionaryFile', type=argparse.FileType('w'), required=False)

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
    if args.source == 'local':
        schema_dictionary = generate_schema_dictionary(args.source, args.csdlSchemaDirectories,
                                                       args.jsonSchemaDirectories, args.entity,
                                                       args.schemaFilename, args.oemEntities,
                                                       args.oemSchemaFilenames, args.profile)
    elif args.source == 'remote':
        schema_dictionary = generate_schema_dictionary(args.source, None, None, args.entity,
                                                       None, None, None, None, args.schemaURL)
    elif args.source == 'annotation':
        # Just choose a dummy complex entity type to start the annotation dictionary generation process.
        schema_dictionary = generate_schema_dictionary(args.source, args.csdlSchemaDirectories,
                                                       args.jsonSchemaDirectories, 'RedfishExtensions.PropertyPattern',
                                                       'RedfishExtensions_v1.xml')

    # Print table data.
    if schema_dictionary.dictionary:
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
