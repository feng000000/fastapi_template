cd ${HOME_DIR}

alembic upgrade head
if [ $? -ne 0 ]; then
    echo "Run migrations failed"
    exit 1
fi

uvicorn "app:create_app" --host 0.0.0.0 --port 8000 --workers 4 --factory
