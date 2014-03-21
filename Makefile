test:
	py.test  -rxs --cov imhotep --cov-report term-missing -k imhotep imhotep

clean:
	rm -rf build/

upload:
	python setup.py sdist upload
