cd ${HOME_DIR}

alembic upgrade head
if [ $? -ne 0 ]; then
    echo "Run migrations failed"
    exit 1
fi

uvicorn "app:create_app" -h 0.0.0.0 --port 8000
