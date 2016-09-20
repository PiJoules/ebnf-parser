python setup.py bdist_wheel
wheel install dist/parser_gen-?.?.?-py?-none-any.whl --force
wheel install-scripts parser_gen
python setup.py develop

