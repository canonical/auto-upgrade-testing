# Helpful doc: http://pep8.readthedocs.org/en/latest/intro.html#error-codes
#!/bin/bash
RED='\033[0;31m'
GREEN='\033[0;32m'

OUTPUT=flake8_output.txt
if [ -f $OUTPUT ]; then
    rm $OUTPUT
fi

python3 -m flake8 --output-file=$OUTPUT .

result=$?
if [ $result != 0 ]; then
    echo -e -n "${RED}Flake8 errors. Check flake8 output for more information\n"
    cat $OUTPUT
    exit 1;
else
    echo -e -n "${GREEN}Congratulations!!! Static check PASSED\n"
fi
