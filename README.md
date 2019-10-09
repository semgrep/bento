# Bento

Bento finds the bugs that matter to you.

Bento is a command line tool that automatically tailors linters and static analysis tools to your project, letting you focus on writing code rather than figuring out configs.

## Installation

### Requirements

You must have Python 3.6 or greater installed.

### Get Bento

Run

```
pip3 install bento-cli
```

### In your project

To set up for a project, navigate to the root of your project (e.g., where your `.git` directory is located).

Then run:

```
bento setup
```

This will install Bento for your project.

### For git

Add this to your `.gitignore`:

```
.bento
```

## Usage

To find all violations in your project, run:

```
bento check
```

To suppress all violations, run:

```
bento reset
```

and commit the resulting `.bento-baseline.yml` file.
