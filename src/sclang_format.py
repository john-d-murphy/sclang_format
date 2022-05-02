"""
This script takes in a SuperCollider code file and uses a tree-sitter
generated .so file to parse and format the code according to SuperCollider
coding conventions.
"""

#### Imports

import argparse
import logging
import format_rules as fr
import sys

from tree_sitter import Language, Parser, Tree

#### Logger
log = logging.getLogger("root")
LOG_FORMAT = "[%(asctime)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT)
log.setLevel(logging.DEBUG)

#### Constants

# List Of Format Rule Classes
pre_format = [fr.StripTrailingWhitespace(), fr.NormalizeText()]
inline_format = [
    fr.BracketSpacing,
    fr.DontUseSpaceBeforeSemicolons,
    fr.BinaryOperatorSpacing,
]
post_format = [fr.NoMoreThan80Characters, fr.EndOfFileNewLine]

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

    ### Get the treesitter language object
    language, parser = get_treesitter_parser(arguments)

    ### Read the passed file
    data = read_file(arguments)

    ### Get the tree
    tree = fr.Helpers.get_tree(parser, data, None)

    ### Check if code parses
    query = language.query(""" (ERROR) @error """)
    captures = query.captures(tree.root_node)

    # If there is an error in the parsing, return with
    # error code.
    if len(captures) > 0:
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
        required=True,
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

    with open(arguments.supercollider_file, "r", encoding="utf8") as file:
        data = file.read()

    return data

    # return open(arguments.supercollider_file).read().splitlines()


# def get_tree(parser, file_contents):
#    return parser.parse(bytes(file_contents, "utf8"))


def tree_to_string(tree):
    print("foo")


# Language.build_library(
#    "sclang.so", ["/home/murphy/Downloads/tree-sitter-supercollider"]
# )
#
#
# tree = parser.parse(
#    bytes(
#        """
# (
# {
# var n;
# n=10;
#
# Resonz.ar(
# Mix.fill(n,{
# var freq, numcps;
#
# freq= rrand(50,560.3);
# numcps= rrand(2,20);
# Pan2.ar(Gendy4.ar(6.rand,6.rand,1.0.rand,1.0.rand,freq ,freq, 1.0.rand, 1.0.rand, numcps, SinOsc.kr(exprand(0.02,0.2), 0, numcps/2, numcps/2), 0.5/(n.sqrt)), 1.0.rand2)
# })
# ,MouseX.kr(100,2000), MouseY.kr(0.01,1.0))
# ;
# }.play
# )
# """,
#        "utf8",
#    )
# )
#
# for node in traverse_tree(tree):
#    print(node)

if __name__ == "__main__":
    main()
