import os
import shutil
import tomllib
import dataclasses

def parse_toml_config(filepath):
    """
    Parses a TOML file into a Python dictionary using tomllib (Python 3.11+).

    Args:
        filepath (str): The path to the TOML file.

    Returns:
        dict: A dictionary representing the TOML configuration.
              Returns an empty dictionary if the file is not found or parsing fails.
    """
    try:
        # Note: You should open the file in binary read mode ('rb') for tomllib.load()
        with open(filepath, 'rb') as f:
            config_data = tomllib.load(f)
        return config_data
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return {}
    except tomllib.TOMLDecodeError as e:
        print(f"Error parsing TOML file '{filepath}': {e}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}


@dataclasses.dataclass(frozen=True)
class ImmutableDict:
    """
    A custom frozen dataclass that behaves like an immutable dictionary.

    It takes a standard dictionary during initialization and stores its items
    as an immutable tuple of (key, value) tuples. Attempts to modify the
    ImmutableDict after creation will result in an error.
    """

    # _data is the internal, immutable representation of the dictionary.
    # init=False means it's not part of the dataclass's generated __init__ signature.
    # repr=False means it won't be included in the default __repr__ output.
    _data: tuple = dataclasses.field(init=False, repr=False)

    def __new__(cls, initial_dict: dict):
        """
        __new__ is called before __init__ and is responsible for creating
        and returning a new instance. For immutable objects, it's often
        used to set up the core immutable state before __init__ or
        dataclass processing.
        """
        if not isinstance(initial_dict, dict):
            raise TypeError("initial_dict must be a dictionary")

        instance = super().__new__(cls)
        # Use object.__setattr__ to set the _data attribute directly on the
        # new instance. This bypasses the frozen dataclass's __setattr__
        # enforcement during initialization.
        object.__setattr__(instance, '_data', tuple(initial_dict.items()))
        return instance

    # Note: We do not define __init__ or __post_init__ here, as __new__
    # handles the initialization of _data. The dataclass's generated __init__
    # would still be called, but since _data is init=False and there are no
    # other fields, it essentially does nothing.

    def __getitem__(self, key):
        """
        Overrides the item access (e.g., immutable_dict[key]).
        Iterates through the internal tuple of tuples to find the value.
        """
        for k, v in self._data:
            if k == key:
                return v
        raise KeyError(f"Key '{key}' not found in ImmutableDict")

    def __getattr__(self, name):
        """
        Overrides attribute access (e.g., immutable_dict.attribute_name).
        This method is called only if the attribute is not found by normal means.
        It allows accessing dictionary keys as attributes, provided the key
        is a string and a valid Python identifier.
        """
        # Check if the name is a string, as only string keys can be accessed as attributes.
        if isinstance(name, str):
            for k, v in self._data:
                if k == name:
                    return v
        # If the key is not found or is not a valid attribute name, raise AttributeError.
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}' or key '{name}'")
    
    def __setitem__(self, *args):
        raise TypeError('ImmutableDict is immutable')
    
    # def __setattr__(self, *args):
    #     raise TypeError('ImmutableDict is immutable')

    # The __setattr__ method is implicitly handled by the `frozen=True` argument
    # in the @dataclasses.dataclass decorator. Any attempt to set an attribute
    # on an instance of ImmutableDict after its creation will automatically
    # raise a `dataclasses.FrozenInstanceError`, ensuring immutability.
    # Therefore, an explicit __setattr__ override is not needed and would
    # interfere with the dataclass's built-in immutability enforcement.

    def keys(self):
        """
        Returns a tuple containing all keys in the ImmutableDict.
        """
        return tuple(item[0] for item in self._data)

    def values(self):
        """
        Returns a tuple containing all values in the ImmutableDict.
        """
        return tuple(item[1] for item in self._data)

    def items(self):
        """
        Returns the internal tuple of (key, value) tuples, representing
        all items in the ImmutableDict.
        """
        return self._data

    def __len__(self):
        """
        Returns the number of items in the ImmutableDict.
        """
        return len(self._data)

    def __contains__(self, key):
        """
        Checks if a key exists in the ImmutableDict (e.g., 'key' in immutable_dict).
        """
        for k, _ in self._data:
            if k == key:
                return True
        return False

    def get(self, key, default=None):
        """
        Behaves like the standard dictionary's get() method, returning the
        value for a key if found, otherwise returning the default value.
        """
        try:
            return self[key]
        except KeyError:
            return default
        
    def __iter__(self):
        for k, v in self._data:
            yield k

    def __repr__(self):
        """
        Provides a user-friendly string representation of the ImmutableDict.
        """
        # Reconstruct a dict-like string from _data for representation
        items_str = ", ".join(f"{repr(k)}: {repr(v)}" for k, v in self._data)
        return f"{self.__class__.__name__}({{{items_str}}})"


@dataclasses.dataclass(frozen=True)
class Config:
    metadata_ruleset: ImmutableDict
    socket_path: str | None = '/tnp/mpris.sock'
    plugin_paths: list[str] | None = None
    discord_rpc: bool = False

    @classmethod
    def from_config(cls):
        config_home = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')), 'mpris-drpc')
        config_file = os.path.join(config_home, 'config.toml')
        if not os.path.exists(config_file):
            os.mkdir(config_home)
            os.mkdir(os.path.join(config_home, 'plugins'))
            shutil.copy('./example_config.toml', config_file)
        
        config = parse_toml_config(config_file)
        config['global']['plugin_paths'] = [os.path.expanduser(p) for p in config['global']['plugin_paths']]
        if config:
            return cls(config['ruleset'], **config['global'], **config['drpc'])
        else:
            return cls(metadata_ruleset=ImmutableDict({}), socket_path='/tnp/mpris.sock')