VERSION := $(shell cat ./src/jule/__init__.py | grep VERSION | sed 's/VERSION = //' | sed -e "s/'//g")

IMAGE_VERSION := $(VERSION)
WHEEL_VERSION := $(VERSION)

SRC_ROOT          := ./src/
SRC               := $(shell find $(SRC_ROOT) -type f -name '*.py' -not -name '*_test.py')
PYTHON            := python3
FLAKE8            := flake8
INCLUDE_TTYD      := n  # override via make arguments (make INCLUDE_TTYD=y)

# add extra files
SRC := $(SRC) requirements.txt requirements-dev.txt
SRC := $(SRC) setup.py

default: lint dist

PHONY: lint
lint: lint.done

lint.done: $(SRC) .flake8
	$(FLAKE8) $(SRC_ROOT)
	touch lint.done

dist/jule-$(WHEEL_VERSION)-py3-none-any.whl: $(SRC)
	$(info *** SRC UPDATED -> REBUILD WHEEL: $?)
	$(PYTHON) -m build --wheel

.PHONY: dist/whl
dist/whl: dist/jule-$(WHEEL_VERSION)-py3-none-any.whl

.PHONY: dist
dist: dist/whl

.PHONY: clean
clean:
	rm -rf dist
	rm -rf build

.PHONY: list
list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'