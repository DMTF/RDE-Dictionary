#! /usr/bin/python3
# Copyright Notice:
# Copyright 2018-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/RDE-Dictionary/blob/master/LICENSE.md

"""
RDE Dictionary Builder

File : rde-dictionary-builder.py

Brief : This file contains the definitions and functionalities for generating
        a RDE schema dictionary from a set of standard Redfish CSDL and JSON Schema
        files
"""

from lxml import etree
import json
import re
import os.path
from operator import itemgetter
import pprint
from tabulate import tabulate
import urllib.request
from collections import namedtuple
from copy import deepcopy
import binascii
import glob
import collections
from ._internal_utils import *

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
    """
    Returns the primitive type for a property or null if not primitive
    """
    m = re.compile('Edm\.(.*)').match(property_type)
    if m:  # primitive type?
        primitive_type = m.group(1)
        if primitive_type == "DateTimeOffset" or primitive_type == "Duration" or primitive_type == "TimeOfDay" or primitive_type == "Guid":
            primitive_type = 'String'
        if ((primitive_type == "SByte") or (primitive_type == "Int16") or (primitive_type == "Int32") or
                (primitive_type == "Int64") or (primitive_type == "Decimal")):
            primitive_type = 'Integer'
        if primitive_type == "PrimitiveType":
            primitive_type = 'Choice'
        return primitive_type
    return ''


PROPERTY_SEQ_NUMBER = 0
PROPERTY_FIELD_STRING = 1
PROPERTY_TYPE = 2
PROPERTY_FLAGS = 3
PROPERTY_OFFSET = 4
PROPERTY_EXPAND = 5


def is_property_nullable(property):
    """
    Return True if the property is nullable, False otherwise
    """
    property_is_nullable = True
    if property.get('Nullable') is not None:
        property_is_nullable = property.get('Nullable') == 'true'
    return property_is_nullable


def get_property_permissions(property):
    """
    Returns whether the read-only versus read-write permissions for a property. If the permission is not set,
    then the permission is null.
    """
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


def get_entity_name(entity):
    """
    Returns the entity name after stripping off namespace and/or version information

    Args:
        entity: The full entity name
    """

    components = entity.split('.')
    return components[len(components)-1]


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
    """
    Adds all entity and complex types into the entity repo for the specified document

    Args:
        doc:  The document to search for enums
        entity_repo: Found enums will be added to the entity_repo
    """
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


def add_enums(doc, entity_repo):
    """
    Adds all enum types into the entity repo for the specified document

    Args:
        doc:  The document to search for enums
        entity_repo: Found enums will be added to the entity_repo
    """
    for enum_type in doc.xpath('//edm:EnumType', namespaces=ODATA_ALL_NAMESPACES):
        enum_type_name = get_qualified_entity_name(enum_type)
        if enum_type_name not in entity_repo:
            entity_repo[enum_type_name] = ('Enum', [])

        enum_dict = {}
        for enum_member in enum_type.xpath('child::edm:Member', namespaces=ODATA_ALL_NAMESPACES):
            ver = ''
            # check for Redfish.Revision
            revisions = enum_member.xpath(
                'child::edm:Annotation[@Term=\'Redfish.Revisions\']/edm:Collection/edm:Record',
                namespaces=ODATA_ALL_NAMESPACES)

            if len(revisions) == 1:
                props = revisions[0].xpath('child::edm:PropertyValue[@Property=\"Kind\"]',
                                   namespaces=ODATA_ALL_NAMESPACES)
                if len(props) == 1 and props[0].get('EnumMember') == 'Redfish.RevisionKind/Added':
                    ver = revisions[0].xpath('child::edm:PropertyValue[@Property=\'Version\']',
                                   namespaces=ODATA_ALL_NAMESPACES)[0].get('String')

            if ver not in enum_dict:
                enum_dict[ver] = []
            enum_dict[ver].append(enum_member.get('Name'))

        # sort the keys (the keys are the version strings).
        sorted_enum_dict = collections.OrderedDict(sorted(enum_dict.items()))

        # Add the sorted enum values to the entity repo
        for e in sorted_enum_dict:
            # alphabetically sort all the values as case insensitive
            sorted_enum_dict[e] = sorted(sorted_enum_dict[e], key=lambda s: s.casefold())
            for item in sorted_enum_dict[e]:
                entity_repo[enum_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append([item])


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
        if os.path.isfile(os.path.join(csdl_dir, filename)):
            return os.path.join(csdl_dir, filename)
    return ''


def find_json_schema_source(json_schema_dirs, filename):
    for json_schema_dir in json_schema_dirs:
        if os.path.isfile(os.path.join(json_schema_dir, filename)):
            return os.path.join(json_schema_dir, filename)
    return ''


def is_version_greater_than(version_to_compare, filename):
    """
    Return True if filename has a version greater than version_to_compare

    Args:
        version_to_compare: The version in Redfish format (e.g. 'v1_0_0')
        filename: The full filename without any path information

    Returns:
        True if filename version greater than version_to_compare, False otherwise
    """
    [base_filename, version, extension] = filename.split('.')
    return to_ver32(version) > to_ver32(version_to_compare)


def find_json_schema_files_with_version(json_schema_dirs, filename):
    """
    Returns a list of json-schema files that have the same or less version as the passed in filename.
    Filename are ordered from oldest to newest version.

    Args:
        json_schema_dirs: The list of directories to search for filename
        filename: the filename of the file

    Return:
        Returns the list of filenames that meet the criteria
    """
    [base_filename, highest_version, extension] = filename.split('.')

    filenames = []   # list of filenames sorted from lowest to highest version
    for json_schema_dir in json_schema_dirs:
        filenames = filenames + glob.glob(os.path.join(json_schema_dir, base_filename) + '.*.' + extension)

    # remove any filenames with version > highest_version
    filenames = [x for x in filenames if not is_version_greater_than(highest_version, os.path.basename(x))]

    return filenames


def add_namespaces(csdl_schema_dirs, source, doc_list):
    global includeNamespaces
    global verbose

    # check to see if source is from a remote location
    is_remote = re.search("^http(s?)://", source) is not None

    doc_name = source
    schema_string = ''
    if is_remote:
        doc_name = extract_doc_name_from_url(source)

    # first load the CSDL file as a string
    if doc_name not in doc_list:
        if is_remote:
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
            if is_remote:
                dependent_source = ref.get('Uri')
            else:
                dependent_source = find_csdl_source(csdl_schema_dirs, extract_doc_name_from_url(ref.get('Uri')))

                if os.path.exists(dependent_source) is False:
                    continue
                if verbose:
                    print(dependent_source)
            add_namespaces(csdl_schema_dirs, dependent_source, doc_list)


def get_latest_version(entity):
    global includeNamespaces

    # search the namespaces for all 'entity.vMajor_Minor_Errata'
    result = [key for key, value in includeNamespaces.items() if key.startswith(entity.split('.')[1]+'.')]

    # The last item in result will have the latest version
    if result:  # This is a versioned namespace
        return result[len(result) - 1].split('.')[1]
    else:  # This is unversioned, return v0_0_0
        return 'v0_0_0'


def to_ver32(version):
    """
    Converts version in Redfish format (e.g. v1_0_0) to a PLDM ver32

    Args:
        version: The Redfish version to convert

    Returns:
        The version in ver32 format
    """

    # The last item in result will have the latest version
    if version != 'v0_0_0':  # This is a versioned namespace
        ver_array = version[1:].split('_')   # skip the 'v' and split the major, minor and errata
        ver_number = ((int(ver_array[0]) | 0xF0) << 24) | ((int(ver_array[1]) | 0xF0) << 16) | ((int(ver_array[2])
                                                                                                 | 0xF0) << 8)
        return ver_number
    else:  # This is an un-versioned entity, return v0_0_0
        return 0xFFFFFFFF


def to_redfish_version(ver32):
    """
    Converts a PLDM ver32 number to a Redfish version in the format vMajor_Minor_Errata
    """
    if ver32 == 0xFFFFFFFF:  # un-versioned
        return ''
    else:
        return 'v'+str((ver32 >> 24) & 0x0F)+'_'+str((ver32 >> 16) & 0x0F)+'_'+str((ver32 >> 8) & 0x0F)


def get_latest_version_as_ver32(entity):
    """
    Returns the latest version of the entity as a PLDM ver32 array of bytes

    Args:
        entity: The EntityType or ComplexType in the format Namespace.Entity (e.g. Drive.Drive)
    """

    version = get_latest_version(entity)

    # The last item in result will have the latest version
    return to_ver32(version)


def add_all_entity_and_complex_types(doc_list, entity_repo):
    for key in doc_list:
        add_entity_and_complex_types(doc_list[key], entity_repo)
        add_enums(doc_list[key], entity_repo)
        add_actions(doc_list[key], entity_repo)
        add_annotation_terms(doc_list[key], entity_repo)

    # second pass, add seq numbers
    for key in entity_repo:
        for seq, item in enumerate(entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            item.insert(0, seq)


def get_base_type(child):
    global includeNamespaces
    global verbose

    if child.get('BaseType') is not None:
        m = re.compile('(.*)\.(\w*)').match(child.get('BaseType'))
        base_namespace = m.group(1)
        base_entity_name = m.group(2)

        assert base_namespace in includeNamespaces, \
            "Could not find base namespace %s, source line %d" % (base_namespace, child.sourceline)
        base_types = includeNamespaces[base_namespace].xpath(
            'child::edm:EntityType[@Name=\'%s\'] | child::edm:ComplexType[@Name=\'%s\']' % (base_entity_name,
                                                                                            base_entity_name),
            namespaces=ODATA_ALL_NAMESPACES)
        if len(base_types) == 1:
            return base_types[0]
        assert False, "Could not find base type %s, source line %d" % (child.get('BaseType'), child.sourceline)


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
        elements = includeNamespaces[namespace].xpath('child::edm:*[@Name=\'%s\']' % entity_name,
                                           namespaces=ODATA_ALL_NAMESPACES)
        if len(elements) >= 1:
            return elements[0]
        assert False, "Could not find %s" % (type)

    return None


def print_table_data(data):
    print(tabulate(data, headers="firstrow", tablefmt="grid"))


def add_dictionary_row(dictionary, index, seq_num, format, format_flags, field_string, child_count, offset):
    dictionary.append([index, seq_num, format, format_flags, field_string, child_count, offset])


def add_dictionary_entries(schema_dictionary, entity_repo, entity, entity_offset_map, is_parent_array,
                           anonymous_entry_name=''):
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

        # For a set or enum add an anonymous entry indicating this is a set or enum if used in the context of an array
        offset = start
        if is_parent_array and (entity_type == 'Set' or entity_type == 'Enum'):
            add_dictionary_row(schema_dictionary, start, 0, entity_type, '', anonymous_entry_name,
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


def generate_json_dictionary(json_schema_dirs, dictionary, dictionary_byte_array, entity):
    stream = DictionaryByteArrayStreamSimple(dictionary_byte_array)

    # skip the version-tag, dictionary flags and entries to get to the version
    stream.get_int(1)  # ver-tag
    stream.get_int(1)  # dictionary flags
    stream.get_int(2)  # #entries
    ver32 = stream.get_int(4)
    version_str = to_redfish_version(ver32)

    summary = {}

    summary['schema_name'] = entity
    summary['schema_version'] = ver32

    # Special case for annotations
    if entity == 'annotation':
        summary['schema_url'] = 'http://redfish.dmtf.org/schemas/v1/redfish-payload-annotations.'\
                                +to_redfish_version(ver32)+'.json'
    elif entity == 'RedfishError.RedfishError':
        summary['schema_url'] = 'http://redfish.dmtf.org/schemas/v1/redfish-error.'\
                                +to_redfish_version(ver32)+'.json'
    else:
        summary['schema_url'] = find_schema_url(json_schema_dirs, entity.split('.')[0], version_str,
                                                entity.split('.')[1])

    summary['schema_dictionary_length_bytes'] = len(dictionary_byte_array)
    summary['schema_dictionary_crc_32'] = binascii.crc32(bytes(dictionary_byte_array))
    summary['schema_dictionary_bytes'] = dictionary_byte_array
    assert(len(summary['schema_dictionary_bytes']) == summary['schema_dictionary_length_bytes'])

    return json.dumps(summary)


def print_dictionary_summary(dictionary, dictionary_byte_array):
    print("Total Entries:", len(dictionary))
    fixed_size = dictionary_binary_header_size() + dictionary_binary_entry_size() * len(dictionary)
    print("Fixed size consumed (bytes):", fixed_size)
    print("Field string size consumed (bytes):", len(dictionary_byte_array) - fixed_size)
    print('Total size (bytes):', len(dictionary_byte_array))
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


def get_ref_parts(ref):
    """
    Returns the different parts of a ref: the namespace, version and entity
    e.g. "$ref": "http://redfish.dmtf.org/schemas/swordfish/v1/Volume.v1_0_0.json#/definitions/Volume"
    will return Volume, v1_0_0, Volume
    """
    [schema_url, entity] = ref.split('#')
    entity = entity[entity.rfind('/') + 1:]  # remove preceding /../ from entity

    m = re.compile('.*/(\w+)\.?(\w*)\.json$').match(schema_url)
    if m:
        return m.group(1), m.group(2), entity

    return None, None, None


def get_entity_name_from_json_ref(ref):
    # e.g. $ref": "http://redfish.dmtf.org/schemas/v1/Settings.json#/definitions/Settings
    # should translate to Settings.Settings
    namespace, version, entity = get_ref_parts(ref)
    return namespace+'.'+entity


def compare_redfish_versions(ver1, ver2):
    """
    Return 0 if ver1 == ver2, 1 if ver1 > ver2 and -1 if ver1 < ver2
    """
    ver32_ver1 = to_ver32(ver1)
    ver32_ver2 = to_ver32(ver2)
    if ver32_ver1 == ver32_ver2:
        return 0
    elif ver32_ver1 < ver32_ver2:
        return -1
    else:
        return 1


def find_schema_url(json_schema_dirs, namespace, version, entity):
    """
    Returns the url for a specific namespace+version+entity

    Args:
        json_schema_dirs: list of json schema directories to search for url information
        namespace: namespace the entity resides in
        version: version information
        entity: entity name

    Returns:
        schema url if found, otherwise empty string
    """

    # hack - to handle the case where the dictionary was generated for a version that is available in csdl but not
    # in json-schema yet, we record the closest version found and return that url by modifying it's version.
    closest_url = ''
    closest_ver = ''

    # find the un-versioned json schema file for this namespace
    unversioned_schema_filename = namespace + '.json'
    for json_schema_dir in json_schema_dirs:
        if os.path.isfile(os.path.join(json_schema_dir, unversioned_schema_filename)):
            with open(os.path.join(json_schema_dir, unversioned_schema_filename)) as file:
                json_schema = json.load(file)

            if version == '' and '$id' in json_schema:  # this is an un-versioned. We just use the '$id'
                return json_schema['$id']

            if 'anyOf' in json_schema['definitions'][entity]:
                list_of_refs = json_schema['definitions'][entity]['anyOf']
                for ref in list_of_refs:
                    if '$ref' in ref:
                        ref_namespace, ref_version, ref_entity = get_ref_parts(ref['$ref'])

                        if namespace == ref_namespace and entity == ref_entity:  # versioned namespace
                            if version == ref_version:
                                return ref['$ref']
                            else:
                                # hack - let's record this as a candidate url if it is close enough
                                # (for cases where the json-schema does not have the url yet)
                                if closest_url == '' or (compare_redfish_versions(ref_version, closest_ver) == 1
                                                         and compare_redfish_versions(ref_version, version) == -1):
                                    closest_url = ref['$ref']
                                    closest_ver = ref_version

    # if we are here, we didn't find an exact match but we may have found one close enough.
    if closest_url != '':
        # substitute the version
        return closest_url.replace(closest_ver, version)
    else:
        return ''


def convert_json_type_to_bej_format(k, v, entity_repo):
    bej_format = ''
    offset = ''
    if 'type' in v:
        json_format = v['type']

        if json_format == 'string':
            bej_format = 'String'
        elif json_format == 'number' or json_format == 'integer':
            bej_format = 'Integer'
        elif json_format == 'object':
            # TODO expand object
            bej_format = 'Set'
            if '$ref' in v:
                offset = get_entity_name_from_json_ref(v['$ref'])
        elif json_format == 'array':
            bej_format = 'Array'
            dont_care, offset = convert_json_type_to_bej_format(k, v['items'], entity_repo)

        elif json_format == 'boolean':
            bej_format = 'Boolean'
        else:
            if verbose:
                print('Unknown format', json_format)
                assert (False)
    elif '$ref' in v:
        # bej_format = 'Set'
        offset = get_entity_name_from_json_ref(v['$ref'])
        bej_format = entity_repo[offset][ENTITY_REPO_TUPLE_TYPE_INDEX]
    else:
        print('Error')
        assert(False)

    return bej_format, offset


def generate_annotation_dictionary(annotation_version, json_schema_dirs, entity_repo, entity_offset_map):
    """ Generate the annotation dictionary.

    Args:
        annotation_version: The version of the annotation file to use in the format 'vX_Y_Z'
                            (redfish-payload-annotations.vX_Y_Z.json)
        json_schema_dirs: List of JSON schema directories.
        entity_repo: A built entity repo that can be use to generate the dictionary
        entity_offset_map: A prebuilt entity offset map that can be used to generate the dictionary

    Return:
        The annotation schema dictionary
    """
    payload_annotation_files = find_json_schema_files_with_version(
        json_schema_dirs, 'redfish-payload-annotations.'+annotation_version+'.json')

    # build an entity-repo entry for all the payload annotation entries. Once we have built the entity-repo annotation
    # entry, we can add a reference to it in the first row of the dictionary and we can just let the generate
    # dictionary take care of the rest.
    # Start at the oldest version to the newest version to get the sequence number correct
    global verbose

    entity_repo['Annotations'] = ('Set', [])
    for payload_annotation_file in payload_annotation_files:
        with open(payload_annotation_file) as f:
            json_schema = json.load(f)

            properties = []
            payload_annotation_sections = ['properties', 'patternProperties']
            for payload_annotation_section in payload_annotation_sections:
                for k, v in json_schema[payload_annotation_section].items():
                    bej_format, offset = convert_json_type_to_bej_format(k, v, entity_repo)

                    # strip any patterns from k and remove any trailing '$'
                    k = k[k.find('@'):]
                    if '$' in k:
                        k = k[:-1]
                    if bej_format == 'Array':
                        entry = [k, bej_format, '', offset, 'AutoExpand']
                    else:
                        entry = [k, bej_format, '', offset]
                    properties.append(entry)

            # sort and add to the entity_repo
            # add only unique entries - this is to handle Swordfish vs Redfish conflicting schema (e.g. Volume)
            entity_repo['Annotations'][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
                [item for item in sorted(properties, key=itemgetter(0))
                 if item not in entity_repo['Annotations'][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
            )

    # second pass, add seq numbers
    for seq, item in enumerate(entity_repo['Annotations'][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
        item.insert(0, seq)

    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    annotation_dictionary = []
    add_dictionary_row(annotation_dictionary, 0, 0, "Set", '', "Annotations", 0, 'Annotations')
    annotation_dictionary = generate_dictionary(annotation_dictionary, entity_repo, entity_offset_map, False)

    return annotation_dictionary


def truncate_entity_repo(entity_repo, required_properties, is_truncated, enum_key = ""):
    """Truncate the entity repository based on the required_properties dictionary."""

    for req_entity, req_values in required_properties.items():
        if req_entity in entity_repo:
            for property in reversed(entity_repo[req_entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
                if property[ENTITY_REPO_ENTRY_PROPERTY_NAME] not in req_values:
                    entity_repo[req_entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].remove(property)
                    is_truncated = True

    return


def process_profile(json_profile, entity, entity_repo):
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
        build_requirements(json_resource, required_properties, entity, entity_repo)
    return required_properties


def build_requirements(obj, required_properties, entity, entity_repo):
    """Generate a required_properties dictionary used to truncate the entity repository.

    The required_properties dictionary is generated in a way such that every property specified in the
    profile is converted into a key-value pair where:
    - key = property name
    - value = list of valid enums
    For properties that are not enums, or that do not have valid enums specified, the value in the
    key-value pair is an empty list.
    """

    if 'PropertyRequirements' in obj:
        if entity not in required_properties:
            required_properties[entity] = []

        # go thru each required property and fetch the type
        for prop in obj['PropertyRequirements'].items():
            if isinstance(prop[1], dict):  # prop[0] is the prop name, prop[1] is the prop requirements
                # find the entry in the entity_repo that corresponds to this property
                is_found = False
                for entity_repo_prop in entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
                    if prop[0] == entity_repo_prop[ENTITY_REPO_ENTRY_PROPERTY_NAME]:
                        is_found = True
                        required_properties[entity].append(prop[0])
                        if entity_repo_prop[ENTITY_REPO_ENTRY_TYPE] == 'Set' or \
                                entity_repo_prop[ENTITY_REPO_ENTRY_TYPE] == 'Enum' or \
                                entity_repo_prop[ENTITY_REPO_ENTRY_TYPE] == 'Array' :
                            build_requirements(prop[1], required_properties,
                                               entity_repo_prop[ENTITY_REPO_ENTRY_REFERENCE], entity_repo)
                if not is_found and '@' not in prop[0]:
                    raise Exception("Profile property not found in schema", prop[0])

    if 'Values' in obj: # For enums
        if entity not in required_properties:
            required_properties[entity] = []

        for val in obj['Values']:
            required_properties[entity].append(val)


def dictionary_binary_header_size():
    version_tag_size = 1
    dictionary_flags_size = 1
    entry_count_size = 2
    schema_version_size = 4
    dictionary_size_size = 4

    return version_tag_size + dictionary_flags_size + entry_count_size + schema_version_size + dictionary_size_size


def dictionary_binary_entry_size():
    entry_format_size = 1
    entry_sequence_number_size = 2
    entry_child_pointer_offset_size = 2
    entry_child_count_size = 2
    entry_name_length_size = 1
    entry_name_offset_size = 2

    return entry_format_size + entry_sequence_number_size + entry_child_pointer_offset_size + entry_child_count_size + \
           entry_name_length_size + entry_name_offset_size


def dictionary_binary_size(dictionary, copyright):
    total_field_string_size = 0
    for item in dictionary:
        if len(item[DICTIONARY_ENTRY_FIELD_STRING]):
            total_field_string_size = total_field_string_size + len(item[DICTIONARY_ENTRY_FIELD_STRING]) \
                                   + 1  # for null termination
    copyright_len = 0
    if copyright:
        copyright_len = len(copyright) + 1  # for null termination

    return dictionary_binary_header_size() + len(dictionary) * dictionary_binary_entry_size() + \
           total_field_string_size + 1 + copyright_len


def binary_offset_from_dictionary_offset(offset):
    return dictionary_binary_header_size() + (offset * dictionary_binary_entry_size())


def dictionary_offset_from_binary_offset(offset):
    if offset:
        return int((offset - dictionary_binary_header_size() + 1)/dictionary_binary_entry_size())
    else:
        return offset


bej_format_table = {
    'Set':           0x00,
    'Array':         0x01,
    'Integer':       0x03,
    'Enum':          0x04,
    'String':        0x05,
    'Boolean':       0x07,
    'Choice':        0x09,  # bejChoice
    'ResourceLink':  0x0E
}


def to_bej_format(format_str, is_nullable, is_readonly):
    try:
        format = bej_format_table[format_str] << 4
        if is_readonly:
            format |= 0x02
        if is_nullable:
            format |= 0x04
    except:
        print('Unknown Format', format_str)

    return format


bej_format_table_reverse_map = dict((reversed(item) for item in bej_format_table.items()))


def from_bej_format(format):
    return bej_format_table_reverse_map[format >> 4]


def is_nullable(format):
    return (format & 0x04) != 0


def is_readonly(format):
    return (format & 0x02) != 0


def generate_byte_array(dictionary, version, is_truncated, copyright):
    binary_data = []
    binary_data.append(0x00)  # VersionTag

    # DictionaryFlags
    if is_truncated:
        binary_data.append(0x01)
    else:
        binary_data.append(0x00)

    binary_data.extend(len(dictionary).to_bytes(2, 'little', signed=False))  # EntryCount
    binary_data.extend(version.to_bytes(4, 'little', signed=False))  # SchemaVersion
    binary_data.extend(dictionary_binary_size(dictionary, copyright).to_bytes(4, 'little', signed=False))  # DictionarySize

    # track property name offsets, this is initialized to the first property name
    name_offset = dictionary_binary_header_size() + (len(dictionary) * dictionary_binary_entry_size())

    # maintain a dictionary of names to offsets to allow multiple fixed sized entries to point
    # to the same name
    name_to_offset_dict = {}

    # list of unique names to add to the end of the dictionary
    names = []

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

        # NameOffset
        if item[DICTIONARY_ENTRY_FIELD_STRING]:
            if item[DICTIONARY_ENTRY_FIELD_STRING] in name_to_offset_dict:
                offset = name_to_offset_dict[item[DICTIONARY_ENTRY_FIELD_STRING]]
            else:
                # add name and increment name_offset
                name_to_offset_dict[item[DICTIONARY_ENTRY_FIELD_STRING]] = name_offset
                offset = name_offset
                names.append(item[DICTIONARY_ENTRY_FIELD_STRING])
                name_offset += len(item[DICTIONARY_ENTRY_FIELD_STRING]) + 1

            binary_data.extend(offset.to_bytes(2, 'little'))
        else:
            binary_data.extend([0x00, 0x00])

    # Add the property names to the end of the dictionary
    for name in names:
        binary_data.extend([ord(elem) for elem in name])
        binary_data.append(0x00)  # null terminator

    # Add the copyright string if any
    if copyright and len(copyright):
        binary_data.extend((len(copyright) + 1).to_bytes(1, 'little'))
        binary_data.extend([ord(elem) for elem in copyright])
        binary_data.append(0x00)
    else:
        binary_data.append(0x00)  # set the copyright length to zero

    return binary_data


def get_int_from_byte_array(byte_array, start_index, size):
    return int.from_bytes(byte_array[start_index:start_index+size], 'little'), start_index + size


class DictionaryByteArrayStreamSimple:
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
    stream = DictionaryByteArrayStreamSimple(byte_array)

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
        name_offset = stream.get_int(2)

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


def generate_annotation_schema_dictionary(csdl_schema_dirs, json_schema_dirs, version=None, copyright=None):
    """ Generate the annotation schema dictionary.

    Args:
        csdl_schema_dirs: List of CSDL schema directories.
        json_schema_dirs: List of JSON schema directories.
        version: The version of the annotation in Redfish format (e.g. v1_0_0) (default None).

    Return:
        SchemaDictionary: Named tuple which has the following fields:
                          dictionary - The annotation dictionary.
                          dictionary_byte_array - The annotation dictionary in byte array.
                          json_dictionary - Annotation dictionary in JSON format.
    """
    global includeNamespaces
    global verbose

    # Initialize the global variables.
    doc_list = {}
    entity_repo = {}
    entity_offset_map = {}
    includeNamespaces = {}

    # Set the schema file name and entity for annotations.
    # TODO: Does not work with remote locations
    schema_file_name = 'RedfishExtensions_v1.xml'
    entity = 'RedfishExtensions.PropertyPattern'

    # Compute source starting with the first csdl directory. The first one wins.
    source = schema_file_name
    for csdl_dir in csdl_schema_dirs:
        if os.path.isfile(os.path.join(csdl_dir, schema_file_name)):
            source = os.path.join(csdl_dir, schema_file_name)
            break

    # Add namespaces.
    add_namespaces(csdl_schema_dirs, source, doc_list)

    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(doc_list)

    add_all_entity_and_complex_types(doc_list, entity_repo)
    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    # search for entity and build dictionary
    if entity in entity_repo:
        ver = ''
        dictionary = generate_annotation_dictionary(version, json_schema_dirs, entity_repo, entity_offset_map)
        ver = to_ver32(version)

        # Generate dictionary_byte_array.
        dictionary_byte_array = generate_byte_array(dictionary, ver, False, copyright)

        # Generate JSON dictionary.
        json_dictionary = generate_json_dictionary(json_schema_dirs, dictionary, dictionary_byte_array, 'annotation')
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


def generate_schema_dictionary(source_type, csdl_schema_dirs, json_schema_dirs,
                               entity, schema_file_name, oem_entities=None,
                               oem_schema_file_names=None, profile=None, schema_url=None,
                               copyright=None):
    """ Generate the schema dictionary.

    Args:
        source_type: Type of schema file. local or remote.
        csdl_schema_dirs: List of CSDL schema directories.
        json_schema_dirs: List of JSON schema directories.
        entity: Schema entity name.
        schema_file_name: Schema file name.
        oem_entities: List of oem entities (default None).
        oem_schema_file_names: List of OEM schema file names (default None).
        profile: Schema profile (default None)
        schema_url: Schema URL. Used when source_type is remote (default None).
        copyright: Copyright string that should be appended to the binary dictionary

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
    oem_sources = []
    oem_entity_type = ''
    entity_repo = {}
    entity_offset_map = {}
    includeNamespaces = {}

    # Validate source type.
    if source_type not in ['local', 'remote']:
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
                    oem_sources.append(os.path.join(csdl_dir, oem_schema_file))

        oem_entity_type = entity + '.Oem'
        # create a special entity for OEM and set the major entity's oem section to it
        entity_repo[oem_entity_type] = ('Set', [])
        for oemEntityPair in oem_entities:
            oemName, oem_entity = oemEntityPair.split('=')
            entity_repo[oem_entity_type][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].append(
               [oemName, 'Set', '', oem_entity])

    # Add namespaces.
    add_namespaces(csdl_schema_dirs, source, doc_list)
    for oemSource in oem_sources:
        add_namespaces(csdl_schema_dirs, oemSource, doc_list)

    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(doc_list)

    add_all_entity_and_complex_types(doc_list, entity_repo)
    if verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    # set the entity oem entry to the special OEM entity type
    if source_type == 'local' and oem_schema_file_names:
        for property in entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]:
            if property[PROPERTY_FIELD_STRING] == 'Oem':
                property[PROPERTY_OFFSET] = oem_entity_type

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
                profile_requirements = process_profile(json_profile, entity, entity_repo)
                if profile_requirements:
                    truncate_entity_repo(entity_repo, profile_requirements, is_truncated)
                else:
                    if verbose:
                        print('Error parsing profile')
                    return (SchemaDictionary(dictionary=None,
                                             dictionary_byte_array=None,
                                             json_dictionary=None))

            add_dictionary_entries(dictionary, entity_repo, entity, entity_offset_map, True, get_entity_name(entity))
            dictionary = generate_dictionary(dictionary, entity_repo, entity_offset_map)
            ver = get_latest_version_as_ver32(entity)
            if verbose:
                print(entity_offset_map)

        # Generate dictionary_byte_array.
        dictionary_byte_array = generate_byte_array(dictionary, ver, False, copyright)

        # Generate JSON dictionary.
        json_dictionary = generate_json_dictionary(json_schema_dirs, dictionary, dictionary_byte_array, entity)
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


def generate_error_schema_dictionary(csdl_schema_dirs, json_schema_dirs, copyright=None):
    """ Generate the error schema dictionary.

    Args:
        csdl_schema_dirs: List of CSDL schema directories.
        json_schema_dirs: List of JSON schema directories.

    Return:
        SchemaDictionary: Named tuple which has the following fields:
                          dictionary - The error schema dictionary.
                          dictionary_byte_array - The error schema dictionary in byte array.
                          json_dictionary - Error schema dictionary in JSON format.
    """
    return generate_schema_dictionary('local', csdl_schema_dirs, json_schema_dirs,
                                      'RedfishError.RedfishError', 'RedfishError_v1.xml',
                                      oem_entities=None, oem_schema_file_names=None, profile=None, schema_url=None,
                                      copyright=copyright)
