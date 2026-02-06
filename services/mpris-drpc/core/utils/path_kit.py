import os

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, os.path.pardir, os.path.pardir, os.path.pardir))


def get_path(*paths):
    return os.path.join(PROJECT_ROOT, *paths)