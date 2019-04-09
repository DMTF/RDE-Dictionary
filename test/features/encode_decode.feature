@fixture.schema_source
Feature: The dictionary can be used to encode/decode BEJ

    Scenario: Encoding JSON into BEJ using dictionaries
        Given a CSDL schema file Storage_v1.xml and entity Storage.Storage
        When the dictionary is generated with Copyright set to Copyright (c) 2018 DMTF
        Then the following JSON is encoded using the dictionary successfully
            """
            {
               "@odata.type": "#Storage.v1_3_0.Storage",
               "@odata.context": "/redfish/v1/$metadata#Storage.Storage",
               "@odata.id": "/redfish/v1/Systems/1/Storage/1",
               "Id": "RAID Controller 1",
               "Name": "RAID Controller",
               "Description": "RAID Controller",
               "Status": {
                  "State": "Enabled",
                  "Health": "OK",
                  "HealthRollup": "OK"
               },
               "StorageControllers": [
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1#/StorageControllers/0",
                     "@odata.type": "#Storage.v1_3_0.StorageController",
                     "MemberId": "0",
                     "Name": "SAS RAID Controller",
                     "Status": {
                        "State": "Enabled",
                        "Health": "OK"
                     },
                     "Identifiers": [
                        {
                           "DurableNameFormat": "NAA",
                           "DurableName": "5045594843305852483430304E452000"
                        }
                     ],
                     "Manufacturer": "Consorto",
                     "Model": "Consorty RAID Controller XYZ",
                     "SerialNumber": "PEYHC0XRH400NE",
                     "PartNumber": "7334534",
                     "SpeedGbps": 12,
                     "FirmwareVersion": "1.00",
                     "SupportedControllerProtocols": [
                        "PCIe"
                     ],
                     "SupportedDeviceProtocols": [
                        "SAS",
                        "SATA"
                     ]
                  }
               ],
               "Drives": [
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.2"
                  },
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.3"
                  },
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.4"
                  },
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.5"
                  },
                  {
                     "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1/Drives/Disk.Bay.6"
                  }
               ],
               "Volumes": {
                  "@odata.id": "/redfish/v1/volcollection"
               },
               "Links": {
                  "Enclosures": [
                     {
                        "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1"
                     }
                  ]
               }
            }
            """
        And the BEJ can be successfully decoded back to JSON


    Scenario: Encoding large JSON into BEJ using dictionaries
        Given a CSDL schema file Storage_v1.xml and entity Storage.Storage
        When the dictionary is generated with Copyright set to Copyright (c) 2018 DMTF
        Then the following JSON is encoded using the dictionary successfully
            """
            {
               "@odata.type": "#Storage.v1_3_0.Storage",
               "@odata.context": "/redfish/v1/$metadata#Storage.Storage",
               "@odata.id": "/redfish/v1/Systems/1/Storage/1",
               "Id": "RAID Controller 1",
               "Name": "RAID Controller",
               "Description": "RAID Controller",
               "Status": {
                  "State": "Enabled",
                  "Health": "OK",
                  "HealthRollup": "OK"
               },
               "StorageControllers": [
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1#/StorageControllers/0",
                     "@odata.type": "#Storage.v1_3_0.StorageController",
                     "MemberId": "0",
                     "Name": "SAS RAID Controller",
                     "Status": {
                        "State": "Enabled",
                        "Health": "OK"
                     },
                     "Identifiers": [
                        {
                           "DurableNameFormat": "NAA",
                           "DurableName": "5045594843305852483430304E452000"
                        }
                     ],
                     "Manufacturer": "Consorto",
                     "Model": "Consorty RAID Controller XYZ",
                     "SerialNumber": "PEYHC0XRH400NE",
                     "PartNumber": "7334534",
                     "SpeedGbps": 12,
                     "FirmwareVersion": "1.00",
                     "SupportedControllerProtocols": [
                        "PCIe"
                     ],
                     "SupportedDeviceProtocols": [
                        "SAS",
                        "SATA"
                     ]
                  }
               ],
               "Drives": [
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/2"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/3"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/4"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/5"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/6"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/7"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/8"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/9"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/10"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/11"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/12"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/13"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/14"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/15"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/16"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/17"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/18"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/19"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/20"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/21"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/22"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/23"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/24"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/25"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/26"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/27"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/28"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/29"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/30"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/31"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/32"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/33"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/34"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/35"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/36"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/37"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/38"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/39"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/40"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/41"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/42"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/43"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/44"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/45"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/46"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/47"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/48"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/49"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/50"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/51"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/52"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/53"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/54"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/55"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/56"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/57"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/58"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/59"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/60"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/61"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/62"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/63"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/64"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/65"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/66"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/67"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/68"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/69"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/70"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/71"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/72"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/73"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/74"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/75"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/76"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/2"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/3"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/4"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/5"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/6"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/7"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/8"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/9"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/10"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/11"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/12"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/13"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/14"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/15"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/16"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/17"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/18"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/19"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/20"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/21"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/22"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/23"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/24"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/25"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/26"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/27"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/28"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/29"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/30"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/31"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/32"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/33"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/34"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/35"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/36"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/37"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/38"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/39"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/40"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/41"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/42"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/43"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/44"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/45"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/46"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/47"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/48"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/49"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/50"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/51"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/52"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/53"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/54"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/55"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/56"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/57"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/58"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/59"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/60"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/61"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/62"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/63"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/64"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/65"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/66"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/67"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/68"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/69"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/70"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/71"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/72"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/73"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/74"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/75"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/76"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  },
                  {
                     "@odata.id": "/redfish/v1/Systems/1/Storage/1/Drives/1"
                  }
               ],
               "Volumes": {
                  "@odata.id": "/redfish/v1/volcollection"
               },
               "Links": {
                  "Enclosures": [
                     {
                        "@odata.id": "/redfish/v1/Chassis/StorageEnclosure1"
                     }
                  ]
               }
            }
            """
        And the BEJ can be successfully decoded back to JSON
