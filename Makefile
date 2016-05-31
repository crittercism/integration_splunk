INTEGRATION = crittercism_integration
INTEGRATION_TAR = apteligent-crittercism-mobile-application-intelligence_12.spl

test: 
	virtualenv venv; \
	source venv/bin/activate; \
	pip install -r requirements.txt; \
	cd bin; \
	nosetests -v test.py

release: export COPYFILE_DISABLE = true
release:
	mkdir $(INTEGRATION)
	cp LICENSE.md $(INTEGRATION)/LICENSE.md
	cp README.md $(INTEGRATION)/README.md
	cp -r appserver $(INTEGRATION)/appserver
	cp -r bin $(INTEGRATION)/bin
	cp -r default $(INTEGRATION)/default
	cp -r metadata $(INTEGRATION)/metadata
	cp -r static $(INTEGRATION)/static
	find $(INTEGRATION)/ -name "*.pyc" -delete; \
	find $(INTEGRATION)/ -name ".*" -print0 | xargs -0 rm -r; \
	tar -czf $(INTEGRATION_TAR) $(INTEGRATION)/
	rm -rf $(INTEGRATION)/
