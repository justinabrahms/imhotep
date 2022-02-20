test: env
	env/bin/py.test  -rxs --cov imhotep --cov-report term-missing -k imhotep imhotep --durations=3

clean:
	rm -rf build/

upload: test
	env/bin/python setup.py sdist upload

env:
	python -m venv env
	env/bin/pip install -r requirements.txt
