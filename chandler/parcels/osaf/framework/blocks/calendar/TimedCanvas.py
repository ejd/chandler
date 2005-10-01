__copyright__ = "Copyright (c) 2004 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"
__parcel__ = "osaf.framework.blocks.calendar"

import wx

from application import schema
from datetime import datetime, timedelta, date, time
from CalendarCanvas import CalendarCanvasItem, CalendarBlock, wxCalendarCanvas, roundTo
from PyICU import FieldPosition, DateFormat, ICUtzinfo
import osaf.pim.calendar.Calendar as Calendar
from osaf.pim.calendar.TimeZone import TimeZoneInfo

from application.dialogs import RecurrenceDialog

class TimedEventsCanvas(CalendarBlock):

    def instantiateWidget(self):
        super(TimedEventsCanvas, self).instantiateWidget()
        return wxTimedEventsCanvas(self.parentBlock.widget)


class wxTimedEventsCanvas(wxCalendarCanvas):
    def __init__(self, parent, *arguments, **keywords):
        super(wxTimedEventsCanvas, self).__init__(parent, *arguments, **keywords)

        # @@@ rationalize drawing calculations...
        self.hourHeight = 40
        
        self._scrollYRate = 10
        
        self._bgSelectionStartTime = None
        self._bgSelectionEndTime = None
        
        # determines if we're dragging the start or the end of an event, usually
        # the end
        self._bgSelectionDragEnd = True

        self.size = self.GetSize()
        self.size.width -= wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.size.height = self.hourHeight * 24
        self.SetVirtualSize(self.size)

    def wxSynchronizeWidget(self):
        #print "%s rebuilding canvas items" % self
        # we sort the items so that when drawn, the later events are drawn last
        # so that we get proper stacking
        # print "TimedEventsCanvas.wxSynchronizeWidget()"
        currentRange = self.GetCurrentDateRange()
        self.visibleItems = list(self.blockItem.getItemsInRange(currentRange, 
                                                                timedItems=True))
        self._doDrawingCalculations()
        self.RebuildCanvasItems(resort=True)
        self.Refresh()

    def OnSize(self, event):
        # print "wxTimedEventsCanvas.OnSize()  to %s, %sx%s" %(self.GetPosition(), self.GetSize().width, self.GetSize().height)
        self._doDrawingCalculations()
            
        self.RebuildCanvasItems()
        self.Refresh()
        event.Skip()


    def OnInit(self):
        super (wxTimedEventsCanvas, self).OnInit()
        
        self.SetScrollRate(0, self._scrollYRate)
        self.Scroll(0, (self.hourHeight*7)/self._scrollYRate)
        
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

    def ScaledScroll(self, dx, dy):
        (scrollX, scrollY) = self.CalcUnscrolledPosition(0,0)
        scrollX += dx
        scrollY += dy
        
        # rounding ensures we scroll at least one unit
        if dy < 0:
            rounding = -self._scrollYRate
        else:
            rounding = self._scrollYRate

        scaledY = (scrollY // self._scrollYRate) + rounding
        self.Scroll(scrollX, scaledY)
        
    def _doDrawingCalculations(self):

        # @@@ magic numbers

        # FIXME: on wxPython-Mac v2.6.0, this returns negative and otherwise bogus dimension values: e.g., [-15, 960]
        #self.size = self.GetVirtualSize()
        self.size = self.GetSize()
        self.size.width -= wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        self.size.height = self.hourHeight * 24
        self.SetVirtualSize(self.size)

        self.dayHeight = self.hourHeight * 24

        drawInfo = self.blockItem.calendarContainer.calendarControl.widget
        self.xOffset = drawInfo.xOffset

        if self.blockItem.dayMode:
            self.dayWidth = drawInfo.middleWidth
        else:
            self.dayWidth = drawInfo.dayWidth
    
    def GetLocaleHourStrings(self, hourrange):
        """
        use PyICU to format the hour, because some locales
        use a 24 hour clock
        """
        timeFormatter = DateFormat.createTimeInstance()
        hourFP = FieldPosition(DateFormat.HOUR1_FIELD)
        dummyDate = date.today()
        defaultTzinfo = TimeZoneInfo.get(view=self.blockItem.itsView).default
        
        for hour in hourrange:
            timedate = time(hour=hour, tzinfo=defaultTzinfo)
            hourdate = datetime.combine(dummyDate, timedate)
            timeString = timeFormatter.format(hourdate, hourFP)
            (start, end) = (hourFP.getBeginIndex(),hourFP.getEndIndex())
            hourString = str(timeString)[start:end]
            yield hour, hourString

    def DrawBackground(self, dc):
        styles = self.blockItem.calendarContainer
        self._doDrawingCalculations()

        # Use the transparent pen for painting the background
        dc.SetPen(wx.TRANSPARENT_PEN)

        # Paint the entire background
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0, 0, self.size.width, self.size.height + 10)

        self.ShadeToday(dc)
        self.DrawBackgroundSelection(dc)

        # Set text properties for legend
        dc.SetTextForeground(styles.legendColor)
        dc.SetFont(styles.legendFont)

        # Draw the lines separating hours
        halfHourHeight = self.hourHeight/2

        # we'll need these for hour formatting
        for hour,hourString in self.GetLocaleHourStrings(range(24)):

            if hour > 0:
                # Draw the hour legend
                wText, hText = dc.GetTextExtent(hourString)
                dc.DrawText(hourString,
                            self.xOffset - wText - 5,
                            hour * self.hourHeight - (hText/2))
            
            # Draw the line between hours
            dc.SetPen(styles.majorLinePen)
            dc.DrawLine(self.xOffset,
                        hour * self.hourHeight,
                        self.size.width,
                        hour * self.hourHeight)

            # Draw the line between half hours
            dc.SetPen(styles.minorLinePen)
            dc.DrawLine(self.xOffset,
                        hour * self.hourHeight + halfHourHeight,
                        self.size.width,
                        hour * self.hourHeight + halfHourHeight)

        self.DrawDayLines(dc)
        
        legendBorderX = self.xOffset - self.legendBorderWidth/2
        pen = wx.Pen(styles.legendColor, self.legendBorderWidth)
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        
        # hardcode this for now - eventually this should be a preference
        workdayHourStart = 9 # 9am
        workdayHourEnd = 17  # 5pm
        
        dc.DrawLine(legendBorderX, workdayHourStart*self.hourHeight,
                    legendBorderX, workdayHourEnd * self.hourHeight + 1)
        

    def DrawBackgroundSelection(self, dc):
        styles = self.blockItem.calendarContainer
        # draw selection stuff (highlighting)
        if (self._bgSelectionStartTime and self._bgSelectionEndTime):
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(styles.selectionBrush)
            
            rects = \
                TimedCanvasItem.GenerateBoundsRects(self,
                                                    self._bgSelectionStartTime,
                                                    self._bgSelectionEndTime,	
                                                    self.dayWidth)
            for rect in rects:
                dc.DrawRectangleRect(rect)

    @staticmethod
    def sortByStartTime(item1, item2):
        """
        Comparison function for sorting, mostly by start time
        """
        dateResult = Calendar.datetimeOp(item1.startTime, 'cmp', item2.startTime)
        
        # when two items start at the same time, we actually want to show the
        # SHORTER event last, so that painting draws it on top
        if dateResult == 0:
            dateResult = Calendar.datetimeOp(item2.endTime, 'cmp', item1.endTime)
        return dateResult

    def RebuildCanvasItems(self, resort=False):
        if resort:
            self.visibleItems.sort(self.sortByStartTime)
        
        self.canvasItemList = []
        
        dragState = self.dragState
        if (dragState and
            dragState.currentDragBox):
            currentDragItem = dragState.currentDragBox.GetItem()
        else:
            currentDragItem = None
            
        currentDragBox = None

        # First generate a sorted list of TimedCanvasItems
        for item in self.visibleItems:
                                               
            canvasItem = TimedCanvasItem(item, self)
            self.canvasItemList.append(canvasItem)

            # if we're dragging, update the drag state to reflect the
            # newly rebuild canvasItem
            # (should probably happen in CollectionCanvas?)
            if currentDragItem is item:
                currentDragBox = dragState.currentDragBox = canvasItem

        # now generate conflict info
        self.CheckConflicts()

        # next, generate bounds rectangles for each canvasitem
        for canvasItem in self.canvasItemList:
            # drawing rects should be updated to reflect conflicts
            if (currentDragBox is canvasItem and
                currentDragBox.CanDrag()):

                (newStartTime, newEndTime) = self.GetDragAdjustedTimes()

                # override the item's start time for when the time string
                # is actually displayed in the time
                canvasItem.startTime = newStartTime
                
                canvasItem.UpdateDrawingRects(newStartTime, newEndTime)
            else:
                canvasItem.UpdateDrawingRects()
            
        # canvasItemList has to be sorted by depth
        # should be relatively quick because the canvasItemList is already
        # sorted by startTime. If no conflicts, this is an O(n) operation
        # (note that as of Python 2.4, sorts are stable, so this remains safe)
        self.canvasItemList.sort(key=TimedCanvasItem.GetIndentLevel)
        
    def DrawCells(self, dc):
        styles = self.blockItem.calendarContainer
        
        # Set up fonts and brushes for drawing the events
        dc.SetTextForeground(wx.BLACK)
        dc.SetBrush(wx.WHITE_BRUSH)

        selectedBoxes = []
        # finally, draw the items
        brushOffset = self.GetPlatformBrushOffset()
        for canvasItem in self.canvasItemList:

            item = canvasItem.GetItem()
            
            # save the selected box to be drawn last
            if item in self.blockItem.selection:
                selectedBoxes.append(canvasItem)
            else:
                canvasItem.Draw(dc, styles,  brushOffset, False)
            
        # now draw the current item on top of everything else
        for selectedBox in selectedBoxes:
            selectedBox.Draw(dc, styles, brushOffset, True)

    def CheckConflicts(self):
        for itemIndex, canvasItem in enumerate(self.canvasItemList):
            # since these are sorted, we only have to check the items 
            # that come after the current one
            for innerItem in self.canvasItemList[itemIndex+1:]:
                # we know we're done when we stop hitting conflicts
                # 
                # have a guarantee that innerItem.startTime >= item.endTime
                # Since item.endTime < item.startTime, we know we're
                # done
                if Calendar.datetimeOp(innerItem.GetItem().startTime, '>=',
                             canvasItem.GetItem().endTime):
                     break
                
                # item and innerItem MUST conflict now
                canvasItem.AddConflict(innerItem)
            
            # we've now found all conflicts for item, do we need to calculate
            # depth or anything?
            # first theory: leaf children have a maximum conflict depth?
            canvasItem.CalculateConflictDepth()

    def OnKeyPressed(self, event):
        # create an event here - unfortunately the panel can't get focus, so it
        # can't recieve keystrokes yet...
        pass
            
    # handle mouse related actions: move, resize, create, select
    
    def OnSelectItem(self, item):
        if item:
            # clear background selection when an existing item is selected
            self._bgSelectionStartTime = self._bgSelectionEndTime = None
        
        super(wxTimedEventsCanvas, self).OnSelectItem(item)
        
    def OnSelectNone(self, unscrolledPosition):
        selectedTime = self.getDateTimeFromPosition(unscrolledPosition)
        
        # only select something new if there's no existing selection, or if 
        # we're outside of an existing selection
        if (not self._bgSelectionStartTime or
            Calendar.datetimeOp(selectedTime, '<', self._bgSelectionStartTime) or
            Calendar.datetimeOp(selectedTime, '>', self._bgSelectionEndTime)):
            self._bgSelectionStartTime = self.getDateTimeFromPosition(unscrolledPosition)
            self._bgSelectionDragEnd = True
            self._bgSelectionEndTime = self._bgSelectionStartTime + \
                timedelta(hours=1)

        super(wxTimedEventsCanvas, self).OnSelectNone(unscrolledPosition)
        self.Refresh()

    def OnCreateItem(self, unscrolledPosition):
        # @@@ this code might want to live somewhere else, refactored
        
        # if a region is selected, then use that for the event span
        newTime, duration = self.GetNewEventTime(unscrolledPosition)
            
        event = self.CreateEmptyEvent(newTime, duration, False, False)

        # now try to insert the event onto the canvas without too many
        # redraws, and allow the user to start dragging if they are
        # still holding down the mouse button (doesn't quite work yet)
        
        canvasItem = TimedCanvasItem(event, self)
        
        # only problem here is that we haven't checked for conflicts
        canvasItem.UpdateDrawingRects()
        canvasItem.setResizeMode(canvasItem.RESIZE_MODE_END)
        return canvasItem

    def GetNewEventTime(self, unscrolledPosition=None):
        """
        Returns a reasonable startTime and duration for creation of an
        event, taking into account.
        """
        if (self._bgSelectionStartTime):
            # first try selection, if any
            newTime = self._bgSelectionStartTime
            duration = self._bgSelectionEndTime - newTime
            
        elif unscrolledPosition:
            newTime = self.getDateTimeFromPosition(unscrolledPosition)
            duration = timedelta(hours=1)
            
        else:
            # next try the current time today, if visible
            duration = timedelta(hours=1)
            
            now = datetime.today()
            startDay, endDay = self.blockItem.GetCurrentDateRange()
            if startDay <= now <= endDay:
                # if today is in view, try to create the time about an
                # hour from now.
                nowMinute = now.minute
                nowHour = now.hour
                newTime = now.replace(minute=roundTo(nowMinute,15),
                                      hour=nowHour + 1)
            elif self.blockItem.dayMode:
                # create the time at noon on the current day
                newTime = startDay + timedelta(hours=12)
                
            else:
                # finally, just throw it in the middle of the current view
                newTime = startDay + timedelta(days=3, hours=12)
                
        return newTime, duration
            

    def OnBeginResizeItem(self):
        self.StartDragTimer()
        
    def OnEndResizeItem(self):
        self.FinishDrag()
        self.StopDragTimer()
        self.dragState.originalDragBox.ResetResizeMode()
        
    def OnResizingItem(self, unscrolledPosition):
        self.RebuildCanvasItems()
        self.Refresh()
    
    def OnDragTimer(self):
        """
        This timer goes off while we're dragging/resizing
        """
        scrolledPosition = self.CalcScrolledPosition(self.dragState.currentPosition)
        self.ScrollIntoView(scrolledPosition)
    
    def StartDragTimer(self):
        self.scrollTimer = wx.PyTimer(self.OnDragTimer)
        self.scrollTimer.Start(100, wx.TIMER_CONTINUOUS)
    
    def StopDragTimer(self):
        self.scrollTimer.Stop()
        self.scrollTimer = None
        
    def OnBeginDragItem(self):
        self.StartDragTimer()

    def FinishDrag(self):
        currentCanvasItem = self.dragState.currentDragBox
        if not currentCanvasItem.CanDrag():
            return

        proxy = RecurrenceDialog.getProxy(u'ui', currentCanvasItem.GetItem())
        
        (startTime, endTime) = self.GetDragAdjustedTimes()
        duration = endTime - startTime
        proxy.duration = duration
        proxy.startTime = startTime
        
    def OnEndDragItem(self):
        e = None
        try:
            self.FinishDrag()
        finally:
            # make sure the drag timer stops no matter what!
            self.StopDragTimer()
        self.RebuildCanvasItems()
        self.Refresh()
        
    def OnDraggingNone(self, unscrolledPosition):
        dragDateTime = self.getDateTimeFromPosition(unscrolledPosition)
        if self._bgSelectionDragEnd:
            self._bgSelectionEndTime = dragDateTime
        else:
            self._bgSelectionStartTime = dragDateTime
            
        if Calendar.datetimeOp(self._bgSelectionEndTime, '<',
                self._bgSelectionStartTime):
            # swap values, drag the other end
            self._bgSelectionDragEnd = not self._bgSelectionDragEnd
            (self._bgSelectionStartTime, self._bgSelectionEndTime) = \
                (self._bgSelectionEndTime, self._bgSelectionStartTime)
        self.Refresh()
            
        
    def OnDraggingItem(self, unscrolledPosition):
        self.RebuildCanvasItems()
        self.Refresh()

    def GetDragAdjustedStartTime(self, tzinfo):
        """
        When a moving drag is originated within a canvasItem, the drag
        originates from a point within the canvasItem, represented by
        dragOffset

        During a drag, you need to put a canvasItem at currentPosition,
        but you also want to make sure to round it to the nearest dayWidth,
        so that the event will sort of stick to the current column until
        it absolutely must move
        """
        dx,dy = self.dragState.dragOffset
        dx = roundTo(dx, self.dayWidth)
        
        position = self.dragState.currentPosition - (dx, dy)

        return self.getDateTimeFromPosition(position, tzinfo=tzinfo)

    def GetDragAdjustedTimes(self):
        """
        Return a new start/end time for the currently selected event, based
        on the current position and drag state. Handles both move and
        resize drags
        """
        item = self.dragState.originalDragBox.GetItem()
        resizeMode = self.dragState.originalDragBox.resizeMode
        if resizeMode is None:
            # moving an item, need to adjust just the start time
            # for the relative position of the mouse in the item
            newStartTime = self.GetDragAdjustedStartTime(item.startTime.tzinfo)
            newEndTime = newStartTime + item.duration

        # top/bottom resizes: just set the appropriate start/end
        # to where the mouse is
        elif resizeMode == TimedCanvasItem.RESIZE_MODE_START:
            newStartTime = \
                self.getDateTimeFromPosition(self.dragState.currentPosition,
                                             tzinfo=item.startTime.tzinfo)
            newEndTime = item.endTime
            # getDateTimeFromPosition always sets a non-None tzinfo, even if
            # it's passed tzinfo=None, so newEndTime needs a timezone, too
            if newEndTime.tzinfo is None:
                newEndTime = newEndTime.replace(tzinfo=newStartTime.tzinfo)
            
        elif resizeMode == TimedCanvasItem.RESIZE_MODE_END:
            newEndTime = \
                self.getDateTimeFromPosition(self.dragState.currentPosition,
                                             tzinfo=item.endTime.tzinfo)
            newStartTime = item.startTime
            # getDateTimeFromPosition always sets a non-None tzinfo, even if
            # it's passed tzinfo=None, so newEndTime needs a timezone, too
            if newStartTime.tzinfo is None:
                newStartTime = newStartTime.replace(tzinfo=newEndTime.tzinfo)

        if newEndTime < newStartTime:
            newEndTime = newStartTime + timedelta(minutes=15)

        return (newStartTime, newEndTime)
                    
    def getRelativeTimeFromPosition(self, drawInfo, position):
        """
        Get just the hours/minutes from the canvas
        """
        deltaHours = position.y / self.hourHeight
        deltaMinutes = ((position.y % self.hourHeight) * 60) / self.hourHeight
        deltaMinutes = roundTo(deltaMinutes, 15)
        return timedelta(hours=deltaHours, minutes=deltaMinutes)
        
    def getPositionFromDateTime(self, datetime):
        (startDay, endDay) = self.GetCurrentDateRange()
        
        if datetime.tzinfo is None:
            datetime = datetime.replace(tzinfo=ICUtzinfo.getDefault())
        else:
            datetime = datetime.astimezone(ICUtzinfo.getDefault())
            
        if datetime.date() < startDay.date() or \
           datetime.date() > endDay.date():
            raise ValueError, "Must be visible on the calendar"
        
        delta = Calendar.datetimeOp(datetime, '-', startDay)
        x = (self.dayWidth * delta.days) + self.xOffset
        y = int(self.hourHeight * (datetime.hour + datetime.minute/float(60)))
        return wx.Point(x, y)

class TimedCanvasItem(CalendarCanvasItem):
    resizeBufferSize = 5
    textMargin = 3
    
    RESIZE_MODE_START = 1
    RESIZE_MODE_END = 2
    
    def __init__(self, item, calendarCanvas, *arguments, **keywords):
        super(TimedCanvasItem, self).__init__(None, item)
        
        # this is really annoying that we need to keep a reference back to 
        # the calendar canvas in every single TimedCanvasItem, but we
        # need it for drawing hints.. is there a better way?
        self._calendarCanvas = calendarCanvas

    def UpdateDrawingRects(self, startTime=None, endTime=None):

        # allow caller to override start/end time
        item = self.GetItem()
        
        if not startTime:
            startTime = item.startTime
            
        if not endTime:
            endTime = item.endTime
       
        dayWidth = self._calendarCanvas.dayWidth
        if self._calendarCanvas.blockItem.dayMode:
            # in day mode, canvasitems are drawn side-by-side	
            maxDepth = self.GetMaxDepth()	
            width = dayWidth / (maxDepth + 1)	
            indent = width * self.GetIndentLevel()	
        else:	
            # in week mode, stagger the canvasitems by 5 pixels            
            indent = self.GetIndentLevel() * 5
            width = dayWidth - self.GetMaxDepth() * 5

        self._boundsRects = list(self.GenerateBoundsRects(self._calendarCanvas,
                                                          startTime, endTime,
                                                          width, indent))
        self._bounds = self._boundsRects[0]

        r = self._boundsRects[-1]
        self._resizeLowBounds = wx.Rect(r.x, r.y + r.height - self.resizeBufferSize,
                                        r.width, self.resizeBufferSize)
        
        r = self._boundsRects[0]
        self._resizeTopBounds = wx.Rect(r.x, r.y,
                                        r.width, self.resizeBufferSize)

    def GetBoundsRects(self):
        return self._boundsRects

    def isHitResize(self, point):
        """
        Hit testing of a resize region.
        
        @param point: point in unscrolled coordinates
        @type point: wx.Point
        @return: True if the point hit the resize region
        @rtype: Boolean
        """
        return (self._resizeTopBounds.Inside(point) or
                self._resizeLowBounds.Inside(point))

    def isHit(self, point):
        """
        User may have clicked in any of the possible bounds
        """
        for rect in self._boundsRects:
            if rect.Inside(point):
                return True
        return False

    def getResizeMode(self, point):
        """
        Returns the mode of the resize, either RESIZE_MODE_START or
        RESIZE_MODE_END.

        The resize mode is RESIZE_MODE_START if dragging from the top of the
        event, and RESIZE_MODE_END if dragging from the bottom of the
        event. None indicates that we are not resizing at all.

        The whole _forceResizeMode is to make sure that we stay in the same
        mode during a drag, even if we mouseover another region that would
        cause a different drag mode

        AF: This should really be handled automatically by the dragging code

        @param point: drag start position in uscrolled coordinates
        @type point: wx.Point
        @return: resize mode, RESIZE_MODE_START, RESIZE_MODE_END or None
        @rtype: string or None
        """
        
        if hasattr(self, '_forceResizeMode'):
            return self._forceResizeMode
            
        if self._resizeTopBounds.Inside(point):
            return self.RESIZE_MODE_START
        if self._resizeLowBounds.Inside(point):
            return self.RESIZE_MODE_END
        return None
        
    def setResizeMode(self, mode):
        self._forceResizeMode = mode

    def ResetResizeMode(self):
        if hasattr(self, '_forceResizeMode'):
            del self._forceResizeMode

    def StartDrag(self, position):
        self.resizeMode = self.getResizeMode(position)
    
    @staticmethod
    def GenerateBoundsRects(calendarCanvas, startTime, endTime, width, indent=0):
        """
        Generate a bounds rectangle for each day period. For example, an event
        that goes from noon monday to noon wednesday would have three bounds rectangles::
            one from noon monday to midnight
            one for all day tuesday
            one from midnight wednesday morning to noon wednesday
        """

        # calculate how many unique days this appears on 
        defaultTzinfo = ICUtzinfo.getDefault()
        
        if startTime.tzinfo is None:
            startTime = startTime.replace(tzinfo=defaultTzinfo)
        else:
            startTime = startTime.astimezone(defaultTzinfo)


        if endTime.tzinfo is None:
            endTime = endTime.replace(tzinfo=defaultTzinfo)
        else:
            endTime = endTime.astimezone(defaultTzinfo)
        
        # Safe to do comparison here because we've made sure
        # that neither datetime is naive
        days = 1 + (endTime.date() - startTime.date()).days
        
        currentDayStart = datetime.combine(startTime, 
                            time(tzinfo=startTime.tzinfo))
        for i in xrange(days):
            
            # first calculate the midnight time for the beginning and end
            # of the current day
            currentDayEnd = currentDayStart + timedelta(days=1)
            
            # ok to use min, max, since startTime, endTime are not naive
            boundsStartTime = max(startTime, currentDayStart)
            boundsEndTime = min(endTime, currentDayEnd)
            
            try:
                rect = TimedCanvasItem.MakeRectForRange(calendarCanvas,
                                                           boundsStartTime,
                                                           boundsEndTime)
                rect.x += indent
                rect.width = width
                yield rect
            except ValueError:
                pass
                
            currentDayStart = currentDayEnd
        
    @staticmethod
    def MakeRectForRange(calendarCanvas, startTime, endTime):
        """
        Turn a datetime range into a rectangle that can be drawn on the screen
        This is a static method, and can be used outside this class
        """
        startPosition = calendarCanvas.getPositionFromDateTime(startTime)
        
        # ultimately, I'm not sure that we should be asking the calendarCanvas
        # directly for dayWidth and hourHeight, we probably need some system 
        # instead similar to getPositionFromDateTime where we pass in a duration
        duration = (endTime - startTime)
        duration = duration.days * 24 + duration.seconds / float(3600)
        if duration == 0:
            duration = 0.5;
        (cellWidth, cellHeight) = \
                    (calendarCanvas.dayWidth,
                     int(duration * calendarCanvas.hourHeight))
        
        return wx.Rect(startPosition.x, startPosition.y, cellWidth, cellHeight)

