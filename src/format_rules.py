import re
from tree_sitter import Language, Parser, Tree, Node

# Interface for Format Rule
class FormatRule(object):

    # Public
    @classmethod
    def format(self, arguments, data, tree, parser, language):
        # Use the private formatter
        data, tree = self.__format(arguments, data, tree, parser, language)

        # Rebuild the tree from the existing tree
        # tree = Helpers.get_tree(parser, data, tree)
        tree = Helpers.get_tree(parser, data, None)
        return data, tree

    # Private
    @staticmethod
    def __format(arguments, data, tree, parser, language):
        raise NotImplementedError


#################################


class Helpers(object):
    @staticmethod
    def get_query_result_and_newline_data(tree, query, data):

        # Sort the results so that the match that is at the last position
        # is the first in the list. This way we can edit the string in
        # place and only rebuild the tree after all the edits have been
        # made.

        # TODO: why doesn't this return properly all the time ?

        captures = sorted(query.captures(tree.root_node))
        captures.reverse()

        newline_offsets = Helpers.get_all_newline_offsets(data)

        return captures, newline_offsets

    @staticmethod
    def get_all_newline_offsets(data):
        # Use the positive lookbehind technique to match
        # the character after the newline. The [0] is in place, as the 0th
        # character is always the start of the first line.
        return [0] + [match.start() for match in re.finditer("(?<=\n).", data)]

    @staticmethod
    def position_offset(data, line, offset):
        i = 0
        current_line = 0
        current_offset = 0
        for char in data:
            # If we have found the character, return
            if current_line is line and current_offset is offset:
                return i

            # Continue iterating
            if char == "\n":
                i = i + 1
                current_line = current_line + 1
                current_offset = 0
            else:
                i = i + 1
                current_offset = current_offset + 1

    @staticmethod
    def replace_range(data, start_offset, end_offset, new_data):
        print("############")
        print(
            "Start: " + str(start_offset) + " [" + str(data[start_offset]) + "]"
        )
        print("End: " + str(end_offset) + " [" + str(data[end_offset]) + "]")
        print("############")
        return new_data.join([data[:start_offset], data[end_offset:]])

    # @staticmethod
    # def get_end_position_from_node(node):
    #    return

    @staticmethod
    def edit_data(data, start_edit, end_edit, new_data):
        pass
        # Start_Edit and End_Edit are an array with the form: line num / character
        # Find where this represents in the string
        # remove that chunk / insert edited text into that chunk

    @staticmethod
    def get_tree(parser, data, tree):
        if tree is None:
            return parser.parse(bytes(data, "utf8"))
        else:
            return parser.parse(bytes(data, "utf8"), tree)

    @staticmethod
    def traverse_tree(tree: Tree):
        cursor = tree.walk()

        reached_root = False
        while reached_root == False:
            yield cursor.node

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            retracing = True
            while retracing:
                if not cursor.goto_parent():
                    retracing = False
                    reached_root = True

                if cursor.goto_next_sibling():
                    retracing = False


#### Format Rules
# Most Taken from:
# https://github.com/supercollider/supercollider/wiki/Code-style-guidelines

# The basic loop of a formatter is to:
#   1) Find the places in the tree, parser where the data needs to be modified.
#      Start from the end so we can modify the data in place.
#   2) Update the data string appropriately.
#   3) Public method will update the tree.

# Normalize Data - put text into a common format to be more
# easily formatted. This should be run as a pre-formatter prior
# to create the tree, parser.
class NormalizeText(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        # Normalizing will convert tabs to spaces, remove all leading whitespace,
        # collapse multiple spaces into one, remove starting spaces and
        # remove all empty lines.
        data = re.sub("\t", " ", data)
        data = re.sub(" +", " ", data)
        data = re.sub(r"^$\n", "", data, flags=re.MULTILINE)
        data = data.lstrip()
        return data, tree


# Lines can't be more than 80 characters wide
# Reason: Historical Standard
class NoMoreThan80Characters(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


### End-of-File Newline

# Rule: Use exactly one newline at the end of a file.
# Git considers a file without a terminating newline
# to be malformed, and will complain when you commit
# a change without one! You can set your editor to
# fix this behavior.
class EndOfFileNewLine(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        data = data + "\n"
        return data, tree


### Trailing whitespace

# Rule: Don't end lines with whitespace characters.
# This keeps diffs clean as it prevents accidental whitespace
# from being committed. Other users whose editors automatically
# strip trailing whitespace will be forced to either redo your
# mistake or commit unnecessary changes. If your editor supports
# automatically removing trailing whitespace, consider turning
# that behavior on.
class StripTrailingWhitespace(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        data = data.rstrip()
        return data, tree


### Spaces in Expressions and Statements

# Rule: Use spaces around binary operators
# Binary operators, including key binary operators,
# should have one space before and after.
class BinaryOperatorSpacing(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):

        query = language.query(
            """
           (binary_expression) @binary_exp
           """
        )

        captures, newline_offsets = Helpers.get_query_result_and_newline_data(
            tree, query, data
        )

        # A binary expression will always have three parts
        # - A prefix
        # - The binary operator
        # - The suffix
        # The binary operator itself is the second element
        # in the binary expression child array.
        #
        # We'll pull that out of the match array and then
        # resort.

        operators = []

        for match in captures:
            operators.append(match[0].children[1])

        operators = sorted(
            operators,
            key=lambda operator: [operator.start_point, operator.end_point],
            reverse=True,
        )

        for operator in operators:

            start_line = operator.start_point[0]
            start_offset = operator.start_point[1]
            end_line = operator.end_point[0]
            end_offset = operator.end_point[1]
            start_matched_char_loc = newline_offsets[start_line] + start_offset
            end_matched_char_loc = newline_offsets[end_line] + end_offset
            operator = data[start_matched_char_loc:end_matched_char_loc]

            # Handle the right side
            if data[end_matched_char_loc] != " ":
                data = (
                    data[:start_matched_char_loc]
                    + operator
                    + " "
                    + data[end_matched_char_loc:]
                )

            # Handle the left side
            if data[start_matched_char_loc - 1] != " ":
                data = (
                    data[:start_matched_char_loc]
                    + " "
                    + operator
                    + data[end_matched_char_loc:]
                )

        return data, tree


# Rule: Add spaces after commas.
# Commas should have one space after, but not before.
class AddSpacesAfterCommas(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):

        query = language.query(
            """
           (",") @comma
           """
        )

        captures, newline_offsets = Helpers.get_query_result_and_newline_data(
            tree, query, data
        )

        for comma in captures:
            line = comma[0].start_point[0]
            offset = comma[0].start_point[1]
            matched_char_loc = newline_offsets[line] + offset

            # Handle the right side
            if data[matched_char_loc + 1] != " ":
                data = (
                    data[: (matched_char_loc + 1)]
                    + " "
                    + data[(matched_char_loc + 1) :]
                )

            # Handle the left side
            if data[matched_char_loc - 1] == " ":
                data = data[: (matched_char_loc - 1)] + data[matched_char_loc:]

        return data, tree


# Rule: Don't use spaces before semicolons.
# Semicolons should immediately follow the end of the statement,
# with no additional space.
#
# x = 3 + 5 ; // incorrect
# x = 3 + 5;  // correct
class DontUseSpaceBeforeSemicolons(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        data = re.sub(" ;", ";", data)
        return data, tree


# Rule: Add spaces within curly brackets {},
# but not parentheses (), square brackets [], or argument lists ||.
# When written on a single line, there should be no spaces inside
# parentheses (), square brackets [], or argument list pipes ||.
# Curly braces {} delimit functions, and should have exactly one
# space after the opening brace and one space before the closing
# brace. This includes having a space between { and the | that
# begins an argument list.
#
# // correct:
# a = f.value(10);
# b = [1, 2, 3];
# c = b.collect({ |x| x + 3 });
#
# // incorrect:
# a = f.value( 10 );
# b = [ 1, 2, 3 ];
# c = b.collect({| x | x + 3});
class BracketSpacing(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):

        # NB: The treesitter will not parse a parameter list with spaces,
        # so adding (parameter_list ("|") ("|")) @no_space to the query
        # is moot.
        #
        # This is a known issue:
        # https://github.com/madskjeldgaard/tree-sitter-supercollider/issues/42
        #
        # When the issue is resolved, it's a TODO to add the query for the parameter
        # list and the appropriate handling logic back in.
        query = language.query(
            """
           ("(") @no_space_left
           (")") @no_space_right
           ("[") @no_space_left
           ("]") @no_space_right
           ("{") @space_left
           ("}") @space_right
           """
        )

        captures, newline_offsets = Helpers.get_query_result_and_newline_data(
            tree, query, data
        )

        for match in captures:
            match_type = match[1]
            line = match[0].start_point[0]
            offset = match[0].start_point[1]
            matched_char_loc = newline_offsets[line] + offset

            if match_type == "no_space_left":
                location_to_check = matched_char_loc + 1
                char_to_check = data[location_to_check]
                if char_to_check == " ":
                    data = (
                        data[: (matched_char_loc + 1)]
                        + data[(location_to_check + 1) :]
                    )
            elif match_type == "no_space_right":
                location_to_check = matched_char_loc - 1
                char_to_check = data[location_to_check]
                if char_to_check == " ":
                    data = data[:location_to_check] + data[matched_char_loc:]

            elif match_type == "space_left":
                location_to_check = matched_char_loc + 1
                char_to_check = data[location_to_check]
                if char_to_check != " ":
                    data = (
                        data[:location_to_check]
                        + " "
                        + data[(matched_char_loc + 1) :]
                    )

            elif match_type == "space_right":
                location_to_check = matched_char_loc - 1
                char_to_check = data[location_to_check]
                if char_to_check != " ":
                    data = (
                        data[: (location_to_check) + 1]
                        + " "
                        + data[matched_char_loc:]
                    )

        return data, tree


### Indentation

# Rule: use tabs for indentation.
# The SuperCollider class library uses tabs for indentation.
class UseTabsForIndentation(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


# Rule: Use K&R style for multi-line blocks
# For all three bracket types, use K&R indent style.
# The open brace comes at the end of the first line,
# rather than on a separate line.
#
# // correct
# x = {
#     y = y + 1;
#     3.rand
# };
#
# // Allman style: avoid
# x =
# {
#     y = y + 1;
#     3.rand
# };
class UseKRStyle(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


### Method Calls

# Rule: don't space around .
# . may be used either inline or multiline.
# Inline, don't put any space around it.
#
# // good:
# foo.value(bar)
#
# // bad:
# foo . value(bar)
# In long chains of method calls on the same object,
# it may be beneficial to split the method call across
# two lines. The dot should be on the second line, not
# the first, and it should be indented one level.
# Don't put whitespace between the dot and the method name.
#
# Button()
#    .states_([["blorp", nil, nil]])
#    .action_({
#        "hey hey hey".postln
#    });
class FormatDotNotation(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


### Methods and functions

## Parameter Lists

# Rule: Use pipes instead of the arg keyword to express
# parameter lists. The pipe-enclosed parameter list is
# used in most modern code, and mimics parameter lists in
# Smalltalk. Programmers coming from languages other than
# Smalltalk may also find that it appears closer to C-family
# function signature notation.
#
# Although the SuperCollider compiler will allow commas to be
# omitted in parameter lists, adding them makes for clearer code,
# especially when default arguments are provided.
#
# // good:
# x = { |foo = 3, bar = (4.dbamp)| /* ... */ };
#
# // bad, unclear:
# x = { |foo = 3 bar = (4.dbamp)| /* ... */ };
# // bad, outdated notation:
# x = { arg foo = 3, bar = 4.dbamp; /* ... */ };
#
# Note that with pipe notation, an initializer expression that
# is not a single literal must be enclosed in parentheses.
class FormatParameterLists(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


# Rule: Place the parameter list on the same line as the
# opening curly bracket of a function or method.
# As explained in the previous rule, this is closer to
# conventional Smalltalk style and reads like a parameter
# list in C-family languages.
#
# // good:
# x = { |foo = 3, bar = 4|
#    foo + bar;
# };
#
# // bad:
# x = {
#    |foo = 3, bar = 4|
#    foo + bar;
# };
class ParameterListAlignment(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


## Return Statements

# Recommendation: don't place a semicolon after the
# final statement of a method or function.
# Expressions that are followed by a semicolon suggest
# that another expression follows. A function return
# value isn't followed by any other statement. In this
# way, omitting the optional semicolon after the final
# statement of a method or function can serve to indicate
# an intentional return value.
#
# When code within a method or function changes frequently,
# missing semicolons may trip up the programmer as statements
# are reordered. A similar risk appears in methods where
# the last return statement is likely to be amended with
# further return cases. In those situations, it may make more
# sense to retain the final semicolon.
#
# ExampleClass {
#    exampleMethod { |a, b|
#        var c = a + b;
#        ^c.asString
#    }
# }
# f = { |a, b|
#    var c = a + b;
#    c.asString // semicolon omitted here marks this as the
#                  intended return value
# }
class FormatReturnStatement(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


### Arrays and Collections

## Multi-line arrays

# Rule: Place each element of a multi-line array on its own line.
# Each element should be on a separate line:
#
# x = [
#    "foo",
#    "bar",
#    "baz"
# ];
class FormatMultieLineArray(FormatRule):
    @staticmethod
    def _FormatRule__format(arguments, data, tree, parser, language):
        return data, tree


## Miscellaneous

# Trailing closure syntax
# Recommendation: Use trailing closure syntax
# whenever possible. Especially in control-flow
# methods like do, if, for, case, switch, and while:
#
# // wrong
# if(c, { "true".postln }, { "false".postln });
#
# // right
# if(c) { "true".postln } { "false".postln };
class UseTrailingClosureSyntax(FormatRule):
    @staticmethod
    def format(arguments, data, tree, parser, language):
        return data, tree
