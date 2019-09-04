# Copyright 2019 Jonathan T. Moore
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

all: $(LAMBDA)-$(VERSION).zip

.dep: requirements.txt
	pip install -r requirements.txt -t .
	touch .dep

$(LAMBDA)-$(VERSION).zip: .dep handler.py downloader.py
	python3 -m compileall .
	rm -f $(LAMBDA)-$(VERSION).zip
	zip -r $(LAMBDA)-$(VERSION).zip . -x .git/\* -x \.* -x \*~ -x Makefile -x ci/\* -x venv/\*

clean:
	rm -f *.pyc $(LAMBDA)-$(VERSION).zip *~

distclean: clean
	rm -fr bin *.dist-info boto3 botocore certifi chardet concurrent
	rm -fr dateutil docutils idna jmespath requests s3transfer
	rm -fr wowclient urllib3 six.py
	rm -f .dep

depend: .dep
