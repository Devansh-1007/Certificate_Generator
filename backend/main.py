"""
App entrypoint. Routes live in routes/ (blueprints), auth in middleware.py,
domain objects in models.py, SQL migrations in db/migrations/.
"""

import logging

from flask import Flask
from flasgger import Swagger
from flask_cors import CORS

from routes.clientRoutes import client_bp
from routes.certificateRoutes import certificate_bp
from routes.idRoutes import id_bp
from routes.templateRoutes import templates_bp
from routes.bulkRoutes import bulk_bp

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["SWAGGER"] = {
    "title": "Certificate Generator API",
    "description": "Endpoints for client auth, certificate/ID generation, and AI template design.",
    "version": "2.0.0",
    "template": {
        "info": {
            "contact": {
                "name": "Devansh Choudhary",
                "url": "https://www.linkedin.com/in/devansh-choudhary-ba68a3226/",
                "email": "choudhary.devansh1007@gmail.com",
            }
        }
    },
    "license": {
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
    },
}
swagger = Swagger(app)
CORS(app)

app.register_blueprint(client_bp)
app.register_blueprint(certificate_bp)
app.register_blueprint(id_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(bulk_bp)


if __name__ == "__main__":
    app.run(debug=True)
