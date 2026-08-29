"""Entry point: `python app.py` continua sendo o comando de execução do projeto."""
from src.app import create_app
from src.config.settings import settings

app = create_app()

if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
