.PHONY: build
build:
	PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pipenv_to_requirements
	pipenv run pip3 install -e .

.PHONY: test
test:
	pipenv run pytest

.PHONY: qa-test
qa-test: build
	pipenv run pytest tests/acceptance/qa.py

.PHONY: clean
clean:
	rm -rf *.egg-info dist build

.PHONY: release
release:
	@echo 'Releasing bento'
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*