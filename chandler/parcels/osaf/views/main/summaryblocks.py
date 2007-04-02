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


from application import schema, styles
from osaf.framework.blocks import *
from osaf import pim
from osaf.framework import attributeEditors
from util.MultiStateButton import BitmapInfo, MultiStateBitmapCache
from application.dialogs import RecurrenceDialog
from i18n import ChandlerMessageFactory as _
import wx.grid

CommunicationStatus = pim.mail.CommunicationStatus

# IndexDefinition subclasses for the dashboard indexes
#
# Most fall back on the triage ordering if their primary terms are equal;
# they inherit from this:
class TriageColumnIndexDefinition(pim.MethodIndexDefinition):
    findParams = [
        # We'll return one pair of these or the other, depending on whether
        # sectionTriageStatus exists on the item.
        ('_triageStatus', pim.TriageEnum.now),
        ('_triageStatusChanged', 0),
        ('_sectionTriageStatus', None),
        ('_sectionTriageStatusChanged', 0),
    ]

    def loadIndexValues(self, uuid, params):
        """ 
        Like findValues, except it assumes that the last four 
        values are the triage attributes listed above; it'll
        remove the pair we're not supposed to use.
        """
        values = self.itsView.findInheritedValues(uuid, *params)
        # We'll use sectionTriageStatus if it's there, else triageStatus
        if values[-2] is None:  # no sectionTriageStatus
            return values[0:-2] # just use triageStatus for ordering.
        return values[:-4] + values[-2:] # remove the triageStatus entries

    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            triage, triageChanged = \
                self.loadIndexValues(uuid, TriageColumnIndexDefinition.findParams)                    
            return (triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class TaskColumnIndexDefinition(TriageColumnIndexDefinition):
    findParams = [
        (pim.Stamp.stamp_types.name, []),
        ('displayName', u''),
    ] + TriageColumnIndexDefinition.findParams
    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            stamp_types, displayName, triage, triageChanged = \
                self.loadIndexValues(uuid, TaskColumnIndexDefinition.findParams)
            return (pim.TaskStamp in stamp_types, displayName, triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class CommunicationColumnIndexDefinition(TriageColumnIndexDefinition):
    def compare(self, u1, u2):
        def getCompareTuple(uuid):                            
            triage, triageChanged = \
                self.loadIndexValues(uuid, TriageColumnIndexDefinition.findParams)
            commState = CommunicationStatus.getItemCommState(uuid, self.itsView)
            return (commState, triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))
    
class CalendarColumnIndexDefinition(TriageColumnIndexDefinition):
    findParams = [
        (pim.Stamp.stamp_types.name, []),
        (pim.Remindable.reminders.name, None),
        ('displayDate', pim.Reminder.farFuture),
    ] + TriageColumnIndexDefinition.findParams
    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            stamp_types, reminders, displayDate, triage, triageChanged = \
                self.loadIndexValues(uuid, CalendarColumnIndexDefinition.findParams)
            
            # We need to do this:
            #   hasUserReminder = item.getUserReminder(expiredToo=True) is not None
            # while avoiding loading the items. @@@ Note: This code matches the 
            # implementation of Remindable.getUserReminder - be sure to change 
            # that if you change this!
            
            def hasAUserReminder(remList):
                if remList is not None:
                    for reminderUUID in remList.iterkeys():
                        userCreated = self.itsView.findValue(reminderUUID, 'userCreated', False)
                        if userCreated:
                            return True
                return False
            hasUserReminder = hasAUserReminder(reminders)

            if hasUserReminder:
                reminderState = 0
            elif pim.EventStamp in stamp_types:
                reminderState = 1
            else:
                reminderState = 2
                
            return (reminderState, displayDate, triage, triageChanged)

        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class WhoColumnIndexDefinition(TriageColumnIndexDefinition):
    findParams = [
        ('displayWho', u''),
    ] + TriageColumnIndexDefinition.findParams
    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            displayWho, triage, triageChanged = \
                self.loadIndexValues(uuid, WhoColumnIndexDefinition.findParams)                    
            return (displayWho.lower(), triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class TitleColumnIndexDefinition(TriageColumnIndexDefinition):
    findParams = [
        ('displayName', u''),
    ] + TriageColumnIndexDefinition.findParams
    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            displayName, triage, triageChanged = \
                self.loadIndexValues(uuid, TitleColumnIndexDefinition.findParams)                    
            return (displayName.lower(), triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class DateColumnIndexDefinition(TriageColumnIndexDefinition):
    findParams = [
        ('displayDate', pim.Reminder.farFuture),
    ] + TriageColumnIndexDefinition.findParams
    def compare(self, u1, u2):
        def getCompareTuple(uuid):
            displayDate, triage, triageChanged = \
                self.loadIndexValues(uuid, DateColumnIndexDefinition.findParams)                    
            return (displayDate, triage, triageChanged)
        return cmp(getCompareTuple(u1), getCompareTuple(u2))

class WhoAttributeEditor(attributeEditors.StringAttributeEditor):
    def GetTextToDraw(self, item, attributeName):
        prefix, theText, isSample = \
            super(WhoAttributeEditor, self).GetTextToDraw(item, attributeName)
        
        if not isSample:
            # OVerride the prefix if we have one we recognize
            # (these are in order of how frequently I think they'll occur)
            # Note that there's a space at the end of each one, which separates
            # the prefix from the value.
            whoSource = getattr(item, 'displayWhoSource', '')
            if len(whoSource) > 0:
                if whoSource == 'creator': # ContentItem
                    prefix = _(u'cr ')
                #elif whoSource == '?': # @@@ not sure where 'edited by' will come from
                    #prefix = _(u'ed')
                #elif whoSource == '?': # @@@ not sure where 'updated by' will come from
                    #prefix = _(u'up')
                elif whoSource == 'to': # Mail
                    prefix = _(u'to ')
                elif whoSource == 'from': # Mail
                    prefix = _(u'fr ')
                elif whoSource == 'owner': # Flickr
                    prefix = _(u'ow ')
                elif whoSource == 'author': # Feeds
                    prefix = _(u'au ')
            
        return (prefix, theText, isSample)

class TriageAttributeEditor(attributeEditors.IconAttributeEditor):
    def makeStates(self):
        # The state name has the state in lowercase, which matches the "name"
        # attribute of the various TriageEnums. The state values are mixed-case,
        # which matches the actual icon filenames.
        states = [ BitmapInfo(stateName="Triage.%s" % s.lower(),
                       normal="Triage%s" % s,
                       selected="Triage%s" % s,
                       rollover="Triage%sRollover" % s,
                       rolloverselected="Triage%sRollover" % s,
                       mousedown="Triage%sMousedown" % s,
                       mousedownselected="Triage%sMousedown" % s)
                   for s in "Now", "Later", "Done" ]
        return states
        
    def GetAttributeValue(self, item, attributeName):
        # Determine what state this item is in. 
        value = item.triageStatus
        return value

    def mapValueToIconState(self, value):
        return "Triage.%s" % value.name
    
    def advanceState(self, item, attributeName):
        oldValue = item.triageStatus
        newValue = pim.getNextTriageStatus(oldValue)
        item.setTriageStatus(newValue, pin=True)
        item.resetAutoTriageOnDateChange()

class ReminderColumnAttributeEditor(attributeEditors.IconAttributeEditor):    
    def makeStates(self):
        states = [
            BitmapInfo(stateName="SumEvent.Unstamped",
                       normal=attributeEditors.IconAttributeEditor.noImage,
                       selected=attributeEditors.IconAttributeEditor.noImage,
                       rollover="EventTicklerRollover",
                       rolloverselected="EventTicklerRolloverSelected",
                       mousedown="EventTicklerMousedown",
                       mousedownselected="EventTicklerMousedownSelected"),
            BitmapInfo(stateName="SumEvent.Stamped",
                       normal="EventStamped",
                       selected="EventStampedSelected",
                       rollover="EventTicklerRollover",
                       rolloverselected="EventTicklerRolloverSelected",
                       mousedown="EventTicklerMousedown",
                       mousedownselected="EventTicklerMousedownSelected"),
            BitmapInfo(stateName="SumEvent.Tickled",
                       normal="EventTickled",
                       selected="EventTickledSelected",
                       rollover="EventTicklerRollover",
                       rolloverselected="EventTicklerRolloverSelected",
                       mousedown="EventTicklerMousedown",
                       mousedownselected="EventTicklerMousedownSelected"),
        ]
        return states
    
    def GetAttributeValue(self, item, attributeName):
        # We want the icon shown to match the date displayed in the date column,
        # so just pick a value based on the date we're displaying.
        displayDateSource = getattr(item, 'displayDateSource', None)
        if displayDateSource == 'reminder':
            return "SumEvent.Tickled"
        return displayDateSource == 'startTime' and \
               "SumEvent.Stamped" or "SumEvent.Unstamped"

    def SetAttributeValue(self, item, attributeName, value):
        # Don't bother implementing this - the only changes made in
        # this editor are done via advanceState
        pass
            
    def getToolTip(self, item, attributeName):
        state = self.GetAttributeValue(item, attributeName)
        if state == "SumEvent.Tickled":
            return _(u"Remove custom alarm")
        else:
            return _(u"Add custom alarm")
        return None

    def advanceState(self, item, attributeName):
        # If there is one, remove the existing reminder
        if item.getUserReminder(expiredToo=False) is not None:
            item.userReminderTime = None
            return

        # No existing one -- create one.
        # @@@ unless this is a recurring event, for now.
        if pim.has_stamp(item, pim.EventStamp) and pim.EventStamp(item).isRecurring():
            return # ignore the click.
        item.userReminderTime = pim.Reminder.defaultTime()
        
    def ReadOnly (self, (item, attribute)):
        """
        Until the Detail View supports read-only reminders, always allow
        reminders to be removed.
        
        """
        return False

# Each entry in this list corresponds to a row in the icon grid in 
# the spec. Each will have "Read", "Unread", and "NeedsReply" tacked on
# when we ask the domain model.       
statePairNames = (
    # Base name, True if it shows an icon when 'read'
    ("Plain", False),
    ("PlainDraft", True),
    ("InDraft", True),
    ("In", False),
    ("OutDraft", True),
    ("Out", False),
    ("OutdateDraft", True),
    ("Outdate", False),
    ("IndateDraft", True),
    ("Indate", False),
    ("Queued", True),
    ("Error", True),
)

def getCommStateName(commState):
    """ Return the actual name for this state """
    
    read = (commState & CommunicationStatus.READ) and "Read" or "Unread"
    needsReply = (commState & CommunicationStatus.NEEDS_REPLY) and "NeedsReply" or ""

    # These don't depend on in vs out, so check them first.
    if commState & CommunicationStatus.ERROR:
        return "Error%s%s" % (read, needsReply)
    if commState & CommunicationStatus.QUEUED:
        return "Queued%s%s" % (read, needsReply)
    
    # Note In vs Out (Out wins if both) vs Plain (if neither, we're done).
    if commState & CommunicationStatus.OUT:
        inOut = "Out"
        #  # and keep going...
    elif commState & CommunicationStatus.IN:
        inOut = "In"
        # and keep going...
    else:
        return "Plain%s%s" % (read, needsReply)
    
    # We're Out or In -- do Updating and Draft.
    updating = (commState & CommunicationStatus.UPDATE) and "date" or ""
    draft = (commState & CommunicationStatus.DRAFT) and "Draft" or ""    
    return "%s%s%s%s%s" % (inOut, updating, draft, read, needsReply)

        
class CommunicationsColumnAttributeEditor(attributeEditors.IconAttributeEditor):
    def makeStates(self):
        states = []
        def addState(name, **kwds):
            args = {}
            for state in ("Normal", "Selected", "Rollover", "RolloverSelected", 
                         "Mousedown", "MousedownSelected"):
                lcState = state.lower()
                if not kwds.has_key(lcState):
                    # If a given state isn't specified, build the name automatically
                    args[lcState] = "Mail%s%s" % (name, 
                                                  state != "Normal" and state or '')
                elif kwds[lcState] is None:
                    # If a given state is specified as None, use a blank image.
                    args[lcState] = attributeEditors.IconAttributeEditor.noImage
                else:
                    # Use the given name, but prepend "Mail" to it because that's
                    # how the files are named.
                    args[lcState] = "Mail%s" % kwds[lcState]
            states.append(BitmapInfo(stateName=name, **args))

        # Build pairs of states (Read and Unread)
        for name, hasRead in statePairNames:
            # Each pair has these variations in common
            args = { 
                'rollover': '%sRollover' % name,
                'rolloverselected': '%sRolloverSelected' % name,
                'mousedown': '%sMousedown' % name,
                'mousedownselected': '%sMousedownSelected' % name
            }
            
            # Do Unread
            addState("%sUnread" % name, selected='%sUnreadSelected' % name, 
                     **args)

            # Do Read, whether it has 'read' icon or not.
            if hasRead:
                addState("%sRead" % name, selected='%sReadSelected' % name, 
                         **args)
            else:
                addState("%sRead" % name, normal=None, selected=None, **args)
            
        # Do NeedsReply by itself
        addState("NeedsReply")

        return states

    def mapValueToIconState(self, state):
        # We use one set of icons for all the NeedsReply states.
        if state.find("NeedsReply") != -1:
            return "NeedsReply"
        return state
        
    def GetAttributeValue(self, item, attributeName):
        # Determine what state this item is in.
        return getCommStateName(CommunicationStatus(item).status)

    def SetAttributeValue(self, item, attributeName, value):
        # Don't bother implementing this - the only changes made in
        # this editor are done via advanceState
        pass

    def getNextValue(self, item, attributeName, currentValue):
        # Cycle through: Unread, Read, NeedsReply
        wasUnread = currentValue.find("Unread") != -1
        if currentValue.find("NeedsReply") != -1:
            if wasUnread:
                # Shouldn't happen (if it's needsReply, it oughta be read),
                # but map it to Unread anyway.
                return currentValue.replace("NeedsReply", "")
            return currentValue.replace("ReadNeedsReply", "Unread")
        # It wasn't needsReply. If it was "Unread", mark it "read"
        if wasUnread:
            return currentValue.replace("Unread", "Read")
        
        # Otherwise, it's Read -> ReadNeedsReply.
        return currentValue.replace("Read", "ReadNeedsReply")
    
    def getToolTip(self, item, attributeName):
        nextState = self.getNextValue(item, attributeName,
                                      self.GetAttributeValue(item, attributeName))
        if nextState.find("NeedsReply") != -1:
            return _(u"Mark as Needs reply")
        elif nextState.find("Unread") != -1:
            return _(u"Mark as Unread")
        return _(u"Mark as Read")

    def advanceState(self, item, attributeName):
        # changes to read/unread/needs reply should apply to all occurrences
        item = getattr(item, 'proxiedItem', item)
        item = pim.EventStamp(item).getMaster().itsItem
        
        oldState = self.GetAttributeValue(item, attributeName)
        if oldState.find("NeedsReply") != -1:
            item.read = False
            item.needsReply = False
        elif oldState.find("Unread") != -1:
            item.read = True
            item.needsReply = False
        else: # make it needs-reply (and make sure it's read).
            item.read = True
            item.needsReply = True
        
class TaskColumnAttributeEditor(attributeEditors.IconAttributeEditor):
    def _getStateName(self, isStamped):
        return isStamped and "SumTask.Stamped" or "SumTask.Unstamped"
        
    def makeStates(self):
        states = []
        for (state, normal, selected) in ((False, attributeEditors.IconAttributeEditor.noImage,
                                                  attributeEditors.IconAttributeEditor.noImage),
                                          (True, "TaskStamped",
                                                 "TaskStampedSelected")):
            bmInfo = BitmapInfo()
            bmInfo.stateName = self._getStateName(state)
            bmInfo.normal = normal
            bmInfo.selected = selected
            bmInfo.rollover = "TaskRollover"
            bmInfo.rolloverselected = "TaskRolloverSelected"
            bmInfo.mousedown = "TaskMousedown"
            bmInfo.mousedownselected = "TaskMousedownSelected"
            states.append(bmInfo)

        return states
    
    def GetAttributeValue(self, item, attributeName):
        isStamped = pim.has_stamp(item, pim.TaskStamp)
        return self._getStateName(isStamped)
    
    def SetAttributeValue(self, item, attributeName, value):
        isStamped = pim.has_stamp(item, pim.TaskStamp)
        if isStamped != (value == self._getStateName(True)):
            # Stamp or unstamp the item
            if isinstance(item, pim.TaskStamp.targetType()):
                stampedObject = pim.TaskStamp(item)
                if isStamped:
                    stampedObject.remove()
                else:
                    stampedObject.add()

    def getToolTip(self, item, attributeName):
        state = self.GetAttributeValue(item, attributeName)
        if state == "SumTask.Stamped":
            return _(u"Remove from task list")
        else:
            return _(u"Add to task list")
        return None

    def advanceState(self, item, attributeName):
        if not self.ReadOnly((item, attributeName)):
            isStamped = pim.has_stamp(item, pim.TaskStamp)
            newValue = self._getStateName(not isStamped)
            self.SetAttributeValue(item, attributeName, newValue)


def makeSummaryBlocks(parcel):
    from application import schema
    from i18n import ChandlerMessageFactory as _
    from osaf.framework.blocks.calendar import (
        CalendarContainer, CalendarControl, CanvasSplitterWindow,
        AllDayEventsCanvas, TimedEventsCanvas
        )

    from Dashboard import DashboardBlock
    
    view = parcel.itsView
    detailblocks = schema.ns('osaf.views.detail', view)
    pim_ns = schema.ns('osaf.pim', view)
    blocks = schema.ns('osaf.framework.blocks', view)
    main = schema.ns("osaf.views.main", view)
    repositoryView = parcel.itsView
    
    # Register our attribute editors.
    # If you edit this dictionary, please keep it in alphabetical order by key.
    aeDict = {
        'EventStamp': 'ReminderColumnAttributeEditor',
        'MailStamp': 'CommunicationsColumnAttributeEditor',
        'TaskStamp': 'TaskColumnAttributeEditor',
        'Text+who': 'WhoAttributeEditor',
        'TriageEnum': 'TriageAttributeEditor',
    }
    attributeEditors.AttributeEditorMapping.register(parcel, aeDict, __name__)
    
    
    iconColumnWidth = 23 # temporarily not 20, to work around header bug 6168    
    
    def makeColumnAndIndexes(colName, **kwargs):
        # Create an IndexDefinition that will be used later (when the user
        # clicks on the column header) to build the actual index.
        # By default, we always create index defs that will lazily create a
        # master index when the subindex is needed.
        indexName = kwargs['indexName']
        attributes = kwargs.pop('attributes', [])
        useCompare = kwargs.pop('useCompare', False)
        useMaster = kwargs.pop('useMaster', True)
        baseClass = kwargs.pop('baseClass', pim.AttributeIndexDefinition)
        indexDefinition = baseClass.update(parcel, 
                                           indexName,
                                           useMaster=useMaster,
                                           attributes=attributes)

        # If we want master indexes precreated, here's where
        # to do it. (Initially turned on to help Andi with debugging
        # of bug 8319; turned off again because it made performance 
        # significantly worse.)
        if useMaster: indexDefinition.makeMasterIndex()
            
        # Create the column
        return Column.update(parcel, colName, **kwargs)

    taskColumn = makeColumnAndIndexes('SumColTask',
        icon='ColHTask',
        valueType = 'stamp',
        stamp=pim.TaskStamp,
        width=iconColumnWidth,
        useSortArrows=False,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_FIXED_SIZE,
        readOnly=True,
        indexName='%s.taskStatus' % __name__,
        baseClass=TaskColumnIndexDefinition,
        attributes=list(dict(TaskColumnIndexDefinition.findParams)),)

    commColumn = makeColumnAndIndexes('SumColMail',
        icon='ColHMail',
        valueType='stamp',
        stamp=pim.mail.MailStamp,
        width=iconColumnWidth,
        useSortArrows=False,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_FIXED_SIZE,
        readOnly=True,
        indexName=CommunicationStatus.status.name,
        attributeName=CommunicationStatus.status.name,
        baseClass=CommunicationColumnIndexDefinition,
        attributes=list(dict(TriageColumnIndexDefinition.findParams)) + \
                   list(dict(pim.mail.CommunicationStatus.attributeValues)),)

    whoColumn = makeColumnAndIndexes('SumColWho',
        heading=_(u'Who'),
        width=100,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_SCALABLE,
        readOnly=True,
        indexName='%s.displayWho' % __name__,
        attributeName='displayWho',
        attributeSourceName = 'displayWhoSource',
        format='who',
        baseClass=WhoColumnIndexDefinition,
        attributes=list(dict(WhoColumnIndexDefinition.findParams)),)
    
    titleColumn = makeColumnAndIndexes('SumColAbout',
        heading=_(u'Title'),
        width=120,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_SCALABLE,
        indexName='%s.displayName' % __name__,
        attributeName='displayName',
        baseClass=TitleColumnIndexDefinition,
        attributes=list(dict(TitleColumnIndexDefinition.findParams)),)

    reminderColumn = makeColumnAndIndexes('SumColCalendarEvent',
        icon = 'ColHEvent',
        valueType = 'stamp',
        stamp = pim.EventStamp,
        useSortArrows = False,
        width = iconColumnWidth,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_FIXED_SIZE,
        readOnly = True,
        indexName = '%s.calendarStatus' % __name__,
        baseClass=CalendarColumnIndexDefinition,
        attributes=list(dict(CalendarColumnIndexDefinition.findParams)) + \
                   ['displayDateSource'])

    dateColumn = makeColumnAndIndexes('SumColDate',
        heading = _(u'Date'),
        width = 100,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_SCALABLE,
        readOnly = True,
        attributeName = 'displayDate',
        attributeSourceName = 'displayDateSource',
        indexName = '%s.displayDate' % __name__,
        baseClass=DateColumnIndexDefinition,
        attributes=list(dict(DateColumnIndexDefinition.findParams)) + \
                   ['displayDateSource'])

    triageColumn = makeColumnAndIndexes('SumColTriage',
        icon = 'ColHTriageStatus',
        useSortArrows = False,
        defaultSort = True,
        width = 39,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_FIXED_SIZE,
        collapsedSections=set([str(pim.TriageEnum.later), str(pim.TriageEnum.done)]), 
        attributeName = 'sectionTriageStatus',
        indexName = '%s.triage' % __name__,
        baseClass=TriageColumnIndexDefinition,
        attributes=list(dict(TriageColumnIndexDefinition.findParams)))
        
    rankColumn = makeColumnAndIndexes('SumColRank',
        heading = _(u'Rank'),
        valueType = 'None',
        defaultSort = True,
        useSortArrows = False,
        useMaster = False,
        width = 46,
        scaleColumn = wx.grid.Grid.GRID_COLUMN_SCALABLE,
        readOnly = True,
        indexName ='%s.rank' % __name__,
        format='rank',
        baseClass = pim.NumericIndexDefinition,
        attributes = [])

    # Our detail views share the same delegate instance and contents collection
    detailBranchPointDelegate = detailblocks.DetailBranchPointDelegate.update(
        parcel, 'DetailBranchPointDelegateInstance',
        branchStub = detailblocks.DetailRoot)

    iconColumnWidth = 23 # temporarily not 20, to work around header bug 6168
    DashboardSummaryViewTemplate = SplitterWindow.template(
        'DashboardSummaryViewTemplate',
        eventBoundary = True,
        orientationEnum = "Vertical",
        splitPercentage = 0.65,
        childBlocks = [
            BoxContainer.template('DashboardSummaryContainer',
                orientationEnum = 'Vertical',
                childBlocks = [
                    DashboardBlock.template('DashboardSummaryView',
                        contents = pim_ns.allCollection,
                        scaleWidthsToFit = True,
                        columns = [
                            taskColumn,
                            commColumn,
                            whoColumn,
                            titleColumn,
                            reminderColumn,
                            dateColumn,
                            triageColumn                    
                        ],
                        characterStyle = blocks.SummaryRowStyle,
                        headerCharacterStyle = blocks.SummaryHeaderStyle,
                        prefixCharacterStyle = blocks.SummaryPrefixStyle,
                        sectionLabelCharacterStyle = blocks.SummarySectionLabelStyle,
                        sectionCountCharacterStyle = blocks.SummarySectionCountStyle,
                        rowHeight = 19,
                        elementDelegate = 'osaf.views.main.SectionedGridDelegate',
                        defaultEditableAttribute = u'displayName',
                        emptyContentsShow = False,
                        contextMenu = "ItemContextMenu"),
                    HTML.template('EmptyDashBoardView',
                        text = _(u'<html><body><center>&nbsp;<br>&nbsp;<br>This collection is empty</center></body></html>'),
                        treatAsURL = False,
                        emptyContentsShow = True)
                ]
            ),
            BranchPointBlock.template('DashboardDetailBranchPointBlock',
                delegate = detailBranchPointDelegate)
        ]).install(parcel) # SplitterWindow DashboardSummaryViewTemplate

    saveResultsEvent = AddToSidebarEvent.update(
        parcel, 'SaveResults',
        blockName = 'SaveResults',
        editAttributeNamed = 'displayName',
        sphereCollection = schema.ns('osaf.pim', repositoryView).mine,
        item = schema.ns('osaf.pim', view).searchResults)
        
    SplitterWindow.template(
        'SearchResultsViewTemplate',
        orientationEnum = "Vertical",
        splitPercentage = 0.65,
        eventBoundary = True,
        eventsForNamedLookup = [saveResultsEvent],
        childBlocks = [
            ToolbarItem.template('SaveResultsButton',
                event = saveResultsEvent,
                bitmap = 'ApplicationBarSave.png',
                title = _(u"Save"),
                toolbarItemKind = 'Button',
                location = "ApplicationBar",
                operation = 'InsertAfter',
                itemLocation = 'ApplicationBarQuickEntry',
                helpString = _(u'Save a copy of the results in the sidebar')),
            Table.template('SearchResultsSummaryView',
                contents = pim_ns.allCollection,
                scaleWidthsToFit = True,
                columns = [
                    rankColumn,
                    taskColumn,
                    commColumn,
                    whoColumn,
                    titleColumn,
                    reminderColumn,
                    dateColumn,
                    triageColumn                    
                ],
                characterStyle = blocks.SummaryRowStyle,
                prefixCharacterStyle = blocks.SummaryPrefixStyle,
                headerCharacterStyle = blocks.SummaryHeaderStyle,
                rowHeight = 19,
                elementDelegate = 'osaf.framework.blocks.ControlBlocks.AttributeDelegate',
                       defaultEditableAttribute = u'displayName',
                selection = [[0,0]]),
            BranchPointBlock.template('SearchResultsSummaryDetailBranchPointBlock',
                delegate = detailBranchPointDelegate)
        ]
    ).install(parcel) # SplitterWindow SearchResultsViewTemplate

    SplitterWindow.template(
        'TableViewTemplate',
        orientationEnum = "Vertical",
        splitPercentage = 0.65,
        eventBoundary = True,
        eventsForNamedLookup = [saveResultsEvent],
        childBlocks = [
            Table.template('TableSummaryView',
                contents = pim_ns.allCollection,
                scaleWidthsToFit = True,
                columns = [
                    taskColumn,
                    commColumn,
                    whoColumn,
                    titleColumn,
                    reminderColumn,
                    dateColumn,
                    triageColumn                    
                ],
                characterStyle = blocks.SummaryRowStyle,
                prefixCharacterStyle = blocks.SummaryPrefixStyle,
                headerCharacterStyle = blocks.SummaryHeaderStyle,
                rowHeight = 19,
                elementDelegate = 'osaf.framework.blocks.ControlBlocks.AttributeDelegate',
                       defaultEditableAttribute = u'displayName',
                selection = [[0,0]]),
            BranchPointBlock.template('TableSummaryDetailBranchPointBlock',
                delegate = detailBranchPointDelegate)
        ]
    ).install(parcel)

    TimeZoneChange = BlockEvent.template(
        'TimeZoneChange',
        dispatchEnum = 'BroadcastEverywhere').install(parcel)

    DefaultCharacterStyle = CharacterStyle.update(
        parcel, 'DefaultCharacterStyle',
        fontFamily = 'DefaultUIFont')

    DefaultSmallBoldStyle = CharacterStyle.update(
        parcel, 'DefaultSmallBoldStyle',
        fontFamily = 'DefaultUIFont',
        fontSize = 10.0,
        fontStyle = 'bold')

    DefaultBigStyle = CharacterStyle.update(
        parcel, 'DefaultBigStyle',
        fontFamily = 'DefaultUIFont',
        fontSize = 12.0)

    DefaultBoldStyle = CharacterStyle.update(
        parcel, 'DefaultBoldStyle',
        fontFamily = 'DefaultUIFont',
        fontStyle = 'bold')

    DefaultBigBoldStyle = CharacterStyle.update(
        parcel, 'DefaultBigBoldStyle',
        fontFamily = 'DefaultUIFont',
        fontSize = 13,
        fontStyle = 'bold')

    # save the template because we'll need it for later
    MainCalendarControlT = calendar.CalendarControl.template(
        'MainCalendarControl',
        tzCharacterStyle = DefaultCharacterStyle,
        stretchFactor = 0)

    MainCalendarControl = MainCalendarControlT.install(parcel)

    CalendarDetailBranchPointBlock = BranchPointBlock.template(
        'CalendarDetailBranchPointBlock',
        delegate = detailBranchPointDelegate,
        ).install(parcel)

    WelcomeEvent = schema.ns('osaf.app', view).WelcomeEvent
    CalendarDetailBranchPointBlock.selectedItem = WelcomeEvent
    #detailContentsCollection.clear()
    #detailContentsCollection.add(WelcomeEvent)

    CalendarSummaryView = CalendarContainer.template(
        'CalendarSummaryView',
        calendarControl = MainCalendarControl,
        monthLabelStyle = blocks.BigTextStyle,
        eventLabelStyle = DefaultCharacterStyle,
        eventTimeStyle = DefaultSmallBoldStyle,
        legendStyle = DefaultCharacterStyle,
        orientationEnum = 'Vertical',
        eventsForNamedLookup = [TimeZoneChange]).install(parcel)
    
    SplitterWindow.template('CalendarSummaryViewTemplate',
        eventBoundary = True,
        orientationEnum = 'Vertical',
        splitPercentage = 0.65,
        childBlocks = [
            CalendarContainer.template('CalendarSummaryView',
                childBlocks = [
                    MainCalendarControlT,
                    CanvasSplitterWindow.template('MainCalendarCanvasSplitter',
                        # as small as possible; AllDayEvents's
                        # SetMinSize() should override?
                        splitPercentage = 0.06,
                        orientationEnum = 'Horizontal',
                        calendarControl = MainCalendarControl,
                        childBlocks = [
                            calendar.AllDayEventsCanvas.template('AllDayEvents',
                                calendarContainer = CalendarSummaryView),
                            calendar.TimedEventsCanvas.template('TimedEvents',
                                calendarContainer = CalendarSummaryView,
                                contextMenu = "ItemContextMenu")
                            ]),
                    ]),
            BranchPointBlock.template('CalendarDetailBranchPointBlock',
                delegate = detailBranchPointDelegate)
            ]).install(parcel)
    
    CalendarControl.update(
        parcel, 'MainCalendarControl',
        calendarContainer = CalendarSummaryView)
                                
    # Precache detail views for the basic pim types (and "Block",
    # which is the key used for the None item). Note that the basic
    # stamps (Event, Task, Mail) are now covered by Note
    for keyType in (pim.Note, Block.Block):
        detailBranchPointDelegate.getBranchForKeyItem(
                            schema.itemFor(keyType, view))
    

if __name__ == "__main__":
    # Code to generate a web page for checking the communications column's
    # icon mappings. To generate "icontest.html" in your $CHANDLERHOME, do:
    #   cd $CHANDLERHOME; $CHANDLERBIN/release/RunPython.bat parcels/osaf/views/main/summaryblocks.py
    # (leave off the .bat if you're not on windows)
    # Then, view file:///path/to/your/CHANDLERHOME/icontest.html
    # in your browser.
    import os, itertools
    from util.MultiStateButton import allVariations

    # URL to ChandlerHome in ViewCVS
    viewCVS = "http://viewcvs.osafoundation.org/chandler/trunk/chandler"
    
    # Relative path to the images we'll use
    imageDir = "Chandler.egg-info/resources/images"
    if True:
        # Refer to the images in ViewCVS (so I can paste the resulting HTML
        # into a wiki page, for instance)
        imagePrefix = "%s/Chandler.egg-info/resources/images" % viewCVS
    else:
        # Just reference the images relatively.
        imagePrefix = imageDir
        
    # First, we add a "dump" method to BitMapInfo
    def BitmapInfoDump(self, variation):
        v = getattr(self, variation, None)
        if v is None:
            return "(None)"
        else:
            if v == "pixel":
                v = "pixel.gif"
            else:
                v += ".png"
            return '<img height=32 width=42 src="%s/%s"><br/><font size=-1>%s</font>' % (imagePrefix, v, v)
    BitmapInfo.dump = BitmapInfoDump

    # A utility routine to columnize a list:
    # list(columnnize(list("abcdefghi"), 3)) returns
    # [('a', 'd', 'g'),
    #  ('b', 'e', 'h'),
    #  ('c', 'f', None)]
    # which we need for the icon table HTML.
    def columnize(seq, colCount, default=None):
        cols = []
        overFlow = len(seq) % colCount 
        if overFlow:
            seq.extend([default] * (colCount - overFlow))
            
        colLength = len(seq) / colCount
        cols = [ seq[(c * colLength):((c+1) * colLength)]
                 for c in xrange(colCount) ]        
        return itertools.izip(*cols)
        
    f = open("icontest.html", 'w')
    f.write("""<p>
This is a dump of the icon states in the dashboard task, communications, and 
event columns. See the notes at the bottom of <a href="%s/parcels/osaf/views/main/summaryblocks.py?view=markup">
parcels/osaf/views/main/summaryblocks.py</a> to see how it was created.
</p>""" % viewCVS)
    
    # The variations we'll do are all except these two
    variationList = list(allVariations)
    variationList.remove("disabled")
    variationList.remove("focus")
    
    for cls, iconPrefix in ((TaskColumnAttributeEditor, "Task"),
                            (CommunicationsColumnAttributeEditor, "Mail"),
                            (ReminderColumnAttributeEditor, "Event")):
        f.write("\n<h3>%s</h3>\n" % iconPrefix)
        f.write('<table width="100%" bgcolor="#339933">\n  <tr>\n    <td>&nbsp;</td>\n')
        for v in variationList:
            f.write("    <td align=middle><i>%s</i></td>\n" % v)
        f.write('  </tr>\n')
        setattr(cls, '__init__', lambda *args, **kwds: None)
        states = cls().makeStates()
        for s in states:
            f.write("  <tr>\n")
            f.write("    <td>%s</td>\n" % s.stateName)
            for v in variationList:
                f.write("    <td align=middle>%s</td>\n" % s.dump(v))
            f.write("  </tr>\n")
        f.write("</table>\n")
    
        f.write('&nbsp;<br>&nbsp;<br><table width="100%" bgcolor="#339933">\n')
        images = [ im for im in os.listdir(imageDir) if im.startswith(iconPrefix)]
        images.sort()    
        for rowImages in columnize(images, 4):
            f.write('  <tr>\n')
            for img in rowImages:
                if img is not None:
                    f.write('    <td valign="middle"><img height=32 width=42 src="%s/%s"><font size=-1>%s</font></td>\n' % (imagePrefix, img, img))
                else:
                    f.write('    <td>&nbsp;</td>\n')
            f.write('  </tr>\n')
        f.write("</table>\n")
    #f.write("</body>\n")
    f.close()
