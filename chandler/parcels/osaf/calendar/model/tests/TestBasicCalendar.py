""" Unit test for calendar data parcel
"""

import unittest, os

from model.persistence.FileRepository import FileRepository

from OSAF.calendar.model.CalendarEvent import CalendarEvent
from OSAF.calendar.model.CalendarEvent import CalendarEventFactory

from mx import DateTime

class SimpleTest(unittest.TestCase):
    """Simple calendar data parcel tests"""

    def setUp(self):
        """Creates a new repository and a factory. 
           Loads the schema and calendar """
        
        rootdir = os.environ['CHANDLERDIR']
        schemaPack = os.path.join(rootdir, 'model', 'packs', 'schema.pack')
        calendarPack = os.path.join(rootdir, 'parcels', 'OSAF',
                                    'calendar', 'model', 'calendar.pack')
        self.rep = FileRepository('test')
        self.rep.create()
        self.rep.loadPack(schemaPack)
        self.rep.loadPack(calendarPack)
        self.factory = CalendarEventFactory(self.rep)
    
    def testFactoryBasics(self):
        """Test that the basic factory method worked"""
        item = self.factory.NewItem()
        item.startTime
        item.endTime
        foundItem = self.rep.find(item.getPath())
        self.assert_(foundItem)
        self.assertEqual(foundItem.getUUID(), item.getUUID())

    def testEventBasics(self):
        """Test basic features of CalendarEvent class"""
        item = self.factory.NewItem()
        item.setAttribute("headline", "Test Event")
        self.assertEqual(item.headline, "Test Event")
        self.assertEqual(item.IsRemote(), False)

    def testGetDuration(self):
        """Test the duration property, GET"""
        item = self.factory.NewItem()
        item.startTime = DateTime.DateTime(2003, 1, 1, 10)
        item.endTime = DateTime.DateTime(2003, 1, 1, 11, 30)
        self.assertEqual(item.duration, DateTime.DateTimeDelta(0, 1.5))

    def testSetDuration(self):
        """Test the duration property, SET"""
        item = self.factory.NewItem()
        item.startTime = DateTime.DateTime(2003, 2, 2, 10)
        item.duration = DateTime.DateTimeDelta(0, 1.5)
        self.assertEqual(item.endTime, 
                         DateTime.DateTime(2003, 2, 2, 11, 30))

    def testChangeStartTime(self):
        """Test ChangeStartTime"""
        item = self.factory.NewItem()
        item.startTime = DateTime.DateTime(2003, 3, 3, 10)
        item.endTime = DateTime.DateTime(2003, 3, 3, 11, 30)
        self.assertEqual(item.duration, 
                         DateTime.DateTimeDelta(0, 1.5))
        item.ChangeStart(DateTime.DateTime(2003, 3, 4, 12, 45))
        self.assertEqual(item.duration, 
                         DateTime.DateTimeDelta(0, 1.5))
        self.assertEqual(item.startTime, 
                         DateTime.DateTime(2003, 3, 4, 12, 45))

    def tearDown(self):
        # Note: to use for diagnosis if a test fails
        self.rep.close(purge=True)

if __name__ == "__main__":
    unittest.main()

