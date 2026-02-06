import os
import sys
import importlib
import importlib.util
from typing import Callable, Any

def get_callable_by_id(identification: str, module_directoies: list[str] | None = None) -> Callable[..., dict[str, Any]]:
    module_name, method_name = identification.split('.')
    found = False
    if module_directoies:
        for module_directory in module_directoies:
            if module_directory and f'{module_name}.py' in os.listdir(module_directory) and os.path.exists(module_directory):
                spec = importlib.util.spec_from_file_location('module', os.path.join(module_directory, module_name))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                found = True
                break
    
    if not found:
        try:
            module = importlib.import_module(f'modules.{module_name}')
        except (ImportError, ModuleNotFoundError):
            raise ValueError(f'Module {module_name} not found in module directories {module_directory} nor project module location')
    
    if not hasattr(module, method_name):
        raise ValueError(f'The requested method {method_name} was not found in the specified module {module_name}.')
    return getattr(module, method_name)