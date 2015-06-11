# -*- coding: utf-8 -*-
'''
 CMIS Trac Plugin
 Copyright (C) 2009-2011 klicap - ingeniería del puzle
 Copyright (C) 2015 juanyque

 $Id: web_ui.py 133 2015-06-11 10:00:00Z juanyque $
'''
from genshi.builder import tag
from trac.core import *
from trac.util import TracError
from trac.perm import IPermissionRequestor
from trac.web import IRequestHandler, RequestDone
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_stylesheet, add_script, add_ctxtnav
from cmislib.model import CmisClient
from cmistracplugin.util import render_breadcrumb
import pkg_resources
import re
import os
import unicodedata

__all__ = ['CmisTracPlugin']

CHUNK_SIZE = 4096

class CmisTracPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider, IPermissionRequestor)

    def __init__(self):
        Component.__init__(self)
        self.url_api = None
        self.user = None
        self.password = None
        self.base_path = None
        self.max_size = None
        self.cmis_client = None
        self.repository = None
        self.root_cmis_object = None

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'documents'

    def get_navigation_items(self, req):
        if req.perm.has_permission('REPOSITORY_BROWSER'):
            yield ('mainnav', 'documents', tag.a('Documents', href=req.href.documents()))

    # IRequestHandler methods

    def match_request(self, req):
        '''Check if applicable to this plugin'''
        match = re.match('^(/documents)(/)?(workspace://SpacesStore/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})?(/)?(newfolder|removefolder|renamefolder|upload|download|removedocument)?$', req.path_info)
        if match:
            if match.group(3) != None:
                req.args['objectId'] = match.group(3)
            if match.group(5) != None:
                req.args['op'] = match.group(5)
            return True
        else:
            return False

    def process_request(self, req):
        '''Processes the request. Input validation and call the corresponding method'''
        req.perm.assert_permission('REPOSITORY_BROWSER')
        self.load_config()
        xhr = req.get_header('X-Requested-With') == 'XMLHttpRequest'
        add_script(req, 'common/js/expand_dir.js')
        add_stylesheet(req, 'common/css/browser.css')
        add_stylesheet(req, 'hw/cmistracplugin.css')

        if xhr:
            return 'folder-entries.html', self._render_cmis_object(req, xhr), None

        elif 'op' in req.args and req.args['op'] == 'newfolder':
            if 'objectId' in req.args:
                return 'new-folder.html', self._prepare_newfolder_form(req), None
            else:
                self._process_newfolder_form(req)
                req.redirect(req.href.documents(req.args['objectId']))

        elif 'op' in req.args and req.args['op'] == 'removefolder':
            if 'objectId' in req.args:
                self._process_removefolder(req)
                req.redirect(req.href.documents(req.args['objectId']))

        elif 'op' in req.args and req.args['op'] == 'renamefolder':
            if 'objectId' in req.args:
                if req.method == 'GET':
                    return 'rename-folder.html', self._prepare_renamefolder_form(req), None
                else:
                    self._process_renamefolder_form(req)
                    if req.args['parentId']:
                        req.redirect(req.href.documents(req.args['parentId']))
                    else:
                        req.redirect(req.href.documents(req.args['objectId']))

        elif 'op' in req.args and req.args['op'] == 'upload':
            if 'objectId' in req.args:
                return 'upload-document.html', self._prepare_upload_form(req), None
            elif 'cancel' in req.args:
                req.redirect(req.href.documents(req.args['parentId']))
            else:
                self._process_upload_form(req)
                req.redirect(req.href.documents(req.args['objectId']))

        elif 'op' in req.args and req.args['op'] == 'download':
            if 'objectId' in req.args:
                self._process_download(req)

        elif 'op' in req.args and req.args['op'] == 'removedocument':
            if 'objectId' in req.args:
                self._process_removedocument(req)
                if req.session['lastCmisFolderIdVisited']:
                    req.redirect(req.href.documents(req.session['lastCmisFolderIdVisited']))
                else:
                    req.redirect(req.href.documents())
        else:
            print "cmistracplugin: go to 'repository-browser.html'"
            #self.env.log.debug
            self.log.debug("cmistracplugin: go to 'repository-browser.html'")
            return 'repository-browser.html', self._render_cmis_object(req), None

    # ITemplateProvider methods

    def get_templates_dirs(self):
        return [pkg_resources.resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        return [('hw', pkg_resources.resource_filename(__name__, 'htdocs'))]

    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['REPOSITORY_BROWSER', 'REPOSITORY_UPLOAD', 'REPOSITORY_DOWNLOAD', 'REPOSITORY_CREATE_FOLDER', 'REPOSITORY_REMOVE_FOLDER', 'REPOSITORY_RENAME_FOLDER', 'REPOSITORY_REMOVE_DOCUMENT']

    def load_config(self):
        '''Read available configurations options from trac.ini'''

        self.url_api = self.env.config.get('cmis', 'url_api')
        self.user = self.env.config.get('cmis', 'user')
        self.password = self.env.config.get('cmis', 'password')
        self.base_path = self.env.config.get('cmis', 'base_path')
        self.max_size = self.env.config.getint('cmis', 'max_size')
        self.log.info('Plugin Configuration loaded')
        try:
            self.cmis_client = CmisClient(self.url_api, self.user, self.password)
            self.repository = self.cmis_client.getDefaultRepository()
            self.root_cmis_object = self.repository.getObjectByPath(self.base_path)
        except:
            raise TracError('Unable to connect to the repository. Check the configuration')

    def _render_cmis_object(self, req, xhr = None):
        if 'objectId' in req.args:
            cmis_object = self.repository.getObject(req.args['objectId'])
        else:
            cmis_object = self.root_cmis_object

        data = {}
        data['rootFolder'] = self.root_cmis_object

        print "p1: cmistracplugin: cmis:objectTypeId: " + cmis_object.getProperties()['cmis:objectTypeId']
        #self.env.log.debug
        self.log.debug("l: cmistracplugin: cmis:objectTypeId: " + cmis_object.getProperties()['cmis:objectTypeId'])

        if cmis_object.getProperties()['cmis:objectTypeId'] in ['cmis:folder', 'Folder', 'Section', 'Workspace']:
        #if cmis_object.getProperties()['cmis:objectTypeId'] == 'cmis:folder' || cmis_object.getProperties()['cmis:objectTypeId'] == 'cmis:Section':
            cmis_objects = cmis_object.getChildren().getResults()
            data['breadcrumb'] = render_breadcrumb(self.cmis_client, self.repository, self.root_cmis_object, cmis_object)
            if cmis_object.getObjectId() != self.root_cmis_object.getObjectId():
                data['parentId'] = cmis_object.getProperties()['cmis:parentId']
            data['cmis_objectTypeId'] = 'cmis:folder'

            print "cmistracplugin: cmis_objects: " + str(cmis_objects)
            self.log.debug("cmistracplugin: cmis_objects: " + str(cmis_objects))
            for idx in range(len(cmis_objects)):
                print "-- cmistracplugin: cmis:objectTypeId: " + cmis_objects[idx].getProperties()['cmis:objectTypeId']

            data['cmis_objects'] = cmis_objects
            add_ctxtnav(req, tag.a('New folder', href=req.href.documents(cmis_object.getProperties()['cmis:objectId'], 'newfolder')))
            add_ctxtnav(req, tag.a('Remove folder', href=req.href.documents(cmis_object.getProperties()['cmis:objectId'], 'removefolder')))
            add_ctxtnav(req, tag.a('Rename folder', href=req.href.documents(cmis_object.getProperties()['cmis:objectId'], 'renamefolder')))
            add_ctxtnav(req, tag.a('Upload document', href=req.href.documents(cmis_object.getProperties()['cmis:objectId'], 'upload')))
        elif cmis_object.getProperties()['cmis:objectTypeId'] == 'cmis:document':
            data['breadcrumb'] = render_breadcrumb(self.cmis_client, self.repository, self.root_cmis_object, cmis_object)
            data['cmis_objectTypeId'] = 'cmis:document'
            data['cmis_object'] = cmis_object
        else:
            print "cmistracplugin: Unknow cmis:objectTypeId: " + cmis_object.getProperties()['cmis:objectTypeId']
            #self.env.log.debug
            self.log.debug("cmistracplugin: Unknow cmis:objectTypeId: " + cmis_object.getProperties()['cmis:objectTypeId'])

        if cmis_object.getProperties()['cmis:objectTypeId'] == 'cmis:folder' and xhr == None:
            req.session['lastCmisFolderIdVisited'] = cmis_object.getObjectId()
        return data

    def _prepare_newfolder_form(self, req):
        req.perm.require('REPOSITORY_CREATE_FOLDER')
        data = {
            'parentId': req.args['objectId']
        }
        return data

    def _process_newfolder_form(self, req):
        '''Processes the request to create a new directory'''
        req.perm.require('REPOSITORY_CREATE_FOLDER')
        if req.method == 'POST' and 'name' in req.args and 'parentId' in req.args:
            if 'name' in req.args and req.args['name'] != '':
                parent_folder = self.repository.getObject(req.args['parentId'])
                parent_folder.createFolder(req.args['name'].encode('utf-8'))
                req.args['objectId'] = req.args['parentId']
                del req.args['parentId']
            else:
                raise TracError('The folder name can not be empty')
        self.log.info('A new folder has been created')

    def _process_removefolder(self, req):
        '''Processes the request to remove a folder'''
        req.perm.require('REPOSITORY_REMOVE_FOLDER')
        if 'objectId' in req.args:
            cmis_object = self.repository.getObject(req.args['objectId'])
            if cmis_object.getObjectId() == self.root_cmis_object.getObjectId():
                raise TracError('Can\'t remove root folder')
            parent_folder = self.repository.getObject(cmis_object.getProperties()['cmis:parentId'])
            cmis_object.deleteTree()
            req.args['objectId'] = parent_folder.getObjectId()
        self.log.info('A folder has been removed')

    def _prepare_upload_form(self, req):
        req.perm.require('REPOSITORY_UPLOAD')
        data = {
            'parentId': req.args['objectId'],
            'max_size': self.max_size
        }
        return data

    def _process_upload_form(self, req):
        req.perm.require('REPOSITORY_UPLOAD')
        upload = req.args['document']

        if not hasattr(upload, 'filename') or not upload.filename:
            raise TracError('No file uploaded')

        if hasattr(upload.file, 'fileno'):
            size = os.fstat(upload.file.fileno())[6]
        else:
            upload.file.seek(0, 2) # seek to end of file
            size = upload.file.tell()
            upload.file.seek(0)

        if size == 0:
            raise TracError('Can\'t upload empty document')

        if size > self.max_size:
            raise TracError('Maximum document size: %s KB' % self.max_size)

        # We try to normalize the filename to unicode NFC if we can.
        # Files uploaded from OS X might be in NFD.
        filename = unicodedata.normalize('NFC', unicode(upload.filename, 'utf-8'))
        filename = filename.replace('\\', '/').replace(':', '/')
        filename = os.path.basename(filename)
        if not filename:
            raise TracError('No file uploaded')

        if 'parentId' in req.args:
            cmis_object = self.repository.getObject(req.args['parentId'])
            if cmis_object.getProperties()['cmis:objectTypeId'] == 'cmis:folder':
                cmis_object.createDocument(filename.encode('utf-8'), contentFile = upload.file, contentType = upload.type)

        req.args['objectId'] = req.args['parentId']
        del req.args['parentId']
        self.log.info('A document has been saved')

    def _process_download(self, req):
        req.perm.require('REPOSITORY_DOWNLOAD')
        cmis_object = self.repository.getObject(req.args['objectId'])
        # Validar que es un objecto de tipo documento
        content = cmis_object.getContentStream()
        req.send_response(200)
        req.send_header('Content-Type', cmis_object.getProperties()['cmis:contentStreamMimeType'])
        req.send_header('Content-Length', cmis_object.getProperties()['cmis:contentStreamLength'])
        req.send_header('Last-Modified', cmis_object.getProperties()['cmis:lastModificationDate'])
        req.send_header('Content-Disposition', 'attachment; filename="%s"' % cmis_object.getName())
        req.end_headers()
        chunk = content.read(CHUNK_SIZE)
        while 1:
            if not chunk:
                raise RequestDone
            req.write(chunk)
            chunk = content.read(CHUNK_SIZE)
        self.log.info('A document has been downloaded')

    def _prepare_renamefolder_form(self, req):
        req.perm.require('REPOSITORY_RENAME_FOLDER')
        cmis_object = self.repository.getObject(req.args['objectId'])
        data = {
            'cmis_object': cmis_object
        }
        return data

    def _process_renamefolder_form(self, req):
        req.perm.require('REPOSITORY_RENAME_FOLDER')
        folder = self.repository.getObject(req.args['objectId'])
        parent_folder = folder.getParent()
        props = {
            'cmis:name': req.args['name'].encode('utf-8')
        }
        folder.updateProperties(props)
        if parent_folder:
            req.args['parentId'] = parent_folder.getObjectId()
        self.log.info('A folder has been renamed')

    def _process_removedocument(self, req):
        req.perm.require('REPOSITORY_REMOVE_DOCUMENT')
        if 'objectId' in req.args:
            cmis_object = self.repository.getObject(req.args['objectId'])
            cmis_object.delete()
        self.log.info('A document has been removed')
