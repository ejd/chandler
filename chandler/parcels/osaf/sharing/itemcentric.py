#   Copyright (c) 2003-2007 Open Source Applications Foundation
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

from osaf import pim
import eim, eimml, translator, shares, errors, utility, recordset_conduit
from i18n import ChandlerMessageFactory as _
import logging

logger = logging.getLogger(__name__)


__all__ = [
    'inbound',
    'outbound',
    'outboundDeletion',
]


# Item-centric peer-to-peer sharing

def inbound(peer, text, filter=None, allowDeletion=False, debug=False):

    logger.info("itemcentric.inbound(%s)", str(peer))
    if isinstance(peer, list):
        # Peer email address items can have several that match.  We pass in
        # a list so this code can reuse the one (if any) already associated
        # to the inbound item.
        peers = peer
    else:
        peers = [peer]

    rv = peers[0].itsView

    # At some point, which serializer and translator to use should be
    # configurable
    serializer = eimml.EIMMLSerializer # only using class methods
    trans = translator.SharingTranslator(rv)

    inbound, extra = serializer.deserialize(rv, text, helperView=rv)

    peerRepoId = extra.get('repo', None)
    peerItemVersion = int(extra.get('version', '-1'))

    itemToReturn = None

    aliases = inbound.keys()
    aliases.sort()
    for alias in aliases:
        rsExternal = inbound[alias]

        uuid = trans.getUUIDForAlias(alias)
        if uuid:
            item = rv.findUUID(uuid)
        else:
            item = None

        if rsExternal is not None:

            if item is not None and not getattr(item, '_fake', False):

                # Item already exists
                if not pim.has_stamp(item, shares.SharedItem):
                    shares.SharedItem(item).add()
                shared = shares.SharedItem(item)

                if not getattr(shared, 'peerStates', False):
                    # has no peer states yet, use the first peer in list
                    peer = peers[0]
                else:
                    for state in shared.peerStates:
                        peerUUID = shared.peerStates.getAlias(state)
                        for peer in peers:
                            if peer.itsUUID.str16() == peerUUID:
                                # peer matches
                                break
                        else:
                            # no match; use the first one passed in
                            peer = peers[0]

                state = shared.getPeerState(peer)
                rsInternal= eim.RecordSet(trans.exportItem(item))

            else: # Item doesn't exist yet
                peer = peers[0]
                state = shares.State(itsView=rv, peer=peer)
                rsInternal = eim.RecordSet()


            if state.peerRepoId and (peerRepoId != state.peerRepoId):
                # This update is not from the peer repository we last saw.
                # Treat the update is entirely new
                state.clear()

            if uuid is not None:
                masterAlias, recurrenceID = utility.splitUUID(rv, alias)
                if masterAlias != alias and not state.agreed:
                    # This is a new inbound modification
                    state.agreed += eim.RecordSet(
                        recordset_conduit.getInheritRecords(
                        rsExternal.inclusions, alias))

            state.peerRepoId = peerRepoId

            # Only process recordsets whose version is greater than the last one
            # we say.  In the case of null-repository-view testing, versions are
            # always stuck at zero, so process those as well.

            if ((peerItemVersion == 0) or
                (peerItemVersion > state.peerItemVersion)):

                state.peerItemVersion = peerItemVersion

                dSend, dApply, pending = state.merge(rsInternal, rsExternal,
                    isDiff=False, filter=filter, debug=debug)

                state.autoResolve(rsInternal, dApply, dSend)
                state.updateConflicts(item)

                if dApply:
                    logger.debug("Applying: %s %s", uuid, dApply)
                    trans.startImport()
                    trans.importRecords(dApply)
                    trans.finishImport()

                uuid = trans.getUUIDForAlias(alias)
                if uuid:
                    item = rv.findUUID(uuid)
                else:
                    item = None

                if item is not None and item.isLive():
                    if not pim.has_stamp(item, shares.SharedItem):
                        shares.SharedItem(item).add()

                    shares.SharedItem(item).addPeerState(state, peer)

                    if itemToReturn is None:
                        # the item to return should always be a master, not
                        # a modification
                        itemToReturn = getattr(item, 'inheritFrom', item)

            else:
                logger.info("Out-of-sequence update for %s", uuid)
                raise errors.OutOfSequence("Update %d arrived after %d" %
                    (peerItemVersion, state.peerItemVersion))

        else: # Deletion

            if item is not None:

                # Remove the state
                if pim.has_stamp(item, shares.SharedItem):
                    shared = shares.SharedItem(item)
                    shared.removePeerState(peer)

                # Remove the item (if allowed)
                if allowDeletion:
                    logger.debug("Deleting item: %s", uuid)
                    item.delete(True)
                    item = None

    return itemToReturn



def outbound(peers, item, filter=None, debug=False):

    rv = peers[0].itsView

    if filter is None:
        filter = lambda rs: rs
    else:
        filter = filter.sync_filter

    # At some point, which serializer and translator to use should be
    # configurable
    serializer = eimml.EIMMLSerializer # only using class methods
    trans = translator.SharingTranslator(rv)

    rsInternal = { }

    items = [item]
    version = str(item.itsVersion)

    if pim.has_stamp(item, pim.EventStamp):
        for mod in pim.EventStamp(item).modifications or []:
            # modifications that have been changed purely by
            # auto-triage shouldn't have recordsets created for them
            if not (isinstance(mod, pim.Note) and
                    pim.EventStamp(mod).isTriageOnlyModification() and
                    pim.EventStamp(mod).simpleAutoTriage() == mod._triageStatus):   
                items.append(mod)

    for item in items:
        alias = trans.getAliasForItem(item)
        rsInternal[alias] = filter(eim.RecordSet(trans.exportItem(item)))

        if not pim.has_stamp(item, shares.SharedItem):
            shares.SharedItem(item).add()

        shared = shares.SharedItem(item)

        # Abort if pending conflicts
        if shared.conflictingStates:
            raise errors.ConflictsPending(_(u"Conflicts pending."))

        for peer in peers:
            state = shared.getPeerState(peer)
            # Set agreed state to what we have locally
            state.agreed = rsInternal[alias]

        # Repository identifier:
        if rv.repository is not None:
            repoId = rv.repository.getSchemaInfo()[0].str16()
        else:
            repoId = ""


    text = serializer.serialize(rv, rsInternal, rootName="item", repo=repoId,
                                version=version)

    return text


def outboundDeletion(rv, peers, uuid, debug=False):

    # At some point, which serializer and translator to use should be
    # configurable
    serializer = eimml.EIMMLSerializer # only using class methods

    return serializer.serialize(rv, { uuid : None }, "item")
