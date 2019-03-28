[![Build Status](https://travis-ci.com/DMTF/RDE-Dictionary.svg?branch=master)](https://travis-ci.com/DMTF/RDE-Dictionary)


# rde-dictionary-builder

## Pre Requisites:
Minimum Python Version: 3.6

Minimum Redfish Schema Version: 1.6 (2018.3)

Conformance: PLDM for Redfish Device Enablement 1.0.0 draft 5

The RDE dictionary builder is based on Python 3 and the client system is required to have the Python framework installed before the tool can be installed and executed on the system.  Additionally, the following packages are required to be installed and accessible from the python environment:
* lxml
* tabulate
* gitpython

To install the required packages, use the command:
`pip install <package name>`

To upgrade already installed packages, use the command:
`pip install --upgrade <package name>`

## Usage 
```
usage: rde_schema_dictionary_gen.py [-h] [--verbose] [--silent]
                                    {local,annotation,error,view} ...

positional arguments:
  {local,annotation,error,view}

optional arguments:
  -h, --help            show this help message and exit
  --verbose             increase output verbosity
  --silent              no output prints unless errors
```
### Local Options
```
usage: rde_schema_dictionary_gen.py local [-h] -c
                                          [CSDLSCHEMADIRECTORIES [CSDLSCHEMADIRECTORIES ...]]
                                          -j
                                          [JSONSCHEMADIRECTORIES [JSONSCHEMADIRECTORIES ...]]
                                          -s SCHEMAFILENAME -e ENTITY
                                          [-o [OEMSCHEMAFILENAMES [OEMSCHEMAFILENAMES ...]]]
                                          [-t [OEMENTITIES [OEMENTITIES ...]]]
                                          [-r COPYRIGHT] [-p PROFILE]
                                          [-d OUTPUTFILE]
                                          [-f OUTPUTJSONDICTIONARYFILE]

optional arguments:
  -h, --help            show this help message and exit
  -c [CSDLSCHEMADIRECTORIES [CSDLSCHEMADIRECTORIES ...]], --csdlSchemaDirectories [CSDLSCHEMADIRECTORIES [CSDLSCHEMADIRECTORIES ...]]
  -j [JSONSCHEMADIRECTORIES [JSONSCHEMADIRECTORIES ...]], --jsonSchemaDirectories [JSONSCHEMADIRECTORIES [JSONSCHEMADIRECTORIES ...]]
  -s SCHEMAFILENAME, --schemaFilename SCHEMAFILENAME
  -e ENTITY, --entity ENTITY
  -o [OEMSCHEMAFILENAMES [OEMSCHEMAFILENAMES ...]], --oemSchemaFilenames [OEMSCHEMAFILENAMES [OEMSCHEMAFILENAMES ...]]
  -t [OEMENTITIES [OEMENTITIES ...]], --oemEntities [OEMENTITIES [OEMENTITIES ...]]
  -r COPYRIGHT, --copyright COPYRIGHT
  -p PROFILE, --profile PROFILE
  -d OUTPUTFILE, --outputFile OUTPUTFILE
  -f OUTPUTJSONDICTIONARYFILE, --outputJsonDictionaryFile OUTPUTJSONDICTIONARYFILE
```
  
### Example
```
python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --outputFile drive.bin
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   Row |   Sequence# | Format   | Flags                              | Field String                  |   Child Count | Offset   |
+=======+=============+==========+====================================+===============================+===============+==========+
|     0 |           0 | Set      |                                    | Drive                         |            34 | 1        |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     1 |           0 | Set      | Nullable=False,                    | Actions                       |             2 | 35       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     2 |           1 | String   | Nullable=True,Permission=ReadWrite | AssetTag                      |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     3 |           2 | Integer  | Nullable=True,Permission=Read      | BlockSizeBytes                |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     4 |           3 | Integer  | Nullable=True,Permission=Read      | CapableSpeedGbs               |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     5 |           4 | Integer  | Nullable=True,Permission=Read      | CapacityBytes                 |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     6 |           5 | String   | Nullable=True,Permission=Read      | Description                   |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     7 |           6 | Enum     | Nullable=True,Permission=Read      | EncryptionAbility             |             3 | 37       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     8 |           7 | Enum     | Nullable=True,Permission=Read      | EncryptionStatus              |             5 | 40       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     9 |           8 | Boolean  | Nullable=True,Permission=Read      | FailurePredicted              |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    10 |           9 | Enum     | Nullable=True,Permission=Read      | HotspareType                  |             4 | 45       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    11 |          10 | String   | Nullable=False,Permission=Read     | Id                            |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    12 |          11 | Array    | Nullable=False,                    | Identifiers                   |             1 | 49       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    13 |          12 | Enum     | Nullable=True,Permission=ReadWrite | IndicatorLED                  |             6 | 52       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    14 |          13 | Set      | Nullable=False,                    | Links                         |             4 | 58       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    15 |          14 | Array    | Nullable=False,                    | Location                      |             1 | 62       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    16 |          15 | String   | Nullable=True,Permission=Read      | Manufacturer                  |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    17 |          16 | Enum     | Nullable=True,Permission=Read      | MediaType                     |             3 | 73       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    18 |          17 | String   | Nullable=True,Permission=Read      | Model                         |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    19 |          18 | String   | Nullable=False,Permission=Read     | Name                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    20 |          19 | Integer  | Nullable=True,Permission=Read      | NegotiatedSpeedGbs            |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    21 |          20 | Set      | Nullable=False,                    | Oem                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    22 |          21 | String   | Nullable=True,Permission=Read      | PartNumber                    |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    23 |          22 | Integer  | Nullable=True,Permission=Read      | PredictedMediaLifeLeftPercent |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    24 |          23 | Enum     | Nullable=True,Permission=Read      | Protocol                      |            25 | 76       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    25 |          24 | String   | Nullable=True,Permission=Read      | Revision                      |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    26 |          25 | Integer  | Nullable=True,Permission=Read      | RotationSpeedRPM              |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    27 |          26 | String   | Nullable=True,Permission=Read      | SKU                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    28 |          27 | String   | Nullable=True,Permission=Read      | SerialNumber                  |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    29 |          28 | Set      | Nullable=False,                    | Status                        |             4 | 101      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    30 |          29 | Enum     | Nullable=True,Permission=ReadWrite | StatusIndicator               |             7 | 105      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    31 |          30 | Array    | Nullable=False,                    | Operations                    |             1 | 112      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    32 |          31 | Set      | Nullable=False,Permission=Read     | Assembly                      |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    33 |          32 | Set      | Nullable=False,                    | PhysicalLocation              |            10 | 63       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    34 |          33 | Enum     | Nullable=True,Permission=ReadWrite | HotspareReplacementMode       |             2 | 116      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    35 |           0 | Set      | Nullable=False,                    | Oem                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    36 |           1 | Set      |                                    | SecureErase                   |             0 | 118      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+

...
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   199 |           0 | String   |                                    | Bottom                        |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   200 |           1 | String   |                                    | Front                         |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   201 |           2 | String   |                                    | Left                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   202 |           3 | String   |                                    | Middle                        |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   203 |           4 | String   |                                    | Rear                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   204 |           5 | String   |                                    | Right                         |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   205 |           6 | String   |                                    | Top                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
Total Entries: 206
Fixed size consumed (bytes): 2072
Field string size consumed (bytes): 1702
Total size (bytes): 3898
Signature: 0xf93eb944
```

### Example for annotations
```
python rde_schema_dictionary_gen.py annotation --csdlSchemaDirectories test/schema/metadata --jsonSchemaDirectories test/schema/json-schema -v v1_0_0 --outputFile annotation.bin

+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|   Row |   Sequence# | Format       | Flags                               | Field String                         |   Child Count | Offset   |
+=======+=============+==============+=====================================+======================================+===============+==========+
|     0 |           0 | Set          |                                     | Annotations                          |            19 | 1        |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     1 |           0 | Array        |                                     | @Message.ExtendedInfo                |             1 | 20       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     2 |           1 | String       |                                     | @Redfish.ActionInfo                  |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     3 |           2 | Array        |                                     | @Redfish.AllowableValues             |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     4 |           3 | Set          |                                     | @Redfish.CollectionCapabilities      |             1 | 28       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     5 |           4 | Set          |                                     | @Redfish.MaintenanceWindow           |             2 | 29       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     6 |           5 | Enum         |                                     | @Redfish.OperationApplyTime          |             4 | 31       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     7 |           6 | Set          |                                     | @Redfish.OperationApplyTimeSupport   |             4 | 35       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     8 |           7 | Boolean      |                                     | @Redfish.OptionalOnCreate            |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|     9 |           8 | Boolean      |                                     | @Redfish.RequiredOnCreate            |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    10 |           9 | Boolean      |                                     | @Redfish.SetOnlyOnCreate             |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    11 |          10 | Set          |                                     | @Redfish.Settings                    |             6 | 39       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    12 |          11 | Set          |                                     | @Redfish.SettingsApplyTime           |             3 | 45       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    13 |          12 | Boolean      |                                     | @Redfish.UpdatableAfterCreate        |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    14 |          13 | String       |                                     | @odata.context                       |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    15 |          14 | Integer      |                                     | @odata.count                         |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    16 |          15 | String       |                                     | @odata.etag                          |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    17 |          16 | ResourceLink |                                     | @odata.id                            |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    18 |          17 | String       |                                     | @odata.nextLink                      |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    19 |          18 | String       |                                     | @odata.type                          |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    20 |           0 | Set          |                                     |                                      |             7 | 21       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
...
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    60 |           1 | Array        | Nullable=True,Permission=Read       | RelatedItem                          |             1 | 65       |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    61 |           2 | Set          | Nullable=False,Permission=Read      | TargetCollection                     |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    62 |           0 | String       |                                     | ComputerSystemComposition            |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    63 |           1 | String       |                                     | ComputerSystemConstrainedComposition |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    64 |           2 | String       |                                     | VolumeCreation                       |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
|    65 |           0 | Set          |                                     |                                      |             0 |          |
+-------+-------------+--------------+-------------------------------------+--------------------------------------+---------------+----------+
Total Entries: 66
Fixed size consumed (bytes): 672
Field string size consumed (bytes): 1058
Total size (bytes): 1567
Signature: 0xd9a12d6b
```

### Example for OEM extensions
```
python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --oemSchemaFilenames OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml --oemEntities OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt --outputFile drive.bin

+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   Row |   Sequence# | Format   | Flags                              | Field String                  |   Child Count | Offset   |
+=======+=============+==========+====================================+===============================+===============+==========+
|     0 |           0 | Set      |                                    | Drive                         |            34 | 1        |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     1 |           0 | Set      | Nullable=False,                    | Actions                       |             2 | 35       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     2 |           1 | String   | Nullable=True,Permission=ReadWrite | AssetTag                      |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     3 |           2 | Integer  | Nullable=True,Permission=Read      | BlockSizeBytes                |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     4 |           3 | Integer  | Nullable=True,Permission=Read      | CapableSpeedGbs               |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     5 |           4 | Integer  | Nullable=True,Permission=Read      | CapacityBytes                 |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     6 |           5 | String   | Nullable=True,Permission=Read      | Description                   |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     7 |           6 | Enum     | Nullable=True,Permission=Read      | EncryptionAbility             |             3 | 37       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     8 |           7 | Enum     | Nullable=True,Permission=Read      | EncryptionStatus              |             5 | 40       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     9 |           8 | Boolean  | Nullable=True,Permission=Read      | FailurePredicted              |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    10 |           9 | Enum     | Nullable=True,Permission=Read      | HotspareType                  |             4 | 45       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    11 |          10 | String   | Nullable=False,Permission=Read     | Id                            |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    12 |          11 | Array    | Nullable=False,                    | Identifiers                   |             1 | 49       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    13 |          12 | Enum     | Nullable=True,Permission=ReadWrite | IndicatorLED                  |             6 | 52       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    14 |          13 | Set      | Nullable=False,                    | Links                         |             4 | 58       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    15 |          14 | Array    | Nullable=False,                    | Location                      |             1 | 62       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    16 |          15 | String   | Nullable=True,Permission=Read      | Manufacturer                  |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    17 |          16 | Enum     | Nullable=True,Permission=Read      | MediaType                     |             3 | 73       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    18 |          17 | String   | Nullable=True,Permission=Read      | Model                         |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    19 |          18 | String   | Nullable=False,Permission=Read     | Name                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
...
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   212 |           2 | String   |                                    | Left                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   213 |           3 | String   |                                    | Middle                        |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   214 |           4 | String   |                                    | Rear                          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   215 |           5 | String   |                                    | Right                         |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   216 |           6 | String   |                                    | Top                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   217 |           0 | Integer  |                                    |                               |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   218 |           0 | String   |                                    |                               |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   219 |           0 | Array    | Nullable=True,Permission=Read      | Statuses                      |             1 | 220      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   220 |           0 | Set      |                                    |                               |             4 | 103      |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
Total Entries: 221
Fixed size consumed (bytes): 2222
Field string size consumed (bytes): 1835
Total size (bytes): 4179
Signature: 0xd3639e74
```

### Example generating a truncated dictionary using a profile
Use the following example_profile.json to truncate the dictionary.
```
{
    "SchemaDefinition": "RedfishInteroperabilityProfile.v1_0_1",
    "ProfileName": "Example Profile",
    "ProfileVersion": "0.1",
    "ContactInfo": "",
    "RequiredProfiles": {
        "DMTFBasic": {
            "MinVersion": "1.0.0"
        }
    },
    "Protocol": {
        "MinVersion": "1.5",
        "Discovery": "None",
        "HostInterface": "None",
        "ExpandQuery": "None",
        "SelectQuery": "None",
        "FilterQuery": "None"
    },
    "Resources": {
        "Drive": {
            "MinVersion": "1.5.0",
            "Purpose": "Every implementation must have one or more drive resources",
            "PropertyRequirements": {
                "ReadRequirement": "Mandatory",
                "@odata.context": {
                    "ReadRequirement": "Mandatory"
                },
                "@odata.id": {
                    "ReadRequirement": "Mandatory"
                },
                "@odata.etag": {
                    "ReadRequirement": "Mandatory"
                },
                "@odata.type": {
                    "ReadRequirement": "Mandatory"
                },
                "Id":{
                    "ReadRequirement": "Mandatory"
                },
                "Name": {
                    "ReadRequirement": "Mandatory"
                },
                "Status": {
                    "PropertyRequirements": {
                        "State": {
                            "ReadRequirement": "Mandatory",
                            "Comparison": "AnyOf",
                            "Values": ["Enabled", "Disabled", "StandbyOffline", "StandbySpare", "UnavailableOffline", "Updating"]
                        },
                        "Health": {
                            "ReadRequirement": "Mandatory",
                            "Purpose": "Health of the drive"
                        }
                    }
                },
                "IndicatorLED": {
                    "ReadRequirement": "Mandatory",
                    "Comparison": "AnyOf",
                    "Values": ["Lit", "Off"]
                },
                "Model": {
                    "ReadRequirement": "Mandatory"
                },
                "Revision": {
                    "ReadRequirement": "Mandatory"
                },
                "CapacityBytes": {
                    "ReadRequirement": "Mandatory",
                    "Purpose": "Actual drive capacity"
                },
                "BlockSizeBytes": {
                    "ReadRequirement": "Mandatory"
                },
                "Protocol": {
                    "ReadRequirement": "Mandatory",
                    "Comparison": "AnyOf",
                    "Values": ["SAS", "SATA", "NVMe"]
                },
                "MediaType": {
                    "ReadRequirement": "Mandatory",
                    "Comparison": "AnyOf",
                    "Values": ["HDD", "SSD", "SMR"]
                },
                "Manufacturer": {
                    "ReadRequirement": "Mandatory"
                },
                "SerialNumber": {
                    "ReadRequirement": "Mandatory"
                },
                "StatusIndicator": {
                    "ReadRequirement": "Mandatory",
                    "Purpose": "SES status of drive",
                    "Comparison": "AnyOf",
                    "Values": ["OK", "Fail", "Rebuild", "PredictiveFailureAnalysis", "HotSpare"]
                },
                "Identifiers": {
                    "ReadRequirement": "Mandatory",
                    "MinCount": 1,
                    "PropertyRequirements": {
                        "DurableName": {
                            "ReadRequirement": "Mandatory"
                        },
                        "DurableNameFormat": {
                            "ReadRequirement": "Mandatory",
                            "Comparison": "Equal",
                            "Values": ["NAA"]
                        }
                    }
                },
                "PhysicalLocation": {
                    "ReadRequirement": "Mandatory",
                    "PropertyRequirements": {
                        "PartLocation": {
                            "ReadRequirement": "Mandatory",
                            "PropertyRequirements": {
                                "LocationOrdinalValue": {
                                    "ReadRequirement": "Mandatory"
                                },
                                "LocationType": {
                                    "ReadRequirement": "Mandatory",
                                    "Comparison": "Equal",
                                    "Values": ["Bay"]
                                },
                                "ServiceLabel": {
                                    "ReadRequirement": "Mandatory"
                                }
                            }
                        }
                    }
                },
                "RotationSpeedRPM": {
                    "ReadRequirement": "Conditional",
                    "ConditionalRequirements": [{
                        "Purpose": "Applicable only if MediaType is HDD or SMR",
                        "CompareProperty": "MediaType",
                        "CompareType": "AnyOf",
                        "CompareValues": ["HDD", "SMR"],
                        "ReadRequirement": "Mandatory"
                    }]
                },
                "CapableSpeedGbs": {
                    "ReadRequirement": "Mandatory"
                },
                "NegotiatedSpeedGbs": {
                    "ReadRequirement": "Mandatory"
                }
            }
        }
    }
}
```
```
python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --profile example_profile.json

+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|   Row |   Sequence# | Format   | Flags                              | Field String                  |   Child Count | Offset   |
+=======+=============+==========+====================================+===============================+===============+==========+
|     0 |           0 | Set      |                                    | Drive                         |            24 | 1        |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     1 |           2 | Integer  | Nullable=True,Permission=Read      | BlockSizeBytes                |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     2 |           3 | Integer  | Nullable=True,Permission=Read      | CapableSpeedGbs               |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     3 |           4 | Integer  | Nullable=True,Permission=Read      | CapacityBytes                 |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     4 |           8 | Boolean  | Nullable=True,Permission=Read      | FailurePredicted              |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     5 |           9 | Enum     | Nullable=True,Permission=Read      | HotspareType                  |             2 | 25       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     6 |          10 | String   | Nullable=False,Permission=Read     | Id                            |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     7 |          11 | Array    | Nullable=False,                    | Identifiers                   |             1 | 27       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     8 |          12 | Enum     | Nullable=True,Permission=ReadWrite | IndicatorLED                  |             4 | 30       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|     9 |          13 | Set      | Nullable=False,                    | Links                         |             1 | 34       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    10 |          15 | String   | Nullable=True,Permission=Read      | Manufacturer                  |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
...
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    61 |           9 | String   |                                    | UnavailableOffline            |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    62 |          10 | String   |                                    | Updating                      |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    63 |           0 | Integer  | Nullable=True,Permission=Read      | LocationOrdinalValue          |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    64 |           1 | Enum     | Nullable=True,Permission=Read      | LocationType                  |             1 | 66       |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    65 |           4 | String   | Nullable=True,Permission=Read      | ServiceLabel                  |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
|    66 |           0 | String   |                                    | Bay                           |             0 |          |
+-------+-------------+----------+------------------------------------+-------------------------------+---------------+----------+
Total Entries: 67
Fixed size consumed (bytes): 682
Field string size consumed (bytes): 611
Total size (bytes): 1347
Signature: 0x1ae1ca48
```

# pldm-bej-encoder-decoder

## Example Encoding JSON into PLDM BEJ
1. Create schema and annotation dictionaries for the schema that the input JSON object conforms to (this examples uses the Redfish Drive schema):
```
python rde_schema_dictionary_gen.py local --csdlSchemaDirectories test/schema/metadata  test/schema/oem-csdl --jsonSchemaDirectories test/schema/json-schema --schemaFilename Drive_v1.xml --entity Drive.Drive --oemSchemaFilenames OEM1DriveExt_v1.xml OEM2DriveExt_v1.xml --oemEntities OEM1=OEM1DriveExt.OEM1DriveExt OEM2=OEM2DriveExt.OEM2DriveExt --outputFile drive.bin

python rde_schema_dictionary_gen.py annotation --csdlSchemaDirectories test/schema/metadata --jsonSchemaDirectories test/schema/json-schema -v v1_0_0 --outputFile annotation.bin
```

2. Use the encoder to encode the JSON file to PLDM BEJ format. The below example encodes the following drive JSON:
```
{
    "@odata.id": "/redfish/v1/drives/1",
    "@odata.type": "#Drive.v1_5_0.Drive",
    "@odata.etag": "FBS4553345",
    "Id": "Drive1",
    "Name": "Disk Bay 1",
    "IndicatorLED": "Lit",
    "Model": "Consorto MM0500FBFVQ",
    "Revision": "C1.1",
    "Status": {
       "State": "Enabled",
       "Health": "Warning"
    },
    "Status@Message.ExtendedInfo": [
        {
            "MessageId": "PredictiveFailure",
            "Severity": "Warning",
            "RelatedProperties": ["FailurePredicted", "MediaType"]
        },
        {
            "MessageId": "LinkFailure",
            "Severity": "Warning",
            "MessageArgs": ["Port", "1"]
        }
    ],
    "CapacityBytes": 500105991946,
    "BlockSizeBytes": 512,
    "Identifiers": [
        {
            "DurableNameFormat": "NAA",
            "DurableName": "5000C5004183A941"
        }
    ],
    "FailurePredicted": true,
    "Protocol": "SAS",
    "MediaType": "HDD",
    "Manufacturer": "CONSORTO",
    "SerialNumber": "9XF11DLF00009238W7LN",
    "PhysicalLocation": {
       "PartLocation": {
           "LocationOrdinalValue": 1,
           "LocationType": "Bay",
           "ServiceLabel": "Port=A:Bay=1"
       }
    },
    "RotationSpeedRPM": 15000,
    "CapableSpeedGbs": 12,
    "NegotiatedSpeedGbs": 12,
    "Operations": [
       {
           "OperationName": "Erasing",
           "PercentageComplete": 20,
           "AssociatedTask": {
              "@odata.id": "/redfish/v1/Tasks/1"
           }
       },
       {
           "OperationName": "Rebuilding",
           "PercentageComplete": 70,
           "AssociatedTask": {
              "@odata.id": "/redfish/v1/Tasks/2"
           }
       }
    ],
   "Links": {
      "Volumes": [
         {
            "@odata.id": "/redfish/v1/Systems/1/Storage/1/Volumes/1"
         },
         {
            "@odata.id": "/redfish/v1/Systems/1/Storage/1/Volumes/2"
         },
         {
            "@odata.id": "/redfish/v1/Systems/1/Storage/1/Volumes/3"
         }
      ]
   },
   "Oem": {
       "OEM1": {
           "@odata.type": "#OEMDriveExt.v1_0_0.OEM1DriveExt",
           "ArrayOfStrings": [
               "str1",
               "str2",
               "str3",
               "str4"
           ],
           "ArrayOfInts": [
               10,
               20,
               30,
               40,
               50
           ]
       }
   }
}
```

Note: Specify a PDR map file to capture URLs to PDR mapping that can then later be used for decoding

```
python pldm_bej_encoder_decoder.py encode --schemaDictionary drive.bin --annotationDictionary annotation.bin --jsonFile test\drive.json --bejOutputFile drive_bej.bin --pdrMapFile pdr.txt
```
```
0X000000: 00 F0 F0 F1 00 00 00 01 00 00 02 00 03 01 19 01 ................
0X000010: 21 E0 01 02 01 00 01 25 50 01 14 23 44 72 69 76 !......%P..#Driv
0X000020: 65 2E 76 31 5F 35 5F 30 2E 44 72 69 76 65 00 01 e.v1_5_0.Drive..
0X000030: 1F 50 01 0B 46 42 53 34 35 35 33 33 34 35 00 01 .P..FBS4553345..
0X000040: 14 50 01 07 44 72 69 76 65 31 00 01 24 50 01 0B .P..Drive1..$P..
0X000050: 44 69 73 6B 20 42 61 79 20 31 00 01 18 40 01 01 Disk.Bay.1...@..
0X000060: 01 01 01 22 50 01 15 43 6F 6E 73 6F 72 74 6F 20 ..."P..Consorto.
0X000070: 4D 4D 30 35 30 30 46 42 46 56 51 00 01 30 50 01 MM0500FBFVQ..0P.
0X000080: 05 43 31 2E 31 00 01 38 00 01 10 01 02 01 06 40 .C1.1..8.......@
0X000090: 01 01 01 03 01 00 40 01 01 01 02 01 38 A0 01 9B ......@.....8...
0X0000A0: 01 01 10 01 96 01 02 01 01 00 01 52 01 03 01 05 ...........R....
0X0000B0: 50 01 12 50 72 65 64 69 63 74 69 76 65 46 61 69 P..PredictiveFai
0X0000C0: 6C 75 72 65 00 01 0D 50 01 08 57 61 72 6E 69 6E lure...P..Warnin
0X0000D0: 67 00 01 09 10 01 27 01 02 01 01 50 01 11 46 61 g.....'....P..Fa
0X0000E0: 69 6C 75 72 65 50 72 65 64 69 63 74 65 64 00 01 ilurePredicted..
0X0000F0: 03 50 01 0A 4D 65 64 69 61 54 79 70 65 00 01 03 .P..MediaType...
0X000100: 00 01 38 01 03 01 05 50 01 0C 4C 69 6E 6B 46 61 ..8....P..LinkFa
0X000110: 69 6C 75 72 65 00 01 0D 50 01 08 57 61 72 6E 69 ilure...P..Warni
0X000120: 6E 67 00 01 03 10 01 13 01 02 01 01 50 01 05 50 ng..........P..P
0X000130: 6F 72 74 00 01 03 50 01 02 31 00 01 08 30 01 05 ort...P..1...0..
0X000140: 0A D7 A3 70 74 01 04 30 01 02 00 02 01 16 10 01 ...pt..0........
0X000150: 26 01 01 01 00 00 01 1F 01 02 01 02 40 01 01 01 &...........@...
0X000160: 03 01 00 50 01 11 35 30 30 30 43 35 30 30 34 31 ...P..5000C50041
0X000170: 38 33 41 39 34 31 00 01 10 70 01 01 01 01 2E 40 83A941...p.....@
0X000180: 01 01 01 13 01 20 40 01 01 01 00 01 1E 50 01 09 ......@......P..
0X000190: 43 4F 4E 53 4F 52 54 4F 00 01 36 50 01 15 39 58 CONSORTO..6P..9X
0X0001A0: 46 31 31 44 4C 46 30 30 30 30 39 32 33 38 57 37 F11DLF00009238W7
0X0001B0: 4C 4E 00 01 40 00 01 28 01 01 01 0A 00 01 21 01 LN..@..(......!.
0X0001C0: 03 01 00 30 01 01 01 01 02 40 01 01 01 00 01 08 ...0.....@......
0X0001D0: 50 01 0D 50 6F 72 74 3D 41 3A 42 61 79 3D 31 00 P..Port=A:Bay=1.
0X0001E0: 01 32 30 01 02 98 3A 01 06 30 01 01 0C 01 26 30 .20...:..0....&0
0X0001F0: 01 01 0C 01 3C 10 01 55 01 02 01 00 00 01 23 01 ....<..U......#.
0X000200: 03 01 02 50 01 08 45 72 61 73 69 6E 67 00 01 04 ...P..Erasing...
0X000210: 30 01 01 14 01 00 00 01 09 01 01 01 21 E0 01 02 0...........!...
0X000220: 01 01 01 02 00 01 26 01 03 01 02 50 01 0B 52 65 ......&....P..Re
0X000230: 62 75 69 6C 64 69 6E 67 00 01 04 30 01 01 46 01 building...0..F.
0X000240: 00 00 01 09 01 01 01 21 E0 01 02 01 02 01 1A 00 .......!........
0X000250: 01 33 01 01 01 02 10 01 2C 01 03 01 00 00 01 09 .3......,.......
0X000260: 01 01 01 21 E0 01 02 01 03 01 02 00 01 09 01 01 ...!............
0X000270: 01 21 E0 01 02 01 04 01 04 00 01 09 01 01 01 21 .!.............!
0X000280: E0 01 02 01 05 01 28 00 01 83 01 01 01 00 00 01 ......(.........
0X000290: 7C 01 03 01 25 50 01 21 23 4F 45 4D 44 72 69 76 |...%P.!#OEMDriv
0X0002A0: 65 45 78 74 2E 76 31 5F 30 5F 30 2E 4F 45 4D 31 eExt.v1_0_0.OEM1
0X0002B0: 44 72 69 76 65 45 78 74 00 01 02 10 01 2A 01 04 DriveExt.....*..
0X0002C0: 01 00 50 01 05 73 74 72 31 00 01 02 50 01 05 73 ..P..str1...P..s
0X0002D0: 74 72 32 00 01 04 50 01 05 73 74 72 33 00 01 06 tr2...P..str3...
0X0002E0: 50 01 05 73 74 72 34 00 01 00 10 01 20 01 05 01 P..str4.........
0X0002F0: 00 30 01 01 0A 01 02 30 01 01 14 01 04 30 01 01 .0.....0.....0..
0X000300: 1E 01 06 30 01 01 28 01 08 30 01 01 32
JSON size: 1469
Total encode size: 781
Compression ratio(%): 46.83458134785569
```

## Example Decoding PLDM BEJ into JSON
```
python pldm_bej_encoder_decoder.py decode --schemaDictionary drive.bin --annotationDictionary annotation.bin --bejEncodedFile drive_bej.bin --pdrMapFile pdr.txt

{
   "@odata.id": "/redfish/v1/drives/1",
   "@odata.type": "#Drive.v1_5_0.Drive",
   "@odata.etag": "FBS4553345",
   "Id": "Drive1",
   "Name": "Disk Bay 1",
   "Status": {
      "State": "Enabled",
      "Health": "OK"
   },
   "IndicatorLED": "Lit",
   "Model": "Consorto MM0500FBFVQ",
   "Revision": "C1.1",
   "CapacityBytes": 500105991946,
   "BlockSizeBytes": 512,
   "FailurePredicted": false,
   "Protocol": "SAS",
   "MediaType": "HDD",
   "Manufacturer": "CONSORTO",
   "SerialNumber": "9XF11DLF00009238W7LN",
   "Identifiers": [
      {
         "DurableNameFormat": "NAA",
         "DurableName": "5000C5004183A941"
      }
   ],
   "PhysicalLocation": {
      "PartLocation": {
         "LocationOrdinalValue": 1,
         "LocationType": "Bay",
         "ServiceLabel": "Port=A:Bay=1"
      }
   },
   "RotationSpeedRPM": 15000,
   "CapableSpeedGbs": 12,
   "NegotiatedSpeedGbs": 12,
   "Operations": [
      {
         "OperationName": "Erasing",
         "PercentageComplete": 20,
         "AssociatedTask": {
            "@odata.id": "/redfish/v1/Tasks/1"
         }
      },
      {
         "OperationName": "Rebuilding",
         "PercentageComplete": 70,
         "AssociatedTask": {
            "@odata.id": "/redfish/v1/Tasks/2"
         }
      }
   ],
   "Links": {
      "Volumes": [
         {
            "@odata.id": "/redfish/v1/Volumes/1"
         },
         {
            "@odata.id": "/redfish/v1/Volumes/2"
         },
         {
            "@odata.id": "/redfish/v1/Volumes/3"
         }
      ]
   }
}
```
