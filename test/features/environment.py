#! /usr/bin/python3
# Copyright Notice:
# Copyright 2018-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/RDE-Dictionary/blob/master/LICENSE.md

from behave import *
from behave import fixture, use_fixture
import parse
from parse_type import TypeBuilder
from behave import register_type
import re
import sys
import shutil
import os
from behave import register_type
import requests
import zipfile

sys.path.append('./test')
from utils import *


# Cardinality support for numbers in parse
# d+ allows list of integers e.g. 1, 2, 3
# w+ allows list of words e.g. hello, world
# h  allow hex numbers e.g. 0x123F
# h+ allows list of hex numbgers e.g. 0x123, 0x345, 0xDEF
# cv allows a context variable name that needs to be accessed
@parse.with_pattern(r"\d+")
def parse_number(text):
    return int(text)


@parse.with_pattern(r"[0-9a-zA-Z\$]+")
def parse_word(text):
    return text


@parse.with_pattern(r"\w+")
def parse_hex(text):
    return int(text, 16)


@parse.with_pattern(r"{\w+}")
def parse_context_variable(text):
    return text[1:-1]


# Allows using context variables and expression evaluation:
# {SomeVariable}
#   will be evaluated to context.SomeVariable
# `{SomeVariable} + 4 + {SomeOtherVariable}`
#   will be evaluated to context.SomeVariable + 4 + context.SomeOtherVariable
def parse_with_context_variables(context, text):
    isEval = re.match(r'^[`{].*?[`}]$', text) is not None

    # strip of trailing `
    if re.match(r'^`.*?`$', text):
        text = text[1:-1]

    # first substitute any {Variable} with context.Variable
    result = re.sub(r'{(?P<var>\w+)}', r'context.\g<var>', text)

    if isEval:
        result = eval(result)

    return result


parse_numbers = TypeBuilder.with_many(parse_number, listsep=",")
parse_words = TypeBuilder.with_many(parse_word, listsep=",")
parse_hexs = TypeBuilder.with_many(parse_hex, listsep=",")
parse_one_hex = TypeBuilder.with_zero_or_one(parse_hex)
parse_is_is_not = TypeBuilder.make_choice(["is", "is NOT"])
parse_have_not_have = TypeBuilder.make_choice(["have", "NOT have"])
parse_has_does_not_have = TypeBuilder.make_choice(["has", "does NOT have"])
parse_one_context_variables = TypeBuilder.with_zero_or_one(parse_context_variable)
type_dict = {
    'd+': parse_numbers,
    'w+': parse_words,
    'h': parse_one_hex,
    'h+': parse_hexs,
    'is': parse_is_is_not,
    'have': parse_have_not_have,
    'has': parse_has_does_not_have,
    'cv': parse_one_context_variables
}
register_type(**type_dict)

# schema_sources:
#    schema_source (git, local)
#        schema_dir
#            csdl_sub_dir
#            json_sub_dir
# -D schema_sources=[
#    {"git", "http://ip/repo.git", "schema_dir", "metadata", "json-schema"},
#    {"local", "schema_dir", "metadata", "json-schema"}
#    ]

@fixture
def schema_source(context, **kwargs):
    # -- SETUP-FIXTURE PART:
    schema_sources = eval(context.config.userdata['schema_sources'])
    context.csdl_dirs = []
    context.json_schema_dirs = []
    context.dirs_to_cleanup = []
    for schema_source in schema_sources:
        if schema_source['source'] == 'git':
            # fill the schema dir with schema from the source
            if re.search('.*\.git$', schema_source['repo']):
                repo = cloneFrom(schema_source['repo'], schema_source['schema_dir'], schema_source['branch'],
                                 [schema_source['csdl_dir'], schema_source['json_schema_dir']])
                assert repo, "Could not fetch repo"
                context.dirs_to_cleanup.append(schema_source['schema_dir'])
                schema_test_dir = schema_source['schema_dir']
        elif schema_source['source'] == 'http':
            r = requests.get(schema_source['url'], allow_redirects=True)
            open('tmp_schema.zip', 'wb').write(r.content)
            with zipfile.ZipFile('tmp_schema.zip', 'r') as zip_ref:
                zip_ref.extractall(schema_source['schema_dir'])
                schema_test_dir = schema_source['schema_dir'] + '//' + os.listdir(schema_source['schema_dir'])[0]

        context.csdl_dirs.append(schema_test_dir + '//' + schema_source['csdl_dir'])
        context.json_schema_dirs.append(schema_test_dir + '//' + schema_source['json_schema_dir'])



def before_tag(context, tag):
    if tag == 'fixture.schema_source':
        use_fixture(schema_source, context)


def after_tag(context, tag):
    if tag == 'fixture.schema_source':
        for dir_to_cleanup in context.dirs_to_cleanup:
            shutil.rmtree(dir_to_cleanup, onerror=onerror)