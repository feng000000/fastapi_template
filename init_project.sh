

if [ -d ".git" ]; then
    echo ".git directory exists."
else
    echo "git init..."
    git init
fi

poetry install --no-root
pre-commit install
pre-commit run --all-files

echo ""
echo "Remember to finish TODOs"
echo ""
grep -r "TODO:" .
