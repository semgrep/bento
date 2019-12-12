.PHONY: build
build:
	PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pipenv_to_requirements
	pipenv run pip3 install -e .

.PHONY: test
test:
	pipenv run pytest

.PHONY: qa-test
qa-test: build
	pipenv run pytest -s tests/acceptance/qa.py

.PHONY: env-test
env-test:
	docker build -f tests/acceptance/environments/python36.Dockerfile .

.PHONY: clean
clean:
	rm -rf *.egg-info dist build

.PHONY: package
package:
	@echo "Building Bento"
	PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pipenv_to_requirements
	python3 setup.py sdist bdist_wheel

.PHONY: release
release: package
	@echo "Releasing Bento"
	python3 -m twine upload dist/*