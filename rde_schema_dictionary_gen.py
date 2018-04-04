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

includeNamespaces = {}
entityToPropertyMap = {}
ENUM_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EnumType'
COMPLEX_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}ComplexType'
TYPE_DEFINITION = '{http://docs.oasis-open.org/odata/ns/edm}TypeDefinition'
ENTITY_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EntityType'
NAVIGATION_PROPERTY = '{http://docs.oasis-open.org/odata/ns/edm}NavigationProperty'
ACTION_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}Action'
ALL_NAMESPACES = {'edm': 'http://docs.oasis-open.org/odata/ns/edm', 'edmx': 'http://docs.oasis-open.org/odata/ns/edmx'}

OPTIMIZE_REDUNDANT_DICTIONARY_ENTRIES = True


def get_base_properties(entity_type):
    properties = []
    if entity_type.get('BaseType') is not None:
        base_type = entity_type.get('BaseType')
        base_entity = get_base_type(entity_type)
        properties = get_properties(base_entity)
        properties = properties + get_base_properties(base_entity)

        # If the object is derived from Resource or ResourceCollection then we add the OData properties
        if base_type == 'Resource.v1_0_0.Resource' or base_type == 'Resource.v1_0_0.ResourceCollection':
            properties.append(['@odata.context', 'String', ''])
            properties.append(['@odata.id', 'String', ''])
            properties.append(['@odata.type', 'String', ''])
            properties.append(['@odata.etag', 'String', ''])

    return properties


def strip_version(val):
    m = re.compile('(\w+)\.v.*?\.(\w+)').search(val)
    if m:
        return m.group(1) + '.' + m.group(2)
    return val


def get_properties(some_type):
    properties = []
    property_elements = some_type.xpath('descendant-or-self::edm:Property | edm:NavigationProperty',
                                        namespaces=ALL_NAMESPACES)
    for property_element in property_elements:
        property_name = property_element.get('Name')

        property_type = property_element.get('Type')

        is_auto_expand = property_element.tag != NAVIGATION_PROPERTY \
            or (property_element.tag == NAVIGATION_PROPERTY
                and len(property_element.xpath('child::edm:Annotation[@Term=\'OData.AutoExpand\']',
                                               namespaces=ALL_NAMESPACES)))
        is_auto_expand_refs = not is_auto_expand

        m = re.compile('Edm\.(.*)').match(property_type)
        if m:  # primitive type?
            primitive_type = m.group(1)
            if primitive_type == "DateTimeOffset" or primitive_type == "Duration" or primitive_type == "TimeOfDay" \
                    or primitive_type == "Guid":
                primitive_type = 'String'
            if ((primitive_type == "SByte") or (primitive_type == "Int16") or (primitive_type == "Int32") or
                    (primitive_type == "Int64") or (primitive_type == "Decimal")):
                primitive_type = 'Integer'
            properties.append([property_name, primitive_type, ''])
        else:  # complex type
            complex_type = None
            is_array = re.compile('Collection\((.*?)\)').match(property_type)
            if is_array:
                if is_auto_expand_refs:
                    # TODO fix references
                    # properties.append([propertyName, 'Array', strip_version(m.group(1)), 'AutoExpandRef'])
                    properties.append([property_name, 'Array', 'AutoExpandRef'])
                else:  # AutoExpand or not specified
                    array_type = is_array.group(1)

                    if array_type.startswith('Edm.'):  # primitive types
                        properties.append([property_name, 'Array', array_type, ''])
                    else:
                        properties.append([property_name, 'Array', strip_version(is_array.group(1)), 'AutoExpand'])

                # add the @count property for navigation properties that are arrays
                if property_element.tag == NAVIGATION_PROPERTY:
                    properties.append([property_name+'@odata.count', 'Integer', ''])

            else:
                complex_type = find_element_from_type(property_type)

            if complex_type is not None:
                if complex_type.tag == ENUM_TYPE:
                    properties.append([property_name, 'Enum', strip_version(property_type)])
                elif complex_type.tag == COMPLEX_TYPE or complex_type.tag == ENTITY_TYPE:
                    if is_auto_expand_refs:
                        properties.append([property_name, 'SchemaLink', ''])
                    else:
                        properties.append([property_name, 'Set', strip_version(property_type)])
                elif complex_type.tag == TYPE_DEFINITION:
                    assert(re.compile('Edm\..*').match(complex_type.get('UnderlyingType')))
                    m = re.compile('Edm\.(.*)').match(complex_type.get('UnderlyingType'))
                    properties.append([property_name, m.group(1), ''])
                else:
                    print(complex_type.tag)
                    assert False

    return properties


def get_namespace(entity_type):
    namespace = entity_type.xpath('parent::edm:Schema', namespaces=ALL_NAMESPACES)[0].get('Namespace')
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


ENTITY_REPO_TUPLE_TYPE_INDEX = 0
ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX = 1


def add_entity_and_complex_types(doc, entity_repo):
    for entityType in doc.xpath('//edm:EntityType | //edm:ComplexType', namespaces=ALL_NAMESPACES):
        properties = []
        if is_abstract(entityType) is not True:
            if is_parent_abstract(entityType):
                properties = get_base_properties(entityType)

            properties = properties + get_properties(entityType)

            entity_type_name = get_qualified_entity_name(entityType)
            if entity_type_name not in entity_repo:
                entity_repo[entity_type_name] = ('Set', [])

            # sort and add to the map
            # add only unique entries - this is to handle Swordfish vs Redfish conflicting schema (e.g. Volume)
            entity_repo[entity_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
                [item for item in sorted(properties, key=itemgetter(0))
                 if item not in entity_repo[entity_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
            )

    for enum_type in doc.xpath('//edm:EnumType', namespaces=ALL_NAMESPACES):
        enum_type_name = get_qualified_entity_name(enum_type)
        if enum_type_name not in entity_repo:
            entity_repo[enum_type_name] = ('Enum', [])
        entity_repo[enum_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
            [[enum] for enum in enum_type.xpath('child::edm:Member/@Name', namespaces=ALL_NAMESPACES)
             if [enum] not in entity_repo[enum_type_name][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
        )

    # TODO: fix actions
    for actionType in doc.xpath('//edm:Action', namespaces=ALL_NAMESPACES):
        print("Action: ", actionType.get('Name'))
        for child in actionType:
            print('    ', child.tag)


def add_namespaces(source, doc_list, local_or_remote):
    doc_name = source
    schema_string = ''
    if local_or_remote == 'remote':
        doc_name = extract_doc_name_from_url(source)

    # first load the CSDL file as a string
    if doc_name not in doc_list:
        if local_or_remote == 'remote':
            # ignore odata references
            if source.find('http://docs.oasis') == -1:
                try:
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
        for namespace in doc.xpath('descendant-or-self::edm:Schema[@Namespace]', namespaces=ALL_NAMESPACES):
            if namespace.get('Namespace') not in includeNamespaces:
                includeNamespaces[namespace.get('Namespace')] = namespace
            else:
                return

        # bring in all dependent documents and their corresponding namespaces
        for ref in doc.xpath('descendant-or-self::edmx:Reference', namespaces=ALL_NAMESPACES):
            if local_or_remote == 'remote':
                dependent_source = ref.get('Uri')
            else:
                dependent_source = args.schemaDir + '/metadata/' + extract_doc_name_from_url(ref.get('Uri'))
                if os.path.exists(dependent_source) is False:
                    continue
                print(dependent_source)
            add_namespaces(dependent_source, doc_list, local_or_remote)


def find_enum(key, dictionary):
    for k, v in dictionary.items():
        if k == key and "enum" in v:
            return v
        elif isinstance(v, dict):
            f = find_enum(key, v)
            if f is not None and "enum" in f:
                return f
    return None


def add_all_entity_and_complex_types(doc_list):
    entity_repo = {}
    for key in doc_list:
        add_entity_and_complex_types(doc_list[key], entity_repo)

    # add special ones for AutoExpandRefs
    entity_repo['AutoExpandRef'] = ('Set', [['@odata.id', 'String', '']])

    # second pass, add seq numbers
    for key in entity_repo:
        for seq, item in enumerate(entity_repo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            item.insert(0, seq)
        # TODO: Fix enums
        if entity_repo[key][ENTITY_REPO_TUPLE_TYPE_INDEX] == 'Enum':
            # build a list of json schema files that need to be scanned for the enum in question
            [base_filename, enum_name] = key.split('.')
            print("Need to look at json schema to fix enums for", key, base_filename)
            enum_values = []
            for file in os.listdir(args.schemaDir + '/json-schema/'):
                if file.startswith(base_filename + '.'):
                    json_schema = json.load(open(args.schemaDir + '/json-schema/' + file))
                    # search json schema for enum

                    print("Looking for", enum_name,"in", args.schemaDir + '/json-schema/' + file)
                    json_enum = find_enum(enum_name, json_schema)
                    if json_enum is not None:
                        print(json_enum["enum"])
                        enum_values = enum_values + list((Counter(json_enum["enum"]) - Counter(enum_values)).elements())
                        print(enum_values)
    return entity_repo


def get_base_type(child):
    if child.get('BaseType') is not None:
        m = re.compile('(.*)\.(\w*)').match(child.get('BaseType'))
        base_namespace = m.group(1)
        base_entity_name = m.group(2)
        return includeNamespaces[base_namespace].xpath(
            'child::edm:EntityType[@Name=\'%s\'] | child::edm:ComplexType[@Name=\'%s\']' % (base_entity_name,
                                                                                            base_entity_name),
            namespaces=ALL_NAMESPACES)[0]


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
                                                  namespaces=ALL_NAMESPACES)[0]
    return None


def print_table_data(data):
    print(tabulate(data, headers="firstrow", tablefmt="grid"))


def add_dictionary_entries(schema_dictionary, entity_repo, entity):
    SEQ_NUMBER = 0
    FIELD_STRING = 1
    TYPE = 2
    OFFSET = 3
    EXPAND = 4

    if entity in entity_repo:
        entity_type = entity_repo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX]
        start = len(schema_dictionary)
        for index, property in enumerate(entity_repo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            if entity_type == 'Enum':  # this is an enum
                schema_dictionary.append(
                    [index + start, 'String', property[SEQ_NUMBER], property[FIELD_STRING], ''])
            elif property[TYPE] == 'Array':  # this is an array
                # TODO fix == 5 by making AutoExpand also 4 elements
                if len(property) == 5 and property[EXPAND] == 'AutoExpand':
                    schema_dictionary.append(
                        [index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING], property[OFFSET]])
                else:
                    schema_dictionary.append(
                        [index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING], property[OFFSET]])
            else:
                schema_dictionary.append([index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING],
                                          property[OFFSET]])


DICTIONARY_INDEX = 0
DICTIONARY_FORMAT = 1
DICTIONARY_SEQUENCE_NUMBER = 2
DICTIONARY_FIELD_STRING = 3
DICTIONARY_OFFSET = 4


def print_dictionary_summary(schema_dictionary):
    print("Total Entries:", len(schema_dictionary))
    print("Fixed size consumed:", 10 * len(schema_dictionary))
    # calculate size of free form property names:
    total_field_string_size = 0
    for item in schema_dictionary:
        total_field_string_size = total_field_string_size + len(item[DICTIONARY_FIELD_STRING])
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
    elif format == 'SchemaLink':
        return '0x0F'


def generate_byte_array(schema_dictionary):
    # first entry is the schema entity
    print('const uint8', schema_dictionary[0][DICTIONARY_FIELD_STRING].split('.')[1]
          + '_schema_dictionary[]= { 0x00, 0x00')

    iter_schema = iter(schema_dictionary)
    next(iter_schema)  # skip the first entry since it is the schema entity
    for item in iter_schema:
        print(to_format(item[DICTIONARY_FORMAT]))
        pass


def find_item_offset(schema_dictionary, item_to_find):
    offset = 0
    for index, item in enumerate(schema_dictionary):
        if item[DICTIONARY_FIELD_STRING] == item_to_find:
            offset = index
            break

    return offset


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
    local_parser.add_argument('--outputFile', type=str, required=False)

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.source is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # bring in all dependent documents and their corresponding namespaces
    doc_list = {}
    source = ''
    if args.source == 'local':
        source = args.schemaDir + '/' + 'metadata/' + args.schemaFilename
    elif args.source == 'remote':
        source = args.schemaURL
    add_namespaces(source, doc_list, args.source)

    entity = args.entity
    if args.verbose:
        pprint.PrettyPrinter(indent=3).pprint(doc_list)

    entity_repo = add_all_entity_and_complex_types(doc_list)
    if args.verbose:
        pprint.PrettyPrinter(indent=3).pprint(entity_repo)

    # search for entity and build dictionary
    if entity in entity_repo:
        schema_dictionary = [[0, 'Set', 0, entity, 1]]
        add_dictionary_entries(schema_dictionary, entity_repo, entity)

        can_expand = True
        while can_expand:
            tmp_dictionary = schema_dictionary.copy()
            was_expanded = False
            for index, item in enumerate(schema_dictionary):
                if (type(item[DICTIONARY_OFFSET]) == str and item[DICTIONARY_OFFSET] != ''
                    and (item[DICTIONARY_OFFSET] in entity_repo)) \
                        and (item[DICTIONARY_FORMAT] == 'Set' or item[DICTIONARY_FORMAT] == 'Enum'
                             or item[DICTIONARY_FORMAT] == 'Array'):

                    # optimization: check to see if dictionary already contains an entry for the complex type/enum.
                    # If yes, then just reuse it instead of creating a set of entries.
                    offset = 0
                    if OPTIMIZE_REDUNDANT_DICTIONARY_ENTRIES:
                        offset = find_item_offset(schema_dictionary, item[DICTIONARY_OFFSET])

                    if offset == 0:
                        offset = len(tmp_dictionary)
                        item_type = entity_repo[item[DICTIONARY_OFFSET]][ENTITY_REPO_TUPLE_TYPE_INDEX]
                        next_offset = offset + 1
                        # if there are no properties for an entity (e.g. oem), then leave a blank offset
                        if len(entity_repo[item[DICTIONARY_OFFSET]][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]) == 0:
                            next_offset = ''
                        tmp_dictionary.append([offset, item_type, 0, item[DICTIONARY_OFFSET], next_offset])
                        add_dictionary_entries(tmp_dictionary, entity_repo, item[DICTIONARY_OFFSET])
                    tmp_dictionary[index][DICTIONARY_OFFSET] = offset
                    was_expanded = True
                    break
            if was_expanded:
                schema_dictionary = tmp_dictionary.copy()
            else:
                can_expand = False

            # print_table_data(
            #    [[ "Entry", "Format", "Sequence#", "Field String", "Offset"]]
            #    +
            #    schema_dictionary
            # )

        print_table_data(
            [["Entry", "Format", "Sequence#", "Field String", "Offset"]]
            +
            schema_dictionary
        )

        print_dictionary_summary(schema_dictionary)

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
