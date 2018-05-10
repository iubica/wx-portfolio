#!/bin/env python
#----------------------------------------------------------------------------
# Name:         Main.py
# Purpose:      Testing lots of stuff, controls, window types, etc.
#
# Author:       Robin Dunn
#
# Created:      A long time ago, in a galaxy far, far away...
# Copyright:    (c) 1999-2017 by Total Control Software
# Licence:      wxWindows license
# Tags:         phoenix-port, py3-port
#----------------------------------------------------------------------------

# FIXME List:
# * Problems with flickering related to ERASE_BACKGROUND
#     and the splitters. Might be a problem with this 2.5 beta...?
#     UPDATE: can't see on 2.5.2 GTK - maybe just a faster machine :)
# * Annoying switching between tabs and resulting flicker
#     how to replace a page in the notebook without deleting/adding?
#     Where is SetPage!? tried freeze...tried reparent of dummy panel....
#     AG: It looks like this issue is fixed by Freeze()ing and Thaw()ing the
#         main frame and not the notebook

# TODO List:
# * UI design more professional (is the new version more professional?)
# * save file positions (new field in viewModule) (@ LoadViewSource)
# * Update main overview

# =====================
# = EXTERNAL Packages =
# =====================
# In order to let a package (like AGW) be included into the TickerScrape tree,
# create a sub-directory of the TickerScrape install folder
# in which all the package's views should live. In addition, the sub-folder
# should contain a Python file called __init__tickerscrape__.py which, 
# when imported, should contain the following methods:
#
# * GetViewBitmap: returns the bitmap to be used in the wxPython view tree
#   control in a PyEmbeddedImage format;
#
# * GetRecentAdditions: returns a list of views to be displayed under the
#   "Recent Additions/Updates" tree item. This list should be a subset 
#   (or the full set) of the package's views;
#
# * GetViews: returns a tuple. The first item of the tuple is the package's name
#   as will be displayed in the TickerScrape view tree, right after 
#   the "Custom Controls" item. The second element of the tuple is the list of
#   views for the external package.
#
# * GetOverview: returns a wx.html-ready representation of the 
#   package's documentation.
#
# Please see the __init__tickerscrape__.py file in the TickerScrape/agw/ folder 
# for an example.

import sys, os, errno, tarfile, time, traceback
import re
import shutil
from threading import Thread
import psutil
import platform

from distutils.version import LooseVersion

import wx
import wx.adv
import wx.lib.agw.aui as aui
import wx.html
from wx.lib.msgpanel import MessagePanel
from wx.adv import TaskBarIcon as TaskBarIcon
from wx.adv import SplashScreen as SplashScreen
import wx.lib.mixins.inspection

import six
from six import exec_, BytesIO
from six.moves import cPickle
from six.moves import urllib

from bs4 import BeautifulSoup

import version
import ViewTree
import Config

# We won't import the images module yet, but we'll assign it to this
# global when we do.
images = None

# The main frame class instance
portfolioFrame = None

# For debugging
##wx.Trap();
##print("wx.VERSION_STRING = %s (%s)" % (wx.VERSION_STRING, wx.USE_UNICODE and 'unicode' or 'ansi'))
##print("pid:", os.getpid())
##raw_input("Press Enter...")

#---------------------------------------------------------------------------

USE_CUSTOMTREECTRL = False
DEFAULT_PERSPECTIVE = "Default Perspective"
TIMER_STATUS_BAR=2000

#---------------------------------------------------------------------------

_styleTable = '<h3>Window %s</h3>\n' \
              '<p>This class supports the following window %s:\n' \
              '<p><table bgcolor=\"#ffffff\" border cols=1>'

_eventTable = '<h3>Events</h3>\n' \
              '<p>Events emitted by this class:\n' \
              '<p><table bgcolor=\"#ffffff\" border cols=1>'

_appearanceTable = '<h3>Appearance</h3>\n' \
                   '<p>Control appearance on various platform:\n' \
                   '<p><table bgcolor=\"#ffffff\" cellspacing=20>'

_styleHeaders = ["Style Name", "Description"]
_eventHeaders = ["Event Name", "Description"]
_headerTable = '<td><b>%s</b></td>'
_styleTag = '<td><tt>%s</tt></td>'
_eventTag = '<td><i>%s</i></td>'
_hexValues = '<td><font color="%s"> %s </font></td>'
_description = '<td>%s</td>'
_imageTag = '<td align=center valign=middle><a href="%s"><img src="%s" alt="%s"></a></td>'
_platformTag = '<td align=center><b>%s</b></td>'

_trunkURL = "http://docs.wxwidgets.org/trunk/"
_docsURL = _trunkURL + "classwx%s.html"
_platformNames = ["wxMSW", "wxGTK", "wxMac"]


_importList = ["wx.aui", "wx.calendar", "wx.html", "wx.media", "wx.wizard",
               "wx.combo", "wx.animate", "wx.gizmos", "wx.glcanvas", "wx.grid",
               "wx.richtext", "wx.stc"]

_dirWX = dir(wx)
for mod in _importList:
    try:
        module = __import__(mod)
    except ImportError:
        continue

#---------------------------------------------------------------------------

def ReplaceCapitals(string):
    """
    Replaces the capital letter in a string with an underscore plus the
    corresponding lowercase character.

    **Parameters:**

    * `string`: the string to be analyzed.
    """

    newString = ""
    for char in string:
        if char.isupper():
            newString += "_%s"%char.lower()
        else:
            newString += char

    return newString


def RemoveHTMLTags(data):
    """
    Removes all the HTML tags from a string.

    **Parameters:**

    * `data`: the string to be analyzed.
    """

    p = re.compile(r'<[^<]*?>')
    return p.sub('', data)


def FormatDocs(keyword, values, num):

    names = list(values.keys())
    names.sort()

    headers = (num == 2 and [_eventHeaders] or [_styleHeaders])[0]
    table = (num == 2 and [_eventTable] or [_styleTable])[0]
    if num == 3:
        text = "<br>" + table%(keyword.lower(), keyword.lower()) + "\n<tr>\n"
    else:
        text = "<br>" + table

    for indx in range(2):
        text += _headerTable%headers[indx]

    text += "\n</tr>\n"

    for name in names:

        text += "<tr>\n"

        description = values[name].strip()
        pythonValue = name.replace("wx", "wx.")

        if num == 3:

            colour = "#ff0000"
            value = "Unavailable"
            cutValue = pythonValue[3:]

            if cutValue in _dirWX:
                try:
                    val = eval(pythonValue)
                    value = "%s"%hex(val)
                    colour = "#0000ff"
                except AttributeError:
                    value = "Unavailable"
            else:
                for packages in _importList:
                    if cutValue in dir(eval(packages)):
                        val = eval("%s.%s"%(packages, cutValue))
                        value = "%s"%hex(val)
                        colour = "#0000ff"
                        pythonValue = "%s.%s"%(packages, cutValue)
                        break

            text += _styleTag%pythonValue + "\n"

        else:

            text += _eventTag%pythonValue + "\n"

        text += _description%FormatDescription(description) + "\n"
        text += "</tr>\n"

    text += "\n</table>\n\n<p>"
    return text


def FormatDescription(description):
    """
    Formats a wxWidgets C++ description in a more wxPython-based way.

    **Parameters:**

    * `description`: the string description to be formatted.
    """

    description = description.replace("wx", "wx.")
    description = description.replace("EVT_COMMAND", "wxEVT_COMMAND")
    description = description.replace("wx.Widgets", "wxWidgets")

    return description


def FormatImages(appearance):

    text = "<p><br>" + _appearanceTable

    for indx in range(2):
        text += "\n<tr>\n"
        for key in _platformNames:
            if indx == 0:
                src = appearance[key]
                alt = key + "Appearance"
                text += _imageTag%(src, src, alt)
            else:
                text += _platformTag%key

        text += "</tr>\n"

    text += "\n</table>\n\n<p>"
    return text


def FindWindowStyles(text, originalText, widgetName):
    """
    Finds the windows styles and events in the input text.

    **Parameters:**

    * `text`: the wxWidgets C++ docs for a particular widget/event, stripped
              of all HTML tags;
    * `originalText`: the wxWidgets C++ docs for a particular widget/event, with
              all HTML tags.
    """

    winStyles, winEvents, winExtra, winAppearance = {}, {}, {}, {}
    inStyle = inExtra = inEvent = False

    for line in text:
        if "following styles:" in line:
            inStyle = True
            continue

        elif "Event macros" in line:
            inEvent = True
            continue

        if "following extra styles:" in line:
            inExtra = True
            continue

        if "Appearance:" in line:
            winAppearance = FindImages(originalText, widgetName)
            continue

        elif not line.strip():
            inStyle = inEvent = inExtra = False
            continue

        if inStyle:
            start = line.index(':')
            windowStyle = line[0:start]
            styleDescription = line[start+1:]
            winStyles[windowStyle] = styleDescription
        elif inEvent:
            start = line.index(':')
            eventName = line[0:start]
            eventDescription = line[start+1:]
            winEvents[eventName] = eventDescription
        elif inExtra:
            start = line.index(':')
            styleName = line[0:start]
            styleDescription = line[start+1:]
            winExtra[styleName] = styleDescription

    return winStyles, winEvents, winExtra, winAppearance


def FindImages(text, widgetName):
    """
    When the wxWidgets docs contain athe control appearance (a screenshot of the
    control), this method will try and download the images.

    **Parameters:**

    * `text`: the wxWidgets C++ docs for a particular widget/event, with
              all HTML tags.
    """

    winAppearance = {}
    start = text.find("class='appearance'")

    if start < 0:
        return winAppearance

    imagesDir = GetDocImagesDir()

    end = start + text.find("</table>")
    text = text[start:end]
    split = text.split()

    for indx, items in enumerate(split):

        if "src=" in items:
            possibleImage = items.replace("src=", "").strip()
            possibleImage = possibleImage.replace('"', "")
            f = urllib.request.urlopen(_trunkURL + possibleImage)
            stream = f.read()
        elif "alt=" in items:
            plat = items.replace("alt=", "").replace("'", "").strip()
            path = os.path.join(imagesDir, plat, widgetName + ".png")
            if not os.path.isfile(path):
                image = wx.ImageFromStream(BytesIO(stream))
                image.SaveFile(path, wx.BITMAP_TYPE_PNG)

            winAppearance[plat] = path

    return winAppearance


#---------------------------------------------------------------------------
# Set up a thread that will scan the wxWidgets docs for window styles,
# events and widgets screenshots

class InternetThread(Thread):
    """ Worker thread class to attempt connection to the internet. """

    def __init__(self, notifyWindow, selectedClass):

        Thread.__init__(self)

        self.notifyWindow = notifyWindow
        self.selectedClass = selectedClass
        self.keepRunning = True
        self.setDaemon(True)

        self.start()


    def run(self):
        """ Run the worker thread. """

        # This is the code executing in the new thread. Simulation of
        # a long process as a simple urllib call

        try:
            url = _docsURL % ReplaceCapitals(self.selectedClass)
            fid = urllib.request.urlopen(url)

            if six.PY2:
                originalText = fid.read()
            else:
                originalText = fid.read().decode("utf-8")
            text = RemoveHTMLTags(originalText).split("\n")
            data = FindWindowStyles(text, originalText, self.selectedClass)

            if not self.keepRunning:
                return

            wx.CallAfter(self.notifyWindow.LoadDocumentation, data)
        except (IOError, urllib.error.HTTPError):
            # Unable to get to the internet
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            wx.CallAfter(self.notifyWindow.StopDownload, message)
        except:
            # Some other strange error...
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            wx.CallAfter(self.notifyWindow.StopDownload, message)


#---------------------------------------------------------------------------
# Show how to derive a custom wxLog class

class MyLog(wx.Log):
    def __init__(self, textCtrl, logTime=0):
        wx.Log.__init__(self)
        self.tc = textCtrl
        self.logTime = logTime

    def DoLogText(self, message):
        if self.tc:
            self.tc.AppendText(message + '\n')



#---------------------------------------------------------------------------
# A class to be used to display source code in the view.  Try using the
# wxSTC in the StyledTextCtrl_2 sample first, fall back to wxTextCtrl
# if there is an error, such as the stc module not being present.
#

try:
    ##raise ImportError     # for testing the alternate implementation
    from wx import stc
    from StyledTextCtrl_2 import PythonSTC

    class CodeEditor(PythonSTC):
        def __init__(self, parent, style=wx.BORDER_NONE):
            PythonSTC.__init__(self, parent, -1, style=style)
            self.SetUpEditor()

        # Some methods to make it compatible with how the wxTextCtrl is used
        def SetValue(self, value):
            # if wx.USE_UNICODE:
                # value = value.decode('iso8859_1')
            val = self.GetReadOnly()
            self.SetReadOnly(False)
            self.SetText(value)
            self.EmptyUndoBuffer()
            self.SetSavePoint()
            self.SetReadOnly(val)

        def SetEditable(self, val):
            self.SetReadOnly(not val)

        def IsModified(self):
            return self.GetModify()

        def Clear(self):
            self.ClearAll()

        def SetInsertionPoint(self, pos):
            self.SetCurrentPos(pos)
            self.SetAnchor(pos)

        def ShowPosition(self, pos):
            line = self.LineFromPosition(pos)
            #self.EnsureVisible(line)
            self.GotoLine(line)

        def GetLastPosition(self):
            return self.GetLength()

        def GetPositionFromLine(self, line):
            return self.PositionFromLine(line)

        def GetRange(self, start, end):
            return self.GetTextRange(start, end)

        def GetSelection(self):
            return self.GetAnchor(), self.GetCurrentPos()

        def SetSelection(self, start, end):
            self.SetSelectionStart(start)
            self.SetSelectionEnd(end)

        def SelectLine(self, line):
            start = self.PositionFromLine(line)
            end = self.GetLineEndPosition(line)
            self.SetSelection(start, end)

        def SetUpEditor(self):
            """
            This method carries out the work of setting up the view editor.
            It's seperate so as not to clutter up the init code.
            """
            import keyword

            self.SetLexer(stc.STC_LEX_PYTHON)
            self.SetKeyWords(0, " ".join(keyword.kwlist))

            # Enable folding
            self.SetProperty("fold", "1" )

            # Highlight tab/space mixing (shouldn't be any)
            self.SetProperty("tab.timmy.whinge.level", "1")

            # Set left and right margins
            self.SetMargins(2,2)

            # Set up the numbers in the margin for margin #1
            self.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
            # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
            self.SetMarginWidth(1, 40)

            # Indentation and tab stuff
            self.SetIndent(4)               # Proscribed indent size for wx
            self.SetIndentationGuides(True) # Show indent guides
            self.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
            self.SetTabIndents(True)        # Tab key indents
            self.SetTabWidth(4)             # Proscribed tab size for wx
            self.SetUseTabs(False)          # Use spaces rather than tabs, or
                                            # TabTimmy will complain!
            # White space
            self.SetViewWhiteSpace(False)   # Don't view white space

            # EOL: Since we are loading/saving ourselves, and the
            # strings will always have \n's in them, set the STC to
            # edit them that way.
            self.SetEOLMode(wx.stc.STC_EOL_LF)
            self.SetViewEOL(False)

            # No right-edge mode indicator
            self.SetEdgeMode(stc.STC_EDGE_NONE)

            # Setup a margin to hold fold markers
            self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
            self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
            self.SetMarginSensitive(2, True)
            self.SetMarginWidth(2, 12)

            # and now set up the fold markers
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,    "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS, "white", "black")

            # Global default style
            if wx.Platform == '__WXMSW__':
                self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                                  'fore:#000000,back:#FFFFFF,face:Courier New')
            elif wx.Platform == '__WXMAC__':
                # TODO: if this looks fine on Linux too, remove the Mac-specific case
                # and use this whenever OS != MSW.
                self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                                  'fore:#000000,back:#FFFFFF,face:Monaco')
            else:
                defsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
                self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                                  'fore:#000000,back:#FFFFFF,face:Courier,size:%d'%defsize)

            # Clear styles and revert to default.
            self.StyleClearAll()

            # Following style specs only indicate differences from default.
            # The rest remains unchanged.

            # Line numbers in margin
            self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,'fore:#000000,back:#99A9C2')
            # Highlighted brace
            self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,'fore:#00009D,back:#FFFF00')
            # Unmatched brace
            self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,'fore:#00009D,back:#FF0000')
            # Indentation guide
            self.StyleSetSpec(wx.stc.STC_STYLE_INDENTGUIDE, "fore:#CDCDCD")

            # Python styles
            self.StyleSetSpec(wx.stc.STC_P_DEFAULT, 'fore:#000000')
            # Comments
            self.StyleSetSpec(wx.stc.STC_P_COMMENTLINE,  'fore:#008000,back:#F0FFF0')
            self.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK, 'fore:#008000,back:#F0FFF0')
            # Numbers
            self.StyleSetSpec(wx.stc.STC_P_NUMBER, 'fore:#008080')
            # Strings and characters
            self.StyleSetSpec(wx.stc.STC_P_STRING, 'fore:#800080')
            self.StyleSetSpec(wx.stc.STC_P_CHARACTER, 'fore:#800080')
            # Keywords
            self.StyleSetSpec(wx.stc.STC_P_WORD, 'fore:#000080,bold')
            # Triple quotes
            self.StyleSetSpec(wx.stc.STC_P_TRIPLE, 'fore:#800080,back:#FFFFEA')
            self.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE, 'fore:#800080,back:#FFFFEA')
            # Class names
            self.StyleSetSpec(wx.stc.STC_P_CLASSNAME, 'fore:#0000FF,bold')
            # Function names
            self.StyleSetSpec(wx.stc.STC_P_DEFNAME, 'fore:#008080,bold')
            # Operators
            self.StyleSetSpec(wx.stc.STC_P_OPERATOR, 'fore:#800000,bold')
            # Identifiers. I leave this as not bold because everything seems
            # to be an identifier if it doesn't match the above criterae
            self.StyleSetSpec(wx.stc.STC_P_IDENTIFIER, 'fore:#000000')

            # Caret color
            self.SetCaretForeground("BLUE")
            # Selection background
            self.SetSelBackground(1, '#66CCFF')

            self.SetSelBackground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))
            self.SetSelForeground(True, wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

        def RegisterModifiedEvent(self, eventHandler):
            self.Bind(wx.stc.EVT_STC_CHANGE, eventHandler)


except ImportError:
    class CodeEditor(wx.TextCtrl):
        def __init__(self, parent):
            wx.TextCtrl.__init__(self, parent, -1, style =
                                 wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2 | wx.TE_NOHIDESEL)

        def RegisterModifiedEvent(self, eventHandler):
            self.Bind(wx.EVT_TEXT, eventHandler)

        def SetReadOnly(self, flag):
            self.SetEditable(not flag)
            # NOTE: STC already has this method

        def GetText(self):
            return self.GetValue()

        def GetPositionFromLine(self, line):
            return self.XYToPosition(0,line)

        def GotoLine(self, line):
            pos = self.GetPositionFromLine(line)
            self.SetInsertionPoint(pos)
            self.ShowPosition(pos)

        def SelectLine(self, line):
            start = self.GetPositionFromLine(line)
            end = start + self.GetLineLength(line)
            self.SetSelection(start, end)


#---------------------------------------------------------------------------
# Constants for module versions

modOriginal = 0
modModified = 1
modDefault = modOriginal

#---------------------------------------------------------------------------

class CodePanel(wx.Panel):
    """Panel for the 'Code' tab"""
    def __init__(self, parent, mainFrame):
        wx.Panel.__init__(self, parent, size=(1,1))
        if 'wxMSW' in wx.PlatformInfo:
            self.Hide()
        self.mainFrame = mainFrame
        self.editor = CodeEditor(self)
        self.editor.RegisterModifiedEvent(self.OnCodeModified)

        self.btnSave = wx.Button(self, -1, "Save Changes")
        self.btnRestore = wx.Button(self, -1, "Delete Modified")
        self.btnSave.Enable(False)
        self.btnSave.Bind(wx.EVT_BUTTON, self.OnSave)
        self.btnRestore.Bind(wx.EVT_BUTTON, self.OnRestore)

        self.radioButtons = { modOriginal: wx.RadioButton(self, -1, "Original", style = wx.RB_GROUP),
                              modModified: wx.RadioButton(self, -1, "Modified") }

        self.controlBox = wx.BoxSizer(wx.HORIZONTAL)
        self.controlBox.Add(wx.StaticText(self, -1, "Active Version:"), 0,
                            wx.RIGHT | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)
        for modID, radioButton in self.radioButtons.items():
            self.controlBox.Add(radioButton, 0, wx.EXPAND | wx.RIGHT, 5)
            radioButton.modID = modID # makes it easier for the event handler
            radioButton.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)

        self.controlBox.Add(self.btnSave, 0, wx.RIGHT, 5)
        self.controlBox.Add(self.btnRestore, 0)

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.controlBox, 0, wx.EXPAND)
        self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.editor, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)


    # Loads a view from a ViewModule object
    def LoadView(self, viewModule):
        self.viewModule = viewModule
        if (modDefault == modModified) and viewModule.Exists(modModified):
            viewModule.SetActive(modModified)
        else:
            viewModule.SetActive(modOriginal)
        self.radioButtons[viewModule.GetActiveID()].Enable(True)
        self.ActiveModuleChanged()

    def ActiveModuleChanged(self):
        self.LoadViewSource(self.viewModule.GetSource())
        self.UpdateControlState()
        self.mainFrame.pnl.Freeze()
        self.ReloadView()
        self.mainFrame.pnl.Thaw()


    def LoadViewSource(self, source):
        self.editor.Clear()
        self.editor.SetValue(source)
        self.JumpToLine(0)
        self.btnSave.Enable(False)


    def JumpToLine(self, line, highlight=False):
        self.editor.GotoLine(line)
        self.editor.SetFocus()
        if highlight:
            self.editor.SelectLine(line)


    def UpdateControlState(self):
        active = self.viewModule.GetActiveID()
        # Update the radio/restore buttons
        for moduleID in self.radioButtons:
            btn = self.radioButtons[moduleID]
            if moduleID == active:
                btn.SetValue(True)
            else:
                btn.SetValue(False)

            if self.viewModule.Exists(moduleID):
                btn.Enable(True)
                if moduleID == modModified:
                    self.btnRestore.Enable(True)
            else:
                btn.Enable(False)
                if moduleID == modModified:
                    self.btnRestore.Enable(False)


    def OnRadioButton(self, event):
        radioSelected = event.GetEventObject()
        modSelected = radioSelected.modID
        if modSelected != self.viewModule.GetActiveID():
            busy = wx.BusyInfo("Reloading view module...")
            self.viewModule.SetActive(modSelected)
            self.ActiveModuleChanged()


    def ReloadView(self):
        if self.viewModule.name != __name__:
            self.mainFrame.RunModule()


    def OnCodeModified(self, event):
        self.btnSave.Enable(self.editor.IsModified())


    def OnSave(self, event):
        if self.viewModule.Exists(modModified):
            if self.viewModule.GetActiveID() == modOriginal:
                overwriteMsg = "You are about to overwrite an already existing modified copy\n" + \
                               "Do you want to continue?"
                dlg = wx.MessageDialog(self, overwriteMsg, "wxPython Demo",
                                       wx.YES_NO | wx.NO_DEFAULT| wx.ICON_EXCLAMATION)
                result = dlg.ShowModal()
                if result == wx.ID_NO:
                    return
                dlg.Destroy()

        self.viewModule.SetActive(modModified)
        modifiedFilename = GetModifiedFilename(self.viewModule.name)

        # Create the demo directory if one doesn't already exist
        if not os.path.exists(GetModifiedDirectory()):
            try:
                os.makedirs(GetModifiedDirectory())
                if not os.path.exists(GetModifiedDirectory()):
                    wx.LogMessage("BUG: Created demo directory but it still doesn't exist")
                    raise AssertionError
            except:
                wx.LogMessage("Error creating demo directory: %s" % GetModifiedDirectory())
                return
            else:
                wx.LogMessage("Created directory for modified demos: %s" % GetModifiedDirectory())

        # Save
        f = open(modifiedFilename, "wt")
        source = self.editor.GetText()
        try:
            f.write(source)
        finally:
            f.close()

        busy = wx.BusyInfo("Reloading view module...")
        self.viewModule.LoadFromFile(modModified, modifiedFilename)
        self.ActiveModuleChanged()

        self.mainFrame.SetTreeModified(True)


    def OnRestore(self, event): # Handles the "Delete Modified" button
        modifiedFilename = GetModifiedFilename(self.viewModule.name)
        self.viewModule.Delete(modModified)
        os.unlink(modifiedFilename) # Delete the modified copy
        busy = wx.BusyInfo("Reloading view module...")

        self.ActiveModuleChanged()

        self.mainFrame.SetTreeModified(False)


#---------------------------------------------------------------------------

def opj(path):
    """Convert paths to the platform-specific separator"""
    st = os.path.join(*tuple(path.split('/')))
    # HACK: on Linux, a leading / gets lost...
    if path.startswith('/'):
        st = '/' + st
    return st


def GetDataDir():
    """
    Return the standard location on this platform for application data
    """
    sp = wx.StandardPaths.Get()
    return sp.GetUserDataDir()


def GetModifiedDirectory():
    """
    Returns the directory where modified versions of the demo files
    are stored
    """
    return os.path.join(GetDataDir(), "modified")


def GetModifiedFilename(name):
    """
    Returns the filename of the modified version of the specified demo
    """
    if not name.endswith(".py"):
        name = name + ".py"
    return os.path.join(GetModifiedDirectory(), name)


def GetOriginalFilename(name):
    """
    Returns the filename of the original version of the specified view
    """
    if not name.endswith(".py"):
        name = name + ".py"

    # Stop looking for views and widgets in the top folder, except for Main
    if name == "Main.py":
        if os.path.isfile(name):
            return name

    originalDir = os.getcwd()
    listDir = os.listdir(originalDir)
    # Loop over the content of the demo directory
    for item in listDir:
        if not os.path.isdir(item):
            # Not a directory, continue
            continue
        dirFile = os.listdir(item)
        # See if a file called "name" is there
        if name in dirFile:
            return os.path.join(item, name)

    # We must return a string...
    return ""


def DoesModifiedExist(name):
    """Returns whether the specified demo has a modified copy"""
    if os.path.exists(GetModifiedFilename(name)):
        return True
    else:
        return False


def GetConfig():
    if not os.path.exists(GetDataDir()):
        os.makedirs(GetDataDir())

    config = wx.FileConfig(
        localFilename=os.path.join(GetDataDir(), "options"))
    return config


def MakeDocDirs():

    docDir = os.path.join(GetDataDir(), "docs")
    if not os.path.exists(docDir):
        os.makedirs(docDir)

    for plat in _platformNames:
        imageDir = os.path.join(docDir, "images", plat)
        if not os.path.exists(imageDir):
            os.makedirs(imageDir)


def GetDocFile():

    docFile = os.path.join(GetDataDir(), "docs", "TrunkDocs.pkl")

    return docFile


def GetDocImagesDir():

    MakeDocDirs()
    return os.path.join(GetDataDir(), "docs", "images")


def SearchView(name, keyword):
    """ Returns whether a view contains the search keyword or not. """
    fid = open(GetOriginalFilename(name), "rt")
    fullText = fid.read()
    fid.close()

    # No need to decode from UTF-8 in Python 3
    # fullText = fullText.decode("iso-8859-1")

    if fullText.find(keyword) >= 0:
        return True

    return False


def HuntExternalViews():
    """
    Searches for external demos (i.e. packages like AGW) in the wxPython
    demo sub-directories. In order to be found, these external packages
    must have a __init__tickerscrape__.py file in their directory.
    """

    externalViews = {}
    originalDir = os.getcwd()
    listDir = os.listdir(originalDir)
    # Loop over the content of the demo directory
    for item in listDir:
        if not os.path.isdir(item):
            # Not a directory, continue
            continue
        dirFile = os.listdir(item)
        # See if a __init__tickerscrape__.py file is there
        if "__init__tickerscrape__.py" in dirFile:
            # Extend sys.path and import the external demos
            sys.path.append(item)
            externalViews[item] = __import__("__init__tickerscrape__")

    if not externalViews:
        # Nothing to import...
        return {}

    # Modify the tree items and icons
    index = 0
    for category, demos in ViewTree.viewTree:
        # We put the external packages right before the
        # More Windows/Controls item
        if category == "More Windows/Controls":
            break
        index += 1

    # Sort and reverse the external demos keys so that they
    # come back in alphabetical order
    keys = list(externalViews.keys())
    keys.sort()
    keys.reverse()

    # Loop over all external packages
    for extern in keys:
        package = externalViews[extern]
        # Insert a new package in the ViewTree.viewTree of demos
        ViewTree.viewTree.insert(index, package.GetViews())
        # Get the recent additions for this package
        ViewTree.viewTree[3][1].extend(package.GetRecentAdditions())
        # Extend the demo bitmaps and the catalog
        ViewTree.viewPngs.insert(index+1, extern)
        images.catalog[extern] = package.GetViewBitmap()

    # That's all folks...
    return externalViews


def LookForExternals(externalViews, viewName):
    """
    Checks if a view name is in any of the external packages (like AGW) or
    if the user clicked on one of the external packages parent items in the
    tree, in which case it returns the html overview for the package.
    """

    pkg = overview = None
    # Loop over all the external views
    for key, package in externalViews.items():
        # Get the tree item name for the package and its views
        treeName, treeViews = package.GetViews()
        # Get the overview for the package
        treeOverview = package.GetOverview()
        if treeName == viewName:
            # The user clicked on the parent tree item, return the overview
            return pkg, treeOverview
        elif viewName in treeViews:
            # The user clicked on a real view, return the package
            return key, overview

    # No match found, return None for both
    return pkg, overview

#---------------------------------------------------------------------------

class ModuleDictWrapper(object):
    """Emulates a module with a dynamically compiled __dict__"""
    def __init__(self, dict):
        self.dict = dict

    def __getattr__(self, name):
        if name in self.dict:
            return self.dict[name]
        else:
            raise AttributeError

class ViewModule(object):
    """
    Dynamically manages the original/modified versions of a view
    module
    """
    def __init__(self, name):
        self.modActive = -1
        self.name = name

        #              (dict , source ,  filename , description   , error information )
        #              (  0  ,   1    ,     2     ,      3        ,          4        )
        self.modules = [[dict(),  ""    ,    ""     , "<original>"  ,        None],
                        [dict(),  ""    ,    ""     , "<modified>"  ,        None]]

        getcwd = os.getcwd if six.PY3 else os.getcwdu
        for i in [modOriginal, modModified]:
            self.modules[i][0]['__file__'] = \
                os.path.join(getcwd(), GetOriginalFilename(name))

        # load original module
        self.LoadFromFile(modOriginal, GetOriginalFilename(name))
        self.SetActive(modOriginal)

        # load modified module (if one exists)
        if DoesModifiedExist(name):
            self.LoadFromFile(modModified, GetModifiedFilename(name))


    def LoadFromFile(self, modID, filename):
        self.modules[modID][2] = filename
        file = open(filename, "rt")
        self.LoadFromSource(modID, file.read())
        file.close()


    def LoadFromSource(self, modID, source):
        self.modules[modID][1] = source
        self.LoadDict(modID)


    def LoadDict(self, modID):
        if self.name != __name__:
            source = self.modules[modID][1]
            description = self.modules[modID][2]
            if six.PY2:
                description = description.encode(sys.getfilesystemencoding())

            try:
                code = compile(source, description, "exec")
                exec_(code, self.modules[modID][0])
            except:
                self.modules[modID][4] = ViewModuleError(sys.exc_info())
                self.modules[modID][0] = None
            else:
                self.modules[modID][4] = None


    def SetActive(self, modID):
        if modID != modOriginal and modID != modModified:
            raise LookupError
        else:
            self.modActive = modID


    def GetActive(self):
        dict = self.modules[self.modActive][0]
        if dict is None:
            return None
        else:
            return ModuleDictWrapper(dict)


    def GetActiveID(self):
        return self.modActive


    def GetSource(self, modID = None):
        if modID is None:
            modID = self.modActive
        return self.modules[modID][1]


    def GetFilename(self, modID = None):
        if modID is None:
            modID = self.modActive
        return self.modules[self.modActive][2]


    def GetErrorInfo(self, modID = None):
        if modID is None:
            modID = self.modActive
        return self.modules[self.modActive][4]


    def Exists(self, modID):
        return self.modules[modID][1] != ""


    def UpdateFile(self, modID = None):
        """Updates the file from which a module was loaded
        with (possibly updated) source"""
        if modID is None:
            modID = self.modActive

        source = self.modules[modID][1]
        filename = self.modules[modID][2]

        try:
            file = open(filename, "wt")
            file.write(source)
        finally:
            file.close()


    def Delete(self, modID):
        if self.modActive == modID:
            self.SetActive(0)

        self.modules[modID][0] = None
        self.modules[modID][1] = ""
        self.modules[modID][2] = ""


#---------------------------------------------------------------------------

class ViewModuleError(object):
    """Wraps and stores information about the current exception"""
    def __init__(self, exc_info):
        import copy

        excType, excValue = exc_info[:2]
        # traceback list entries: (filename, line number, function name, text)
        self.traceback = traceback.extract_tb(exc_info[2])

        # --Based on traceback.py::format_exception_only()--
        if isinstance(excType, type):
            self.exception_type = excType.__name__
        else:
            self.exception_type = excType

        # If it's a syntax error, extra information needs
        # to be added to the traceback
        if excType is SyntaxError:
            try:
                msg, (filename, lineno, self.offset, line) = excValue
            except:
                pass
            else:
                if not filename:
                    filename = "<string>"
                line = line.strip()
                self.traceback.append( (filename, lineno, "", line) )
                excValue = msg
        try:
            self.exception_details = str(excValue)
        except:
            self.exception_details = "<unprintable %s object>" & type(excValue).__name__

        del exc_info

    def __str__(self):
        ret = "Type %s \n \
        Traceback: %s \n \
        Details  : %s" % ( str(self.exception_type), str(self.traceback), self.exception_details )
        return ret

#---------------------------------------------------------------------------

class ViewModuleErrorPanel(wx.Panel):
    """Panel put into the demo tab when the demo fails to run due  to errors"""

    def __init__(self, parent, codePanel, demoError, log):
        wx.Panel.__init__(self, parent, -1)#, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.codePanel = codePanel
        self.nb = parent
        self.log = log

        self.box = wx.BoxSizer(wx.VERTICAL)

        # Main Label
        self.box.Add(wx.StaticText(self, -1, "An error has occurred while trying to run the view module")
                     , 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # Exception Information
        boxInfo      = wx.StaticBox(self, -1, "Exception Info" )
        boxInfoSizer = wx.StaticBoxSizer(boxInfo, wx.VERTICAL ) # Used to center the grid within the box
        boxInfoGrid  = wx.FlexGridSizer( cols=2 )
        textFlags    = wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.TOP
        boxInfoGrid.Add(wx.StaticText(self, -1, "Type: "), 0, textFlags, 5 )
        boxInfoGrid.Add(wx.StaticText(self, -1, str(demoError.exception_type)) , 0, textFlags, 5 )
        boxInfoGrid.Add(wx.StaticText(self, -1, "Details: ") , 0, textFlags, 5 )
        boxInfoGrid.Add(wx.StaticText(self, -1, demoError.exception_details) , 0, textFlags, 5 )
        boxInfoSizer.Add(boxInfoGrid, 0, wx.ALIGN_CENTRE | wx.ALL, 5 )
        self.box.Add(boxInfoSizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # Set up the traceback list
        # This one automatically resizes last column to take up remaining space
        from ListCtrl import TestListCtrl
        self.list = TestListCtrl(self, -1, style=wx.LC_REPORT  | wx.SUNKEN_BORDER)
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.list.InsertColumn(0, "Filename")
        self.list.InsertColumn(1, "Line", wx.LIST_FORMAT_RIGHT)
        self.list.InsertColumn(2, "Function")
        self.list.InsertColumn(3, "Code")
        self.InsertTraceback(self.list, demoError.traceback)
        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list.SetColumnWidth(2, wx.LIST_AUTOSIZE)
        self.box.Add(wx.StaticText(self, -1, "Traceback:")
                     , 0, wx.ALIGN_CENTER | wx.TOP, 5)
        self.box.Add(self.list, 1, wx.GROW | wx.ALIGN_CENTER | wx.ALL, 5)
        self.box.Add(wx.StaticText(self, -1, "Entries from the view module are shown in blue\n"
                                           + "Double-click on them to go to the offending line")
                     , 0, wx.ALIGN_CENTER | wx.BOTTOM, 5)

        self.box.Fit(self)
        self.SetSizer(self.box)


    def InsertTraceback(self, list, traceback):
        #Add the traceback data
        for x in range(len(traceback)):
            data = traceback[x]
            list.InsertItem(x, os.path.basename(data[0])) # Filename
            list.SetItem(x, 1, str(data[1]))              # Line
            list.SetItem(x, 2, str(data[2]))              # Function
            list.SetItem(x, 3, str(data[3]))              # Code

            # Check whether this entry is from the demo module
            if data[0] == "<original>" or data[0] == "<modified>": # FIXME: make more generalised
                self.list.SetItemData(x, int(data[1]))   # Store line number for easy access
                # Give it a blue colour
                item = self.list.GetItem(x)
                item.SetTextColour(wx.BLUE)
                self.list.SetItem(item)
            else:
                self.list.SetItemData(x, -1)        # Editor can't jump into this one's code


    def OnItemSelected(self, event):
        # This occurs before OnDoubleClick and can be used to set the
        # currentItem. OnDoubleClick doesn't get a wxListEvent....
        self.currentItem = event.Index
        event.Skip()


    def OnDoubleClick(self, event):
        # If double-clicking on a demo's entry, jump to the line number
        line = self.list.GetItemData(self.currentItem)
        if line != -1:
            self.nb.SetSelection(1) # Switch to the code viewer tab
            wx.CallAfter(self.codePanel.JumpToLine, line-1, True)
        event.Skip()


#---------------------------------------------------------------------------

class MainPanel(wx.Panel):
    """
    Just a simple derived panel where we override Freeze and Thaw to work
    around an issue on wxGTK.
    """
    def Freeze(self):
        if 'wxMSW' in wx.PlatformInfo:
            return super(MainPanel, self).Freeze()

    def Thaw(self):
        if 'wxMSW' in wx.PlatformInfo:
            return super(MainPanel, self).Thaw()

#---------------------------------------------------------------------------

class DemoTaskBarIcon(TaskBarIcon):
    TBMENU_RESTORE = wx.NewId()
    TBMENU_CLOSE   = wx.NewId()
    TBMENU_CHANGE  = wx.NewId()
    TBMENU_REMOVE  = wx.NewId()

    def __init__(self, frame):
        TaskBarIcon.__init__(self, wx.adv.TBI_DOCK) # wx.adv.TBI_CUSTOM_STATUSITEM
        self.frame = frame

        # Set the image
        icon = self.MakeIcon(images.tickerScrapeLogo.GetImage())
        self.SetIcon(icon, "tickerScrapeLogo")
        self.imgidx = 1

        # bind some events
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=self.TBMENU_RESTORE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarChange, id=self.TBMENU_CHANGE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarRemove, id=self.TBMENU_REMOVE)


    def CreatePopupMenu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        menu = wx.Menu()
        menu.Append(self.TBMENU_RESTORE, "Restore wxPython Demo")
        menu.Append(self.TBMENU_CLOSE,   "Close wxPython Demo")
        menu.AppendSeparator()
        menu.Append(self.TBMENU_CHANGE, "Change the TB Icon")
        menu.Append(self.TBMENU_REMOVE, "Remove the TB Icon")
        return menu


    def MakeIcon(self, img):
        """
        The various platforms have different requirements for the
        icon size...
        """
        if "wxMSW" in wx.PlatformInfo:
            img = img.Scale(16, 16)
        elif "wxGTK" in wx.PlatformInfo:
            img = img.Scale(22, 22)
        # wxMac can be any size upto 128x128, so leave the source img alone....
        icon = wx.IconFromBitmap(img.ConvertToBitmap())
        return icon


    def OnTaskBarActivate(self, evt):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()


    def OnTaskBarClose(self, evt):
        wx.CallAfter(self.frame.Close)


    def OnTaskBarChange(self, evt):
        names = [ "WXPdemo", "Mondrian", "Pencil", "Carrot" ]
        name = names[self.imgidx]

        eImg = getattr(images, name)
        self.imgidx += 1
        if self.imgidx >= len(names):
            self.imgidx = 0

        icon = self.MakeIcon(eImg.Image)
        self.SetIcon(icon, "This is a new icon: " + name)


    def OnTaskBarRemove(self, evt):
        self.RemoveIcon()


#---------------------------------------------------------------------------
class TickerScrapeFrame(wx.Frame):

    overviewText = "Views Help"

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, size = (970, 720),
                          style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)

        self.SetMinSize((640,480))

        self.pnl = pnl = MainPanel(self)

        self.mgr = aui.AuiManager()
        self.mgr.SetManagedWindow(pnl)

        self.loaded = False
        self.cwd = os.getcwd()
        self.curOverview = ""
        self.viewPage = None
        self.codePage = None
        self.shell = None
        self.firstTime = True
        self.finddlg = None

        icon = images.tickerScrapeLogo.GetIcon()
        self.SetIcon(icon)

        try:
            self.tbicon = DemoTaskBarIcon(self)
        except:
            self.tbicon = None

        self.otherWin = None

        self.allowDocs = False
        self.downloading = False
        self.internetThread = None
        self.updating = False
        self.updateThread = None
        self.downloadImage = 2
        self.sendDownloadError = True
        self.downloadTimer = wx.Timer(self, wx.ID_ANY)

        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_ICONIZE, self.OnIconfiy)
        self.Bind(wx.EVT_MAXIMIZE, self.OnMaximize)
        self.Bind(wx.EVT_TIMER, self.OnDownloadTimer, self.downloadTimer)

        self.Centre(wx.BOTH)

        self.statusBar = self.CreateStatusBar(2)#, wx.ST_SIZEGRIP
        self.statusBar.SetStatusWidths([-2, -1])

        self.downloadGauge = wx.Gauge(self.statusBar, wx.ID_ANY, 50)
        self.downloadGauge.SetToolTip("Downloading Docs...")
        self.downloadGauge.Hide()

        self.updateGauge = wx.Gauge(self.statusBar, wx.ID_ANY, 50)
        self.updateGauge.Hide()

        self.sizeChanged = False
        self.Reposition()

        self.statusBar.Bind(wx.EVT_SIZE, self.OnStatusBarSize)
        self.statusBar.Bind(wx.EVT_IDLE, self.OnStatusBarIdle)

        self.statusBarTimer = wx.Timer(self, id=TIMER_STATUS_BAR)
        self.Bind(wx.EVT_TIMER, self.OnStatusBarTimer, self.statusBarTimer)

        statusText = "Welcome to TickerScrape %s" % version.VERSION_STRING
        self.SetStatusBarText(statusText)

        self.dying = False
        self.skipLoad = False
        self.allowAuiFloating = False

        def EmptyHandler(evt): pass

        self.ReadConfigurationFile()
        self.externalViews = HuntExternalViews()

        # Create a Notebook
        self.nb = wx.Notebook(pnl, -1, style=wx.CLIP_CHILDREN)

        self.useNbImages = True
        if 'wxMac' in wx.PlatformInfo:
            self.useNbImages = False
            
        if self.useNbImages:
            imgList = wx.ImageList(16, 16)
            for png in ["overview", "code", "demo"]:
                bmp = images.catalog[png].GetBitmap()
                imgList.Add(bmp)
            for indx in range(9):
                bmp = images.catalog["spinning_nb%d"%indx].GetBitmap()
                imgList.Add(bmp)
            self.nb.AssignImageList(imgList)

        self.BuildMenuBar()

        self.finddata = wx.FindReplaceData()
        self.finddata.SetFlags(wx.FR_DOWN)

        # Create a TreeCtrl
        leftPanel = wx.Panel(pnl, style=wx.TAB_TRAVERSAL|wx.CLIP_CHILDREN)
        self.treeMap = {}
        self.searchItems = {}

        self.tree = TickerScrapeTree(leftPanel)

        self.filter = wx.SearchCtrl(leftPanel, style=wx.TE_PROCESS_ENTER)
        self.filter.ShowCancelButton(True)
        self.filter.Bind(wx.EVT_TEXT, self.RecreateTree)
        self.filter.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN,
                         lambda e: self.filter.SetValue(''))
        self.filter.Bind(wx.EVT_TEXT_ENTER, self.OnSearch)

        searchMenu = wx.Menu()
        item = searchMenu.AppendRadioItem(-1, "Sample Name")
        self.Bind(wx.EVT_MENU, self.OnSearchMenu, item)
        item = searchMenu.AppendRadioItem(-1, "Sample Content")
        self.Bind(wx.EVT_MENU, self.OnSearchMenu, item)
        self.filter.SetMenu(searchMenu)

        self.RecreateTree()
        self.tree.SetExpansionState(self.expansionState)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnItemExpanded)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)
        self.tree.Bind(wx.EVT_LEFT_DOWN, self.OnTreeLeftDown)

        # Set up a wx.html.HtmlWindow on the Overview Notebook page
        # we put it in a panel first because there seems to be a
        # refresh bug of some sort (wxGTK) when it is directly in
        # the notebook...

        if 0:  # the old way
            self.ovr = wx.html.HtmlWindow(self.nb, -1, size=(400, 400))
            self.nb.AddPage(self.ovr, self.overviewText, imageId=0)

        else:  # hopefully I can remove this hacky code soon, see SF bug #216861
            panel = wx.Panel(self.nb, -1, style=wx.CLIP_CHILDREN)
            self.ovr = wx.html.HtmlWindow(panel, -1, size=(400, 400))
            self.nb.AddPage(panel, self.overviewText, imageId=0)

            def OnOvrSize(evt, ovr=self.ovr):
                ovr.SetSize(evt.GetSize())
            panel.Bind(wx.EVT_SIZE, OnOvrSize)
            panel.Bind(wx.EVT_ERASE_BACKGROUND, EmptyHandler)

        if "gtk2" in wx.PlatformInfo or "gtk3" in wx.PlatformInfo:
            self.ovr.SetStandardFonts()
        self.SetOverview(self.overviewText, mainOverview)


        # Set up a log window
        self.log = wx.TextCtrl(pnl, -1,
                              style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        if wx.Platform == "__WXMAC__":
            self.log.MacCheckSpelling(False)

        # Set the wxWindows log target to be this textctrl
        #wx.Log.SetActiveTarget(wx.LogTextCtrl(self.log))

        # But instead of the above we want to show how to use our own wx.Log class
        wx.Log.SetActiveTarget(MyLog(self.log))

        # for serious debugging
        #wx.Log.SetActiveTarget(wx.LogStderr())
        #wx.Log.SetTraceMask(wx.TraceMessages)

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        wx.GetApp().Bind(wx.EVT_ACTIVATE_APP, self.OnAppActivate)

        # add the windows to the splitter and split it.
        leftBox = wx.BoxSizer(wx.VERTICAL)
        leftBox.Add(self.tree, 1, wx.EXPAND)
        leftBox.Add(wx.StaticText(leftPanel, label = "Filter Views:"), 0, wx.TOP|wx.LEFT, 5)
        leftBox.Add(self.filter, 0, wx.EXPAND|wx.ALL, 5)
        if 'wxMac' in wx.PlatformInfo:
            leftBox.Add((5,5))  # Make sure there is room for the focus ring
        leftPanel.SetSizer(leftBox)

        # select initial items
        self.nb.SetSelection(0)
        self.tree.SelectItem(self.root)

        # Load 'Main' module
        self.LoadView(self.overviewText)
        self.loaded = True

        # select some other initial module?
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg.endswith('.py'):
                arg = arg[:-3]
            selectedDemo = self.treeMap.get(arg, None)
            if selectedDemo:
                self.tree.SelectItem(selectedDemo)
                self.tree.EnsureVisible(selectedDemo)

        # Use the aui manager to set up everything
        self.mgr.AddPane(self.nb, aui.AuiPaneInfo().CenterPane().Name("Notebook"))
        self.mgr.AddPane(leftPanel,
                         aui.AuiPaneInfo().
                         Left().Layer(2).BestSize((240, -1)).
                         MinSize((240, -1)).
                         Floatable(self.allowAuiFloating).FloatingSize((240, 700)).
                         Caption("Views").
                         CloseButton(False).
                         Name("DemoTree"))
        self.mgr.AddPane(self.log,
                         aui.AuiPaneInfo().
                         Bottom().BestSize((-1, 150)).
                         MinSize((-1, 140)).
                         Floatable(self.allowAuiFloating).FloatingSize((500, 160)).
                         Caption("TickerScrape Log Messages").
                         CloseButton(False).
                         Name("LogWindow"))

        self.auiConfigurations[DEFAULT_PERSPECTIVE] = self.mgr.SavePerspective()
        self.mgr.Update()

        self.mgr.SetAGWFlags(self.mgr.GetAGWFlags() ^ aui.AUI_MGR_TRANSPARENT_DRAG)

    def ReadConfigurationFile(self):

        self.auiConfigurations = {}
        self.expansionState = [0, 1]

        config = GetConfig()
        val = config.Read('ExpansionState')
        if val:
            self.expansionState = eval(val)

        val = config.Read('AUIPerspectives')
        if val:
            self.auiConfigurations = eval(val)

        val = config.Read('AllowDownloads')
        if val:
            self.allowDocs = eval(val)

        val = config.Read('AllowAUIFloating')
        if val:
            self.allowAuiFloating = eval(val)

        MakeDocDirs()
        pickledFile = GetDocFile()

        if not os.path.isfile(pickledFile):
            self.pickledData = {}
            return

        fid = open(pickledFile, "rb")
        try:
            self.pickledData = cPickle.load(fid)
        except:
            self.pickledData = {}

        fid.close()


    def BuildMenuBar(self):

        # Make a File menu
        self.mainmenu = wx.MenuBar()
        self.fileMenu = wx.Menu()

        loadItem = wx.MenuItem(self.fileMenu, -1, '&Load...', 'Load the portfolio from file')
        self.menuLoadItemId = loadItem.GetId()
        self.fileMenu.Append(loadItem)
        self.Bind(wx.EVT_MENU, self.OnFileLoad, loadItem)

        saveItem = wx.MenuItem(self.fileMenu, -1, '&Save\tCtrl-S', 'Save the portfolio')
        self.menuSaveItemId = saveItem.GetId()
        self.fileMenu.Append(saveItem)
        self.fileMenu.Enable(self.menuSaveItemId, Config.PortfolioChanged())
        self.Bind(wx.EVT_MENU, self.OnFileSave, saveItem)

        saveAsItem = wx.MenuItem(self.fileMenu, -1, 'Save &As...', 'Save the portfolio as file')
        self.menuSaveAsItemId = saveAsItem.GetId()
        self.fileMenu.Append(saveAsItem)
        self.Bind(wx.EVT_MENU, self.OnFileSaveAs, saveAsItem)

        self.fileMenu.AppendSeparator()

        wx.App.SetMacExitMenuItemId(9123)
        exitItem = wx.MenuItem(self.fileMenu, 9123, 
                               'E&xit\tCtrl-Q', 'Terminate the application')
        exitItem.SetBitmap(images.catalog['exit'].GetBitmap())
        self.fileMenu.Append(exitItem)
        self.Bind(wx.EVT_MENU, self.OnFileExit, exitItem)
        self.mainmenu.Append(self.fileMenu, '&File')

        # Make a Views menu
        menu = wx.Menu()
        for indx, item in enumerate(ViewTree.viewTree[:-1]):
            menuItem = wx.MenuItem(menu, -1, item[0])
            submenu = wx.Menu()
            for childItem in item[1]:
                mi = submenu.Append(-1, childItem)
                self.Bind(wx.EVT_MENU, self.OnViewsMenu, mi)
            menuItem.SetBitmap(images.catalog[ViewTree.viewPngs[indx+1]].GetBitmap())
            menuItem.SetSubMenu(submenu)
            menu.Append(menuItem)
        self.mainmenu.Append(menu, '&Views')

        # Make an Option menu

        menu = wx.Menu()
        item = wx.MenuItem(menu, -1, 'Allow download of docs', 'Docs for window styles and events from the web', wx.ITEM_CHECK)
        menu.Append(item)
        item.Check(self.allowDocs)
        self.Bind(wx.EVT_MENU, self.OnAllowDownload, item)

        item = wx.MenuItem(menu, -1, 'Delete saved docs', 'Deletes the cPickle file where docs are stored')
        item.SetBitmap(images.catalog['deletedocs'].GetBitmap())
        menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnDeleteDocs, item)

        menu.AppendSeparator()
        item = wx.MenuItem(menu, -1, 'Allow floating panes', 'Allows the demo panes to be floated using wxAUI', wx.ITEM_CHECK)
        menu.Append(item)
        item.Check(self.allowAuiFloating)
        self.Bind(wx.EVT_MENU, self.OnAllowAuiFloating, item)

        auiPerspectives = list(self.auiConfigurations.keys())
        auiPerspectives.sort()
        perspectivesMenu = wx.Menu()
        item = wx.MenuItem(perspectivesMenu, -1, DEFAULT_PERSPECTIVE, "Load startup default perspective", wx.ITEM_RADIO)
        self.Bind(wx.EVT_MENU, self.OnAUIPerspectives, item)
        perspectivesMenu.Append(item)
        for indx, key in enumerate(auiPerspectives):
            if key == DEFAULT_PERSPECTIVE:
                continue
            item = wx.MenuItem(perspectivesMenu, -1, key, "Load user perspective %d"%indx, wx.ITEM_RADIO)
            perspectivesMenu.Append(item)
            self.Bind(wx.EVT_MENU, self.OnAUIPerspectives, item)

        menu.Append(wx.ID_ANY, "&AUI Perspectives", perspectivesMenu)
        self.perspectives_menu = perspectivesMenu

        item = wx.MenuItem(menu, -1, 'Save Perspective', 'Save AUI perspective')
        item.SetBitmap(images.catalog['saveperspective'].GetBitmap())
        menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnSavePerspective, item)

        item = wx.MenuItem(menu, -1, 'Delete Perspective', 'Delete AUI perspective')
        item.SetBitmap(images.catalog['deleteperspective'].GetBitmap())
        menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnDeletePerspective, item)

        menu.AppendSeparator()

        item = wx.MenuItem(menu, -1, 'Restore Tree Expansion', 'Restore the initial tree expansion state')
        item.SetBitmap(images.catalog['expansion'].GetBitmap())
        menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnTreeExpansion, item)

        self.mainmenu.Append(menu, '&Options')
        self.options_menu = menu

        # Make a Help menu
        menu = wx.Menu()
        findItem = wx.MenuItem(menu, -1, '&Find\tCtrl-F', 'Find in the Demo Code')
        findItem.SetBitmap(images.catalog['find'].GetBitmap())
        if 'wxMac' not in wx.PlatformInfo:
            findNextItem = wx.MenuItem(menu, -1, 'Find &Next\tF3', 'Find Next')
        else:
            findNextItem = wx.MenuItem(menu, -1, 'Find &Next\tCtrl-G', 'Find Next')
        findNextItem.SetBitmap(images.catalog['findnext'].GetBitmap())
        menu.Append(findItem)
        menu.Append(findNextItem)
        menu.AppendSeparator()

        shellItem = wx.MenuItem(menu, -1, 'Open Py&Shell Window\tF5',
                                'An interactive interpreter window with the demo app and frame objects in the namesapce')
        shellItem.SetBitmap(images.catalog['pyshell'].GetBitmap())
        menu.Append(shellItem)
        inspToolItem = wx.MenuItem(menu, -1, 'Open &Widget Inspector\tF6',
                                   'A tool that lets you browse the live widgets and sizers in an application')
        inspToolItem.SetBitmap(images.catalog['inspect'].GetBitmap())
        menu.Append(inspToolItem)
        menu.AppendSeparator()
        reloadApp = menu.Append(-1, '&Reload', 'Reload application')
        updateApp = menu.Append(-1, '&Check for updates', 'Check for updates')
        menu.AppendSeparator()
        helpAbout = menu.Append(wx.ID_ABOUT, 
                                '&About TickerScrape', 
                                'About TickerScrape')

        self.Bind(wx.EVT_MENU, self.OnOpenShellWindow, shellItem)
        self.Bind(wx.EVT_MENU, self.OnOpenWidgetInspector, inspToolItem)
        self.Bind(wx.EVT_MENU, self.OnReload, reloadApp)
        self.Bind(wx.EVT_MENU, self.OnUpdate, updateApp)
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, helpAbout)
        self.Bind(wx.EVT_MENU, self.OnHelpFind,  findItem)
        self.Bind(wx.EVT_MENU, self.OnFindNext,  findNextItem)
        self.Bind(wx.EVT_FIND, self.OnFind)
        self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateFindItems, findItem)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateFindItems, findNextItem)
        self.mainmenu.Append(menu, '&Help')
        self.SetMenuBar(self.mainmenu)

        self.EnableAUIMenu()

        if False:
            # This is another way to set Accelerators, in addition to
            # using the '\t<key>' syntax in the menu items.
            aTable = wx.AcceleratorTable([(wx.ACCEL_ALT,  ord('X'), exitItem.GetId()),
                                          (wx.ACCEL_CTRL, ord('H'), helpAbout.GetId()),
                                          (wx.ACCEL_CTRL, ord('F'), findItem.GetId()),
                                          (wx.ACCEL_NORMAL, wx.WXK_F3, findNextItem.GetId()),
                                          (wx.ACCEL_NORMAL, wx.WXK_F9, shellItem.GetId()),
                                          ])
            self.SetAcceleratorTable(aTable)

    #---------------------------------------------
    def EnableFileMenuSaveItem(self, enable):
        self.fileMenu.Enable(self.menuSaveItemId, enable)

    #---------------------------------------------
    def RecreateTree(self, evt=None):
        # Catch the search type (name or content)
        searchMenu = self.filter.GetMenu().GetMenuItems()
        fullSearch = searchMenu[1].IsChecked()

        if evt:
            if fullSearch:
                # Do not`scan all the demo files for every char
                # the user input, use wx.EVT_TEXT_ENTER instead
                return

        expansionState = self.tree.GetExpansionState()

        current = None
        item = self.tree.GetSelection()
        if item:
            prnt = self.tree.GetItemParent(item)
            if prnt:
                current = (self.tree.GetItemText(item),
                           self.tree.GetItemText(prnt))

        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Views")
        self.tree.SetItemImage(self.root, 0)
        self.tree.SetItemData(self.root, 0)

        treeFont = self.tree.GetFont()
        catFont = self.tree.GetFont()

        # The native treectrl on MSW has a bug where it doesn't draw
        # all of the text for an item if the font is larger than the
        # default.  It seems to be clipping the item's label as if it
        # was the size of the same label in the default font.
        if USE_CUSTOMTREECTRL or 'wxMSW' not in wx.PlatformInfo:
            treeFont.SetPointSize(treeFont.GetPointSize()+2)

        treeFont.SetWeight(wx.FONTWEIGHT_BOLD)
        catFont.SetWeight(wx.FONTWEIGHT_BOLD)
        self.tree.SetItemFont(self.root, treeFont)

        firstChild = None
        selectItem = None
        filter = self.filter.GetValue()
        count = 0

        for category, items in ViewTree.viewTree:
            count += 1
            if filter:
                if fullSearch:
                    items = self.searchItems[category]
                else:
                    items = [item for item in items if filter.lower() in item.lower()]
            if items:
                child = self.tree.AppendItem(self.root, category, image=count)
                self.tree.SetItemFont(child, catFont)
                self.tree.SetItemData(child, count)
                if not firstChild: firstChild = child
                for childItem in items:
                    image = count
                    if DoesModifiedExist(childItem):
                        image = len(ViewTree.viewPngs)
                    theDemo = self.tree.AppendItem(child, childItem, image=image)
                    self.tree.SetItemData(theDemo, count)
                    self.treeMap[childItem] = theDemo
                    if current and (childItem, category) == current:
                        selectItem = theDemo


        self.tree.Expand(self.root)
        if firstChild:
            self.tree.Expand(firstChild)
        if filter:
            self.tree.ExpandAll()
        elif expansionState:
            self.tree.SetExpansionState(expansionState)
        if selectItem:
            self.skipLoad = True
            self.tree.SelectItem(selectItem)
            self.skipLoad = False

        self.tree.Thaw()
        self.searchItems = {}

    def SetStatusBarText(self, msg, time = 3):
        # Set the status
        self.statusBar.SetStatusText(msg, 0)

        # Cancel the timer
        self.statusBarTimer.Stop()

        # Should we set a timer?
        if time:
            self.statusBarTimer.Start(time * 1000)

    def OnStatusBarTimer(self, evt):
        # Expiration callback for the status bar timer: clear the text
        self.statusBar.SetStatusText("", 0)

    def OnStatusBarSize(self, evt):
        self.Reposition()  # for normal size events

        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.
        self.sizeChanged = True


    def OnStatusBarIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()


    # reposition the download gauge
    def Reposition(self):
        # rect = self.statusBar.GetFieldRect(1)
        # self.downloadGauge.SetPosition((rect.x+2, rect.y+2))
        # self.downloadGauge.SetSize((rect.width-4, rect.height-4))
        self.sizeChanged = False


    def OnSearchMenu(self, event):

        # Catch the search type (name or content)
        searchMenu = self.filter.GetMenu().GetMenuItems()
        fullSearch = searchMenu[1].IsChecked()

        if fullSearch:
            self.OnSearch()
        else:
            self.RecreateTree()


    def OnSearch(self, event=None):

        value = self.filter.GetValue()
        if not value:
            self.RecreateTree()
            return

        wx.BeginBusyCursor()

        for category, items in ViewTree.viewTree:
            self.searchItems[category] = []
            for childItem in items:
                if SearchView(childItem, value):
                    self.searchItems[category].append(childItem)

        wx.EndBusyCursor()
        self.RecreateTree()


    def SetTreeModified(self, modified):
        item = self.tree.GetSelection()
        if modified:
            image = len(ViewTree.viewPngs)
        else:
            image = self.tree.GetItemData(item)
        self.tree.SetItemImage(item, image)


    def WriteText(self, text):
        if text[-1:] == '\n':
            text = text[:-1]
        wx.LogMessage(text)

    def write(self, txt):
        self.WriteText(txt)

    #---------------------------------------------
    def OnItemExpanded(self, event):
        item = event.GetItem()
        wx.LogMessage("OnItemExpanded: %s" % self.tree.GetItemText(item))
        event.Skip()

    #---------------------------------------------
    def OnItemCollapsed(self, event):
        item = event.GetItem()
        wx.LogMessage("OnItemCollapsed: %s" % self.tree.GetItemText(item))
        event.Skip()

    #---------------------------------------------
    def OnTreeLeftDown(self, event):
        # reset the overview text if the tree item is clicked on again
        pt = event.GetPosition()
        item, flags = self.tree.HitTest(pt)
        if item == self.tree.GetSelection():
            self.SetOverview(self.tree.GetItemText(item)+" Help", self.curOverview)
        event.Skip()

    #---------------------------------------------
    def OnSelChanged(self, event):
        if self.dying or not self.loaded or self.skipLoad:
            return

        self.StopDownload()

        item = event.GetItem()
        itemText = self.tree.GetItemText(item)
        self.LoadView(itemText)

        self.StartDownload()

    #---------------------------------------------
    def LoadView(self, viewName):
        try:
            wx.BeginBusyCursor()
            self.pnl.Freeze()

            os.chdir(self.cwd)
            self.ShutdownViewModule()

            if viewName == self.overviewText:
                # User selected the "Views" node
                # ie: _this_ module
                # Changing the main window at runtime not yet supported...
                self.viewModule = ViewModule(__name__)
                self.SetOverview(self.overviewText, mainOverview)
                self.LoadViewSource()
                self.UpdateNotebook(0)
            else:
                if os.path.exists(GetOriginalFilename(viewName)):
                    wx.LogMessage("Loading view %s.py..." % viewName)
                    self.viewModule = ViewModule(viewName)
                    self.LoadViewSource()

                else:
                    package, overview = LookForExternals(self.externalViews, viewName)

                    if package:
                        wx.LogMessage("Loading view %s.py..." % ("%s/%s"%(package, viewName)))
                        self.viewModule = ViewModule("%s/%s"%(package, viewName))
                        self.LoadViewSource()
                    elif overview:
                        self.SetOverview(viewName, overview)
                        self.codePage = None
                        self.UpdateNotebook(0)
                    else:
                        self.SetOverview("Views Help", mainOverview)
                        self.codePage = None
                        self.UpdateNotebook(0)

        finally:
            wx.EndBusyCursor()
            self.pnl.Thaw()

    #---------------------------------------------
    def LoadViewSource(self):
        self.codePage = None
        self.codePage = CodePanel(self.nb, self)
        self.codePage.LoadView(self.viewModule)

    #---------------------------------------------
    def RunModule(self):
        """Runs the active module"""

        module = self.viewModule.GetActive()
        self.ShutdownViewModule()
        overviewText = ""

        # o The RunTest() for all samples must now return a window that can
        #   be placed in a tab in the main notebook.
        # o If an error occurs (or has occurred before) an error tab is created.

        if module is not None:
            wx.LogMessage("Loading view module...")
            if hasattr(module, "overview"):
                overviewText = module.overview

            try:
                if hasattr(module, "GetWindow"):
                    self.viewPage = module.GetWindow(self, self.nb, self)
                elif hasattr(module, "runTest"): # Obsoleted
                    self.viewPage = module.runTest(self, self.nb, self)
            except:
                self.viewPage = ViewModuleErrorPanel(self.nb, self.codePage,
                                                     ViewModuleError(sys.exc_info()), self)

            wx.LogMessage("Loaded %s for module %s" % (self.viewPage, module))

            bg = self.nb.GetThemeBackgroundColour()
            if bg:
                self.viewPage.SetBackgroundColour(bg)

            assert self.viewPage is not None, "runTest must return a window!"

        else:
            # There was a previous error in compiling or exec-ing
            self.viewPage = ViewModuleErrorPanel(self.nb, self.codePage,
                                                 self.viewModule.GetErrorInfo(), self)

        self.SetOverview(self.viewModule.name + " Help", overviewText)

        if self.firstTime:
            # change to the view page the first time a module is run
            self.UpdateNotebook(2)
            self.firstTime = False
        else:
            # otherwise just stay on the same tab in case the user has changed to another one
            self.UpdateNotebook()

    #---------------------------------------------
    def ShutdownViewModule(self):
        if self.viewPage:
            # inform the window that it's time to quit if it cares
            if hasattr(self.viewPage, "ShutdownView"):
                self.viewPage.ShutdownView()
                # wx.YieldIfNeeded() # in case the page has pending events
            elif hasattr(self.viewPage, "ShutdownDemo"):
                # Backward compatibility
                self.viewPage.ShutdownDemo()
                # wx.YieldIfNeeded() # in case the page has pending events
            self.viewPage = None

    #---------------------------------------------
    def UpdateNotebook(self, select = -1):
        nb = self.nb
        debug = False
        self.pnl.Freeze()

        def UpdatePage(page, pageText):
            pageExists = False
            pagePos = -1
            for i in range(nb.GetPageCount()):
                if nb.GetPageText(i) == pageText:
                    pageExists = True
                    pagePos = i
                    break

            if page:
                if not pageExists:
                    # Add a new page
                    nb.AddPage(page, pageText, imageId=nb.GetPageCount())
                    if debug: wx.LogMessage("DBG: ADDED %s" % pageText)
                else:
                    if nb.GetPage(pagePos) != page:
                        # Reload an existing page
                        nb.DeletePage(pagePos)
                        nb.InsertPage(pagePos, page, pageText, imageId=pagePos)
                        if debug: wx.LogMessage("DBG: RELOADED %s" % pageText)
                    else:
                        # Excellent! No redraw/flicker
                        if debug: wx.LogMessage("DBG: SAVED from reloading %s" % pageText)
            elif pageExists:
                # Delete a page
                nb.DeletePage(pagePos)
                if debug: wx.LogMessage("DBG: DELETED %s" % pageText)
            else:
                if debug: wx.LogMessage("DBG: STILL GONE - %s" % pageText)

        if select == -1:
            select = nb.GetSelection()

        UpdatePage(self.codePage, "Code")
        UpdatePage(self.viewPage, "View")

        if select >= 0 and select < nb.GetPageCount():
            nb.SetSelection(select)

        self.pnl.Thaw()

    #---------------------------------------------
    def SetOverview(self, name, text):
        self.curOverview = text
        lead = text[:6]
        if lead != '<html>' and lead != '<HTML>':
            text = '<br>'.join(text.split('\n'))
        # if wx.USE_UNICODE:
            # text = text.decode('iso8859_1')
        self.ovr.SetPage(text)
        self.nb.SetPageText(0, os.path.split(name)[1])

    #---------------------------------------------

    def StartDownload(self):

        if self.downloading or not self.allowDocs:
            return

        item = self.tree.GetSelection()
        if self.tree.ItemHasChildren(item):
            return

        itemText = self.tree.GetItemText(item)

        if itemText in self.pickledData:
            self.LoadDocumentation(self.pickledData[itemText])
            return

        text = self.curOverview
        text += "<br><p><b>Checking for documentation on the wxWidgets website, please stand by...</b><br>"

        lead = text[:6]
        if lead != '<html>' and lead != '<HTML>':
            text = '<br>'.join(text.split('\n'))

        self.ovr.SetPage(text)

        self.downloadTimer.Start(100)
        self.downloadGauge.Show()
        self.Reposition()
        self.downloading = True
        self.internetThread = InternetThread(self, itemText)

    #---------------------------------------------

    def StopDownload(self, error=None):

        self.downloadTimer.Stop()

        if not self.downloading:
            return

        if error:
            if self.sendDownloadError:
                self.log.AppendText("Warning: problems in downloading documentation from the wxWidgets website.\n")
                self.log.AppendText("Error message from the documentation downloader was:\n")
                self.log.AppendText("\n".join(error))
                self.sendDownloadError = False

        if self.useNbImages:
            self.nb.SetPageImage(0, 0)

        self.internetThread.keepRunning = False
        self.internetThread = None

        self.downloading = False
        self.downloadGauge.Hide()
        self.Reposition()

        text = self.curOverview

        lead = text[:6]
        if lead != '<html>' and lead != '<HTML>':
            text = '<br>'.join(text.split('\n'))

        self.ovr.SetPage(text)

    #---------------------------------------------

    def LoadDocumentation(self, data):

        text = self.curOverview
        addHtml = False

        if '<html>' not in text and '<HTML>' not in text:
            text = '<br>'.join(text.split('\n'))

        styles, events, extra, appearance = data

        if appearance:
            text += FormatImages(appearance)

        for names, values in zip(["Styles", "Extra Styles", "Events"], [styles, extra, events]):
            if not values:
                continue

            headers = (names == "Events" and [2] or [3])[0]
            text += "<p>" + FormatDocs(names, values, headers)

        item = self.tree.GetSelection()
        itemText = self.tree.GetItemText(item)

        self.pickledData[itemText] = data

        if six.PY2:
            # TODO: verify that this encoding is correct
            text = text.decode('iso8859_1')

        self.StopDownload()
        self.ovr.SetPage(text)
        #print("load time: ", time.time() - start)


    #---------------------------------------------
    def GetUpdateName(self, url):
        try:
            fid = urllib.request.urlopen(url)
            originalText = fid.read().decode("utf-8")
        except (IOError, urllib.error.HTTPError):
            # Unable to get to the internet
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            return None, message
        except:
            # Some other strange error...
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            return None, message

        ver_major, ver_minor = version.VERSION_STRING.split('.')

        #self.log.AppendText("Version: %s %s\n" % (ver_major, ver_minor))
        #self.log.AppendText("Platform: %s, machine: %s\n" % (platform.system(), platform.machine()))
        
        p = ""
        cpu = ""
        install_suffix = ""
        update_suffix = ".tgz"

        if platform.system() == 'Windows':
            p = "windows"
            if re.match(r'(.*)64', platform.machine(), re.M|re.I):
                cpu = "x86_64"
            else:
                cpu = "x86"

            install_suffix = "-setup.exe"
        if platform.system() == 'Linux':
            p = "linux"
            if re.match(r'(.*)64', platform.machine(), re.M|re.I):
                cpu = "x86_64"
            else:
                cpu = "x86"

            install_suffix = ".tgz"

        install_regex = "tickerscrape-install-([0-9]*).([0-9]*)-%s-%s%s" % (p, cpu, install_suffix)
        update_regex = "tickerscrape-update-([0-9]*).([0-9]*)%s" % (update_suffix)
        #self.log.AppendText("Expected platform: %s-%s\n" % (p, cpu))
        #self.log.AppendText("Installer: %s\n" % (install_regex))
        #self.log.AppendText("Updater: %s\n" % (update_regex))

        # Initialize the install & update versions 
        # (which may end up being None...)
        install_ver_major = None
        install_ver_minor = None
        install_fname = None
        update_ver_major = None
        update_ver_minor = None
        update_fname = None

        # Parse the contents
        soup = BeautifulSoup(originalText, 'lxml')

        # Get the list of install & update packages
        a = soup.find_all('a')
        for i in a:
            fname = i['href']
            
            if fname == '/':
                continue
            self.log.AppendText("File download available: %s\n" % fname)

            s = re.search(install_regex, fname)
            if s: 
                # Get the major, minor version of the file
                major, minor = s.group(1), s.group(2)
                
                # Continue if not newer than current version
                if (major < ver_major):
                    continue
                if (major == ver_major and minor <= ver_minor):
                    continue

                # Continue if not newer than previsuly-found version
                if install_ver_major != None:
                    if install_ver_major > major:
                        continue
                if install_ver_minor != None:
                    if install_ver_minor > minor:
                        continue

                install_ver_major, install_ver_minor = major, minor
                install_fname = fname

                self.log.AppendText("Installer: %s\n" % (fname))

            s = re.search(update_regex, fname)
            if s: 
                # Get the major, minor version of the file
                major, minor = s.group(1), s.group(2)
                
                # Continue if not newer than current version
                if (major != ver_major):
                    continue
                if (minor <= ver_minor):
                    continue

                # Continue if not newer than previsuly-found version
                if update_ver_major != None:
                    if update_ver_major > major:
                        continue
                if update_ver_minor != None:
                    if update_ver_minor > minor:
                        continue

                update_ver_major, update_ver_minor = major, minor
                update_fname = fname

                self.log.AppendText("Updater: %s\n" % (fname))

        # If both the install and the updater have the same major and minor
        # version, use the updater
        if install_fname and update_fname:
            if install_ver_major > update_ver_major:
                update_fname = None
        if install_fname and update_fname:
            if install_ver_major == update_ver_major and install_ver_minor > update_ver_minor:
                update_fname = None
        if install_fname and update_fname:
            install_fname = None

        download_fname = None

        if install_fname:
            download_fname = install_fname
        if update_fname:
            download_fname = update_fname

        return download_fname, None

    def MessageDialogOK(self, msg, caption):
        dlg = wx.MessageDialog(self, msg, caption,
                               wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    #---------------------------------------------

    # Update methods
    def StartUpdate(self):

        #self.log.AppendText("In %s()\n" % (sys._getframe().f_code.co_name))
        url = "http://tickerscrape.com/downloads/"
        fname, err = self.GetUpdateName(url)

        self.log.AppendText("GetUpdateName() ret %s, %s\n" % (fname, err))
        if err:
            self.MessageDialogOK("TickerScrape update error: %s" % err[0],
                                 "Update TickerScrape")
            return

        if not fname:
            self.MessageDialogOK("TickerScrape is already up to date.",
                                 "Update TickerScrape")
            return

        dlg = wx.MessageDialog(self, 
                               "Download and install %s?" % fname,
                               "Update TickerScrape",
                               wx.YES_NO | wx.ICON_INFORMATION
                               )
        ret = dlg.ShowModal()
        dlg.Destroy()
        dlg = None

        if ret == wx.ID_NO:
            return

        # Make the downloads directory
        try:
            os.mkdir("downloads")
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir("downloads"):
                pass
            else:
                self.log.AppendText("Mkdir downloads errno %d\n" % (exc.errno))
                return

        self.log.AppendText("Downloading %s...\n" % (url + fname))

        try:
            d = urllib.request.urlopen(url + fname)
            meta = d.info()
            d_size = int(meta["Content-Length"])
            self.log.AppendText("%s size %d\n" % (fname, d_size))
        except (IOError, urllib.error.HTTPError):
            # Unable to get to the internet
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            return
        except:
            # Some other strange error...
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            return

        dlg = wx.ProgressDialog("Update TickerScrape",
                                "Downloading %s ..." % fname,
                                maximum = d_size,
                                parent=self,
                                style = 0
                                | wx.PD_APP_MODAL
                                | wx.PD_CAN_ABORT
                                #| wx.PD_CAN_SKIP
                                #| wx.PD_ELAPSED_TIME
                                #| wx.PD_ESTIMATED_TIME
                                #| wx.PD_REMAINING_TIME
                                #| wx.PD_AUTO_HIDE
                                )
        try:
            f = open("downloads/" + fname, "wb")
            f_size = 0
            keep_going = True
            while keep_going:
                chunk = d.read(1024*1024)
                wx.Yield()
                if not chunk:
                    break
                f.write(chunk)
                f_size = f.tell()
                (keep_going, skip) = dlg.Update(f_size)

            f.close()
            
        except (IOError, urllib.error.HTTPError):
            # Unable to get to the internet
            dlg.Destroy()
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            self.MessageDialogOK("TickerScrape update error: %s" % message,
                                 "Update TickerScrape")
            return
        except:
            # Some other strange error...
            dlg.Destroy()
            t, v = sys.exc_info()[:2]
            message = traceback.format_exception_only(t, v)
            self.MessageDialogOK("TickerScrape update error: %s" % message,
                                 "Update TickerScrape")
            return

        was_cancelled = dlg.WasCancelled()

        # For some reason the dialog does not close until we return out
        # TO DO: figure this out. Yield() makes no difference, Hide() also
        # does not help.
        dlg.Hide()
        dlg.Destroy()
        dlg = None
        wx.Yield()

        if was_cancelled:
            self.MessageDialogOK("TickerScrape update cancelled.",
                                 "Update TickerScrape")
            return

        # The install has been downloaded. 
        # Install it and restart the app
        if os.path.isdir(".git"):
            self.MessageDialogOK("Detected Git sandbox, skipping installation.",
                                 "Update TickerScrape")
            return

        if re.search("^tickerscrape-(.*).exe", fname):
            self.log.AppendText("Executing downloads/%s\n" % fname)
            ExecApp("downloads/%s" % fname)
                
        elif re.search("^tickerscrape-(.*).tgz", fname):
            tar = tarfile.open("downloads/" + fname, mode="r:gz")
            self.log.AppendText("Extracting downloads/%s\n" % fname)
            tar.extractall()
            tar.close()
                
            self.log.AppendText("Restarting app\n")
                
            RestartApp("--no-splash")
        else:
            self.log.AppendText("downloads/%s: unexpected suffix\n" % fname)

    #---------------------------------------------

    # Menu methods
    def OnFileLoad(self, *event):
        wildcard = "XML files (*.xml)|*.xml|" \
                   "All files (*.*)|*.*"
        
        # Create the dialog
        dlg = wx.FileDialog(
            self, 
            message="Load portfolio from file",
            defaultDir=wx.StandardPaths.Get().GetUserDataDir(),
            defaultFile="wxPortfolio.xml",
            wildcard=wildcard,
            style=wx.FD_OPEN|
                  wx.FD_CHANGE_DIR|wx.FD_FILE_MUST_EXIST|
                  wx.FD_PREVIEW
            )

        # Show the dialog and retrieve the user response. 
        # If it is the OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()
            
            Config.PortfolioReadXml(paths[0])

            self.SetStatusBarText("Portfolio loaded from '%s'" % paths[0])

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

    def OnFileSave(self, *event):
        Config.PortfolioSave()
        self.SetStatusBarText("Portfolio saved")

    def OnFileSaveAs(self, *event):
        wildcard = "XML files (*.xml)|*.xml|" \
                   "All files (*.*)|*.*"

        # Create the dialog.
        dlg = wx.FileDialog(
            self, 
            message="Save file as ...", 
            defaultDir=wx.StandardPaths.Get().GetUserDataDir(),
            defaultFile="", 
            wildcard=wildcard, 
            style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT
        )

        # This sets the default filter that the user will initially see. 
        # Otherwise, the first filter in the list will be used by default.
        dlg.SetFilterIndex(0)
        
        # Show the dialog and retrieve the user response. If it is 
        # the OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            
            Config.PortfolioSaveXml(path)

            self.SetStatusBarText("Portfolio saved to %s" % path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

    def OnFileExit(self, *event):
        self.statusBarTimer.Stop()
        self.Close()

    def OnAllowDownload(self, event):

        self.allowDocs = event.IsChecked()
        if self.allowDocs:
            self.StartDownload()
        else:
            self.StopDownload()


    def OnDeleteDocs(self, event):

        deleteMsg = "You are about to delete the downloaded documentation.\n" + \
                    "Do you want to continue?"
        dlg = wx.MessageDialog(self, deleteMsg, "wxPython Demo",
                               wx.YES_NO | wx.NO_DEFAULT| wx.ICON_QUESTION)
        result = dlg.ShowModal()
        if result == wx.ID_NO:
            dlg.Destroy()
            return

        dlg.Destroy()

        busy = wx.BusyInfo("Deleting downloaded data...")
        wx.SafeYield()

        pickledFile = GetDocFile()
        docDir = os.path.split(pickledFile)[0]

        if os.path.exists(docDir):
            shutil.rmtree(docDir, ignore_errors=True)

        self.pickledData = {}
        del busy
        self.sendDownloadError = True


    def OnAllowAuiFloating(self, event):

        self.allowAuiFloating = event.Checked()
        for pane in self.mgr.GetAllPanes():
            if pane.name != "Notebook":
                pane.Floatable(self.allowAuiFloating)

        self.EnableAUIMenu()
        self.mgr.Update()


    def EnableAUIMenu(self):

        menuItems = self.options_menu.GetMenuItems()
        for indx in range(4, len(menuItems)-1):
            item = menuItems[indx]
            item.Enable(self.allowAuiFloating)


    def OnAUIPerspectives(self, event):
        perspective = self.perspectives_menu.GetLabel(event.GetId())
        self.mgr.LoadPerspective(self.auiConfigurations[perspective])
        self.mgr.Update()


    def OnSavePerspective(self, event):
        dlg = wx.TextEntryDialog(self, "Enter a name for the new perspective:", "AUI Configuration")

        dlg.SetValue(("Perspective %d")%(len(self.auiConfigurations)+1))
        if dlg.ShowModal() != wx.ID_OK:
            return

        perspectiveName = dlg.GetValue()
        menuItems = self.perspectives_menu.GetMenuItems()
        for item in menuItems:
            if item.GetLabel() == perspectiveName:
                wx.MessageBox("The selected perspective name:\n\n%s\n\nAlready exists."%perspectiveName,
                              "Error", style=wx.ICON_ERROR)
                return

        item = wx.MenuItem(self.perspectives_menu, -1, dlg.GetValue(),
                           "Load user perspective %d"%(len(self.auiConfigurations)+1),
                           wx.ITEM_RADIO)
        self.Bind(wx.EVT_MENU, self.OnAUIPerspectives, item)
        self.perspectives_menu.Append(item)
        item.Check(True)
        self.auiConfigurations.update({dlg.GetValue(): self.mgr.SavePerspective()})


    def OnDeletePerspective(self, event):
        menuItems = self.perspectives_menu.GetMenuItems()
        lst = []
        loadDefault = False

        for indx, item in enumerate(menuItems):
            if indx > 0:
                lst.append(item.GetLabel())

        dlg = wx.MultiChoiceDialog(self,
                                   "Please select the perspectives\nyou would like to delete:",
                                   "Delete AUI Perspectives", lst)

        if dlg.ShowModal() == wx.ID_OK:
            selections = dlg.GetSelections()
            strings = [lst[x] for x in selections]
            for sel in strings:
                self.auiConfigurations.pop(sel)
                item = menuItems[lst.index(sel)+1]
                if item.IsChecked():
                    loadDefault = True
                    self.perspectives_menu.GetMenuItems()[0].Check(True)
                self.perspectives_menu.DeleteItem(item)
                lst.remove(sel)

        if loadDefault:
            self.mgr.LoadPerspective(self.auiConfigurations[DEFAULT_PERSPECTIVE])
            self.mgr.Update()


    def OnTreeExpansion(self, event):
        self.tree.SetExpansionState(self.expansionState)


    def OnReload(self, event):
        # Restart the whole app
        RestartApp("--no-splash")

    def OnUpdate(self, event):
        self.StartUpdate()

    def OnHelpAbout(self, event):
        from About import MyAboutBox
        about = MyAboutBox(self)
        about.ShowModal()
        about.Destroy()

    def OnHelpFind(self, event):
        if self.finddlg != None:
            return

        self.nb.SetSelection(1)
        self.finddlg = wx.FindReplaceDialog(self, self.finddata, "Find",
                        wx.FR_NOMATCHCASE | wx.FR_NOWHOLEWORD)
        self.finddlg.Show(True)


    def OnUpdateFindItems(self, evt):
        evt.Enable(self.finddlg == None)


    def OnFind(self, event):
        editor = self.codePage.editor
        self.nb.SetSelection(1)
        end = editor.GetLastPosition()
        textstring = editor.GetRange(0, end).lower()
        findstring = self.finddata.GetFindString().lower()
        backward = not (self.finddata.GetFlags() & wx.FR_DOWN)
        if backward:
            start = editor.GetSelection()[0]
            loc = textstring.rfind(findstring, 0, start)
        else:
            start = editor.GetSelection()[1]
            loc = textstring.find(findstring, start)
        if loc == -1 and start != 0:
            # string not found, start at beginning
            if backward:
                start = end
                loc = textstring.rfind(findstring, 0, start)
            else:
                start = 0
                loc = textstring.find(findstring, start)
        if loc == -1:
            dlg = wx.MessageDialog(self, 'Find String Not Found',
                          'Find String Not Found in Demo File',
                          wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        if self.finddlg:
            if loc == -1:
                self.finddlg.SetFocus()
                return
            else:
                self.finddlg.Destroy()
                self.finddlg = None
        editor.ShowPosition(loc)
        editor.SetSelection(loc, loc + len(findstring))



    def OnFindNext(self, event):
        if self.finddata.GetFindString():
            self.OnFind(event)
        else:
            self.OnHelpFind(event)

    def OnFindClose(self, event):
        event.GetDialog().Destroy()
        self.finddlg = None


    def OnOpenShellWindow(self, evt):
        if self.shell:
            # if it already exists then just make sure it's visible
            s = self.shell
            if s.IsIconized():
                s.Iconize(False)
            s.Raise()
        else:
            # Make a PyShell window
            from wx import py
            namespace = { 'wx'    : wx,
                          'app'   : wx.GetApp(),
                          'frame' : self,
                          }
            self.shell = py.shell.ShellFrame(None, locals=namespace)
            self.shell.SetSize((640,480))
            self.shell.Show()

            # Hook the close event of the main frame window so that we
            # close the shell at the same time if it still exists
            def CloseShell(evt):
                if self.shell:
                    self.shell.Close()
                evt.Skip()
            self.Bind(wx.EVT_CLOSE, CloseShell)


    def OnOpenWidgetInspector(self, evt):
        # Activate the widget inspection tool, giving it a widget to preselect
        # in the tree.  Use either the one under the cursor, if any, or this
        # frame.
        from wx.lib.inspection import InspectionTool
        wnd = wx.FindWindowAtPointer()
        if not wnd:
            wnd = self
        InspectionTool().Show(wnd, True)


    #---------------------------------------------
    def OnCloseWindow(self, event):
        self.mgr.UnInit()
        self.dying = True
        self.viewPage = None
        self.codePage = None
        self.mainmenu = None
        self.StopDownload()
        self.StopUpdate()

        # if self.tbicon is not None:
            # self.tbicon.Destroy()

        config = GetConfig()
        config.Write('ExpansionState', str(self.tree.GetExpansionState()))
        config.Write('AUIPerspectives', str(self.auiConfigurations))
        config.Write('AllowDownloads', str(self.allowDocs))
        config.Write('AllowAUIFloating', str(self.allowAuiFloating))

        config.Flush()

        MakeDocDirs()
        pickledFile = GetDocFile()
        fid = open(pickledFile, "wb")
        cPickle.dump(self.pickledData, fid, cPickle.HIGHEST_PROTOCOL)
        fid.close()

        # Has portfolio config changed?
        if Config.PortfolioChanged():
            if wx.MessageBox("Save updated portfolio?",
                             "Please confirm",
                             wx.ICON_QUESTION | wx.YES_NO) == wx.YES:
                Config.PortfolioSave()

        self.statusBarTimer.Stop()
        self.Destroy()


    #---------------------------------------------
    def OnIdle(self, event):
        if self.otherWin:
            self.otherWin.Raise()
            self.viewPage = self.otherWin
            self.otherWin = None


    #---------------------------------------------

    def OnDownloadTimer(self, event):

        self.downloadGauge.Pulse()

        self.downloadImage += 1
        if self.downloadImage > 9:
            self.downloadImage = 3

        if self.useNbImages:
            self.nb.SetPageImage(0, self.downloadImage)
##        wx.SafeYield()

    #---------------------------------------------

    def ShowTip(self):
        config = GetConfig()
        showTipText = config.Read("tips")
        if showTipText:
            showTip, index = eval(showTipText)
        else:
            showTip, index = (1, 0)

        # if showTip:
            # tp = wx.CreateFileTipProvider(opj("data/tips.txt"), index)
            # showTip = wx.ShowTip(self, tp)
            # index = tp.GetCurrentTip()
            # config.Write("tips", str( (showTip, index) ))
            # config.Flush()

    #---------------------------------------------
    def OnViewsMenu(self, event):
        try:
            selectedView = self.treeMap[self.mainmenu.GetLabel(event.GetId())]
        except:
            selectedView = None
        if selectedView:
            self.tree.SelectItem(selectedView)
            self.tree.EnsureVisible(selectedView)


    #---------------------------------------------
    def OnIconfiy(self, evt):
        wx.LogMessage("OnIconfiy: %s" % evt.Iconized())
        evt.Skip()

    #---------------------------------------------
    def OnMaximize(self, evt):
        wx.LogMessage("OnMaximize")
        evt.Skip()

    #---------------------------------------------
    def OnActivate(self, evt):
        #wx.LogMessage("OnActivate: %s" % evt.GetActive())
        evt.Skip()

    #---------------------------------------------
    def OnAppActivate(self, evt):
        #wx.LogMessage("OnAppActivate: %s" % evt.GetActive())
        evt.Skip()

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------

class MySplashScreen(SplashScreen):
    def __init__(self):
        bmp = wx.Image(opj("bitmaps/ticker-scrape-logo.png")).ConvertToBitmap()
        SplashScreen.__init__(self, bmp,
                              wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_TIMEOUT,
                              1000, None, -1)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.fc = wx.CallLater(2000, self.ShowMain)


    def OnClose(self, evt):
        # Make sure the default handler runs too so this window gets
        # destroyed
        evt.Skip()
        self.Hide()

        # if the timer is still running then go ahead and show the
        # main frame now
        if self.fc.IsRunning():
            self.fc.Stop()
            self.ShowMain()


    def ShowMain(self):
        global portfolioFrame
        portfolioFrame = TickerScrapeFrame(None, "TickerScrape")
        portfolioFrame.Show()
        if self.fc.IsRunning():
            self.Raise()
        wx.CallAfter(portfolioFrame.ShowTip)




#---------------------------------------------------------------------------

from wx.lib.mixins.treemixin import ExpansionState
if USE_CUSTOMTREECTRL:
    import wx.lib.agw.customtreectrl as CT
    TreeBaseClass = CT.CustomTreeCtrl
else:
    TreeBaseClass = wx.TreeCtrl


class TickerScrapeTree(ExpansionState, TreeBaseClass):
    def __init__(self, parent):
        TreeBaseClass.__init__(self, parent, style=wx.TR_DEFAULT_STYLE|
                               wx.TR_HAS_VARIABLE_ROW_HEIGHT)
        self.BuildTreeImageList()
        if USE_CUSTOMTREECTRL:
            self.SetSpacing(10)
            self.SetWindowStyle(self.GetWindowStyle() & ~wx.TR_LINES_AT_ROOT)

        self.SetInitialSize((100,80))


    def AppendItem(self, parent, text, image=-1, wnd=None):
        if USE_CUSTOMTREECTRL:
            item = TreeBaseClass.AppendItem(self, parent, text, image=image, wnd=wnd)
        else:
            item = TreeBaseClass.AppendItem(self, parent, text, image=image)
        return item

    def BuildTreeImageList(self):
        imgList = wx.ImageList(16, 16)
        for png in ViewTree.viewPngs:
            imgList.Add(images.catalog[png].GetBitmap())

        # add the image for modified demos.
        imgList.Add(images.catalog["custom"].GetBitmap())

        self.AssignImageList(imgList)


    def GetItemIdentity(self, item):
        return self.GetItemData(item)


#---------------------------------------------------------------------------

class MyApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def OnInit(self):

        # Check runtime version
        if (LooseVersion(version.WX_PYTHON_VERSION_MIN) >
            LooseVersion(wx.VERSION_STRING)):
            wx.MessageBox(caption="Warning",
                          message="You're using version %s of wxPython, but this application needs version >= %s.\n"
                          "There may be some version incompatibilities..."
                          % (wx.VERSION_STRING, version.WX_PYTHON_VERSION_MIN))

        if (LooseVersion(version.WX_PYTHON_VERSION_MAX) <
            LooseVersion(wx.VERSION_STRING)):
            wx.MessageBox(caption="Warning",
                          message="You're using version %s of wxPython, but this application needs version <= %s.\n"
                          "There may be some version incompatibilities..."
                          % (wx.VERSION_STRING, version.WX_PYTHON_VERSION_MAX))

        self.InitInspection()  # for the InspectionMixin base class

        # Now that we've warned the user about possibile problems,
        # lets import images
        import images as i
        global images
        images = i

        # For debugging
        #self.SetAssertMode(wx.PYAPP_ASSERT_DIALOG|wx.PYAPP_ASSERT_EXCEPTION)

        wx.SystemOptions.SetOption("mac.window-plain-transition", 1)
        self.SetAppName("tickerScrape")

        if "--no-splash" not in sys.argv:
        # Create and show the splash screen.  It will then create and
        # show the main frame when it is time to do so.  Normally when
        # using a SplashScreen you would create it, show it and then
        # continue on with the application's initialization, finally
        # creating and showing the main application window(s).  In
        # this case we have nothing else to do so we'll delay showing
        # the main frame until later (see ShowMain above) so the users
        # can see the SplashScreen effect.
            splash = MySplashScreen()
            splash.Show()
        else:
            global portfolioFrame
            portfolioFrame = TickerScrapeFrame(None, "TickerScrape")
            portfolioFrame.Show()

        return True

#---------------------------------------------------------------------------
def RestartApp(argv_extra):
    """Restarts the current program, with file objects and descriptors
       cleanup
    """

    p = psutil.Process(os.getpid())
    for handler in p.open_files() + p.connections():
        if handler.fd != -1:
            os.close(handler.fd)

    exe = sys.executable
    argv = list(sys.argv)
    argv.append(argv_extra)

    os.execl(exe, exe, *argv)

#---------------------------------------------------------------------------
def ExecApp(fname):
    """Execute the installer, after cleaning up file descriptors
    """

    p = psutil.Process(os.getpid())
    for handler in p.open_files() + p.connections():
        if handler.fd != -1:
            os.close(handler.fd)

    os.execl(fname, fname)

#---------------------------------------------------------------------------

def main():
    app = MyApp(False)

    # Read the initial portfolio holdings
    Config.PortfolioRead()

    app.MainLoop()

#---------------------------------------------------------------------------


mainOverview = """<html><body>
<h2>TickerScrape Help</h2>

<p> TickerScrape is a <b>GUI toolkit</b> for investment portfolio management,
implemented using <b>wxPython</b>, and using <b>web scraping</b> of investment data. Users can employ the existing web scrapers, or implement extension scrapers right within the TickerScrape toolkit. Users can also create extension widgets, which can be added to the TickerScrape views, allowing full customization of the TickerScrape app.

<p> Like Python and wxPython, TickerScrape is <b>Open Source</b>, which means 
that it is free for anyone to use and the source code is available for anyone
to look at and modify.  Or anyone can contribute fixes or enhancements to the project.

<p> TickerScrape is availabled for <b>Windows x32</b> and <b>x64</b>, Linux <b>x32</b> and <b>x64</b> and <b>MAC OS X</b>. 

<p> <b>This toolkit</b> will display each TickerScrape view's code in the
View Code pane. Views can be <b>added</b>, <b>edited</b>, <b>cloned</b>, or <b>removed</b> from the tree control on the left pane. Views are versioned so past versions of views can be recovered.
"""


#----------------------------------------------------------------------------
#----------------------------------------------------------------------------

if __name__ == '__main__':
    __name__ = 'Main'
    main()

#----------------------------------------------------------------------------

