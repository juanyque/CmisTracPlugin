# -*- coding: utf-8 -*-
'''
 CMIS Trac Plugin
 Copyright (C) 2009-2011 klicap - ingeniería del puzle
 Copyright (C) 2015 juanyque

 $Id$
'''
from cmislib.model import ResultSet, UP_REL, HTTPError
from cmislib.exceptions import CmisException, NotSupportedException

def render_breadcrumb(cmis_client, repository, cmis_root_folder, cmis_object):
    breadcrumb = []
    if cmis_object.getProperties()['cmis:objectTypeId'] in ['cmis:document', 'File']:
        breadcrumb.append(cmis_object)
        result_set = get_object_parents(cmis_client, repository, cmis_object)
        cmis_object = result_set.getResults()[0]
    elif cmis_object.getProperties()['cmis:objectTypeId'] in ['cmis:folder', 'Folder', 'Section', 'Workspace']:
        while cmis_object != None and cmis_object.getObjectId() != cmis_root_folder.getObjectId():
            breadcrumb.append(cmis_object)
            try:
                cmis_object = cmis_object.getParent()
            except NotSupportedException:
                cmis_object = None
    else:
        print "cmistracplugin: Unknow cmis:objectTypeId: " + cmis_object.getProperties()['cmis:objectTypeId']

    # Interesante forma de invertir una lista de forma recursiva. http://tinyurl.com/2v7ygrt
    #backwards = lambda l: (backwards (l[1:]) + l[:1] if l else [])
    #return backwards(breadcrumb)
    print "cmis: len(breadcrumb): " + str(len(breadcrumb))
    print "cmis: srt(breadcrumb): " + str(breadcrumb)
    breadcrumb.reverse()

    return breadcrumb

def get_object_parents(cmis_client, repository, cmis_object):
    parent_url = cmis_object._getLink(UP_REL)

    if parent_url == None:
        raise NotSupportedException('Root folder does not support getObjectParents')

    # invoke the URL
    result = cmis_client.get(parent_url)

    if type(result) == HTTPError:
        raise CmisException(result.code)

    # return the result set
    return ResultSet(cmis_client, repository, result)
