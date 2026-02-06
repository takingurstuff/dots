import re
import ast
import operator

from core.model.config import Config
from core.utils.module_kit import get_callable_by_id

try:
    import regex as pcre_regex_engine
except ImportError:
    pcre_regex_engine = None

class Matcher:
    """
    A parser to evaluate a dictionary against a custom rule string.
    """

    # Regex seems too complicated once the rules themselves are stripped down, removed it, since the primary delimiter is `<->` and the function calls have to follow python syntax, this is not nessaciary
    
    OPERATOR_MAP = {
        'and': operator.and_,
        'or': operator.or_,
        'xor': operator.xor
    }

    def __init__(self, config: Config, rule_string: str):
        """
        Initializes the parser by parsing the rule string.
        """
        self.clauses = []
        self.operators = []
        self._parse_rule(rule_string)
        self.config = config

    def _parse_rule(self, rule_string: str):
        """
        Parses the entire rule string into clauses and operators.
        """
        if not rule_string.startswith("||") or not rule_string.endswith("||"):
            raise ValueError("Rule string must start and end with '||'.")

        clean_rule = rule_string.strip().strip("||").strip()
        parts = [p.strip() for p in clean_rule.split("||")]

        if not parts:
            raise ValueError("Rule cannot be empty.")
            
        clause_parts = parts[::2]
        operator_parts = parts[1::2]
        self.operators = [op.lower() for op in operator_parts]

        for op in self.operators:
            if op not in self.OPERATOR_MAP:
                raise ValueError(f"Invalid logical operator: '{op}'. Must be 'and', 'or', or 'xor'.")

        for clause_str in clause_parts:
            dict_key, fn_call = clause_str.split('<->')
            fn_call = fn_call.strip()
            is_negated = dict_key.strip().split()[0].strip().lower() == 'not'
            dict_key = dict_key.replace('not', '').strip()
            method_name, *args = parse_function_call(fn_call)

            self.clauses.append({
                "negated": bool(is_negated),
                "key": dict_key,
                "method": method_name,
                "args": tuple(args),
                "custom_func_callable": get_callable_by_id(method_name, self.config.plugin_paths) if '.' in method_name else None
            })

    def _evaluate_clause(self, clause: dict, data_dict: dict) -> bool:
        key = clause['key']
        method_name = clause['method']
        custom_method = clause['custom_func_callable']
        if key not in data_dict:
            return False
        value = data_dict[key]
        result = False
        try:
            if method_name == 'regexpr':
                pos_args, kwargs = clause['args']

                # 1. Validate arguments
                if len(pos_args) != 1 or not isinstance(pos_args[0], str):
                    print(f"Warning: regexpr for key '{key}' requires one string argument for the pattern.")
                    return False
                if not set(kwargs.keys()).issubset({'flags'}):
                    print(f"Warning: regexpr for key '{key}' only supports the 'flags' keyword argument.")
                    return False

                pattern = pos_args[0]
                
                # 2. Process flags from kwargs
                re_flags = 0
                if 'flags' in kwargs:
                    flag_names = kwargs['flags']
                    if isinstance(flag_names, list):
                        for flag_name in flag_names:
                            flag_value = getattr(re, flag_name, None)
                            if isinstance(flag_value, re.Flag):
                                re_flags |= flag_value
                            else:
                                print(f"Warning: Unknown regex flag '{flag_name}' for key '{key}'. Ignoring.")
                    else:
                        print(f"Warning: 'flags' argument for key '{key}' must be a list. Ignoring.")

                # 3. Perform search with the combined flags
                if re.search(pattern, str(value), re_flags):
                    result = True

            elif method_name == 'pcre':
                pos_args, kwargs = clause['args']
                if kwargs or len(pos_args) != 1 or not isinstance(pos_args[0], str):
                    print(f"Warning: pcre for key '{key}' requires one string argument and no keyword arguments.")
                    return False
                pattern = pos_args[0]
                if pcre_regex_engine is None:
                    raise ValueError("The 'regex' package is required for pcre() support. Please install it using 'pip install regex'.")
                if pcre_regex_engine.search(pattern, str(value)):
                    result = True

            else:
                if custom_method:
                    pos_args, kwargs = clause['args']
                    method_result = custom_method(*pos_args, **kwargs)
                    if isinstance(method_result, bool):
                        result = method_result
                elif hasattr(value, method_name):
                    method_to_call = getattr(value, method_name)
                    if callable(method_to_call):
                        pos_args, kwargs = clause['args']
                        method_result = method_to_call(*pos_args, **kwargs)
                        if isinstance(method_result, bool):
                            result = method_result
                else:
                    result = False
        except (TypeError, ValueError) as e:
            if "pip install regex" in str(e):
                raise e
            print(f"Warning: Could not execute method '{method_name}' for key '{key}'. Reason: {e}")
            return False

        if clause['negated']:
            return not result
        return result


    def evaluate(self, data_dict: dict) -> bool:
        # This method remains unchanged
        if not self.clauses:
            return True
        final_result = self._evaluate_clause(self.clauses[0], data_dict)
        for i, op_str in enumerate(self.operators):
            op_func = self.OPERATOR_MAP[op_str]
            next_clause_result = self._evaluate_clause(self.clauses[i + 1], data_dict)
            final_result = op_func(final_result, next_clause_result)
        return final_result


class AlwaysTrue:
    def __init__(self):
        pass
    def evaluate(self, something):
        return True


def parse_function_call(call_string: str):
    """
    Parses a function call string with high resilience using the ast module.

    This version correctly handles complex spacing, newlines, and arguments
    that contain commas (e.g., strings or lists).

    Args:
        call_string: A string representing a function call.

    Returns:
        A tuple containing:
        - func_name (str): The name of the function.
        - pos_args (tuple): A tuple of positional arguments.
        - kw_args (dict): A dictionary of keyword arguments.

    Raises:
        ValueError: If the string is not a valid function call.
    """
    try:
        # 1. Parse the string into an Abstract Syntax Tree (AST)
        # We use 'eval' mode because we expect a single expression.
        tree = ast.parse(call_string, mode='eval')
        call_node = tree.body
        
        if not isinstance(call_node, ast.Call):
            raise ValueError("String does not appear to be a function call.")
            
        # 2. Extract the function name
        # ast.unparse handles names like `my_func` and `my_obj.method`
        # Requires Python 3.9+
        func_name = ast.unparse(call_node.func)

        # 3. Extract positional and keyword arguments from the node
        pos_args = []
        kw_args = {}

        # Process positional arguments
        for arg_node in call_node.args:
            # literal_eval can evaluate nodes as well as strings
            try:
                pos_args.append(ast.literal_eval(arg_node))
            except ValueError:
                # If it's not a literal (like a variable), represent it as a string
                pos_args.append(ast.unparse(arg_node))

        # Process keyword arguments
        for kw_node in call_node.keywords:
            try:
                value = ast.literal_eval(kw_node.value)
            except ValueError:
                value = ast.unparse(kw_node.value)
            kw_args[kw_node.arg] = value
            
        return func_name, tuple(pos_args), kw_args

    except (SyntaxError, ValueError, AttributeError) as e:
        raise ValueError(f"Failed to parse function call string: {e}")

if __name__ == '__main__':
    print(parse_function_call('module.func("arg", kwarg="val")'))