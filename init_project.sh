git init

poetry install --no-root
pre-commit install
pre-commit run --all-files

echo ""
echo "Remember to finish TODOs"
echo ""
grep -r "TODO:" .
