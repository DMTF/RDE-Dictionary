#! /usr/bin/python3
# Copyright Notice:
# Copyright 2018-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/RDE-Dictionary/blob/master/LICENSE.md

"""
rdebej._internal_utils
~~~~~~~~~~~~~~
Provides utility functions that are consumed internally by rdebej
"""

# BEJ FORMAT definitions
BEJ_FORMAT_SET = 0x00
BEJ_FORMAT_ARRAY = 0x01
BEJ_FORMAT_NULL = 0x02
BEJ_FORMAT_INTEGER = 0x03
BEJ_FORMAT_ENUM = 0x04
BEJ_FORMAT_STRING = 0x05
BEJ_FORMAT_REAL = 0x06
BEJ_FORMAT_BOOLEAN = 0x07
BEJ_FORMAT_BYTE_STRING = 0x08
BEJ_FORMAT_CHOICE = 0x09
BEJ_FORMAT_PROPERTY_ANNOTATION = 0x0A
BEJ_FORMAT_RESOURCE_LINK = 0x0E
BEJ_FORMAT_RESOURCE_LINK_EXPANSION = 0x0F
BEJ_FORMAT_UNKNOWN = 0xFF

# Internal dictionary index
DICTIONARY_ENTRY_FORMAT = 0
DICTIONARY_ENTRY_FLAGS = 1
DICTIONARY_ENTRY_SEQUENCE_NUMBER = 2
DICTIONARY_ENTRY_OFFSET = 3
DICTIONARY_ENTRY_CHILD_COUNT = 4
DICTIONARY_ENTRY_NAME = 5

BEJ_DICTIONARY_SELECTOR_MAJOR_SCHEMA = 0x00
BEJ_DICTIONARY_SELECTOR_ANNOTATION = 0x01


class DictionaryByteArrayStream:
    def __init__(self, byte_array, offset=0, child_count=-1):
        self._byte_array = byte_array
        self._current_index = offset
        self._child_count = child_count
        self._current_entry = 0

        if self._current_index == 0:
            # skip thru the header
            self.get_int(1)  # VersionTag
            self.get_int(1)  # DictionaryFlags
            self.get_int(4)  # SchemaVersion
            self._total_entries = self.get_int(2)  # EntryCount
            self.get_int(4)  # DictionarySize

            self._child_count = 1

    def get_offset(self):
        return self._current_index

    def get_child_count(self):
        return self._child_count

    def get_int(self, size):
        value = int.from_bytes(self._byte_array[self._current_index:self._current_index+size], 'little')
        self._current_index += size
        return value

    def has_entry(self):
        return self._current_entry < self._child_count

    def get_next_entry(self):
        entry = []
        current_entry = 0
        if self._current_entry < self._child_count or self._child_count == -1:

            format_flags = self.get_int(1)
            entry.append(format_flags >> 4)  # format
            entry.append(format_flags & 0xF)  # flags
            entry.append(self.get_int(2))  # sequence
            entry.append(self.get_int(2))  # offset
            entry.append(self.get_int(2))  # child_count

            name_length = self.get_int(1)
            name_offset = self.get_int(2)

            # fetch the name
            name = ''
            if name_length > 0:
                name = "".join(map(chr, self._byte_array[name_offset:name_offset+name_length-1])) # -1 to skip null terminator

            entry.append(name)

            if self._child_count != -1:
                self._current_entry += 1

        return entry
