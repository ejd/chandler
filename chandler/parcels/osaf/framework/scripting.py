__version__ = "$Revision: 6708 $"
__date__ = "$Date: 2005-08-19 17:29:03 -0700 (Fri, 19 Aug 2005) $"
__copyright__ = "Copyright (c) 2005 Open Source Applications Foundation"
__license__ = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import application.Globals as Globals
import application.schema as schema
import osaf.pim as pim
import osaf.framework.blocks.Block as Block
import osaf.framework.blocks.ControlBlocks as ControlBlocks
import osaf.framework.types.DocumentTypes as DocumentTypes
import osaf.framework.attributeEditors.AttributeEditors as AttributeEditors
import osaf.framework.blocks.detail.Detail as Detail
import application.dialogs.Util as Util
from repository.item.Item import Item
from datetime import datetime
import logging
import wx
import os, sys
import hotshot
import hotshot.stats as stats
from i18n import OSAFMessageFactory as _
from osaf import messages

__all__ = [
    'app_ns', 'cats_profiler', 'hotkey_script', 
    'run_script', 'run_startup_script', 'Script', 'script_file',
    'User'
]

logger = logging.getLogger(__name__)

def installParcel(parcel, oldVersion=None):
    detail = schema.ns('osaf.framework.blocks.detail', parcel)
    blocks = schema.ns("osaf.framework.blocks", parcel.itsView)

    # UI Elements:
    # -----------
    hotkeyArea = detail.makeArea(parcel, 'HotkeyArea',
                            position=0.6,
                            childrenBlocks=[
                                detail.makeLabel(parcel, _(u'Hotkey'), borderTop=4),
                                detail.makeSpacer(parcel, width=6),
                                detail.makeEditor(parcel, 'EditFKey',
                                           viewAttribute=u'fkey',
                                           stretchFactor=0.0,
                                           size=DocumentTypes.SizeType(75, -1)),
                                detail.makeSpacer(parcel, width=60),
                                ]).install(parcel)

    saveFileEvent = Block.BlockEvent.template('SaveFile',
                                              dispatchEnum='SendToSender',
                                              ).install(parcel)

    openFileButton = OpenFileButton.template('openFileButton',
                                             title=_(u'Open'),
                                             buttonKind='Text',
                                             characterStyle=blocks.LabelStyle,
                                             stretchFactor=0.0,
                                             size=DocumentTypes.SizeType(100, -1),
                                             event=saveFileEvent
                                             ).install(parcel)

    saveFileButton = SaveFileButton.template('saveFileButton',
                                             title=_(u'Save'), 
                                             buttonKind='Text',
                                             characterStyle=blocks.LabelStyle,
                                             stretchFactor=0.0,
                                             size=DocumentTypes.SizeType(100, -1),
                                             event=saveFileEvent
                                             ).install(parcel)

    saveAsFileButton = SaveAsFileButton.template('saveAsFileButton',
                                             title=_(u'Save As'), # fill in title later
                                             buttonKind='Text',
                                             characterStyle=blocks.LabelStyle,
                                             stretchFactor=0.0,
                                             size=DocumentTypes.SizeType(100, -1),
                                             event=saveFileEvent
                                             ).install(parcel)

    testCheckboxArea = detail.makeArea(parcel, 'TestCheckboxArea',
                            position=0.7,
                            childrenBlocks=[
                                detail.makeLabel(parcel, _(u'test'), borderTop=4),
                                detail.makeSpacer(parcel, width=6),
                                detail.makeEditor(parcel, 'EditTest',
                                           viewAttribute=u'test',
                                           stretchFactor=0.0,
                                           minimumSize=DocumentTypes.SizeType(16,-1)),
                                detail.makeSpacer(parcel, width=6),
                                openFileButton, saveFileButton, saveAsFileButton,
                                ]).install(parcel)

    scriptTextArea = detail.makeEditor(parcel, 'NotesBlock',
                                       viewAttribute=u'bodyString',
                                       presentationStyle={'lineStyleEnum': 'MultiLine',
                                                          'format': 'fileSynchronized'},
                                       position=0.9).install(parcel)

    filePathArea = detail.makeArea(parcel, 'FilePathArea',
                                   baseClass=FilePathAreaBlock,
                                   position=0.8,
                                   childrenBlocks=[
                                       detail.makeLabel(parcel, _(u'path'), borderTop=4),
                                       detail.makeSpacer(parcel, width=6),
                                       detail.makeEditor(parcel, 'EditFilePath',
                                                         viewAttribute=u'filePath',
                                                         presentationStyle={'format': 'static'}
                                                         )
                                       ]).install(parcel)


    # Block Subtree for the Detail View of a Script
    # ------------
    detail.DetailTrunkSubtree.update(parcel, 'script_detail_view',
                                     key=Script.getKind(parcel.itsView),
                                     rootBlocks=[
                                         detail.makeSpacer(parcel, height=6, position=0.01).install(parcel),
                                         detail.HeadlineArea,
                                         hotkeyArea,
                                         testCheckboxArea,
                                         filePathArea,
                                         detail.makeSpacer(parcel, height=7, position=0.8).install(parcel),
                                         scriptTextArea
                                         ])

    AttributeEditors.AttributeEditorMapping.update(parcel, 
                                                   'Text+fileSynchronized',
                                                   className=__name__ + '.' + 'FileSynchronizedAttributeEditor')

"""
Handle running a Script.
"""
def run_script(scriptText, fileName=u"", profiler=None):
    """
    exec the supplied script, in an environment equivalent to
    what you get when you say:
    from scripting.Helpers import *
    """
    assert len(scriptText) > 0, "Empty script"
    assert fileName is not None

    if profiler:
        profiler.stop() # start with the profile turned off

    scriptText = scriptText.encode(sys.getfilesystemencoding())
    fileName = fileName.encode(sys.getfilesystemencoding())

    # compile the code
    scriptCode = compile(scriptText, fileName, 'exec')

    # next, build a dictionary of names that are predefined
    builtIns = {}

    for attr in __all__:
        builtIns[attr] = globals()[attr]

    # now run that script in our predefined scope
    exec scriptCode in builtIns

class Script(pim.ContentItem):
    """ Persistent Script Item, to be executed. """
    schema.kindInfo(displayName=_(u"Script"), displayAttribute="displayName")
    lastRan = schema.One(schema.DateTime, displayName = _(u"last ran"))
    fkey = schema.One(schema.Text, initialValue = u'')
    test = schema.One(schema.Boolean, initialValue = False)

    filePath = schema.One(schema.Text, initialValue = u'')
    lastSync = schema.One(schema.DateTime)

    # redirections

    about = schema.One(redirectTo = 'displayName')
    who = schema.One(redirectTo = 'creator')
    date = schema.One(redirectTo = 'lastRan')

    def __init__(self, name=None, parent=None, kind=None, view=None,
                 bodyString=None, *args, **keys):
        defaultName = messages.UNTITLED
        if name is not None:
            defaultName = unicode(name)
        keys.setdefault('displayName', defaultName)
        super(Script, self).__init__(name, parent, kind, view, *args, **keys)

        self.lastRan = datetime.now()
        self.lastSync = self.lastRan
        if bodyString is not None:
            self.bodyString = bodyString # property for the body LOB
        self.private = False # can share scripts

    def execute(self):
        self.sync_file_with_model()
        self.lastRan = datetime.now()
        run_script(self.bodyString, fileName=self.filePath)

    def set_body_quietly(self, newValue):
        if newValue != self.bodyString:
            oldQuiet = getattr(self, '_change_quietly', False)
            self._change_quietly = True
            self.bodyString = newValue
            self._change_quietly = oldQuiet

    def onValueChanged(self, name):
        if name == 'body':
            self.model_data_changed()

    def model_data_changed(self):
        if self.filePath and not getattr(self, '_change_quietly', False):
            self.modelModTime = datetime.now()

    def sync_file_with_model(self, preferFile=False):
        """
        Synchronize file and model - which ever is latest wins, with
        conflict dialogs possible if both have changed since the last sync.
        """
        if self.filePath and not getattr(self, '_change_quietly', False):
            writeFile = False
            # make sure we have a model modification time
            if not hasattr(self, 'modelModTime'):
                self.modelModTime = self.lastSync
            # get modification date for the file
            try:
                fileModTime = datetime.fromtimestamp(os.stat(self.filePath)[8])
            except OSError:
                fileModTime = self.lastSync
                writeFile = True
            if preferFile or fileModTime > self.modelModTime:
                self.set_body_quietly(self.file_contents(self.filePath))
            elif writeFile or fileModTime < self.modelModTime:
                # model is newer
                latest = self.modelModTime
                if fileModTime > self.lastSync:
                    caption = _(u"Overwrite script file?")
                    msg = _(u"The file associated with this script has been changed,"
                            "\nbut those changes are older than your recent edits.\n\n"
                            "Do you want to overwrite those file changes with your\n"
                            "recent edits of this script?")
                    if not Util.yesNo(wx.GetApp().mainFrame, caption, msg):
                        return
                self.write_file(self.bodyString)
                fileModTime = datetime.fromtimestamp(os.stat(self.filePath)[8])
            # now the file and model match
            self.lastSync = self.modelModTime = fileModTime

    def file_contents(self, filePath):
        """
        return the contents of our script file
        """
        scriptFile = open(filePath, 'rt')
        try:
            scriptText = scriptFile.read(-1)
        finally:
            scriptFile.close()
        return scriptText

    def write_file(self, scriptText):
        """
        write the contents of our script file into the file
        """
        scriptFile = open(self.filePath, 'wt')
        try:
            scriptText = scriptFile.write(scriptText)
        finally:
            scriptFile.close()

    def set_file(self, fileName, siblingPath):
        #Convert fileName with the system charset encoding
        #to bytes to prevent the join function from trying to downcast
        #the unicode fileName to ascii
        fileName = fileName.encode(sys.getfilesystemencoding())
        #Convert the filePath bytes to unicode for storage
        filePath = unicode(os.path.join(os.path.dirname(siblingPath), fileName), sys.getfilesystemencoding())
        self.bodyString = self.file_contents(filePath)
        self.filePath = filePath

class FileSynchronizedAttributeEditor(AttributeEditors.StringAttributeEditor):
    """
    Delegate for an Attribute Editor that synchronizes the attribute with
    a file's contents.
    """
    def BeginControlEdit (self, item, attributeName, control):
        """ 
        Prepare to edit this value. 
        """
        # sync first, then we'll have the right value
        item.sync_file_with_model()
        return super(FileSynchronizedAttributeEditor, self).BeginControlEdit(item, attributeName, control)

    def SetAttributeValue (self, item, attributeName, value):
        """ Set the value of the attribute given by the value. """
        # has the data really changed?
        if value != self.GetAttributeValue(item, attributeName):
            # update the model data
            super(FileSynchronizedAttributeEditor, 
                         self).SetAttributeValue(item, attributeName, value)
            # update the file data too
            item.sync_file_with_model()

class FilePathAreaBlock(Detail.DetailSynchronizedContentItemDetail):
    """
    Block to show (or hide) the File Path area of the script.
    """
    def shouldShow(self, item):
        return len(item.filePath) > 0

class OpenFileButton(Detail.DetailSynchronizer, ControlBlocks.Button):
    """
    Block to show (or hide) the "Open File" button, and
    to handle that event.
    """
    def shouldShow(self, item):
        self._item = item
        return len(item.bodyString) == 0

    def onSaveFileEvent(self, event):
        """
        Open a file to associate with this script, or save an existing
        script to a file.
        """
        if not self._item.bodyString:
            # no script body, open and overwrite existing model data
            title = _(u"Open a script file")
            message = _(u"Open an existing script file, or choose a name\n"
                        "for a new file for this script.")
            flags = wx.OPEN
        else:
            # model data exists, we need a place to write it
            title =_(u"Save this script file as")
            message = _(u"Choose an existing script file, or enter a name\n"
                        "for a new file for this script.")
            flags = wx.SAVE | wx.OVERWRITE_PROMPT

        if self._item.filePath:
            # already have a file, default to that name and path
            # dirname returns unicode here since the filePath variable is unicode
            path = os.path.dirname(self._item.filePath)
            name = self._item.filePath.split(os.sep)[-1]
        else:
            # no file yet, point to scripts directory, use display name
            name = self._item.displayName+u".py"
            # dirname returns an str of bytes since the __file__ variable is bytes
            path = os.path.dirname(schema.ns('osaf.app', self).scripts.__file__)
            # convert the path bytes to unicode
            path = unicode(path, sys.getfilesystemencoding())

        # present the Open/Save dialog
        result = Util.showFileDialog(wx.GetApp().mainFrame, 
                                     title,
                                     path,
                                     name,
                                     _(u"Python files|*.py|") + _(u"All files (*.*)|*.*"),
                                     flags)
        cmd, dir, fileName = result

        if cmd == wx.ID_OK:
            preferFile = len(self._item.bodyString) == 0
            writeFile = not preferFile
            self._item.filePath = os.path.join(dir, fileName)
            self._item.sync_file_with_model(preferFile=preferFile)
            resyncEvent = schema.ns('osaf.framework.blocks.detail', self).Resynchronize
            self.post(resyncEvent, {})
            self.postEventByName('ResyncDetailParent', {})

class SaveFileButton(OpenFileButton):
    """
    Block to show (or hide) the "Save" button, and
    to handle that event.
    """
    def shouldShow(self, item):
        self._item = item
        return len(item.bodyString) > 0 and len(item.filePath) == 0

class SaveAsFileButton(OpenFileButton):
    """
    Block to show (or hide) the "Save As" button, and
    to handle that event.
    """
    def shouldShow(self, item):
        self._item = item
        return len(item.bodyString) > 0 and len(item.filePath) > 0


def hotkey_script(event, view):
    """
    Check if the event is a hot key to run a script.
    Returns True if it does trigger a script to run, False otherwise.
    """
    keycode = event.GetKeyCode()
    # for now, we just allow function keys to be hot keys.
    if (keycode >= wx.WXK_F1 and keycode <= wx.WXK_F24
            and not event.AltDown()
            and not event.CmdDown()
            and not event.ControlDown()
            and not event.MetaDown()
            and not event.ShiftDown()):
        # try to find the corresponding Script
        targetFKey = _(u"F%(FunctionKeyNumber)s") % {'FunctionKeyNumber':unicode(keycode-wx.WXK_F1+1)}

        # maybe we have an existing script?
        script = _findHotKeyScript(targetFKey, view)
        if script:
            wx.CallAfter(script.execute)
            return True

    # not a hot key
    return False

def _findHotKeyScript(targetFKey, view):
    # find a script that starts with the given name
    for aScript in Script.iterItems(view):
        if aScript.fkey == targetFKey:
            return aScript
    return None

global_cats_profiler = None # remember the CATS profiler here

def run_startup_script(view):
    global global_cats_profiler
    if Globals.options.testScripts:
        try:
            for aScript in Script.iterItems(view):
                if aScript.test:
                    aScript.execute()
        finally:
            # run the cleanup script
            schema.ns('osaf.app', view).CleanupAfterTests.execute()

    fileName = Globals.options.scriptFile
    if fileName:
        scriptFileText = script_file(fileName)
        if scriptFileText:
            # check if we should turn on the profiler for this script
            if Globals.options.catsProfile:
                profiler = hotshot.Profile(Globals.options.catsProfile)
                global_cats_profiler = profiler
                profiler.runcall(run_script, scriptFileText, fileName=fileName, 
                                               profiler=profiler)
                profiler.close()
                global_cats_profiler = None
            else:
                run_script(scriptFileText, fileName = fileName)

def cats_profiler():
    return global_cats_profiler

def script_file(fileName, siblingPath=None):
    """
    Return the script from the file, given a file name
    and a path to a sibling file.
    """
    #Encode the unicode filename to the system character set encoding
    fileName = fileName.encode(sys.getfilesystemencoding())

    if siblingPath is not None:
        fileName = os.path.join(os.path.dirname(siblingPath), fileName)
    # read the script from a file, and return it.
    scriptFile = open(fileName, 'rt')
    try:
        scriptText = scriptFile.read(-1)
    finally:
        scriptFile.close()
    return scriptText

class EventTiming(dict):
    """
    dictionary of event timings for events that have
    been sent by CPIA Script since this dictionary was reset.
    Use clear() to reset timings.
    """
    def start_timer(self):
        return datetime.now()

    def end_timer(self, startTime, eventName):
        self.setdefault(eventName, []).append(datetime.now()-startTime)

    def get_strings(self):
        strTimings = {}
        for eName, timingList in self.iteritems():
            strList = []
            for timing in timingList:
                strList.append(str(timing))
            strTimings[eName] = strList
        return strTimings

    strings = property(get_strings)

class BlockProxy(object):
    """
    Proxy for a Block which is dynamically located by name.
    Since Blocks come and go in CPIA, this proxy helps
    provide a solid reference point for locating the
    currently rendered Block by name.
    You can construct it with a set of children block
    attributes which are also located by name.
    """
    def __init__(self, blockName, app_ns, children={}):
        # create an attribute that looks up this block by name
        self.proxy = blockName
        self.children = children
        self.app_ns = app_ns

    def __getattr__(self, attr):
        # if it's a block that's our child, return it
        child_name = self.children.get(attr, None)
        if child_name:
            return getattr(self.app_ns, child_name)
        # delegate the lookup to our View
        block = getattr(self.app_ns, self.proxy)
        return getattr(block, attr)

    def focus(self):
        block = getattr(self.app_ns, self.proxy)
        block.widget.SetFocus()

class RootProxy(BlockProxy):
    """ 
    Proxy to the Main View Root block. 
    Handles BlockEvents as methods.
    """

    def __init__(self, *args, **keys):
        super(RootProxy, self).__init__(*args, **keys)
        # our timing object
        self.timing = EventTiming()

    """
    We need to find the best BlockEvent at runtime on each invokation,
    because the BlockEvents come and go from the soup as UI portions
    are rendered and unrendered.  The best BlockEvent is the one copied
    into the soup and attached to rendered blocks that were also copied.
    """
    def post_script_event(self, eventName, event, argDict=None, timing=None, **keys):
        # Post the supplied event, keeping track of the timing if requested.
        # Also, call Yield() on the application, so it gets some time during
        #   script execution.
        if argDict is None:
            argDict = {}
        try:
            argDict.update(keys)
        except AttributeError:
            # make sure the first parameter was a dictionary, or give a friendly error
            message = "BlockEvents may only have one positional parameter - a dict"
            raise AttributeError, message
        # remember timing information
        if timing is not None:
            startTime = timing.start_timer()
        # post the event
        result = Globals.mainViewRoot.post(event, argDict)
        # finish timing
        if timing is not None:
            timing.end_timer(startTime, eventName)
        # let the Application get some time
        wx.GetApp().Yield()
        return result

    # Attributes that are BlockEvents get converted to functions
    # that invoke that event.
    # All other attributes are redirected to the root view.
    def __getattr__(self, attr):
        def scripted_blockEvent(argDict=None, **keys):
            # merge the named parameters, into the dictionary positional arg
            return self.post_script_event(attr, best, argDict, timing=self.timing, **keys)
        best = Block.Block.findBlockEventByName(attr)
        if best is not None:
            return scripted_blockEvent
        else:
            # delegate the lookup to our View
            return getattr(Globals.mainViewRoot, attr)


"""
Children to use for the Detail View.
This is a mapping of the form:
attribute_name: block_name
"""
detail_children = {
    'title': 'HeadlineBlock',
    'location': 'CalendarLocation',
    'mail_from': 'FromEditField',
    'mail_to': 'ToMailEditField',
    'all_day': 'EditAllDay',
    'start_date': 'EditCalendarStartDate',
    'start_time': 'EditCalendarStartTime',
    'end_date': 'EditCalendarEndDate',
    'end_time': 'EditCalendarEndTime',
    'time_zone': 'EditTimeZone',
    'status': 'EditTransparency',
    'recurrence': 'EditRecurrence',
    'reminder': 'EditReminder',
    'notes': 'NotesBlock',
    }

class AppProxy(object):
    """
    Proxy for the app namespace, and the items you'd expect
    in that namespace.
    Provides easy access to useful attributes, like "view".
    Has attributes for its major children blocks, like
    "root", "sidebar", "calendar", etc.
    All BlockEvents are mapped onto methods in this class, 
    so you can say AppProxy.NewTask() to post the "NewTask"
    event.
    """
    def __init__(self, view):
        # our view attribute
        self.itsView = view
        # we proxy to the app name space
        self.app_ns = schema.ns('osaf.app', view)
        # view proxies
        self.root = RootProxy('MainViewRoot', self)
        self.appbar = BlockProxy('ApplicationBar', self)
        self.markupbar = BlockProxy('MarkupBar', self)
        self.sidebar = BlockProxy('Sidebar', self)
        self.calendar = BlockProxy('CalendarSummaryView', self)
        self.summary = BlockProxy('TableSummaryView', self)
        self.detail = BlockProxy('DetailView', self, children=detail_children)

    def item_named(self, itemClass, itemName):
        for item in itemClass.iterItems(self.itsView):
            if self._name_of(item) == itemName:
                return item
        return None

    def _name_of(self, item):
        try:
            return item.about
        except AttributeError:
            pass
        try:
            return item.blockName
        except AttributeError:
            pass
        try:
            return item.displayName
        except AttributeError:
            pass
        try:
            return item.itsName
        except AttributeError:
            pass
        return None

    # Attributes that are named blocks are found by name.
    # All other attributes are redirected to the app name space.
    def __getattr__(self, attr):
        block = Block.Block.findBlockByName(attr)
        if block is not None:
            return block
        else:
            return getattr(self.app_ns, attr)

    """
    Emulating User-level Actions
    """
class User(object):
    """
    Emulate User Actions
    """
    @classmethod
    def emulate_typing(cls, string, ctrlFlag = False, altFlag = False, shiftFlag = False):
        """ emulate_typing the string into the current focused widget """
        success = True
        def set_event_info(event):
            # setup event info for a keypress event
            event.m_keyCode = keyCode
            event.m_rawCode = keyCode
            event.m_shiftDown = char.isupper() or shiftFlag
            event.m_controlDown = event.m_metaDown = ctrlFlag
            event.m_altDown = altFlag
            event.SetEventObject(widget)
        # for each key, check for specials, then try several approaches
        app = wx.GetApp()
        for char in string:
            keyCode = ord(char)
            if keyCode == wx.WXK_RETURN:
                cls.emulate_return()
            elif keyCode == wx.WXK_TAB:
                cls.emulate_tab(shiftFlag=shiftFlag)
            else:
                # in case the focus has changed, get the new focused widget
                widget = wx.Window_FindFocus()
                # try calling any bound key handler
                keyPress = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
                set_event_info(keyPress)
                downWorked = widget.ProcessEvent(keyPress)
                keyUp = wx.KeyEvent(wx.wxEVT_KEY_UP)
                set_event_info(keyUp)
                upWorked = widget.ProcessEvent(keyUp)
                if not (downWorked or upWorked): # key handler worked?
                    # try calling EmulateKeyPress
                    emulateMethod = getattr(widget, 'EmulateKeyPress', lambda k: False)
                    if '__WXMSW__' in wx.PlatformInfo:
                        emulateMethod = lambda k: False
                    if not emulateMethod(keyPress): # emulate worked?
                        # try calling WriteText
                        writeMethod = getattr(widget, 'WriteText', None)
                        if writeMethod:
                            writeMethod(char)
                        else:
                            success = False # remember we had a failure
                app.Yield()
        return success

    @classmethod 
    def emulate_tab(cls, shiftFlag=False):
        if shiftFlag:
            flags = wx.NavigationKeyEvent.IsBackward
        else:
            flags = wx.NavigationKeyEvent.IsForward
        wx.Window_FindFocus().Navigate(flags)

    @classmethod
    def emulate_click(cls, block, x=None, y=None, double=False):
        """ Simulates left mouse click on the given block or widget """
        try:
            widget =  block.widget
        except AttributeError:
            widget = block
        # event settings
        mouseEnter = wx.MouseEvent(wx.wxEVT_ENTER_WINDOW)
        if double:
            mouseDown = wx.MouseEvent(wx.wxEVT_LEFT_DCLICK)
        else:
            mouseDown = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
        mouseUp = wx.MouseEvent(wx.wxEVT_LEFT_UP)
        mouseLeave = wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW)
        if x:
            mouseEnter.m_x = mouseDown.m_x = mouseUp.m_x = x
        if y:
            mouseEnter.m_y = mouseDown.m_y = mouseUp.m_y = y
        mouseEnter.SetEventObject(widget)
        mouseDown.SetEventObject(widget)
        mouseUp.SetEventObject(widget)
        mouseLeave.SetEventObject(widget)
        # events processing
        widget.ProcessEvent(mouseEnter)
        widget.ProcessEvent(mouseDown)
        if not double:
            widget.ProcessEvent(mouseUp)
        widget.ProcessEvent(mouseLeave)
        # Give Yield to the App
        wx.GetApp().Yield()

    @classmethod
    def emulate_return(cls, block=None):
        """ Simulates a return-key event in the given block """
        try:
            if block :
                widget = block.widget
            else :
                widget = wx.Window_FindFocus()
        except AttributeError:
            return False
        else:
            # return-key down
            ret_d = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
            ret_d.m_keyCode = wx.WXK_RETURN
            # return-key up
            ret_up = wx.KeyEvent(wx.wxEVT_KEY_UP)
            ret_up.m_keyCode = wx.WXK_RETURN
            # text updated event
            tu = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_UPDATED)
            tu.SetEventObject(widget)
            # kill focus event
            kf = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)
            kf.SetEventObject(widget)
            # Text enter
            ent = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER)
            ent.SetEventObject(widget)

            #work around for mac bug
            widget.ProcessEvent(tu) #for start/end time and location field
            #work around for canvasItem
            widget.ProcessEvent(kf) #for canvasItem title
            # events processing
            widget.ProcessEvent(ret_d)
            widget.ProcessEvent(ret_up)
            # Give Yield & Idle to the App
            cls.idle()
            return True

    @classmethod
    def emulate_sidebarClick(cls, sidebar, cellName, double=False):
        ''' Process a left click on the given cell in the given sidebar'''
        # for All, In, Out, Trash collection find by item rather than itemName
        chandler_collections = {"All":schema.ns('osaf.app', Globals.mainViewRoot).allCollection,
                                "Out":schema.ns('osaf.app', Globals.mainViewRoot).outCollection,
                                "In":schema.ns('osaf.app', Globals.mainViewRoot).inCollection,
                                "Trash":schema.ns('osaf.app', Globals.mainViewRoot).TrashCollection}
        if cellName in chandler_collections.keys():
            cellName = chandler_collections[cellName]

        cellRect = None
        for i in range(sidebar.widget.GetNumberRows()):
            item = sidebar.widget.GetTable().GetValue(i,0)[0]
            if item.displayName == cellName or item == cellName:
                cellRect = sidebar.widget.CalculateCellRect(i)
                break
        if cellRect:
            # events processing
            gw = sidebar.widget.GetGridWindow()
            # +3 work around for the sidebar bug
            cls.emulate_click(gw, x=cellRect.GetX()+3, y=cellRect.GetY()+3, double=double)
            return True
        else:
            return False

    @classmethod
    def idle(cls):
        app = wx.GetApp()
        app.Yield()
        app.ProcessEvent(wx.IdleEvent())
        app.Yield()

def app_ns(view=None):
    if view is None:
        view = wx.GetApp().UIRepositoryView
    return AppProxy(view)
