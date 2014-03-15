test:
	py.test  -rxs --cov . --cov-report term-missing

clean:
	rm -rf build/
