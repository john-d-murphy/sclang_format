"""
This script takes in a SuperCollider code file and uses a tree-sitter
generated .so file to parse and format the code according to SuperCollider
coding conventions.
"""

#### Imports

import argparse
import logging
import format_rules as fr
import re
import sys

from tree_sitter import Language, Parser, Tree

#### Logger
log = logging.getLogger("root")
LOG_FORMAT = "[%(asctime)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT)
log.setLevel(logging.DEBUG)

#### Constants

STD_IN = "-"

# List Of Format Rule Classes
pre_format = [
    fr.NoMoreThan80Characters,
    fr.StripTrailingWhitespace,
    fr.JoinElementsOntoSingleLines,
    # This is currently handled by the "remove spaces" method.
    # This needs to be reactivated when the linked bug in the
    # tree-sitter is fixed.
    # fr.NormalizeText,
]
inline_format = [
    fr.FormatParameterLists,
    fr.BracketSpacing,
    fr.DontUseSpaceBeforeSemicolons,
    fr.AddSpacesAroundAssignment,
    fr.BinaryOperatorSpacing,
    fr.AddSpacesAfterCommas,
    fr.FormatReturnStatement,
    fr.ParameterListAlignment,
]
post_format = [fr.AddNewlinesInFunctions, fr.IndentFile, fr.EndOfFileNewLine]

### Main


def main():
    """
    Main method that parses the SuperCollider file and prints out the formatted code.
    Does the following:
        * Parses arguments
        * Gets the treesitter parser
        * Reads the file
        * Generates the tree for the file
        * Parses the tree
        * Prints out the result
    """

    ### Parse and display arguments
    arguments = parse_arguments()

    ### Read the passed file or from stdin
    data = read_file(arguments)

    ### Naive normalization to accomidate this bug:
    ### https://github.com/madskjeldgaard/tree-sitter-supercollider/issues/42
    data = naive_normalize(data)

    ### Get the treesitter language object
    language, parser = get_treesitter_parser(arguments)

    ### Get the tree
    tree = fr.Helpers.get_tree(parser, data, None)

    ### Check if code parses
    query = language.query(""" (ERROR) @error """)
    captures = query.captures(tree.root_node)

    # If there is an error in the parsing, return with
    # error code.
    if len(captures) > 0:
        print_unparsable_sections(arguments, data, captures)
        sys.exit(1)

    ### Run the pre-formatters
    for f in pre_format:
        data, tree = f.format(arguments, data, tree, parser, language)

    ### Run the inline formatters
    for f in inline_format:
        data, tree = f.format(arguments, data, tree, parser, language)

    ### Run the post-formatters
    for f in post_format:
        data, tree = f.format(arguments, data, tree, parser, language)

    # Print the text to standard out
    # TODO: Is there a better way to handle this ?
    print(data)

    sys.exit(0)


def parse_arguments():
    """Parses Arguments and Fails if required arguments are not supplied
    Returns
    ----------
    arguments: Parsed argument list
    """

    ### Get Arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-f",
        "--supercollider_file",
        help="Absolute path of the file to parse",
        default=STD_IN,
        required=False,
    )
    parser.add_argument(
        "-l",
        "--treesitter_library",
        help="Absolute path of the compiled treesitter .so file",
        required=True,
    )

    parser.add_argument(
        "-t",
        "--use_tabs",
        help="Use Tabs for spacing - default (True)",
        default=True,
    )

    parser.add_argument(
        "-x",
        "--maximum_line_length",
        help="Maximum Line Length - default (80)",
        default=80,
    )

    arguments = parser.parse_args()
    arguments.use_tabs = str_to_bool(arguments.use_tabs)

    return arguments


def str_to_bool(value):

    if isinstance(value, bool):
        return value
    elif value.lower() in ("yes", "true", "y", "t", "1"):
        return True
    elif value.lower() in ("no", "false", "n", "f", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean Type Expected")


def get_treesitter_parser(arguments):
    """
    Returns treesitter parser for the SuperCollider Language

    Parameters
    ----------
    arguments: Command-line arguments

    Returns
    ----------
    parser: Treesitter parser object
    """
    language = Language(
        arguments.treesitter_library,
        "supercollider",
    )
    parser = Parser()

    parser.set_language(language)

    return language, parser


def read_file(arguments):
    """
    Returns file in a format the tree-sitter can parse

    Parameters
    ----------
    arguments: Command-line arguments

    Returns
    ----------
    file_lines: File parsed into an array of lines
    """

    if arguments.supercollider_file == STD_IN:
        with sys.stdin as file:
            data = file.read()
    else:
        with open(arguments.supercollider_file, "r", encoding="utf8") as file:
            data = file.read()

    return data


def naive_normalize(data):
    # Do some of the normalization here as well.
    # This method needs to be removed once the parsing bug is fixed.
    data = re.sub("\t", " ", data)
    data = re.sub(" +", " ", data)

    # Replace two or more newlines with two newlines. This is to allow
    # separation between logical blocks, but not allow an excess of
    # whitespace, similar to how black does it.
    data = re.sub(r"\n[\n]+", "\n\n", data)

    # Don't allow whitespace to follow a newline. Stripping seems to not
    # work for some of these use cases, so this takes care of that
    # manually.
    data = re.sub(r"\n ", "\n", data)

    # Remove spaces around assignments to allow for parsing and address
    # the bug in the argument list.
    data = re.sub("= ", "=", data)
    data = re.sub(" =", "=", data)

    # Remove spaces around pipes to allow for parsing and address
    # the bug in the argument list. We currently don't have any
    # semantics here, so we can't say to only remove the spaces
    # within the argument list.
    data = re.sub("\| ", "|", data)
    data = re.sub(" \|", "|", data)

    # Strip is not removing the whitespace after the open brace.
    # Not sure why this is - this is a hack to clean this up.
    data = re.sub("{ ", "{", data)

    # If 'play' at end of line with no semicolon, add semicolon
    # after play. Tree won't parse without it.
    data = re.sub("play\n", "play;\n", data)

    # Remove all whitespaces
    data = data.strip()

    return data


def print_unparsable_sections(arguments, data, errors):
    newline_offsets = fr.Helpers.get_all_newline_offsets(data)
    for error in errors:
        start_line = error[0].start_point[0]
        start_offset = error[0].start_point[1]
        end_line = error[0].end_point[0]
        end_offset = error[0].end_point[1]
        start_matched_char_loc = newline_offsets[start_line] + start_offset
        end_matched_char_loc = newline_offsets[end_line] + end_offset
        bad_data = data[start_matched_char_loc:end_matched_char_loc]

        print(
            "Error: "
            + str(start_line)
            + ":"
            + str(start_offset)
            + " - ["
            + bad_data
            + "]"
        )


if __name__ == "__main__":
    main()
