from flask import Flask


def create_app():
    app = Flask(__name__)

    # регистрируем маршруты
    from app.web.routes import web_bp

    app.register_blueprint(web_bp)

    return app


app = create_app()
