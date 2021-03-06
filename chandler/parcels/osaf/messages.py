#   Copyright (c) 2003-2008 Open Source Applications Foundation
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


from i18n import ChandlerMessageFactory as _

#XXX: Relook at how to leverage wxstd translations

UNTITLED = _(u"Untitled")
# L10N: The word 'me' is used to represent the
#       current Chandler user. Instead of
#       displaying the users email address in
#       the UI for fields such as the From:,
#       'me' will be used instead.
ME = _(u"me")

"""Common GUI Stuff. This might come directly from WxWidgets"""
UNDO   = _(u"&Undo")
REDO   = _(u"&Redo")
CUT    = _(u"Cu&t")
COPY   = _(u"&Copy")
PASTE  = _(u"&Paste")
CLEAR  = _(u"C&lear")
SELECT_ALL = _(u"Select &All")
ERROR = _(u"Error")

"""Menu Item / Markup bar button Titles"""
SEND = _(u"Send")
SENT = _(u"Sent")
UPDATE = _(u"Update")
UPDATED = _(u"Updated")
REPLY = _(u"Reply")
REPLY_ALL = _(u"Reply All")
FORWARD = _(u"Forward")
STAMP_MAIL = _(u"Address item")
STAMP_TASK = _(u"Star item")
STAMP_CALENDAR = _(u"Add to Calendar")
UNSTAMP_MAIL = _(u"Remove Addresses")
UNSTAMP_TASK = _(u"Remove star")
UNSTAMP_CALENDAR = _(u"Remove from Calendar")
STAMP_TRIAGE = _(u"Change Triage status")
PRIVATE = _(u"Never share")
NOT_PRIVATE = _(u"Allow sharing")
READONLY = _(u"View-only")

STAMP_MAIL_HELP = _(u"Address item")
STAMP_TASK_HELP = _(u"Star this item")
STAMP_CALENDAR_HELP = _(u"Add to Calendar")
UNSTAMP_MAIL_HELP = _(u"Remove Addresses")
UNSTAMP_TASK_HELP = _(u"Remove star")
UNSTAMP_CALENDAR_HELP = _(u"Remove from Calendar")
STAMP_TRIAGE_HELP = _(u"Change Triage status")

"""Server Account Settings"""
USERNAME = _(u"User name")
PASSWORD = _(u"Password")
HOST = _(u"Host")
PORT = _(u"Port")
PATH = _(u"Path")

"""Account Configuration"""
NEW_ACCOUNT = _(u"New %(accountType)s Account")
ACCOUNT_PREFERENCES = _(u"Account Preferences")
ACCOUNT = _(u"%(accountName)s Account")

# SSL
SSL_HOST_MISMATCH = _(u'Peer certificate does not match host, got %(actualHost)s')

