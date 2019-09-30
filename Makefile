.PHONY: build
build:
	@echo 'Building bento via `build.sh`'
	@/bin/bash build.sh

.PHONY: test
test:
	pipenv run pytest

.PHONY: clean
clean:
	rm -rf *.egg-info dist build

.PHONY: release
release:
	@echo 'Releasing bento'
	python3 setup.py sdist bdist_wheel
	python3 -m twine upload dist/*