# sgrep Readme

The goal of sgrep is to allow programmers to express complex code *patterns* with a familiar syntax. The idea is to mix the convenience of grep with the correctness and precision of a compiler frontend. We integrated sgrep into Bento to allow developers and security engineers to easily develop and run custom checks on every commit.

## Principles

sgrep’s design follows 3 principles:
 
1. Use **metavariables **to support finding generalized patterns.
2. Provide an **ellipses operator** **‘...’ **to support pattern matching code sequences.
3. Leverage **code equivalences **in the language so one pattern can match variations of code.

## Installation

Requirements:

* Python 3.6+
* Docker

On macOS and Ubuntu:

```
$ pip3 install bento-cli
$ bento init
```



## Usage

Bento, r2c’s program analysis toolkit, has a suite of tools and checks it runs by default: **sgrep is not enabled by default**. You can run sgrep independently with the following command:

```
`$ bento check -t r2c.sgrep`
```

To enable it to run alongside of Bento’s default tools:

```
$ bento enable tool r2c.sgrep
```



## Writing Bento Checks

Custom checks in Bento are defined in `.bento-sgrep.yml`. Note that the order of the rules in this file is important! The first rule that matches a code pattern will trigger. This allows you to define patterns with greater specificity first, and fallback to more general patterns later in the file.

`.bento-sgrep.yml` contains a list of `rules` similar to the following:

```
rules:
  - id: is_equal_to_self
    pattern: $X == $X
    message: This may be a comparator typo (e.g., `>=`, `!=`). X == X will always be true, unless X is NaN.
    languages: [python, javascript]
    severity: WARNING
```

Each rule object has these fields:

|Field	|Type	|Description	|Required	|
|---	|---	|---	|---	|
|id	|string	|None unique check-id that should be descriptive and understandable in isolation by the user. e.g. `no-unused-var`.	|Y	|
|pattern	|string	|See Example Patterns below.	|Y	|
|message	|string	|Description of the rule that will be output when a match is found.	|Y	|
|languages	|array<string>	|Languages the check is relevant for. Can be python or javascript.	|Y	|
|severity	|string	|Case sensitive string equal to WARNING, ERROR, OK	|Y	|



## Example Patterns

### expression Matching

```
pattern: 1 + foo(42)

# CODE EXAMPLES

foobar(1 + foo(42)) + whatever()
```



### metavariables

```
pattern: $X + $Y

# CODE EXAMPLES

foo() + bar()
```



### reusING metavariableS

```
pattern: ￼$X == $X

# CODE EXAMPLES

1+2 == 1+2
```



### Function Calls

**With Arguments After a Match**

```
pattern: foo(1, ...)

# CODE EXAMPLES

foo(1, "extra stuff", False)
foo(1) # matches no arguments as well
```


**With Arguments Before a Match**

```
pattern: foo(..., 1, ...)

# CODE EXAMPLES

foo(1, 2)
foo(2, 1)
foo(2, 3, 1)
```


**Object with Method Call**

```
pattern: $X.get(..., None)

# CODE EXAMPLES

json_data.get('success', None)
```


**Keyword Arguments in Any Order **

```
pattern: foo(kwd1=$X, color=$Y) 

# CODE EXAMPLES (keyword arguments in arbitrary order)

foo(color=2, kwd1=True)

```



### match any string by reusing again the ‘...’ operator

```
pattern: foo("...")

# CODE EXAMPLES

foo("this is a specific string")

```



### match Special strings using regexps

```
pattern: foo("=~/.*a.*/")

# CODE EXAMPLES

foo("this has an a")
```

Current limitation: the regexp syntax is the one used in OCaml, see https://caml.inria.fr/pub/docs/manual-ocaml/libref/Str.html. We are considering switching to a Perl-style regexp by using PCRE library.


### Match ANY statement

```
pattern: if $E:
           return $E

# CODE EXAMPLES

if test_env:
    return test_env
```

### Match ANY identifiers using metavariables

```
￼'import $X'

# CODE EXAMPLES

import random
```



### match conditionals

```
'if $X:
     $Y
'

# CODE EXAMPLES

if __name__ == "__main__":
    print('hello world')
```

Note that for multiline patterns, you need to use the `-f` option and store the pattern in a file, e.g., 
`sgrep -f cond-stmt.sgrep foo.py`

Note you can’t match a half statement because that is not a valid AST element. See the limitations section below.


### match a sequence of statements with ‘...’

```
'if $X:
     ...
'

# CODE EXAMPLES

if __name__ == "__main__":
    print('hello world')
    foo()
    bar()
```



### In a statement context, a Metavariable can also match any statement

```
'if $X:
   $Y
'

# CODE EXAMPLES
if 1:
  foo()

if 2:
  return 1
   
if 3:     # matches a “block” (a single statement containing multiple statements)
  foo()
  bar()
```

Because in Python there is usually no terminator (e.g., `;`), there is an ambiguity about ‘$Y’ in the above, which could match a statement and also an expression that is then matched later.


### Match on import types

```
subprocess.Popen(...)

# CODE EXAMPLES

import subprocess as s
s.Popen()
```



## Limitations

### sgrep is not grep

```
'foo'
which is parsed as an expression pattern, will match code like
foo()
bar+foo
foo(1,2)

but will not match code like
import foo

because in the above, foo is not an expression, but rather a name part of an import statement.
```



### Method calls and calls are parsed differently

```
'foo(...)'
should match code like
foo(1,2)
but will not match code like
obj.foo(1,2)
because the AST for a Call and a method Call is different internally.
to match method calls use
'$X.foo(...)'
```



### YOU can not use a half expression or half statement pattern

```
'1+'  or 'if $X:' are not valid patterns, because they are not full AST elements.
```

### 

## More info

Have suggestions, feature requests, or bug reports? Send us a note at hello@r2c.dev

See the archive at [https://github.com/facebookarchive/pfff/wiki/Sgrep](https://github.com/facebookarchive/pfff/wiki/Sgrep) for an introduction to sgrep, its motivations, and its basic interface.

