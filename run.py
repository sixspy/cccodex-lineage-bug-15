import os

from waitress import serve

from app.main import create_app


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7400"))
    app = create_app()
    serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
