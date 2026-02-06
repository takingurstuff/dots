import json
import logging
from typing import Literal, Callable, Any

from core.constants import log_level
from core.model.config import Config
from core.utils.module_kit import get_callable_by_id
from core.model.matcher import Matcher, AlwaysTrue, parse_function_call

log = logging.getLogger(__name__)
log.setLevel(log_level)

matchers: list[tuple[Matcher, Callable[..., dict[str, Any]], tuple[Any], dict[str, Any]]] = []

def initialize_matchers(config: Config):
    global matchers
    for rule, func in config.metadata_ruleset.items():
        matcher = Matcher(config, rule) if rule != 'always' else AlwaysTrue()
        fn_name, args, kwargs = parse_function_call(func)
        handler = get_callable_by_id(fn_name, config.plugin_paths)
        matchers.append((matcher, handler, args, kwargs))


def metadata_process(config: Config, metadata: dict[str, Any]) -> dict[str, Any]:
    log.debug('Starting Module Execution')
    metadata = metadata.copy()
    global matchers
    if not matchers:
        initialize_matchers(config)

    for matcher, handler, args, kwargs in matchers:
        if matcher.evaluate(metadata):
            metadata = handler(metadata, log, *args, **kwargs)

    log.debug('Finished Module Execution')

    return metadata

