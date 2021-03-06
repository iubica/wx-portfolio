# viewdata.py

"""
Globals for the main.py wxPython views.
"""

#-------------------------------------------------------------------------------
#
# viewPngs
#
# These are the images names used in the wxPortfolio treectrl.
# These come from images.py or bitmaps/imagename.ext
#
# viewPngs = ["imagename1", "imagename2", "etc"]
#
#-------------------------------------------------------------------------------

viewPngs = ["overview", # Top level views
            "custom", # Portfolio
            "custom", # Performance
            "custom", # Config
            "recent", # Recent Additions/Updates
            "frame",  # ...
            "dialog", 
            "moredialog", 
            "core",
            "book", 
            "customcontrol", 
            "morecontrols", 
            "layout", 
            "process",
            "clipboard", 
            "images", 
            "miscellaneous"]


#-------------------------------------------------------------------------------
#
# viewTree
#
# These are the View Catagory Headers
# and View Module Names(Ex: Frame.py without ext)
#
# ('View Category Name', [
#       'ViewModuleName1',
#       'ViewModuleName2',
#       'Etc',
#       ]),
#
# The ViewModuleName should correspond to a ViewModuleName.py file in the
# top folder, with the following globals and methods:
#   overview - HTML string showing in the Help tab 
#   runTest(frame, nb, log) - returns panel object for module
#
#-------------------------------------------------------------------------------

viewTree = [
    # portfolio views
    ('Portfolio', [
        'Holdings',
        'Accounts',
    ]),

    ('Performance', [
        'PerformanceHistory',
        'TrailingTotalReturns',
    ]),

    ('Configuration', [
        'AccountTypes',
        'Categories',
    ]),

    # new stuff
    ('Recent Additions/Updates', [
        'FileCtrl',
        'Overlay',
        'RearrangeDialog',
        'RichMessageDialog',
        'ToolTip',
        'TimePickerCtrl',
        'BannerWindow',
    ]),

    # managed windows == things with a (optional) caption you can close
    ('Frames and Dialogs', [
        'AUI_DockingWindowMgr',
        'AUI_MDI',
        'Dialog',
        'Frame',
        'MDIWindows',
        'MiniFrame',
        'Wizard',
    ]),

    # the common dialogs
    ('Common Dialogs', [
        'AboutBox',
        'ColourDialog',
        'DirDialog',
        'FileDialog',
        'FindReplaceDialog',
        'FontDialog',
        'MessageDialog',
        'MultiChoiceDialog',
        'PageSetupDialog',
        'PrintDialog',
        'ProgressDialog',
        'SingleChoiceDialog',
        'TextEntryDialog',
        'RearrangeDialog',
        'RichMessageDialog',
        'NotificationMessage',
        'RichToolTip',
    ]),

    # dialogs from libraries
    ('More Dialogs', [
        'ImageBrowser',
        'ScrolledMessageDialog',
    ]),

    # core controls
    ('Core Windows/Controls', [
        'BitmapButton',
        'Button',
        'CheckBox',
        'CheckListBox',
        'Choice',
        'ComboBox',
        'CommandLinkButton',
        'DVC_CustomRenderer',
        'DVC_DataViewModel',
        'DVC_IndexListModel',
        'DVC_ListCtrl',
        'DVC_TreeCtrl',
        'Gauge',
        'Grid',
        'Grid_MegaExample',
        'GridLabelRenderer',
        'ListBox',
        'ListCtrl',
        'ListCtrl_virtual',
        'ListCtrl_edit',
        'Menu',
        'PopupMenu',
        'PopupWindow',
        'RadioBox',
        'RadioButton',
        'SashWindow',
        'ScrolledWindow',
        'SearchCtrl',
        'Slider',
        'SpinButton',
        'SpinCtrl',
        'SpinCtrlDouble',
        'SplitterWindow',
        'StaticBitmap',
        'StaticBox',
        'StaticText',
        'StatusBar',
        'StockButtons',
        'TextCtrl',
        'ToggleButton',
        'ToolBar',
        'TreeCtrl',
        'Validator',
    ]),

    ('"Book" Controls', [
        'AUI_Notebook',
        'Choicebook',
        'FlatNotebook',
        'Listbook',
        'Notebook',
        'Toolbook',
        'Treebook',
    ]),

    ('Custom Controls', [
        'AnalogClock',
        'ColourSelect',
        'ComboTreeBox',
        'Editor',
        'FileCtrl',
        'GenericButtons',
        'GenericDirCtrl',
        'ItemsPicker',
        #'LEDNumberCtrl',  # TODO
        'MultiSash',
        'PlateButton',
        'PopupControl',
        'PyColourChooser',
        'TreeListCtrl',  # TODO or toss it?
    ]),

    # controls coming from other libraries
    ('More Windows/Controls', [
        'ActiveX_FlashWindow',
        'ActiveX_IEHtmlWindow',
        'ActiveX_PDFWindow',
        'BitmapComboBox',
        'Calendar',
        'CalendarCtrl',
        'CheckListCtrlMixin',
        'CollapsiblePane',
        'ComboCtrl',
        'ContextHelp',
        'DatePickerCtrl',
        #'DynamicSashWindow',  # TODO
        'EditableListBox',
        'ExpandoTextCtrl',
        'FancyText',
        'FileBrowseButton',
        'FloatBar',
        'FloatCanvas',
        'HtmlWindow',
        'HTML2_WebView',
        'InfoBar',
        'IntCtrl',
        'MaskedEditControls',
        'MaskedNumCtrl',
        'MediaCtrl',
        'MultiSplitterWindow',
        'OwnerDrawnComboBox',
        'Pickers',
        'PropertyGrid',
        'PyCrust',
        'PyPlot',
        'PyShell',
        'ResizeWidget',
        'RichTextCtrl',
        'ScrolledPanel',
        #'SplitTree',         # TODO or toss it?
        'StyledTextCtrl_1',
        'StyledTextCtrl_2',
        'TablePrint',
        'Throbber',
        'Ticker',
        'TimeCtrl',
        'TimePickerCtrl',
        'TreeMixin',
        'VListBox',
    ]),

    # How to lay out the controls in a frame/dialog
    ('Window Layout', [
        'GridBagSizer',
        'LayoutAnchors',
        'LayoutConstraints',
        'Layoutf',
        'ScrolledPanel',
        'SizedControls',
        'Sizers',
        'WrapSizer',
        'XmlResource',
        'XmlResourceHandler',
        'XmlResourceSubclass',
    ]),

    # ditto
    ('Process and Events', [
        'DelayedResult',
        'EventManager',
        'KeyEvents',
        'Process',
        'PythonEvents',
        'Threads',
        'Timer',
        ##'infoframe',    # needs better explanation and some fixing
    ]),

    # Clipboard and DnD
    ('Clipboard and DnD', [
        'CustomDragAndDrop',
        'DragAndDrop',
        'URLDragAndDrop',
    ]),

    # Images
    ('Using Images', [
        'AdjustChannels',
        'AlphaDrawing',
        'AnimateCtrl',
        'ArtProvider',
        'BitmapFromBuffer',
        'Cursor',
        'DragImage',
        'Image',
        'ImageAlpha',
        'ImageFromStream',
        'Img2PyArtProvider',
        'Mask',
        'RawBitmapAccess',
        'Throbber',
    ]),

    # Other stuff
    ('Miscellaneous', [
        'AlphaDrawing',
        'BannerWindow',
        'Cairo',
        'Cairo_Snippets',
        'ColourDB',
        ##'DialogUnits',   # needs more explanations
        'DragScroller',
        'DrawXXXList',
        'FileHistory',
        'FontEnumerator',
        'GetMouseState',
        'GraphicsContext',
        'GraphicsGradient',
        'GLCanvas',
        'I18N',
        'Joystick',
        'MimeTypesManager',
        'MouseGestures',
        'OGL',
        'Overlay',
        'PDFViewer',
        'PenAndBrushStyles',
        'PrintFramework',
        'PseudoDC',
        'RendererNative',
        'ShapedWindow',
        'Sound',
        'StandardPaths',
        'SystemSettings',
        'ToolTip',
        'UIActionSimulator',
        'Unicode',
    ]),

    ('Check out the samples dir too', []),

]

