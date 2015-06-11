# -*- coding: utf-8 -*-
#
# CMIS Trac Plugin
# Copyright (C) 2009-2011 klicap - ingeniería del puzle
# Copyright (C) 2015 juanyque
#
# $Id: setup.py 133 2015-06-11 10:00:00Z juanyque $
#
from setuptools import setup, find_packages

setup(
    name='CmisTracPlugin',
    version='1.2.0',
    packages=find_packages(),
    author='juanyque',
    author_email='juan.mobilife@gmail.com',
    description='Integra una solucion ECM a traves de CMIS',
    url='https://github.com/juanyque/CmisTracPlugin',
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
