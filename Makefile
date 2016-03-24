test:
	py.test  -rxs --cov imhotep --cov-report term-missing -k imhotep imhotep --durations=3

clean:
	rm -rf build/

upload:
	python setup.py sdist upload
