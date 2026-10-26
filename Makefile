.PHONY: test check-clean package help

help:
	@echo "Available commands:"
	@echo "  make test         - Run full pytest regression and backend suite"
	@echo "  make check-clean  - Run CI check verifying no secrets, DBs, or storage files tracked"
	@echo "  make package      - Build clean distribution zip excluding .env, *.db*, storage_data, node_modules"

test:
	python -m pytest backend/tests/test_security_regressions.py -v

check-clean:
	python scripts/check_clean_repo.py

package:
	python scripts/package.py
