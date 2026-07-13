import os

# absolute path to swagger_docs so swag_from works from inside blueprints
SWAGGER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "swagger_docs"
)


def swagger_doc(name):
    return os.path.join(SWAGGER_DIR, name)
