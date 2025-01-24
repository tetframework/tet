Running all test suites 

We need dependencies for the tests
```
pip install -e '.[test]'
```

Run all tests
```bash 
pytest --verbose -rP -vv -s
```
Ignore DeprecationWarning
```bash
pytest --verbose -rP -vv -s -W ignore::DeprecationWarning
```

Run it as a module if you have a problem with the path
```bash
python -m pytest ./tests --verbose -rP -vv -s
```
