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


@fixture
def schema_source_git(context, **kwargs):
    # -- SETUP-FIXTURE PART:
    context.schema_source = context.config.userdata['schema_source']
    context.schema_branch = context.config.userdata['branch']
    context.schema_dir = os.getcwd() + '/' + context.config.userdata['schema_dir']
    context.dictionary_dir = context.config.userdata['dictionary_dir']

    # fill the schema dir with schema from the source
    if re.search('.*\.git$', context.schema_source):
        repo = cloneFrom(context.schema_source, context.schema_dir, context.schema_branch,
                               ['metadata', 'json-schema'])
        assert repo, "Could not fetch repo"


@fixture
def schema_source_local(context, **kwargs):
    context.schema_dir = os.getcwd() + '/' + context.config.userdata['schema_dir']
    context.dictionary_dir = context.config.userdata['dictionary_dir']


def before_tag(context, tag):
    if tag == 'fixture.source.git':
        use_fixture(schema_source_git, context)
    elif tag == 'fixture.source.local':
        use_fixture(schema_source_local, context)


def after_tag(context, tag):
    if tag == 'fixture.source.git':
        shutil.rmtree(context.schema_dir, onerror=onerror)