#   Copyright (c) 2006-2007 Open Source Applications Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from setuptools import setup

setup(
    name = "Chandler-p2pPlugin",
    version = "0.1",
    description = "Peer to peer collection sharing for Chandler",
    author = "OSAF",
    test_suite = "p2p.tests",
    packages = ["p2p"],
    include_package_data = True,
    entry_points = {
        "chandler.parcels": ["p2p = p2p"]
    },
    classifiers = ["Development Status :: 3 - Alpha",
                   "Environment :: Plugins",
                   "Framework :: Chandler",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Office/Business :: Groupware"],
    long_description = open('README.txt').read(),
)

