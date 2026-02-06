# ⚠️ Security Warning: User-Provided Modules

This application allows you to extend its functionality by loading custom Python modules (`.py` files) from directories specified in your `config.toml`. This is a powerful feature that enables a high degree of customization.

However, this also carries a **significant security risk**. A malicious or poorly written Python module can execute **arbitrary code** on your system. This could include, but is not limited to:

*   Reading, modifying, or deleting your personal files.
*   Accessing your network and sending your data to third parties.
*   Installing malware or other unwanted software.

**You MUST review and trust the source of any custom modules you download and add to your `plugin_paths`. Only use modules from developers and sources you trust completely**

The modules are distributed as plaintext python files, not binaries, this project does not and will not support loading binaries, although loading and utilizing foreign functions within the modules are allowed.

By using any feature involving custom mdoules, you acknowledge that you are responsible for vetting the code you run and for the security of the modules you load.


# MPRIS-DRPC: MPRIS metadata preprocessor server with discord rich presence support
## Features:
* **Album Art Matching:** built in modules to find missing art urls for youtube an NND with yt-dlp (requires yt-dlp)
* **Lyric Matching:** built in modules to locate lyric files from lrclib can be paired with other preprocessers for more robust matching
* **Metadata Matching:** A robust matadata matching system that can trigger specified functions if the rule matches
* **Plugin System:** Full support for plugins, plugins are python files and primarily define matching functions and preprocessor functions. built in are modules for adding missing metadata and matching lyrics, extra modules can be added to paths specified in `plugin_paths` in `config.toml`

# Configuration
MPRIS-DRPC is configured in TOML format, the file is stored at `$(XDG_CONFIG_HOME)/mpris-drpc/config.toml`, plugin_paths by default is set to `$(XDG_CONFIG_HOME)/mpris-drpc/plugins`, additional paths may be specified in the configuration

Example:
```toml
[global]
# the server socket file, the server will listen here for clients
socket_path = '/tmp/mpris.sock'

# additional module directories, the server will locate directories here first, then in the distribution module directory
# meaning that modules placed here with the same name as distribution module would override it
plugin_paths = ['~/.config/mpris-drpc/plugins']

# The server has discord rich presence support, enable this flag to use it
discord_rpc = false

[ruleset]
# You can add your own rulesets to trigger metadata preprocessing here, the key follows the Rule expression syntax, and requires escaping. 
# The value is the callable method, following format `module.metghod(args, kwargs), remeber that internally these functions receive an implicit first argument being the metadata dictonary
"|| xesam:url <-> __contains__('nicovideo,jp') ||" = 'nnd.nnd_handler()' # Handle niconico urls with yt-dlp assistance to get arturl and the uploader (requires yt-dlp)


[drpc]
# Keys under this section only come into effect when `discord_rpc` is true, as these are rich presence options

```

#### Avalaible keys under global section:
* `socket_path`: the IPC socket location the server runs on
* `plugin_paths`: paths to search for plugins for, multiple can be selected, the leftmost path is searched first, if a user plgin shares name with a builtin, the user plugin overrides
* `discord_rpc`: Discord Rich Presence (WIP)

---------------------------------------

#### Avalaible Keys under ruleset section:

The ruleset section is different as there are no defined keys, the rules are directly defined as keys, and the corresponding function is the value, the function called must specify both the module it is from and the callable name, additional arguments and keyword arguments may be passed in the prenthesis with standard python syntax, the function will receive an implicit first argument being the metadata dictonary

For the rule syntax, refer to the next section

----------------------------------------------

#### Avalaible Keys Under drpc section:

WIP

# Rule Format Syntax

The parser evaluates rules defined in a specific string format. Each rule is composed of one or more **clauses** linked by **logical operators**, all wrapped within double pipes (`||`).

### Basic Structure

The basic structure of a rule is `|| clause_1 || logical_operator || clause_2 ||`.

  * The entire rule **must** begin and end with `||`.
  * Clauses and operators are separated by `||`.
  * Whitespace (spaces, tabs, newlines) is largely ignored, so you can format rules for readability.

### Clause Syntax

Each clause follows the format `(not) dict_key <-> method(arguments)`.

  * **`not` (Optional)**: If present, it inverts the boolean result of the clause.
  * **`dict_key`**: The key whose value you want to test from the input dictionary.
  * **`<->`**: A required separator, ligatures affect this so for clarity the syntax is: `<` `-` `>`.
  * **`method(arguments)`**: The function to execute on the dictionary value.

-----

### Supported Methods

#### 1\. Generic Object Methods

You can call a method on a value of any data type (`str`, `list`, `set`, etc.). If the method exists and returns a boolean-like value, the clause passes; otherwise, it fails, additional arguments accpeted by the method may be passed in using python syntax within the method signature.

  * **Syntax:** `method_name(arguments)`
  * **Examples:** `startswith('A')`, `__contains__(42)`, `is_integer()`

#### 2\. Standard Regex (`regexpr`)

Performs a regex search using Python's built-in `re` module. The dictionary value is automatically converted to a string before matching, flags can be specified as list of strings in the flags keyword argument, the name must be all caps and match the flag name without the `re.` prefix.

  * **Syntax:** `regexpr('pattern', flags=['FLAG_NAME'])`
  * **Examples:** `regexpr('^line', flags=['IGNORECASE', 'MULTILINE'])`
 
#### 3\. Advanced PCRE (`pcre`)

Performs a regex search using the powerful third-party `regex` library. This requires the package to be installed (`pip install regex`). The value is converted to a string before matching, additional arguments accepted by `regex.search` may be passed in using python synatx within the method signature.

  * **Syntax:** `pcre('pattern')`
  * **Examples:** `pcre('^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', concurrent=True)`

#### 4\. User-Provided Methods

Invokes a custom function from a Python module you provide. The module must be located in one of the configured `plugin_paths`, the dictonary value associated with the `dict_key` is an implicit first argument to the method, additional arguments may be passed in using python syntax within the method signature.

  * **Syntax:** `module_name.method_name(arguments)`
  * **Examples:** `validators.is_email_valid('arg', strict=False)`

-----

### Logical Operators

You can connect clauses using the following logical operators:

  * **`and`**: True only if both clauses are true.
  * **`or`**: True if at least one clause is true.
  * **`xor`**: True if exactly one of the two clauses is true.