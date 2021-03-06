#   Copyright (c) 2003-2008 Open Source Applications Foundation
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

import tools.QAUITestAppLib as QAUITestAppLib

# initialization
fileName = "PerfLargeDataNewEventFileMenu.log"
logger = QAUITestAppLib.QALogger(fileName, "Creating new event from the File Menu after large data import") 

try:
    # creation
    QAUITestAppLib.UITestView(logger)#, u'Generated3000.ics')

    # action
    event = QAUITestAppLib.UITestItem("Event", logger)
    
    # verification
    event.Check_DetailView({"displayName":"New Event"})
    
finally:
    # cleaning
    logger.Close()
