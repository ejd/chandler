#   Copyright (c) 2003-2007 Open Source Applications Foundation
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

# item package


class Indexable(object):
    'A superclass for values that implement their full text indexing.'    

    def isIndexed(self):
        raise NotImplementedError, '%s.isIndexed' %(type(self))

    def indexValue(self, view, uItem, uAttribute, uValue, version):
        raise NotImplementedError, '%s.indexValue' %(type(self))
