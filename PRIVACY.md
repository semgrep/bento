# Bento Privacy Policy

Bento collects usage data to help inform how to improve the product. This document describes:

* principles that guide the collection and usage of usage data
* the data collected
* what data is not collected
* why specific data is collected and how it’s used

# Principles

These guidelines inform decisions about data collection:

* Transparency:
    * Collect and use information in a way that is transparent and benefits the user
* User control
    * Develop products and advocate for best practices that put users in control of their data
* Limited data
    * Collect what is needed, de-identify where possible, and delete when no longer necessary

# Definitions

## Personal data

Personal data includes: 

* .git related information, such as: repository name, commit, git user name, git user email
* IP address
* source code and context of findings

## Collected data

Bento collects data to help improve the Bento user experience for users everywhere. The following information is collected and sent to r2c:

* Anonymized version of repository name, current commit, paths of files, names of checks that fire
* Aggregate count of checks that fire
* Names of checks that are disabled for the tools running in Bento
* The user’s OS, shell information, user agent, and anonymized IP
* Bento asks users to share error dump data on crashes 

## Sample data and definition of fields

This is a sample blob of data collected by Bento and sent to r2c:
```json
{
    "X-R2C-Bento-User-Platform": "Darwin-18.7.0-x86_64-i386-64bit",
    "X-R2C-Bento-User-Shell": "/bin/bash",
    "ua": "python-requests/2.22.0",
    "client_ip": "136.24.226.0",
    "tool": "r2c.flake8",
    "timestamp": "2019-09-27T17:53:40.148497",
    "repository": "aa3a1e42e4a89f38c2d5fdede90f45471e2f9f383e09e363197ab03225fd05e8",
    "commit": "faab68724239ceb66f18c91281d4bcc71d82d0f7",
    "user": "0207e8d62d5e45e1b464c9b70e60949aeb00a9fc1eac6d96f45af44573d76d70",
    "ignored_rules": ["F406"],
    "path_hash": "b08fd7a517303ab07cfa211f74d03c1a4c2e64b3b0656d84ff32ecb449b785d2",
    "rule_id_hash": "233d7433c1eb2e65b6c36608da1051769ef4cafad4816152c8e9c85d4d3ea7d2",
    "count": 1,
    "filtered_count": 0,
    "error": false,
    "event_name": "DUMMY_EVENT_NAME"
  }
  ```
## Definition and description of fields

| Field        | Description           | Use case  |
| ------------- |:-------------:| -----:|
| X-R2C-Bento-User-Platform     | OS description | Reproduce and debug issues with specific platforms |
| X-R2C-Bento-User-Shell| 	shell description| 	Reproduce and debug issues with specific shells
| ua	| user agent| 	Reserved for future Bento variants
| client_ip	| 	| Rough geolocation of clients so we can best support our users
| tool	| The tool which triggered the event [r2c.eslint, r2c.flake8]| 	Improve Bento integration with the tool
| timestamp| 	Time when the event fired	| Reproduce and debug issues
| repository	| SHA256 hash of the repository name| 	Reserved for future tailoring of checks to the repository
| commit	| Git commit hash| 	To understand when checks get fixed
| user	| SHA256 hash of GitHub email	| Know if checks are either specifically or universally disdained or fixed
| ignored_rules	| Rules that are explicitly ignored using Bento (by using `bento disable`)	| Understand which checks are useful and which are not
| path_hash	| SHA256 hash of the relative file path which is relevant to the event| 	Measure check adoption and fixes; in conjuction with rule_id_hash and count, infer if checks get addressed
| rule_id_hash	| SHA256 hash of the rule_id which caused the event	| Measure check adoption and fixes; in conjuction with path_hash and count, infer if checks get addressed
| count| 	Number of times a check fires for this path| 	Number of times a check fires for a path; in conjuction with rule_id_hash and rule_id_hash, infer if checks get addressed
| filtered_count| 	Number of times a check fires, not including archived checks.| 	Measure check adoption and fixes
| error| 	Boolean reperesenting if this was an error event| 	Reproduce and debug issues
| event_name	| Generic Bento label| 	Generic Bento label



