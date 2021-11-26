# Pradhyum's Awesomely Magical Language (PAML)

PAML is a way to write configuration files in an enjoyable format. 

**Because it is so enjoyable, some might consider it too enjoyable: There are security isses to
this program. Use with caution.**

## Spec

A PAML program is made up of a series of *assignments* and *manual expressions*. Assignments are
your run-of-the-mill assignments: `x = 5`, `y = "asdf"`. What comes after the equal sign is
an *expression*, which will be defined later; it is the core of the language. A manual expression
is simply an expression prefixed by two colons: `:: 5`. Its result will be discarded, so it's usually
used to print out information. It must be prefixed to that you understand that you're running
expressions in a configuration language, something that is rarely needed.

An expression is literally everything else in the language. There are many different types of
expressions. Many of them refer to expressions We can start with the simplest expression: the literal. 

A literal can be a number or a string. Strings have standard escapes and numbers include (I believe) 
both integers and floats: `1`, `"asdf"`

A method is simply an expression, followed by a dot, then a name. It is used to extract objects
out of mappings: `builtins.format`, `{a = 5}.a`

To create a function, use the keyword `fn`, followed by an optional comma separated list of
arguments, an arrow (`->`), and the expression that is the body, ended by `endfn`:

```
fn x, y -> builtins.add(x, y) endfn
```

To call a function, use your standard syntax of following the function object with a comma separated
list of values enclosed in parentheses.

Conditionals must have an if, then, and else clause: `if 1 then builtins.add(1, 1) else 0`

Variables conform to C naming rules and Python naming conventions

A mapping consists of a complete sub-program enclosed in curly braces (`{`, `}`). Everything inside
the mapping will behave as if it is inside that environment. Outside variables can still be accessed.

Comments are started with the pound symbol and continue until the end of the line.
