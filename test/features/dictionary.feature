@fixture.schema_source
Feature: The dictionary is generated with the correct format

    Scenario Outline: Dictionary headers are encoded correctly
        Given a CSDL schema file <Schema> and entity <Entity>
        When the dictionary is generated with Copyright set to Copyright (c) 2018 DMTF
        Then the dictionary header shall have the VersionTag equal to 0x00
        And the dictionary header shall have the DictionaryFlags equal to 0x00
        And the dictionary header shall have the EntryCount greater than 0x00
        And the dictionary header shall have the SchemaVersion greater than 0x00
        And the dictionary header shall have the SchemaVersion not equal to 0xFFFFFFFF
        And the dictionary header shall have the DictionarySize greater than 0x00
        And the dictionary size is correct
        And the dictionary shall have the Copyright set to Copyright (c) 2018 DMTF

        Examples:
            | Schema                | Entity                        |
            | Storage_v1.xml        | Storage.Storage               |
            | Drive_v1.xml          | Drive.Drive                   |
            | ComputerSystem_v1.xml | ComputerSystem.ComputerSystem |
            | Port_v1.xml           | Port.Port                     |


    Scenario: Generate dictionaries for all schema files
        Given a list of schema files
        Then the resulting dictionaries have valid header information
