# -*- coding: utf-8 -*-
##
##
## This file is part of Indico.
## Copyright (C) 2002 - 2012 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.
from MaKaC.plugins.Collaboration.base import SpeakerStatusEnum
from indico.MaKaC.services.implementation.base import TextModificationBase
"""
Services for Collaboration plugins
"""

from MaKaC.services.implementation.contribution import ContributionDisplayBase
from MaKaC.services.implementation.conference import ConferenceModifBase, ConferenceDisplayBase
from MaKaC.plugins.Collaboration.urlHandlers import UHCollaborationElectronicAgreementForm
from MaKaC.plugins.Collaboration.mail import ElectronicAgreementNotification, ElectronicAgreementOrganiserNotification
from MaKaC.common.mail import GenericMailer
from MaKaC.common.Configuration import Config

from indico.util.i18n import N_


#TODO: Need to verify if the ContributionDisplayBase is the good parent to inherit from
class SetSpeakerEmailAddress(ContributionDisplayBase):

    def _checkParams(self):
        ContributionDisplayBase._checkParams(self)

        self.newEmailAddress = self._params['value']
        self.spkId = self._params['spkId']

    def _getAnswer(self):
        self._contribution.getSpeakerById(self.spkId).setEmail(self.newEmailAddress)
        self._contribution.notifyModification()

class SetChairEmailAddress(ConferenceModifBase):

    def _checkParams(self):
        ConferenceModifBase._checkParams(self)

        self.newEmailAddress = self._params['value']
        self.spkId = self._params['spkId']

    def _getAnswer(self):
        self._conf.getChairById(self.spkId).setEmail(self.newEmailAddress)

class GetSpeakerEmailListByCont(ConferenceModifBase):
    def _checkParams(self):
        ConferenceModifBase._checkParams(self)
        self.contList = self._params['contList']
        self.userId = self._params['userId']

    def _getAnswer(self):
        manager = self._conf.getCSBookingManager()
        resultList = []
        for cont in self.contList:
            resultList.extend(manager.getSpeakerEmailListByContribution(cont, self.userId))

        return resultList

class SendElectronicAgreement(ConferenceModifBase):
    def _buildEmailList(self, value):
        emailList = []
        if (value == ""):
            return emailList
        else:
            # replace to have only one separator
            value = value.replace(" ",",")
            value = value.replace(";",",")
            emailList = value.split(",")
            return emailList

    def _checkParams(self):
        ConferenceModifBase._checkParams(self)

        self.uniqueIdList = self._params['uniqueIdList']

        self.emailToList = []

        self.fromEmail = self._params['from']['email']
        self.fromName = self._params['from']['name']
        self.content = self._params['content']
        self.cc = self._buildEmailList(self._params['cc'])
        manager = self._conf.getCSBookingManager()
        for uniqueId in self.uniqueIdList:
            self.emailToList.extend(manager.getSpeakerEmailByUniqueId(uniqueId, self._aw.getUser()))

    def processContent(self, speakerWrapper):
        fullUrl = UHCollaborationElectronicAgreementForm().getURL(self._conf.getId(), speakerWrapper.getUniqueIdHash())
        url = "<a href='%s'>%s</a>"%(fullUrl, fullUrl)

        talkTitle = speakerWrapper.getContribution().getTitle() if speakerWrapper.getContribution() else self._conf.getTitle()

        return self.content.format(url=url, talkTitle = talkTitle, name= speakerWrapper.getObject().getDirectFullName())

    def _getAnswer(self):
        report = ""
        i = 0
        for email in self.emailToList:
            i += 1
            if i != len(self.emailToList):
                report += "%s, "%email
            else:
                report += "%s."%email

        #{url} and {talkTitle} are mandatory to send the EA link
        if self.content.find('{url}') == -1:
            report = "url_error"
        elif self.content.find('{talkTitle}') == -1:
            report = "talkTitle_error"
        else:
            manager = self._conf.getCSBookingManager()
            for uniqueId in self.uniqueIdList:
                sw = manager.getSpeakerWrapperByUniqueId(uniqueId)
                sw.setStatus(SpeakerStatusEnum.PENDING)
                subject = """[Indico] Electronic Agreement: '%s'"""%(self._conf.getTitle())
                notification = ElectronicAgreementNotification([sw.getObject().getEmail()], self.cc, self.fromEmail, self.fromName, self.processContent(sw), subject)

                GenericMailer.sendAndLog(notification, self._conf,
                                         "MaKaC/plugins/Collaboration/RecordingRequest/collaboration.py",
                                         None)
        return report

class RejectElectronicAgreement(ConferenceDisplayBase):

    MESSAGE_REJECT = """Dear manager,
The speaker {speaker} has rejected the electronic agreement for the event '{title}'.

Event URL: {url}

Best Regards,

CERN Recording Team"""

    def _checkParams(self):
        ConferenceDisplayBase._checkParams(self)
        self.authKey = self._params["authKey"]
        self.reason = self._params["reason"]

    def _getAnswer(self):
        spkWrapper = None
        manager = self._conf.getCSBookingManager()
        for sw in manager.getSpeakerWrapperList():
            if sw.getUniqueIdHash() == self.authKey:
                spkWrapper = sw

        if spkWrapper:
            spkWrapper.setStatus(SpeakerStatusEnum.REFUSED)
            spkWrapper.setRejectReason(self.reason)
            spkWrapper.triggerNotification()
            if manager.notifyElectronicAgreementAnswer():
                subject = """[Indico] Electronic Agreement Rejected: '%s' (speaker : %s)""" % (self._conf.getTitle(), spkWrapper.getSpeakerId())
                content = _(self.MESSAGE_REJECT).format(
                    speaker=spkWrapper.getObject().getFullName(),
                    title=self._conf.getTitle(),
                    url=self._conf.getURL())
                emailToList = [self._conf.getCreator().getEmail()]
                for event_manager in self._conf.getManagerList():
                    emailToList.append(event_manager.getEmail())
                notification = ElectronicAgreementOrganiserNotification(emailToList, Config.getInstance().getNoReplyEmail(), content, subject)

                GenericMailer.sendAndLog(notification, self._conf,
                                         "MaKaC/plugins/Collaboration/RecordingRequest/collaboration.py",
                                         None)

class AcceptElectronicAgreement(ConferenceDisplayBase):

    MESSAGE_ACCEPT = """Dear manager,
The speaker {speaker} has accepted the electronic agreement for the event '{title}'.

Event URL: {url}

Best Regards,

CERN Recording Team"""

    def _checkParams(self):
        ConferenceDisplayBase._checkParams(self)
        self.authKey = self._params["authKey"]

    def _getAnswer(self):
        spkWrapper = None
        manager = self._conf.getCSBookingManager()
        for sw in manager.getSpeakerWrapperList():
            if sw.getUniqueIdHash() == self.authKey:
                spkWrapper = sw

        if spkWrapper:
            spkWrapper.setStatus(SpeakerStatusEnum.SIGNED, self._req.get_remote_ip())
            spkWrapper.triggerNotification()
            if manager.notifyElectronicAgreementAnswer():
                subject = """[Indico] Electronic Agreement Accepted: '%s' (speaker : %s)""" % (self._conf.getTitle(), spkWrapper.getSpeakerId())
                content = _(self.MESSAGE_ACCEPT).format(
                    speaker=spkWrapper.getObject().getFullName(),
                    title=self._conf.getTitle(),
                    url=self._conf.getURL())
                emailToList = [self._conf.getCreator().getEmail()]
                for event_manager in self._conf.getManagerList():
                    emailToList.append(event_manager.getEmail())
                notification = ElectronicAgreementOrganiserNotification(emailToList, Config.getInstance().getNoReplyEmail(), content, subject)

                GenericMailer.sendAndLog(notification, self._conf,
                                         "MaKaC/plugins/Collaboration/RecordingRequest/collaboration.py",
                                         None)


class ToggleNotifyElectronicAgreementAnswer(TextModificationBase, ConferenceModifBase):

    def _checkParams(self):
        ConferenceModifBase._checkParams(self)
        self._CSManager = self._conf.getCSBookingManager()

    def _handleSet(self):
        self._CSManager.setNotifyElectronicAgreementAnswer(self._value)

    def _handleGet(self):
        return self._CSManager.notifyElectronicAgreementAnswer()


methodMap = {
    "collaboration.setEmailSpeaker": SetSpeakerEmailAddress,
    "collaboration.setEmailChair": SetChairEmailAddress,
    "collaboration.sendElectronicAgreement": SendElectronicAgreement,
    "collaboration.getSpeakerEmailList": GetSpeakerEmailListByCont,
    "collaboration.rejectElectronicAgreement": RejectElectronicAgreement,
    "collaboration.acceptElectronicAgreement": AcceptElectronicAgreement,
    "collaboration.toggleNotifyElectronicAgreementAnswer": ToggleNotifyElectronicAgreementAnswer
}
