.PHONY: format lint test build clean check
.DEFAULT_GOAL := check

# Package-scoped tasks. mise resolves the package from this directory through
# package:current, so the package name does not need to be passed explicitly.
format:
	mise run format
lint:
	mise run lint
test:
	mise run test
build:
	mise run build
clean:
	mise run clean
check:
	mise run format
	mise run lint
	mise run test
