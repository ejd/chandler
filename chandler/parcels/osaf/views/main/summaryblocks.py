#   Copyright (c) 2003-2006 Open Source Applications Foundation
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


from osaf.framework.blocks import *

def makeSummaryBlocks(parcel):
    from application import schema
    from i18n import ChandlerMessageFactory as _
    from osaf.framework.blocks.calendar import (
        CalendarContainer, CalendarControl, CanvasSplitterWindow,
        AllDayEventsCanvas, TimedEventsCanvas
        )

    from osaf import pim

    from Dashboard import DashboardBlock
    
    view = parcel.itsView
    detailblocks = schema.ns('osaf.views.detail', view)
    pim_ns = schema.ns('osaf.pim', view)
    blocks = schema.ns('osaf.framework.blocks', view)
    repositoryView = parcel.itsView
    
    # Index definitions that the dashboard will use
    taskStatusIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.taskStatus' % __name__, attributes=[
            # pim.TaskStamp.taskStatus.name, 
            pim.ContentItem.triageStatus.name, 
            pim.ContentItem.triageStatusChanged.name,
        ])
    commStatusIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.communicationStatus' % __name__, attributes=[
            # pim.mail.MailStamp.communicationStatus.name, 
            pim.ContentItem.triageStatus.name, 
            pim.ContentItem.triageStatusChanged.name,
        ])
    displayWhoIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.displayWho' % __name__, attributes=[
            pim.ContentItem.displayWho.name,
            pim.ContentItem.displayDate.name,
        ])
    displayNameIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.displayName' % __name__, attributes=[
            pim.ContentItem.displayName.name, 
            pim.ContentItem.displayDate.name,
        ])
    calStatusIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.calendarStatus' % __name__, attributes=[
            # pim.EventStamp.calendarStatus.name, 
            pim.ContentItem.triageStatus.name, 
            pim.ContentItem.triageStatusChanged.name,
        ])
    dateIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.displayDate' % __name__, attributes=[
            pim.ContentItem.displayDate.name, 
            pim.ContentItem.triageStatus.name, 
            pim.ContentItem.triageStatusChanged.name,
        ])
    triageStatusIndexDef = pim.IndexDefinition.update(parcel, 
        '%s.triageStatus' % __name__, attributes=[
            pim.ContentItem.triageStatus.name, 
            pim.ContentItem.triageStatusChanged.name,
        ])
        
    # Our detail views share the same delegate instance and contents collection
    detailBranchPointDelegate = detailblocks.DetailBranchPointDelegate.update(
        parcel, 'DetailBranchPointDelegateInstance',
        branchStub = detailblocks.DetailRoot)
    #detailContentsCollection = pim.ListCollection.update(
        #parcel, 'DetailContentsCollection')
    iconColumnWidth = 23 # temporarily not 20, to work around header bug 6168
    SplitterWindow.template(
        'TableSummaryViewTemplate',
        eventBoundary = True,
        orientationEnum = "Vertical",
        splitPercentage = 0.65,
        childrenBlocks = [
            DashboardBlock.template('TableSummaryView',
                contents = pim_ns.allCollection,
                scaleWidthsToFit = True,
                columns = [
                    Column.update(parcel, 'SumColTask',
                                  icon = 'ColHTask',
                                  valueType = 'stamp',
                                  stamp = pim.TaskStamp,
                                  attributeName = 'taskStatus',
                                  indexName = taskStatusIndexDef.itsName,
                                  width = iconColumnWidth,
                                  useSortArrows = False,
                                  readOnly = True),
                    Column.update(parcel, 'SumColMail',
                                  icon = 'ColHMail',
                                  valueType = 'stamp',
                                  stamp = pim.mail.MailStamp,
                                  attributeName = 'communicationStatus',
                                  indexName = commStatusIndexDef.itsName,
                                  width = iconColumnWidth,
                                  useSortArrows = False,
                                  readOnly = True),
                    Column.update(parcel, 'SumColWho',
                                  heading = _(u'Who'),
                                  attributeName = 'displayWho',
                                  attributeSourceName = 'displayWhoSource',
                                  indexName = displayWhoIndexDef.itsName,
                                  width = 100,
                                  scaleColumn = True,
                                  readOnly = True),
                    Column.update(parcel, 'SumColName',
                                  heading = _(u'Title'),
                                  attributeName = 'displayName',
                                  indexName = displayNameIndexDef.itsName,
                                  width = 120,
                                  scaleColumn = True),
                    Column.update(parcel, 'SumColCalendarEvent',
                                  icon = 'ColHEvent',
                                  valueType = 'stamp',
                                  attributeName = 'calendarStatus',
                                  indexName = calStatusIndexDef.itsName,
                                  stamp = pim.EventStamp,
                                  useSortArrows = False,
                                  width = iconColumnWidth,
                                  readOnly = True),
                    Column.update(parcel, 'SumColDate',
                                  heading = _(u'Date'),
                                  attributeName = 'displayDate',
                                  attributeSourceName = 'displayDateSource',
                                  indexName = dateIndexDef.itsName,
                                  width = 100,
                                  scaleColumn = True,
                                  readOnly = True),
                    Column.update(parcel, 'SumColTriage',
                                  icon = 'ColHTriageStatus',
                                  attributeName = 'triageStatus',
                                  indexName = triageStatusIndexDef.itsName,                                  useSortArrows = False,
                                  defaultSort = True,
                                  width = 40),
                ],
                characterStyle = blocks.SummaryRowStyle,
                headerCharacterStyle = blocks.SummaryHeaderStyle,
                elementDelegate = 'osaf.views.main.SectionedGridDelegate',
                       defaultEditableAttribute = u'displayName',
                selection = [[0,0]]),
            BranchPointBlock.template('TableSummaryDetailBranchPointBlock',
                delegate = detailBranchPointDelegate,
                #contents = detailContentsCollection
                )
            ]).install(parcel) # SplitterWindow TableSummaryViewTemplate


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
        #contents = detailContentsCollection
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
        childrenBlocks = [
            CalendarContainer.template('CalendarSummaryView',
                childrenBlocks = [
                    MainCalendarControlT,
                    CanvasSplitterWindow.template('MainCalendarCanvasSplitter',
                        # as small as possible; AllDayEvents's
                        # SetMinSize() should override?
                        splitPercentage = 0.06,
                        orientationEnum = 'Horizontal',
                        stretchFactor = 1,
                        calendarControl = MainCalendarControl,
                        childrenBlocks = [
                            calendar.AllDayEventsCanvas.template('AllDayEvents',
                                calendarContainer = CalendarSummaryView),
                            calendar.TimedEventsCanvas.template('TimedEvents',
                                calendarContainer = CalendarSummaryView)
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
    
