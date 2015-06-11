# -*- coding: utf-8 -*-
#
# CMIS Trac Plugin
# Copyright (C) 2009-2011 klicap - ingeniería del puzle
#
# $Id: setup.py 132 2011-06-20 20:30:15Z recena $
#
from setuptools import setup, find_packages

setup(
    name='CmisTracPlugin',
    version='1.1-dev',
    packages=find_packages(),
    author='klicap - ingenieria del puzle, S.L.',
    author_email='hello@klicap.es',
    description='Integra una solucion ECM a traves de CMIS',
    url='http://clinker.klicap.es/projects/alfrescointegration',
    license='GNU GPL v3',
    entry_points = {
        'trac.plugins': [
            'cmistracplugin = cmistracplugin.web_ui',
        ]
    },
    package_data = {
        'cmistracplugin' : [
            'templates/repository-browser.html',
            'templates/folder-entries.html',
            'templates/new-folder.html',
            'templates/upload-document.html',
            'templates/rename-folder.html',
            'templates/document.html',
            'templates/folder.html',
            'htdocs/*.png',
            'htdocs/cmistracplugin.css'
        ]
    },
    install_requires = [
        'cmislib>=0.4.1'
    ],
)