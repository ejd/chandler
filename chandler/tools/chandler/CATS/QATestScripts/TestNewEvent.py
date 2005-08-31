import osaf.framework.scripting.QAUITestAppLib as QAUITestAppLib
import os

filePath = os.path.expandvars('$CATSREPORTDIR')
if not os.path.exists(filePath):
    filePath = os.getcwd()

#initialization
fileName = "TestNewEvent.log"
logger = QAUITestAppLib.QALogger(os.path.join(filePath, fileName),"TestNewEvent")
event = QAUITestAppLib.UITestItem(app_ns().itsView, "Event", logger)

#action
event.logger.Start("setting calendar attributes")
event.SetAttr(displayName="Birthday Party", startDate="09/12/2004", startTime="6:00 PM", location="Club101", status="FYI",body="This is a birthday party invitation")
event.logger.Stop()

#verification
event.Check_DetailView({"displayName":"Birthday Party","startDate":"9/12/04","endDate":"9/12/04","startTime":"6:00 PM","endTime":"7:00 PM","location":"Club101","status":"FYI","body":"This is a birthday party invitation"})

#cleaning
logger.Close()
