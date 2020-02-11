.PHONY: build
build:
	poetry install

.PHONY: test
test:
	poetry run pytest

.PHONY: qa-test
qa-test: build
	poetry run pytest -s tests/acceptance/qa.py

.PHONY: regenerate-tests
regenerate-tests:
	poetry run python tests/acceptance/qa.py

.PHONY: env-test
env-test:
	docker build -f tests/acceptance/environments/python36.Dockerfile -t bento-env-36 .
	docker run -v /var/run/docker.sock:/var/run/docker.sock bento-env-36 pytest tests/acceptance/qa.py

.PHONY: clean
clean:
	rm -rf dist

.PHONY: package
package:
	@echo "Building Bento"
	poetry build

.PHONY: release
release: package
	@echo "Releasing Bento"
	poetry publish
