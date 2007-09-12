#
# Copyright (C) 2007, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

from qt import *
from kdeui import *
from kdecore import *

from utility import *
from dialogs import *
import domain

import ldap


class Browser(KListView):
    """Domain browser"""
    
    def __init__(self, parent, window):
        KListView.__init__(self, parent)
        self.addColumn("")
        self.header().hide()
        self.setRootIsDecorated(True)
        self.window = window
        
        self.menu_domain = QPopupMenu(self)
        self.menu_domain.insertItem(getIconSet("folder", KIcon.Small), i18n("&New Directory"), self.slotNewDirectory)
        self.menu_domain.insertSeparator()
        self.menu_domain.insertItem(getIconSet("remove", KIcon.Small), i18n("&Remove"), self.slotRemove)
        self.menu_domain.insertSeparator()
        self.menu_domain.insertItem(getIconSet("configure", KIcon.Small), i18n("&Configuration"), self.slotProperties)
        
        self.menu_directory = QPopupMenu(self)
        self.menu_directory.insertItem(getIconSet("folder", KIcon.Small), i18n("&New Directory"), self.slotNewDirectory)
        self.menu_directory.insertSeparator()
        self.menu_directory.insertItem(getIconSet("remove", KIcon.Small), i18n("&Remove"), self.slotRemoveDirectory)
        self.menu_directory.insertSeparator()
        self.menu_directory.insertItem(getIconSet("reload", KIcon.Small), i18n("&Refresh"), self.slotRefresh)
        self.menu_directory.insertSeparator()
        self.menu_directory.insertItem(getIconSet("configure", KIcon.Small), i18n("&Properties"), self.slotDirectoryProperties)
        
        self.connect(self, SIGNAL("contextMenuRequested(QListViewItem*, const QPoint &, int)"), self.slotPopup)
        self.connect(self, SIGNAL("expanded(QListViewItem*)"), self.slotExpand)
        self.connect(self, SIGNAL("collapsed(QListViewItem*)"), self.slotCollapse)
        self.connect(self, SIGNAL("selectionChanged()"), self.slotNodeChanged)
        
        self.initDomains()
    
    def initDomains(self):
        dc = self.window.dc
        for connection in dc.connections:
            label = connection.label
            dn = connection.base_dn
            BrowserItem(self, self.window, dn, label, None, connection)
    
    def slotPopup(self, item, point, button):
        if item:
            if isinstance(item.parent(), BrowserItem):
                self.menu_directory.exec_loop(point)
            else:
                self.menu_domain.exec_loop(point)
    
    def slotProperties(self):
        item = self.selectedItem()
        dd = DomainDialog(self, item.connection)
        if dd.exec_loop():
            try:
                item.reloadObject()
            except ldap.LDAPError:
                item.disableDomain()
            if item.connection.isModified():
                dc = self.window.dc
    
    def slotDirectoryProperties(self):
        item = self.selectedItem()
        dd = DirectoryDialog(self, item.dn, item.dc, item.label)
        old_attrs = {
            "o": item.label
        }
        if dd.exec_loop():
            dn = str(dd.dn)
            dc = str(dd.dc)
            o = str(dd.o)
            new_attrs = {
                "o": [o],
            }
            connection = item.connection
            try:
                connection.modify(dn, old_attrs, new_attrs)
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    item.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                item.parent().collapseNodes()
                item.parent().expandNodes()
    
    def slotNewDirectory(self):
        item = self.selectedItem()
        dd = DirectoryDialog(self, item.dn, "", "")
        if dd.exec_loop():
            dn = str(dd.dn)
            dc = str(dd.dc)
            o = str(dd.o)
            attrs = {
                "objectclass": ["dcObject", "organization"],
                "dc": [dc],
                "o": [o],
            }
            connection = item.connection
            try:
                connection.add("dc=%s,%s" % (dc, dn), attrs)
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    item.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                if item.isOpen():
                    item.collapseNodes()
                item.expandNodes()
    
    def slotRemoveDirectory(self):
        item = self.selectedItem()
        confirm = self.window.doubleConfirm(i18n("Remove directory?"), i18n("Are you sure you want to remove '%1' ?").arg(item.text(0)), i18n("This is not undoable. Are you sure you want to continue?"))
        if confirm:
            try:
                item.connection.delete(item.dn)
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    item.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                item.parent().collapseNodes()
                item.parent().expandNodes()
    
    def slotRemove(self):
        item = self.selectedItem()
        confirm = self.window.confirm(i18n("Remove domain?"), i18n("Are you sure you want to remove '%1' ?").arg(item.text(0)))
        if confirm:
            item.disableDomain()
            dc = self.window.dc
            dc.removeConnection(item.connection)
            self.takeItem(item)
    
    def slotRefresh(self):
        self.showObjects()
    
    def slotExpand(self, item):
        item.expandNodes()
    
    def slotCollapse(self, item):
        item.collapseNodes()
    
    def slotNodeChanged(self):
        self.showObjects()
    
    def showObjects(self):
        object_len = 0
        show_tab = None
        
        self.window.computers.clear()
        item = self.selectedItem()
        if item and isinstance(item.parent(), BrowserItem):
            try:
                result = item.connection.search(item.dn, ldap.SCOPE_ONELEVEL, "objectClass=pardusComputer")
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                for computer in result:
                    dn = computer[0]
                    label = unicode(computer[1]["cn"][0])
                    self.window.computers.addUnit(dn, label, "computer")
                self.window.tab.setTabLabel(self.window.computers, i18n("Computers (%1)").arg(len(result)))
                
                show_tab = self.window.computers
                object_len = len(result)
        
        self.window.units.clear()
        item = self.selectedItem()
        if item and isinstance(item.parent(), BrowserItem):
            try:
                result = item.connection.search(item.dn, ldap.SCOPE_ONELEVEL, "objectClass=organizationalUnit")
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                for computer in result:
                    dn = computer[0]
                    label = unicode(computer[1]["ou"][0])
                    self.window.units.addUnit(dn, label, "unit")
                self.window.tab.setTabLabel(self.window.units, i18n("Units (%1)").arg(len(result)))
                if len(result) > object_len:
                    show_tab = self.window.units
                    object_len = len(result)
        
        self.window.users.clear()
        item = self.selectedItem()
        if item and isinstance(item.parent(), BrowserItem):
            try:
                result = item.connection.search(item.dn, ldap.SCOPE_ONELEVEL, "objectClass=posixAccount")
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                for computer in result:
                    dn = computer[0]
                    label = unicode(computer[1]["cn"][0])
                    self.window.users.addUnit(dn, label, "user")
                self.window.tab.setTabLabel(self.window.users, i18n("Users (%1)").arg(len(result)))
                if len(result) > object_len:
                    show_tab = self.window.users
                    object_len = len(result)
        
        self.window.groups.clear()
        item = self.selectedItem()
        if item and isinstance(item.parent(), BrowserItem):
            try:
                result = item.connection.search(item.dn, ldap.SCOPE_ONELEVEL, "objectClass=posixGroup")
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                for computer in result:
                    dn = computer[0]
                    label = unicode(computer[1]["cn"][0])
                    self.window.groups.addUnit(dn, label, "group")
                self.window.tab.setTabLabel(self.window.groups, i18n("Groups (%1)").arg(len(result)))
                if len(result) > object_len:
                    show_tab = self.window.groups
                    object_len = len(result)
        
        self.window.tab.showPage(show_tab)


class BrowserItem(QListViewItem):
    """Domain tree element.
       Requires a parent node object, window object and DN for the node.
       Non-root nodes require a label, root nodes require a connection object."""
    
    def __init__(self, parent, window, dn, label=None, dc=None, connection=None):
        self.window = window
        self.dn = dn
        self.dc = dc
        if connection:
            self.connection = connection
        else:
            self.connection = parent.connection
        self.label = unicode(label)
        QListViewItem.__init__(self, parent, self.label)
        self.setExpandable(True)
        self.initObject()
    
    def initObject(self):
        """Initialize domain object. Gets label from domain server, if it's a root node."""
        if isinstance(self.parent(), BrowserItem):
            self.setState("node_close")
        else:
            try:
                self.connection.bind()
            except ldap.LDAPError, e:
                self.disableDomain()
                return
            try:
                results = self.connection.search(self.dn, ldap.SCOPE_BASE, "objectClass=organization")
                dn, attrs = results[0]
                label = unicode(attrs["o"][0])
                self.setText(0, label)
            except ldap.LDAPError, e:
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
            else:
                self.setState("active")
    
    def reloadObject(self):
        """Reset connection and initialize domain object again."""
        self.connection.unbind()
        self.connection.bind()
        self.initObject()
    
    def getRootNode(self):
        """Find root node."""
        item = self
        while True:
            if not isinstance(item.parent(), BrowserItem):
                return item
            item = item.parent()
    
    def disableDomain(self):
        """Disable domain tree. Used when connection errors occur."""
        self.connection.unbind()
        root = self.getRootNode()
        root.setState("error")
        root.clearNodes()
        root.setOpen(False)
    
    def setState(self, state):
        """Set state of a node. (root: [active, error], others: [node_open, node_close]"""
        self.state = state
        if state == "active":
            self.setPixmap(0, getIcon("connect_established.png", KIcon.Small))
        #elif state == "passive":
        #    self.setPixmap(0, getIcon("connect_creating.png", KIcon.Small))
        elif state == "error":
            self.setPixmap(0, getIcon("connect_no.png", KIcon.Small))
        elif state == "node_open":
            self.setPixmap(0, getIcon("folder_open.png", KIcon.Small))
        elif state == "node_close":
            self.setPixmap(0, getIcon("folder.png", KIcon.Small))
    
    def getChildren(self):
        """Give sub-organizations. Returns False on error"""
        try:
            return self.connection.search(self.dn, ldap.SCOPE_ONELEVEL, "objectClass=organization")
        except ldap.LDAPError, e:
            desc = e.args[0]["desc"]
            if not self.firstChild():
                self.setOpen(False)
            if e.__class__ in domain.LDAPCritical:
                self.disableDomain()
            else:
                self.window.showError(e.args[0]["desc"])
            return False
    
    def expandNodes(self):
        if isinstance(self.parent(), BrowserItem):
            self.setState("node_open")
            self.setOpen(True)
        else:
            try:
                self.reloadObject()
            except ldap.LDAPError, e:
                if not self.firstChild():
                    self.setOpen(False)
                if e.__class__ in domain.LDAPCritical:
                    self.disableDomain()
                else:
                    self.window.showError(e.args[0]["desc"])
                return
        
        organizations = self.getChildren()
        if organizations == False:
            if not self.firstChild():
                self.setOpen(False)
        else:
            self.clearNodes()
            for organization in organizations:
                dn, attrs = organization
                label = unicode(attrs["o"][0])
                BrowserItem(self, self.window, dn, label, attrs["dc"][0])
            
            if not len(organizations):
                self.setOpen(False)
    
    def clearNodes(self):
        kid = self.firstChild()
        while kid:
            tmp = kid.nextSibling()
            self.takeItem(kid)
            kid = tmp
    
    def collapseNodes(self):
        if isinstance(self.parent(), BrowserItem):
            self.setState("node_close")


class ObjectList(KListView):
    def __init__(self, parent, window):
        KListView.__init__(self, parent)
        self.addColumn(i18n("Name"))
        self.addColumn(i18n("Description"))
        #self.header().hide()
        self.setResizeMode(KListView.LastColumn)
        self.setRootIsDecorated(False)
        self.setSelectionMode(QListView.Extended)
        self.window = window
        
        self.menu = QPopupMenu(self)
        self.menu.insertItem(getIconSet("remove", KIcon.Small), i18n("&Remove"), self.slotRemove)
        self.menu.insertSeparator()
        self.menu.insertItem(getIconSet("configure", KIcon.Small), i18n("&Configuration"), self.slotProperties)
        
        self.connect(self, SIGNAL("contextMenuRequested(QListViewItem*, const QPoint&, int)"), self.slotPopup)
    
    def addUnit(self, dn, label, type):
        ObjectListItem(self, self.window, dn, label, type)
    
    def slotPopup(self, item, point, col):
        if item:
            self.menu.exec_loop(point)
    
    def slotProperties(self):
        pass
    
    def slotRemove(self):
        browser = self.window.browser
        items = self.selectedItems()
        if len(items) == 1:
            label = items[0].text(0)
            confirm = self.window.doubleConfirm(i18n("Remove object?"), i18n("Are you sure you want to remove '%1' ?").arg(label), i18n("This is not undoable. Are you sure you want to continue?"))
        elif len(items) < 10:
            labels = [" - %s" % item.text(0) for item in items]
            labels = "\n".join(labels)
            confirm = self.window.doubleConfirm(i18n("Remove objects?"), i18n("Are you sure you want to remove these objects?\n%1").arg(labels), i18n("This is not undoable. Are you sure you want to continue?"))
        else:
            count = len(items)
            confirm = self.window.doubleConfirm(i18n("Remove objects?"), i18n("Are you sure you want to remove %1 objects?").arg(count), i18n("This is not undoable. Are you sure you want to continue?"))
        if confirm:
            connection = browser.selectedItem().connection
            failed = []
            for item in items:
                try:
                    connection.delete(item.dn)
                except ldap.LDAPError, e:
                    if e.__class__ in domain.LDAPCritical:
                        item.disableDomain()
                        return
                    else:
                        failed.append((item, e.args[0]["desc"]))
            if len(failed):
                failed = [" - %s (%s)" % (item.label, message) for item, message in failed]
                failed = "\n".join(failed)
                self.window.showWarning(i18n("Unable to delete these objects:\n%1").arg(failed))
            else:
                count = len(items)
                self.window.showInfo(i18n("Removed %1 objects.").arg(count))
                browser.showObjects()


class ObjectListItem(KListViewItem):
    def __init__(self, parent, window, dn, label, type):
        KListViewItem.__init__(self, parent, label)
        self.dn = dn
        self.label = label
        if type == "computer":
            self.setPixmap(0, getIcon("krdc", KIcon.Small))
        elif type == "user":
            self.setPixmap(0, getIcon("user", KIcon.Small))
        elif type == "group":
            self.setPixmap(0, getIcon("kontact_contacts", KIcon.Small))
        elif type == "unit":
            self.setPixmap(0, getIcon("server", KIcon.Small))