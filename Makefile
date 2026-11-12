.PHONY: build offline test

build:
	python -m thesis build

offline:
	python -m thesis build --offline

test:
	python -m pytest -q
