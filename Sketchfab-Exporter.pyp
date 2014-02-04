"""
Sketchfab Exporter v1.2.2

Copyright: Erwin Santacruz 2012 (www.990adjustments.com)
Written for CINEMA 4D R13 - R15

Name-US: Sketchfab Exporter v1.2.2

Description-US: Model exporter for Sketchfab.com

Creation Date: 09/06/12
Modified Date: 03/16/13
"""

import c4d
from c4d import documents, gui, plugins, bitmaps, storage

import time
import datetime
import sys
import os
import json
import base64
import urllib2
import shelve
import logging
import webbrowser
import zipfile
import threading



#logging.basicConfig(level=logging.DEBUG)

# Install and import the poster modules.
try:
    from poster.encode import multipart_encode
    from poster.streaminghttp import register_openers
except ImportError, err:
    os_string = "osx"

    if c4d.GeGetCurrentOS() == c4d.OPERATINGSYSTEM_WIN:
        os_string = "win64"

    pythonPath = os.path.join(c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY_USER), "python", "packages", os_string)
    filePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "res")
    moduleFile = os.path.join(filePath, "poster-0.8.1.zip")

    try:
        zf = zipfile.ZipFile(moduleFile)
        zf.extractall(pythonPath)
        zf.close()
    except Exception, err:
        gui.MessageDialog("Unable to install necessary files. Please check the help for information on manual module installation.", c4d.GEMB_OK)
    else:
        from poster.encode import multipart_encode
        from poster.streaminghttp import register_openers



__author__                  = "Erwin Santacruz"
__website__                 = "http://990adjustments.com"
__sketchfab__               = "http://sketchfab.com"
__twitter__                 = "@990adjustments"
__email__                   = "hi@990adjustments.com"
__plugin_title__            = "Sketchfab Exporter"
__version__                 = "1.2.2"
__copyright_year__          = datetime.datetime.now().year
__plugin_id__               = 1029390

BTN_ABOUT                   = 100001
BTN_WEB                     = 100002
TXT_MODEL_NAME              = 100003
EDITXT_MODEL_TITLE          = 100004
TXT_DESCRIPTION             = 100005
EDITXT_DESCRIPTION          = 100006
TXT_TAGS                    = 100007
EDITXT_TAGS                 = 100008
TXT_API_TOKEN               = 100009
EDITXT_API_TOKEN            = 100010
BTN_PUBLISH                 = 100011
MENU_SAVE_API_TOKEN         = 100012
BTN_WEB_990                 = 100013
CHK_PRIVATE                 = 100014
BTN_THUMB_SRC_PATH          = 100015
EDITXT_THUMB_SRC_PATH       = 100015
EDITXT_PASSWORD             = 100016

GROUP_WRAPPER               = 20000
GROUP_ONE                   = 20001
GROUP_TWO                   = 20002
GROUP_THREE                 = 20003
GROUP_FOUR                  = 20004
GROUP_FIVE                  = 20005
GROUP_SIX                   = 20006

UA_HEADER                   = 30000
UA_ICON                     = 30001


#Constants
HELP_TEXT = "Sketchfab Exporter v" + __version__
SETTINGS = "com.990adjustments.SketchfabExport"
SKETCHFAB_URL = "https://api.sketchfab.com/v1/models"
COLLADA14 = 1022316

WRITEPATH = os.path.join(storage.GeGetStartupWritePath(), 'Sketchfab')
FILEPATH = os.path.join(WRITEPATH, SETTINGS)

if not os.path.exists(WRITEPATH):
 os.mkdir(WRITEPATH)

# Globals
g_uploaded = False
g_error = ""
g_lastUpdated = ""



class Utilities(object):
    """Several helper methods."""

    def __init__(self, arg):
        super(Utilities, self).__init__()


    @staticmethod
    def ESOpen_website(site):
        """Opens Website.

        :param string site: website url
        """

        webbrowser.open(site)

    @staticmethod
    def ESOpen_about():
        """Show About information dialog box."""

        gui.MessageDialog("{0} v{1}\nCopyright (C) {2} {3}\nAll rights reserved.\n\nWeb:      {4}\nTwitter:  {5}\nEmail:    {6}\n\n\
This program comes with ABSOLUTELY NO WARRANTY. For details, please visit\nhttp://www.gnu.org/licenses/gpl.html".format(__plugin_title__, __version__, __copyright_year__, __author__, __website__, __twitter__, __email__), c4d.GEMB_OK)

    @staticmethod
    def ESZipdir(path, zipObject, title):
        """Adds files to zip object.

        :param string path: path of root directory
        :param object zipObject: the zip object
        :param string title: the name of the .dae file with extension
        """

        include = ['tex']
        for root, dirs, files, in os.walk(path):
            dirs[:] = [i for i in dirs if i in include]
            for file in files:
                if file.startswith('.'):
                    continue
                if file.endswith('.dae'.lower()) and file == title:
                    zipObject.write(os.path.join(root, file))

        # zip textures in tex directory
        texDir = os.path.join(path,'tex');
        if os.path.exists(texDir):
            for f in os.listdir(texDir):
                zipObject.write(os.path.join(path, 'tex', f))



class PublishModelThread(threading.Thread):
    """Class that publishes 3D model to Sketchfab.com."""

    def __init__(self, data, title, activeDoc, activeDocPath):
        threading.Thread.__init__(self)
        self.data = data
        self.title = title
        self.activeDoc = activeDoc
        self.activeDocPath = activeDocPath

    def run(self):
        global g_uploaded
        global g_error

        # Need to work on this some more
        time_start = datetime.datetime.now()
        #t = time_start.strftime("%a %b %d %I:%M %p")
        t = time_start.strftime("%c")

        print("\nUpload started on {0}".format(t))
        print("Exporting...\n")

        exportFile = os.path.join(self.activeDocPath, self.title + '.dae')

        # COLLADA 1.4
        documents.SaveDocument(self.activeDoc, exportFile, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, COLLADA14)

        if not os.path.exists(exportFile):
            g_uploaded = False
            g_error = "Export failed."
            c4d.SpecialEventAdd(__plugin_id__)
            return False

        print("Export successful.")

        # Check size of file
        #if os.stat(exportFile).st_size / 1048576 > 49:
        #    g_uploaded = False
        #    g_error = "File is too large. Your file is over 50MB."

            # Clean up
            #logging.debug("Cleaning up...")
        #    self.cleanup_files(export_file=exportFile)
        #    c4d.SpecialEventAdd(__plugin_id__)
        #    return False

        basepath, dirname = os.path.split(self.activeDocPath)
        archiveName = self.title + '.zip'
        texturePath = os.path.join(self.activeDocPath, 'tex')
        os.chdir(basepath)

        zip = zipfile.ZipFile(archiveName, 'w')
        Utilities.ESZipdir(dirname, zip, self.title+'.dae')
        zip.close()

        self.data['fileModel'] = open(archiveName, 'rb')

        # Connection code
        # Begin upload
        print("Uploading...\n")
        try:
            register_openers()

            post_data, headers = multipart_encode(self.data)
            req = urllib2.Request(SKETCHFAB_URL, post_data, headers)
            response = urllib2.urlopen(req)

            if response and json.loads(str(response.read()))["success"]:
                response.close()
                g_uploaded = True
            else:
                g_error = "Invalid response from server."

        except Exception as error:
            g_uploaded = False
            g_error = error

        finally:
            # Clean up
            #logging.debug("Cleaning up...")
            self.cleanup_files(archiveName, exportFile)
            c4d.SpecialEventAdd(__plugin_id__)

    def cleanup_files(self, archive_name=None, export_file=None):
        if archive_name and os.path.exists(archive_name):
            try:
                #logging.debug("Removing file {0}".format(archive_name))
                os.remove(archive_name)
            except Exception as err:
                print("Unable to remove file {0}".format(archive_name))

        if export_file and os.path.exists(export_file):
            try:
                #logging.debug("Removing file {0}".format(export_file))
                os.remove(export_file)
            except Exception as err:
                print("Unable to remove file {0}".format(export_file))



class UserAreaPathsHeader(gui.GeUserArea):
    """Sketchfab header image."""

    bmp = c4d.bitmaps.BaseBitmap()

    def GetMinSize(self):
        self.width = 600
        self.height = 75
        return (self.width, self.height)

    def DrawMsg(self, x1, y1, x2, y2, msg):
        thisFile = os.path.abspath( __file__ )
        thisDirectory = os.path.dirname(thisFile)
        path = os.path.join(thisDirectory, "res", "header.png")
        result, ismovie = self.bmp.InitWith(path)
        x1 = 0
        y1 = 0
        x2 = self.bmp.GetBw()
        y2 = self.bmp.GetBh()

        if result == c4d.IMAGERESULT_OK:
            self.DrawBitmap(self.bmp, 0, 0, self.bmp.GetBw(), self.bmp.GetBh(), x1, y1, x2, y2, c4d.BMP_NORMALSCALED | c4d.BMP_ALLOWALPHA)

    def Redraw(self):
        thisFile = os.path.abspath( __file__ )
        thisDirectory = os.path.dirname(thisFile)
        path = os.path.join(thisDirectory, "res", "header.png")
        result, ismovie = self.bmp.InitWith(path)
        x1 = 0
        y1 = 0
        x2 = self.bmp.GetBw()
        y2 = self.bmp.GetBh()

        if result == c4d.IMAGERESULT_OK:
            self.DrawBitmap(self.bmp, 0, 0, self.bmp.GetBw(), self.bmp.GetBh(), x1, y1, x2, y2, c4d.BMP_NORMALSCALED | c4d.BMP_ALLOWALPHA)


class MainDialog(gui.GeDialog):
    """Main Dialog Class"""

    userarea_paths_header = UserAreaPathsHeader()
    save_api_token = False

    def InitValues(self):
        """Called when the dialog is initialized by the GUI.
        True if successful, or False to signalize an error.
        """

        global g_lastUpdated

        print("\n{0} v{1} loaded. Copyright (C) {2} {3}. All rights reserved.\n\n\
This program comes with ABSOLUTELY NO WARRANTY. For details, please visit http://www.gnu.org/licenses/gpl.html\n\n".format(__plugin_title__, __version__, __copyright_year__, __author__))

        try:
            #logging.debug("Checking for prefs file")
            prefs = shelve.open(FILEPATH, 'r')

            if 'api_token' in prefs:
                if prefs['api_token']:
                    self.MenuInitString(MENU_SAVE_API_TOKEN, True, True)
                    self.save_api_token = True
                    token = prefs['api_token']
                    self.SetString(EDITXT_API_TOKEN, '-' * len(prefs['api_token']))
                else:
                    self.MenuInitString(MENU_SAVE_API_TOKEN, True, False)
                    self.save_api_token = False

            if 'lastUpdate' in prefs:
                g_lastUpdated = prefs['lastUpdate']
                self.groupSixWillRedraw()

            prefs.close()
        except:
            self.MenuInitString(MENU_SAVE_API_TOKEN, True, False)

        self.Enable(EDITXT_PASSWORD, False)

        return True

    def createGroupFiveItems(self):
        self.AddCheckbox(id=CHK_PRIVATE, flags=c4d.BFH_SCALEFIT | c4d.BFH_LEFT, initw=0, inith=0, name="Private Model (Pro User Only)")
        self.AddStaticText(id=0, flags=c4d.BFH_LEFT, initw=0, inith=0, name="Password (optional):    ")
        self.AddEditText(id=EDITXT_PASSWORD, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, editflags=c4d.EDITTEXT_PASSWORD)

    def groupFiveWillRedraw(self):
        self.LayoutFlushGroup(GROUP_FIVE)
        self.createGroupFiveItems()
        self.LayoutChanged(GROUP_FIVE)

    def createGroupSixItems(self):
        self.AddStaticText(id=0, flags=c4d.BFH_LEFT | c4d.BFH_SCALEFIT, initw=0, inith=0, name=g_lastUpdated)
        self.AddButton(id=BTN_PUBLISH, flags=c4d.BFH_RIGHT | c4d.BFV_BOTTOM, initw=75, inith=16, name="Publish")

    def groupSixWillRedraw(self):
        self.LayoutFlushGroup(GROUP_SIX)
        self.createGroupSixItems()
        self.LayoutChanged(GROUP_SIX)

    def CreateLayout(self):
        """Override - Called when C4D is about to display the dialog.
        True if successful, or False to signalize an error.
        """

        self.SetTitle(__plugin_title__)

        # Create the menu
        self.MenuFlushAll()

        # Options menu
        self.MenuSubBegin("File")
        self.MenuAddCommand(c4d.IDM_CM_CLOSEWINDOW)
        self.MenuSubEnd()

        # Options menu
        self.MenuSubBegin("Options")
        self.MenuAddString(MENU_SAVE_API_TOKEN, "Save API token")
        self.MenuSubEnd()

        # Info menu
        self.MenuSubBegin("Info")
        self.MenuAddString(BTN_ABOUT, "About")
        self.MenuAddString(BTN_WEB, "Visit Sketchfab.com")
        self.MenuAddString(BTN_WEB_990, "Visit 990adjustments.com")
        self.MenuSubEnd()

        self.MenuFinished()

        #----------------------------------------------------------------------
        # Begin WRAPPER
        #----------------------------------------------------------------------

        self.GroupBegin(id=GROUP_WRAPPER,
                        flags=c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT,
                        cols=1,
                        rows=1,
                        title="Wrapper",
                        groupflags=c4d.BORDER_NONE)

        # UA groups
        self.GroupBegin(id=GROUP_ONE,
                        flags=c4d.BFH_SCALEFIT,
                        cols=1,
                        rows=1,
                        title="Header",
                        groupflags=c4d.BORDER_NONE)

        self.GroupSpace(0, 0)
        self.GroupBorderSpace(0, 0, 0, 0)

        self.AddUserArea(UA_HEADER, c4d.BFH_LEFT)
        self.AttachUserArea(self.userarea_paths_header, UA_HEADER)
        self.userarea_paths_header.LayoutChanged()

        self.GroupEnd()

        self.GroupBegin(id=GROUP_TWO,
                        flags=c4d.BFH_SCALEFIT,
                        cols=2,
                        rows=1)

        self.GroupSpace(10, 10)
        self.GroupBorderSpace(6, 6, 6, 6)

        self.AddStaticText(id=TXT_MODEL_NAME, flags=c4d.BFH_RIGHT, initw=0, inith=0, name="Model name:")
        self.AddEditText(id=EDITXT_MODEL_TITLE, flags=c4d.BFH_SCALEFIT, initw=0, inith=0)

        self.GroupEnd()

        self.GroupBegin(id=GROUP_THREE,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT | c4d.BFV_TOP,
                        cols=2,
                        rows=1)

        self.GroupSpace(10, 10)
        self.GroupBorderSpace(6, 6, 6, 6)

        self.AddStaticText(id=TXT_DESCRIPTION, flags=c4d.BFH_RIGHT | c4d.BFV_TOP, initw=0, inith=0, name=" Description: ")
        self.AddMultiLineEditText(id=EDITXT_DESCRIPTION, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, initw=0, inith=100, style=c4d.DR_MULTILINE_MONOSPACED)

        self.GroupEnd()

        self.GroupBegin(id=GROUP_FOUR,
                        flags=c4d.BFH_SCALEFIT,
                        cols=2,
                        rows=2)

        self.GroupSpace(10, 10)
        self.GroupBorderSpace(6, 6, 6, 6)
        self.AddStaticText(id=TXT_TAGS, flags=c4d.BFH_RIGHT, initw=0, inith=0, name="   Tags:")
        self.AddEditText(id=EDITXT_TAGS, flags=c4d.BFH_SCALEFIT, initw=0, inith=0)

        self.AddStaticText(id=TXT_API_TOKEN, flags=c4d.BFH_RIGHT, initw=0, inith=0, name="    API token:")
        self.AddEditText(id=EDITXT_API_TOKEN, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, editflags=c4d.EDITTEXT_PASSWORD)

        self.GroupEnd()


        self.AddSeparatorH(inith=0, flags=c4d.BFH_FIT)

        # Group FIVE
        self.GroupBegin(id=GROUP_FIVE,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM,
                        cols=3,
                        rows=1)

        self.GroupSpace(4, 4)
        self.GroupBorderSpace(6, 6, 6, 6)

        self.groupFiveWillRedraw()
        #self.AddCheckbox(id=CHK_PRIVATE, flags=c4d.BFH_SCALEFIT | c4d.BFH_LEFT, initw=0, inith=0, name="Private Model (Pro User Only)")
        #self.AddStaticText(id=0, flags=c4d.BFH_LEFT, initw=0, inith=0, name="Password (optional):    ")
        #self.AddEditText(id=EDITXT_PASSWORD, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, editflags=c4d.EDITTEXT_PASSWORD)

        self.GroupEnd()

        self.AddSeparatorH(inith=0, flags=c4d.BFH_FIT)
        #self.AddStaticText(id=0, flags=c4d.BFH_LEFT, initw=0, inith=0, name="Thumbnail:")
        #self.AddEditText(id=EDITXT_THUMB_SRC_PATH, flags=c4d.BFH_SCALEFIT, initw=300, inith=12)
        #self.AddButton(id=BTN_THUMB_SRC_PATH, flags=c4d.BFH_RIGHT, initw=30, inith=12, name="...")

        self.GroupBegin(id=GROUP_SIX,
                        flags=c4d.BFH_SCALEFIT | c4d.BFV_BOTTOM,
                        cols=2,
                        rows=1)

        self.GroupSpace(4, 4)
        self.GroupBorderSpace(6, 6, 6, 6)

        self.groupSixWillRedraw()
        #self.AddStaticText(id=0, flags=c4d.BFH_LEFT | c4d.BFH_SCALEFIT, initw=0, inith=0, name=g_lastUpdated)
        #self.AddButton(id=BTN_PUBLISH, flags=c4d.BFH_RIGHT | c4d.BFV_BOTTOM, initw=75, inith=16, name="Publish")

        self.GroupEnd()

        self.GroupEnd()

        #----------------------------------------------------------------------
        # End WRAPPER
        #----------------------------------------------------------------------
        return True

    def setApiToken(self, _setApiToken, _api_token=None):
        """Saves API token.

        :param string _setApiToken: the api token
        :param bool _api_token: save or delete api token
        """

        if _setApiToken:
            try:
                prefs = shelve.open(FILEPATH, 'c')
                prefs['api_token'] = _api_token
                prefs.close()
                #logging.debug("API token successfully saved.")
            except Exception, err:
                print("Could not save API token. Reason: {0}".format(err))
        else:
            # delete settings
            try:
                os.remove(FILEPATH + '.db')
                #logging.debug("API token successfully removed.")
                self.SetString(EDITXT_API_TOKEN, "")
            except Exception, err:
                print("Unable to delete settings. Reason: {0}".format(err))

    def CoreMessage(self, id, msg):
        """Override this function if you want to react
        to C4D core messages. The original message is stored in msg.
        """

        global g_lastUpdated

        if id == __plugin_id__:
            c4d.StatusSetBar(100)

            time_start = datetime.datetime.now()
            #t = time_start.strftime("%a %b %d %I:%M %p")
            t = time_start.strftime("%c")

            try:
                prefs = shelve.open(FILEPATH, 'c')
            except Exception as err:
                print("\nUnable to load prefereces. Reason: ".format(err))

            if g_uploaded:
                gui.MessageDialog("Your model was succesfully uploaded to Sketchfab.com.", c4d.GEMB_OK)
                print("Your model was succesfully uploaded to Sketchfab.com.")

                print("\nUpload ended on {0}".format(t))

                g_lastUpdated = "Successful Upload on {0}".format(t)

                if prefs:
                    prefs['lastUpdate'] = g_lastUpdated
                    prefs.close()
            else:
                gui.MessageDialog("Unable to upload model to Sketchfab.com. Reason: {0}".format(g_error), c4d.GEMB_OK)
                print("Unable to upload model to Sketchfab.com. Reason: {0}".format(g_error))
                g_lastUpdated = "Upload failed on {0}".format(t)

                if prefs:
                    prefs['lastUpdate'] = g_lastUpdated
                    prefs.close()

            self.groupSixWillRedraw()
            self.Enable(BTN_PUBLISH, True)
            self.SetTitle(__plugin_title__)
            c4d.StatusClear()

        return True

    def Command(self, id, msg):
        """Override this function if you want to react to user clicks. Whenever the
        user clicks on a gadget and/or changes its value this function will be
        called.

        It is also called when a string menu item is selected.
        Override it to handle such events.
        """

        global g_lastUpdated

        if id == MENU_SAVE_API_TOKEN:
            if self.save_api_token == True:
                self.MenuInitString(MENU_SAVE_API_TOKEN, True, False)
                self.save_api_token = False
                self.setApiToken(False)
            else:
                self.MenuInitString(MENU_SAVE_API_TOKEN, True, True)
                self.save_api_token = True

        if id == BTN_ABOUT:
            Utilities.ESOpen_about()

        if id == BTN_WEB:
            Utilities.ESOpen_website(__sketchfab__)

        if id == BTN_WEB_990:
            Utilities.ESOpen_website(__website__)

        if id == BTN_THUMB_SRC_PATH:
            selected = storage.LoadDialog(type = c4d.FILESELECTTYPE_ANYTHING)
            if not selected:
                return False
            else:
                self.SetString(EDITXT_THUMB_SRC_PATH, selected)

        if id == CHK_PRIVATE:
            if self.GetBool(CHK_PRIVATE):
                self.Enable(EDITXT_PASSWORD, True)
            else:
                self.groupFiveWillRedraw()
                self.Enable(EDITXT_PASSWORD, False)

        if id == BTN_PUBLISH:
            c4d.StatusSetBar(50)
            g_lastUpdated = "Working it..."
            self.groupSixWillRedraw()

            data = {}
            activeDoc = documents.GetActiveDocument()
            activeDocPath = activeDoc.GetDocumentPath()
            if not os.path.exists(activeDocPath):
                gui.MessageDialog("Please save your scene first.", c4d.GEMB_OK)
                c4d.StatusClear()
                return False

            self.Enable(BTN_PUBLISH, False)
            self.SetTitle("{0} publishing model...".format(__plugin_title__))

            title = self.GetString(EDITXT_MODEL_TITLE)
            description = self.GetString(EDITXT_DESCRIPTION)
            tags = self.GetString(EDITXT_TAGS)
            token = self.GetString(EDITXT_API_TOKEN)
            private = self.GetBool(CHK_PRIVATE)
            password = self.GetString(EDITXT_PASSWORD)

            if '-' in token:
                try:
                    prefs = shelve.open(FILEPATH, 'r')
                except:
                    gui.MessageDialog("Please re-enter your API token.", c4d.GEMB_OK)
                    self.MenuInitString(MENU_SAVE_API_TOKEN, True, False)
                    self.Enable(BTN_PUBLISH, True)
                    self.SetTitle(__plugin_title__)
                    c4d.StatusClear()
                    return False
                else:
                    if 'api_token' in prefs:
                        if prefs['api_token']:
                            api_token = prefs['api_token']
                        else:
                            gui.MessageDialog("Please re-enter your API token.", c4d.GEMB_OK)
                            self.MenuInitString(MENU_SAVE_API_TOKEN, True, False)
                            self.Enable(BTN_PUBLISH, True)
                            self.SetTitle(__plugin_title__)
                            c4d.StatusClear()
                            return False

                    prefs.close()
            else:
                api_token = token

            if len(title) == 0:
                gui.MessageDialog("Please enter a name for your model.", c4d.GEMB_OK)
                self.Enable(BTN_PUBLISH, True)
                self.SetTitle(__plugin_title__)
                c4d.StatusClear()
                return False

            if len(api_token) == 0:
                gui.MessageDialog("Please enter your API token. Your API token can be found in your dashboard at sketchfab.com", c4d.GEMB_OK)
                self.Enable(BTN_PUBLISH, True)
                self.SetTitle(__plugin_title__)
                c4d.StatusClear()
                return False

            # populate data
            if len(description) != 0:
                data['description'] = description

            if len(tags) != 0:
                data['tags'] = tags

            data['title'] = title
            data['token'] = api_token

            if private:
                data['private'] = private

            if private and len(password) != 0:
                data['password'] = password

            if self.save_api_token:
                self.setApiToken(True, api_token)

            # Start Multithread operations
            # pass on data
            self.publish = PublishModelThread(data, title, activeDoc, activeDocPath)
            self.publish.setDaemon(True)
            self.publish.start()

        return True



class SketchfabExporter(plugins.CommandData):
    """Plugin class"""

    dialog = None

    def Execute(self,doc):
        # Check C4D version
        if c4d.GetC4DVersion() < 15000 and c4d.GeGetCurrentOS() == c4d.OPERATINGSYSTEM_WIN:
            c4d.gui.MessageDialog("Sorry, but the plugin is incompatible with the version of Cinema 4D you are currently running.\n\nThe Sketchfab plugin for Windows requires\nCinema 4D R15 or greater.", c4d.GEMB_OK)
            return False

        if self.dialog is None:
            self.dialog = MainDialog()

        return self.dialog.Open(dlgtype = c4d.DLG_TYPE_ASYNC,
                                pluginid = __plugin_id__,
                                defaultw = 600,
                                defaulth = 450)

    def RestoreLayout(self, sec_ref):
        if self.dialog is None:
            self.dialog = MainDialog()

        return self.dialog.Restore(pluginid = __plugin_id__, secret = sec_ref)



if __name__ == "__main__":
    icon = bitmaps.BaseBitmap()
    dir, file = os.path.split(__file__)
    iconPath = os.path.join(dir, "res", "icon.png")
    icon.InitWith(iconPath)

    plugins.RegisterCommandPlugin(id = __plugin_id__,
                                  str = __plugin_title__,
                                  info = 0, 
                                  help = HELP_TEXT,
                                  dat = SketchfabExporter(),
                                  icon = icon)
