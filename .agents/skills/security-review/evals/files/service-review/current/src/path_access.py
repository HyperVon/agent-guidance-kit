import os


ROOT = "/srv/files"


def read_requested(name):
    path = os.path.join(ROOT, name)
    with open(path, "rb") as stream:
        return stream.read()
