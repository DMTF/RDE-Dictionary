from lxml import etree, objectify
import argparse
import json
import re
from collections import OrderedDict
import os.path
from operator import itemgetter
import pprint
from tabulate import tabulate
import urllib.request
import sys

includeNamespaces = {}
entityToPropertyMap = {}
ENUM_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EnumType'
COMPLEX_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}ComplexType'
TYPE_DEFINITION = '{http://docs.oasis-open.org/odata/ns/edm}TypeDefinition'
ENTITY_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}EntityType'
NAVIGATION_PROPERTY = '{http://docs.oasis-open.org/odata/ns/edm}NavigationProperty'
ACTION_TYPE = '{http://docs.oasis-open.org/odata/ns/edm}Action'
ALL_NAMESPACES = {'edm': 'http://docs.oasis-open.org/odata/ns/edm', 'edmx':'http://docs.oasis-open.org/odata/ns/edmx'}

OPTIMIZE_REDUNDANT_DICTIONARY_ENTRIES = True

def getBaseProperties(entityType):
    properties = []
    if entityType.get('BaseType') != None:
        baseType = entityType.get('BaseType')
        baseEntity = getBaseType(entityType)
        properties = getProperties(baseEntity)
        properties = properties + getBaseProperties(baseEntity)

        # If the object is derived from Resource or ResourceCollection then we add the OData properties
        if baseType == 'Resource.v1_0_0.Resource' or baseType == 'Resource.v1_0_0.ResourceCollection':
            properties.append(['@odata.context', 'String', ''])
            properties.append(['@odata.id', 'String', ''])
            properties.append(['@odata.type', 'String', ''])
            properties.append(['@odata.etag', 'String', ''])

    return properties

def stripVersion(type):
    m = re.compile('(\w+)\.v.*?\.(\w+)').search(type)
    if m:
        return m.group(1) + '.' + m.group(2)
    return type

def getProperties(someType, indent=''):
    properties = []
    propertyElements = someType.xpath('descendant-or-self::edm:Property | edm:NavigationProperty',
                                    namespaces=ALL_NAMESPACES)
    for propertyElement in propertyElements:
        propertyName = propertyElement.get('Name')

        propertyType = propertyElement.get('Type')

        isAutoExpand = propertyElement.tag != NAVIGATION_PROPERTY or (propertyElement.tag == NAVIGATION_PROPERTY and len(propertyElement.xpath('child::edm:Annotation[@Term=\'OData.AutoExpand\']', namespaces=ALL_NAMESPACES)))
        isAutoExpandRefs = isAutoExpand == False

        m = re.compile('Edm\.(.*)').match(propertyType)
        if m: # primitive?
            primitiveType = m.group(1)
            if primitiveType == "DateTimeOffset" or  primitiveType == "Duration" or primitiveType == "TimeOfDay" or primitiveType == "Guid":
                primitiveType = 'String'
            if ((primitiveType == "SByte") or (primitiveType == "Int16") or (primitiveType == "Int32") or
                    (primitiveType == "Int64") or (primitiveType == "Decimal")):
                primitiveType = 'Integer'
            properties.append([propertyName, primitiveType, ''])
        else:  # complex
            complexType = None
            isArray = re.compile('Collection\((.*?)\)').match(propertyType)
            if isArray:
                if isAutoExpandRefs:
                    # TODO fix references
                    #properties.append([propertyName, 'Array', stripVersion(m.group(1)), 'AutoExpandRef'])
                    properties.append([propertyName, 'Array', 'AutoExpandRef'])
                else: # AutoExpand or not specified
                    arrayType = isArray.group(1)

                    if arrayType.startswith('Edm.'): # primitive types
                        properties.append([propertyName, 'Array', arrayType, ''])
                    else:
                        properties.append([propertyName, 'Array', stripVersion(isArray.group(1)), 'AutoExpand'])

                # add the @count property for navigation properties that are arrays
                if propertyElement.tag == NAVIGATION_PROPERTY:
                    properties.append([propertyName+'@odata.count', 'Integer', ''])

            else:
                complexType = findElementFromType(propertyType)

            if complexType != None:
                if complexType.tag == ENUM_TYPE:
                    properties.append([propertyName, 'Enum', stripVersion(propertyType)])
                elif complexType.tag == COMPLEX_TYPE or complexType.tag == ENTITY_TYPE:
                    if isAutoExpandRefs:
                        properties.append([propertyName, 'Set', ''])
                    else:
                        properties.append([propertyName, 'Set', stripVersion(propertyType)])
                elif complexType.tag == TYPE_DEFINITION:
                    assert(re.compile('Edm\..*').match(complexType.get('UnderlyingType')))
                    m = re.compile('Edm\.(.*)').match(complexType.get('UnderlyingType'))
                    properties.append([propertyName, m.group(1), ''])
                else:
                    print(complexType.tag)
                    assert (False)

    return properties

def getNamespace(entityType):
    namespace = entityType.xpath('parent::edm:Schema', namespaces=ALL_NAMESPACES)[0].get('Namespace')
    if namespace.find('.') != -1:
        m = re.search('(\w*?)\.v.*', namespace)
        if m:
            namespace = m.group(1)
        else:
            namespace = ''
    return namespace

def getQualifiedEntityName(entity):
    return getNamespace(entity) + '.' + entity.get('Name')

def extractDocNameFromUrl(url):
    m = re.compile('http://.*/(.*\.xml)').match(url)
    if m:
        return m.group(1)
    else:
        return ''

ENTITY_REPO_TUPLE_TYPE_INDEX = 0
ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX = 1
def addEntityAndComplexTypes(doc, entityRepo):
    for entityType in doc.xpath('//edm:EntityType | //edm:ComplexType', namespaces=ALL_NAMESPACES):
        properties = []
        if isAbstract(entityType) is not True:
            if isParentAbstract(entityType):
                properties = getBaseProperties(entityType)

            properties = properties + getProperties(entityType, indent='    ')

            entityTypeName = getQualifiedEntityName(entityType)
            if entityTypeName not in entityRepo:
                entityRepo[entityTypeName] = ('Set',[])

            # sort and add to the map
            # add only unique entries - this is to handle swordfish vs redfish conflicting schema (e.g. Volume)
            entityRepo[entityTypeName][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
                [item for item in sorted(properties, key=itemgetter(0)) if item not in entityRepo[entityTypeName][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
            )

    for enumType in doc.xpath('//edm:EnumType', namespaces=ALL_NAMESPACES):
        enumTypeName = getQualifiedEntityName(enumType)
        if enumTypeName not in entityRepo:
            entityRepo[enumTypeName] = ('Enum', [])
        entityRepo[enumTypeName][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX].extend(
            [[enum] for enum in enumType.xpath('child::edm:Member/@Name', namespaces=ALL_NAMESPACES) if [enum] not in entityRepo[enumTypeName][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]]
        )

    for actionType in doc.xpath('//edm:Action', namespaces=ALL_NAMESPACES):
        print("Balaji", actionType.get('Name'))
        for child in actionType:
            print('    ',child.tag)


def addNamespaces(source, docList, localOrRemote):
    docName = source
    schemaString = ''
    if localOrRemote == 'remote':
        docName = extractDocNameFromUrl(source)

    # first load the CSDL file as a string
    if docName not in docList:
        if localOrRemote == 'remote':
            # ignore odata references
            if source.find('http://docs.oasis') == -1:
                try:
                    print('Opening URL', source)
                    schemaString = urllib.request.urlopen(source).read()
                except:
                    return
            else:
                return
        else:
            with open(source, 'rb') as localFile:
                schemaString = localFile.read()

    if schemaString != '':
        doc = etree.fromstring(schemaString)
        docList[docName] = doc
        # load all namespaces in the current doc
        for namespace in doc.xpath('descendant-or-self::edm:Schema[@Namespace]', namespaces=ALL_NAMESPACES):
            if namespace.get('Namespace') not in includeNamespaces:
                includeNamespaces[namespace.get('Namespace')] = namespace
            else:
                return

        # bring in all dependent documents and their corresponding namespaces
        for ref in doc.xpath('descendant-or-self::edmx:Reference', namespaces=ALL_NAMESPACES):
            dependentSource = ''
            if localOrRemote == 'remote':
                dependentSource = ref.get('Uri')
            else:
                dependentSource = args.schemaDir + '/' + extractDocNameFromUrl(ref.get('Uri'))
                if os.path.exists(dependentSource) == False:
                    continue
                print(dependentSource)
            addNamespaces(dependentSource, docList, localOrRemote)


def addAllEntityAndComplexTypes(docList):
    entityRepo = {}
    for key in docList:
        addEntityAndComplexTypes(docList[key], entityRepo)

    # add special ones for AutoExpandRefs
    entityRepo['AutoExpandRef'] = ('Set', [['@odata.id', 'String', '']])

    # second pass, add seq numbers
    for key in entityRepo:
        for seq,item in enumerate(entityRepo[key][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            item.insert(0, seq)

    return entityRepo

def getBaseType(child):
    if child.get('BaseType') != None:
        m = re.compile('(.*)\.(\w*)').match(child.get('BaseType'))
        baseNamespace = m.group(1)
        baseEntityName = m.group(2)
        return includeNamespaces[baseNamespace].xpath('child::edm:EntityType[@Name=\'%s\'] | child::edm:ComplexType[@Name=\'%s\']' % (baseEntityName, baseEntityName),
                                               namespaces=ALL_NAMESPACES)[0]

def isParentAbstract(entityType):
    baseEntity = getBaseType(entityType)
    return (baseEntity != None) and (baseEntity.get('Abstract') == 'true')

def isAbstract(entityType):
    return (entityType != None) and (entityType.get('Abstract') == 'true')



def findElementFromType(type):
    m = re.compile('(.*)\.(\w*)').match(type)
    namespace = m.group(1)
    entityName = m.group(2)

    # TODO assert here instead of returning None to let users know that all referenced schema files are not available
    if namespace in includeNamespaces:
        return includeNamespaces[namespace].xpath('child::edm:*[@Name=\'%s\']' % (entityName), namespaces=ALL_NAMESPACES)[0]
    return None

def print_table_data( data ):
    print( tabulate(data, headers="firstrow", tablefmt="grid") )

def addDictionaryEntries(schemaDictionary, entityRepo, entity):
    SEQ_NUMBER = 0
    FIELD_STRING = 1
    TYPE = 2
    OFFSET = 3
    EXPAND = 4

    if entity in entityRepo:
        entityType = entityRepo[entity][ENTITY_REPO_TUPLE_TYPE_INDEX]
        start = len(schemaDictionary)
        for index, property in enumerate(entityRepo[entity][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]):
            if entityType == 'Enum': # this is an enum
                schemaDictionary.append(
                    [index + start, 'String', property[SEQ_NUMBER], property[FIELD_STRING], ''])
            elif property[TYPE] == 'Array': # this is an array
                # TODO fix == 5 by making AutoExpand also 4 elements
                if len(property) == 5 and property[EXPAND] == 'AutoExpand':
                    schemaDictionary.append(
                        [index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING], property[OFFSET]])
                else:
                    schemaDictionary.append(
                        [index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING], property[OFFSET]])
            else:
                schemaDictionary.append([index + start, property[TYPE], property[SEQ_NUMBER], property[FIELD_STRING], property[OFFSET]])


DICTIONARY_INDEX = 0
DICTIONARY_FORMAT = 1
DICTIONARY_SEQUENCE_NUMBER = 2
DICTIONARY_FIELD_STRING = 3
DICTIONARY_OFFSET = 4

def printDictionarySummary(schemaDictionary):
    print("Total Entries:", len(schemaDictionary))
    print("Fixed size consumed:", 10 * len(schemaDictionary))
    # calculate size of free form property names:
    totalFieldStringSize = 0
    for item in schemaDictionary:
        totalFieldStringSize = totalFieldStringSize + len(item[DICTIONARY_FIELD_STRING])
    print("Field string size consumed:", totalFieldStringSize)
    print('Total size:', 10 * len(schemaDictionary) + totalFieldStringSize)

def toFormat(format):
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

def generateByteArray(schemaDictionary):
    # first entry is the schema entity
    print('const uint8', schemaDictionary[0][DICTIONARY_FIELD_STRING].split('.')[1]+'_schema_dictionary[]= { 0x00, 0x00');

    iterSchema = iter(schemaDictionary)
    next(iterSchema) # skip the first entry since it is the schema entity
    for item in iterSchema:
        print(toFormat(item[DICTIONARY_FORMAT]))
        pass


def findItemOffset(schemaDictionary, itemToFind):
    offset = 0
    for index, item in enumerate(schemaDictionary):
        if item[DICTIONARY_FIELD_STRING] == itemToFind:
            offset = index
            break

    return offset

if __name__ == '__main__':
    # rde_schema_dictionary parse --schemaDir=directory --schemaFilename=filename
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", help="increase output verbosity")
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

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # bring in all dependent documents and their corresponding namespaces
    docList = {}
    source = ''
    if args.source == 'local':
        source = args.schemaDir + '/' + args.schemaFilename
    elif args.source == 'remote':
        source = args.schemaURL
    addNamespaces(source, docList, args.source)

    entity = args.entity
    #pprint.PrettyPrinter(indent=3).pprint(docList)

    entityRepo = addAllEntityAndComplexTypes(docList)
    #pprint.PrettyPrinter(indent=3).pprint(entityRepo)

    # search for entity and build dictionary
    if entity in entityRepo:
        schemaDictionary = [ [0, 'Set', 0, entity, 1] ]
        addDictionaryEntries(schemaDictionary, entityRepo, entity)

        canExpand = True;
        while canExpand:
            tmpDictionary = schemaDictionary.copy()
            wasExpanded = False
            for index, item in enumerate(schemaDictionary):
                if (type(item[DICTIONARY_OFFSET]) == str and item[DICTIONARY_OFFSET] != '' and (item[DICTIONARY_OFFSET] in entityRepo)) \
                    and (item[DICTIONARY_FORMAT] == 'Set' or item[DICTIONARY_FORMAT] == 'Enum' or item[DICTIONARY_FORMAT] == 'Array'):

                    # optimization: check to see if dictionary already contains an entry for the complex type/enum.
                    # If yes, then just reuse it instead of creating a set of entries.
                    offset = 0
                    if OPTIMIZE_REDUNDANT_DICTIONARY_ENTRIES:
                        offset = findItemOffset(schemaDictionary, item[DICTIONARY_OFFSET])

                    if offset == 0:
                        offset = len(tmpDictionary)
                        itemType = entityRepo[item[DICTIONARY_OFFSET]][ENTITY_REPO_TUPLE_TYPE_INDEX]
                        nextOffset = offset + 1
                        # if there are no properties for an entity (e.g. oem), then leave a blank offset
                        if len(entityRepo[item[DICTIONARY_OFFSET]][ENTITY_REPO_TUPLE_PROPERTY_LIST_INDEX]) == 0:
                            nextOffset = ''
                        tmpDictionary.append([offset, itemType, 0, item[DICTIONARY_OFFSET], nextOffset])
                        addDictionaryEntries(tmpDictionary, entityRepo, item[DICTIONARY_OFFSET])
                    tmpDictionary[index][DICTIONARY_OFFSET] = offset
                    wasExpanded = True
                    break
            if wasExpanded:
                schemaDictionary = tmpDictionary.copy()
            else:
                canExpand = False

            #print_table_data(
            #    [[ "Entry", "Format", "Sequence#", "Field String", "Offset"]]
            #    +
            #    schemaDictionary
            #)

        print_table_data(
            [[ "Entry", "Format", "Sequence#", "Field String", "Offset"]]
            +
            schemaDictionary
        )

        printDictionarySummary(schemaDictionary)


        #generateByteArray(schemaDictionary)

        if args.outputFile:
            file = open(args.outputFile, 'w')
            file.write(json.dumps(schemaDictionary))
            file.close()

            file = open(args.outputFile, 'r')
            dict = json.load(file)
            print(dict)
    else:
        print('Error, cannot find entity:', entity)
