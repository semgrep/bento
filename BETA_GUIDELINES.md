# Bento
Thanks for giving Bento a try.  
We would like you to follow these steps prior to the user interview.

## 1-  Installation
Here are some quick instructions to get you up and running. 
```bash
pip3 install
```  
More detailed instructions are [here](https://github.com/returntocorp/bento).



Bento automatically tailors linters and static analysis with sane defaults on a per-project basis, letting you focus on writing code rather than configuring tools. Bento is free, fully-featured, and you can run Bento on as many projects as you like.

## Installation

### Requirements

Bento is supported on macOS Mojave (10.14) and Ubuntu 18.04+, and requires Python 3.6 or later, and pip3.

Bento supports npm-packaged JavaScript and Python, and is ideal for monorepos.

To run Bento on projects that include JavaScript, Node.js is required and the following versions are supported:

* Node.js 8 (8.10.0 and above)
* Node.js 10 (10.13.0 and above)
* Anything above Node.js 11.10.1

### Installing Bento
Bento is a command-line tool that is simple to install:

```bash
pip3 install bento-cli
```

## Usage
The workflow for Bento is:

1. Initialize Bento
2. Run Bento checks on your source code
3. Fix issues or archive unnecessary warning and errors
4. Disable undesired checks
5. Add Bento to git pre-commit hooks
6. Add Bento to the CI pipeline (e.g., CircleCI)

### Initialize Bento for a project:

In your project directory, run:

```bash
bento init
```

and add some of the artifacts bento produces to your .gitignore file:

```bash
printf "# Bento tools:\n.bento/" >> .gitignore
```

### Analyze your source code
To trigger Bento to analyze your project, run:

```bash
bento check
```


## Community
Join the Bento channel in our [community Slack](https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA) to receive and give support, talk with other users, and share things about Bento. The r2c team is there and ready to help!

## Terms of service and privacy
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

## License
Copyright (c) [r2c](https://r2c.dev ).

![r2c logo](https://r2c.dev/r2c-logo-silhouette.png?gh)
