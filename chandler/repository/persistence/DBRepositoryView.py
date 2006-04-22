
__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003-2004 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

from datetime import timedelta
from time import time

from chandlerdb.item.c import CItem
from chandlerdb.util.c import isuuid
from chandlerdb.persistence.c import DBLockDeadlockError

from repository.item.RefCollections import RefList, TransientRefList
from repository.persistence.RepositoryError \
     import RepositoryError, MergeError, VersionConflictError
from repository.persistence.RepositoryView \
     import RepositoryView, OnDemandRepositoryView
from repository.persistence.Repository import Repository
from repository.persistence.DBLob import DBLob
from repository.persistence.DBRefs import DBRefList, DBChildren, DBNumericIndex
from repository.persistence.DBContainer import HashTuple
from repository.persistence.DBItemIO \
     import DBItemWriter, DBItemVMergeReader, DBItemRMergeReader


class DBRepositoryView(OnDemandRepositoryView):

    def openView(self):

        self._log = set()
        self._indexWriter = None

        super(DBRepositoryView, self).openView()

    def _logItem(self, item):

        if super(DBRepositoryView, self)._logItem(item):
            self._log.add(item)
            return True
        
        return False

    def dirtyItems(self):

        return iter(self._log)

    def hasDirtyItems(self):

        return len(self._log) > 0

    def dirlog(self):

        for item in self._log:
            print item.itsPath

    def cancel(self):

        refCounted = self.isRefCounted()

        for item in self._log:
            item.setDirty(0)
            item._unloadItem(not item.isNew(), self, False)

        self._instanceRegistry.update(self._deletedRegistry)
        self._log.update(self._deletedRegistry.itervalues())
        self._deletedRegistry.clear()

        for item in self._log:
            if not item.isNew():
                self.logger.debug('reloading version %d of %s',
                                  self._version, item)
                self.find(item._uuid)

        self._log.clear()

        if self.isDirty():
            self._roots._clearDirties()
            self.setDirty(0)

        self.prune(10000)

    def queryItems(self, kind=None, attribute=None):

        store = self.store
        
        for itemReader in store.queryItems(self, self._version,
                                           kind and kind.itsUUID,
                                           attribute and attribute.itsUUID):
            uuid = itemReader.getUUID()
            if uuid not in self._deletedRegistry:
                # load and itemReader, trick to pass reader directly to find
                item = self.find(uuid, itemReader)
                if item is not None:
                    yield item

    def queryItemKeys(self, kind=None, attribute=None):

        store = self.store
        
        for uuid in store.queryItemKeys(self, self._version,
                                        kind and kind.itsUUID,
                                        attribute and attribute.itsUUID):
            if uuid not in self._deletedRegistry:
                yield uuid

    def kindForKey(self, uuid):

        if uuid in self._registry:
            return self[uuid].itsKind

        uuid = self.store.kindForKey(self, self._version, uuid)
        if uuid is not None:
            return self[uuid]

        return None

    def searchItems(self, query, attribute=None, load=True):

        store = self.store
        results = []
        docs = store.searchItems(self, self._version, query,
                                 attribute and attribute.itsUUID)
        for uuid, (ver, attribute) in docs.iteritems():
            if not uuid in self._deletedRegistry:
                item = self.find(uuid, load)
                if item is not None:
                    results.append((item, self[attribute]))

        return results

    def _createRefList(self, item, name, otherName,
                       persisted, readOnly, new, uuid):

        if persisted:
            return DBRefList(self, item, name, otherName, readOnly, new, uuid)
        else:
            return TransientRefList(item, name, otherName, readOnly)

    def _createChildren(self, parent, new):

        return DBChildren(self, parent, new)

    def _createNumericIndex(self, **kwds):

        return DBNumericIndex(self, **kwds)
    
    def _registerItem(self, item):

        super(DBRepositoryView, self)._registerItem(item)
        if item.isDirty():
            self._log.add(item)

    def _unregisterItem(self, item, reloadable):

        super(DBRepositoryView, self)._unregisterItem(item, reloadable)
        if item.isDirty():
            self._log.remove(item)

    def _getLobType(self):

        return DBLob

    def _startTransaction(self, nested=False):

        return self.store.startTransaction(self, nested)

    def _commitTransaction(self, status):

        if self._indexWriter is not None:
            self.store._index.optimizeIndex(self._indexWriter)
            self._indexWriter.close()
            self._indexWriter = None
            
        self.store.commitTransaction(self, status)

    def _abortTransaction(self, status):

        if self._indexWriter is not None:
            try:
                self._indexWriter.close()
            except:
                self.logger.exception('Ignorable exception while closing indexWriter during _abortTransaction')
            self._indexWriter = None
            
        self.store.abortTransaction(self, status)

    def _getIndexWriter(self):

        if self._indexWriter is None:
            store = self.store
            if not store._ramdb and store.txn is None:
                raise RepositoryError, "Can't index outside transaction"
            self._indexWriter = store._index.getIndexWriter()

        return self._indexWriter

    def _dispatchHistory(self, history, refreshes, oldVersion, newVersion):

        refs = self.store._refs
        watcherDispatch = self._watcherDispatch

        def dirtyNames():
            if kind is None:
                names = ()
            else:
                names = kind._nameTuple(dirties)
            if status & CItem.KDIRTY:
                names += ('itsKind',)
            return names

        for uItem, version, uKind, status, uParent, pKind, dirties in history:

            if not (pKind is None or pKind == DBItemWriter.NOITEM):
                kind = self.find(pKind)
                if kind is not None:
                    kind.extent._collectionChanged('refresh', 'collection',
                                                   'extent', uItem)

            kind = self.find(uKind)
            names = None
            if kind is not None:
                kind.extent._collectionChanged('refresh', 'collection',
                                               'extent', uItem)
                
                dispatch = self.findValue(uItem, 'watcherDispatch', None)
                if dispatch:
                    isNew = (status & CItem.NEW) != 0
                    for attribute, watchers in dispatch.iteritems():
                        if watchers:
                            if attribute is None:  # item watchers
                                if names is None:
                                    names = dirtyNames()
                                for watcher, watch, methodName in watchers:
                                    watcher = self[watcher.itsUUID]
                                    getattr(watcher, methodName)('refresh', uItem, names)
                            elif isNew or attribute in dirties:
                                value = self.findValue(uItem, attribute, None)
                                if not isuuid(value):
                                    if isinstance(value, RefList):
                                        value = value.uuid
                                    else:
                                        continue
                                for uRef in refs.iterHistory(self, value, version - 1, version, True):
                                    if uRef in refreshes:
                                        self.invokeWatchers(watchers, 'refresh', 'collection', uItem, attribute, uRef)

                for name in kind._iterNotifyAttributes():
                    value = self.findValue(uItem, name, None)
                    if isuuid(value):
                        if kind.getAttribute(name).c.cardinality != 'list':
                            continue
                        refsIterator = refs.iterKeys(self, value, version)
                    elif isinstance(value, RefList):
                        refsIterator = value.iterkeys()
                    else:
                        continue
                    otherName = kind.getOtherName(name, None)
                    for uRef in refsIterator:
                        dispatch = self.findValue(uRef, 'watcherDispatch', None)
                        if dispatch:
                            watchers = dispatch.get(otherName, None)
                            if watchers:
                                self.invokeWatchers(watchers, 'changed', 'notification', uRef, otherName, uItem)

            if watcherDispatch and uItem in watcherDispatch:
                watchers = watcherDispatch[uItem].get(None)
                if watchers:
                    if names is None:
                        names = dirtyNames()
                    for watcher, watch, methodName in list(watchers):
                        watcher = self.find(watcher)
                        if watcher is not None:
                            getattr(watcher, methodName)('refresh', uItem, names)

    def _dispatchChanges(self, changes):

        for item, version, status, literals, references in changes:

            kind = item.itsKind
            uItem = item.itsUUID
            if kind is not None:
                kind.extent._collectionChanged('changed', 'notification',
                                               'extent', uItem)

                for name in kind._iterNotifyAttributes():
                    value = getattr(item, name, None)
                    if value is not None and isinstance(value, RefList):
                        otherName = value._otherName
                        for uRef in value.iterkeys():
                            dispatch = self.findValue(uRef, 'watcherDispatch', None)
                            if dispatch:
                                watchers = dispatch.get(otherName, None)
                                if watchers:
                                    self.invokeWatchers(watchers, 'changed', 'notification', uRef, otherName, uItem)
    
    def refresh(self, mergeFn=None, version=None, notify=True):

        store = self.store
        if not version:
            newVersion = store.getVersion()
        else:
            newVersion = min(long(version), store.getVersion())
        
        refCounted = self.isRefCounted()

        def _refresh(items):
            for item in items():
                item._unloadItem(refCounted or item.isPinned(), self, False)
            for item in items():
                if refCounted or item.isPinned():
                    if item.isSchema():
                        self.find(item.itsUUID)
            for item in items():
                if refCounted or item.isPinned():
                    self.find(item.itsUUID)

        if newVersion > self._version:
            history = []
            refreshes = set()
            unloads = {}
            also = set()
            _log = self._log

            try:
                self._log = set()
                try:
                    merges = self._mergeItems(self._version, newVersion,
                                              history, refreshes, unloads, also,
                                              mergeFn)
                except:
                    raise
                else:
                    # unload items unchanged until changed by merging
                    for item in self._log:
                        item.setDirty(0)
                        unloads[item.itsUUID] = item
            finally:
                self._log = _log

            # unload items changed only in the other view whose older version
            # got loaded as a side-effect of merging
            for uuid in also:
                item = self.find(uuid, False)
                if item is not None:
                    unloads[uuid] = item
                    
            oldVersion = self._version
            self._version = newVersion
            _refresh(unloads.itervalues)

            for uuid in merges.iterkeys():
                item = self.find(uuid)
                if item is not None:
                    item._afterMerge()

            #if merges:
            #    print 'CHECK', self.check()

            if notify:
                before = time()
                self._dispatchHistory(history, refreshes,
                                      oldVersion, newVersion)
                count = self.dispatchNotifications()
                duration = time() - before
                if duration > 1.0:
                    self.logger.warning('%s %d notifications ran in %s',
                                        self, len(history) + count,
                                        timedelta(seconds=duration))
            else:
                self.flushNotifications()

            self.prune(10000)

        elif newVersion == self._version:
            if notify:
                self.dispatchNotifications()
            else:
                self.flushNotifications()

        elif newVersion < self._version:
            self.cancel()
            refCounted = self.isRefCounted()
            unloads = [item for item in self._registry.itervalues()
                       if item._version > newVersion]
            self._version = newVersion
            _refresh(unloads.__iter__)
            self.flushNotifications()

    def commit(self, mergeFn=None, notify=True):

        if not (self._status & RepositoryView.COMMITTING or
                len(self._log) + len(self._deletedRegistry) == 0):
            try:
                release = self._acquireExclusive()
                self._status |= RepositoryView.COMMITTING
                
                store = self.store
                before = time()

                size = 0L
                txnStatus = 0
                newVersion = self._version

                def finish(txnStatus, commit):
                    if txnStatus:
                        if commit:
                            self._commitTransaction(txnStatus)
                        else:
                            self._abortTransaction(txnStatus)
                    return 0
        
                while True:
                    try:
                        self.refresh(mergeFn, None, notify)

                        count = len(self._log) + len(self._deletedRegistry)
                        if count > 500:
                            self.logger.info('%s committing %d items...',
                                             self, count)

                        if count > 0:
                            txnStatus = self._startTransaction(True)
                            if txnStatus == 0:
                                raise AssertionError, 'no transaction started'

                            newVersion = store.nextVersion()

                            itemWriter = DBItemWriter(store)
                            for item in self._log:
                                size += self._saveItem(item, newVersion,
                                                       itemWriter)
                            for item in self._deletedRegistry.itervalues():
                                size += self._saveItem(item, newVersion,
                                                       itemWriter)
                            if self.isDirty():
                                size += self._roots._saveValues(newVersion)

                        txnStatus = finish(txnStatus, True)
                        break

                    except DBLockDeadlockError:
                        self.logger.info('retrying commit aborted by deadlock')
                        txnStatus = finish(txnStatus, False)
                        continue

                    except:
                        if txnStatus:
                            self.logger.exception('aborting transaction (%d kb)', size >> 10)
                        txnStatus = finish(txnStatus, False)
                        raise

                self._version = newVersion
                
                if self._log:
                    for item in self._log:
                        item._version = newVersion
                        item.setDirty(0, None)
                        item._status &= ~(CItem.NEW | CItem.MERGED)
                    self._log.clear()

                    if self.isDirty():
                        self._roots._clearDirties()
                        self.setDirty(0)

                if self._deletedRegistry:
                    self._deletedRegistry.clear()

                after = time()

                if count > 0:
                    duration = after - before
                    try:
                        iSpeed = "%d items/s" % round(count / duration)
                        dSpeed = "%d kbytes/s" % round((size >> 10) / duration)
                    except ZeroDivisionError:
                        iSpeed = dSpeed = 'speed could not be measured'

                    self.logger.info('%s committed %d items (%d kbytes) in %s, %s (%s), version: %d', self, count, size >> 10, timedelta(seconds=duration), iSpeed, dSpeed, newVersion)

            finally:
                self._status &= ~RepositoryView.COMMITTING
                if release:
                    self._releaseExclusive()

    def _saveItem(self, item, newVersion, itemWriter):

        if self.isDebug():
            self.logger.debug('saving version %d of %s',
                              newVersion, item.itsPath)

        if item.isDeleted() and item.isNew():
            return 0
                    
        return itemWriter.writeItem(item, newVersion)

    def mapChanges(self, freshOnly=False):

        if freshOnly:
            if self._status & RepositoryView.FDIRTY:
                self._status &= ~RepositoryView.FDIRTY
            else:
                return

        for item in list(self._log):   # self._log may change while looping
            status = item._status
            if not freshOnly or freshOnly and status & CItem.FDIRTY:
                if freshOnly:
                    status &= ~CItem.FDIRTY
                    item._status = status

                if item.isDeleted():
                    yield (item, item._version, status, [], [])
                elif item.isNew():
                    yield (item, item._version, status,
                           item._values.keys(),
                           item._references.keys())
                else:
                    yield (item, item._version, status,
                           item._values._getDirties(), 
                           item._references._getDirties())
    
    def mapHistory(self, fromVersion=0, toVersion=0, history=None):

        if history is None:
            store = self.store
            if fromVersion == 0:
                fromVersion = self._version
            if toVersion == 0:
                toVersion = store.getVersion()
            history = store._items.iterHistory(self, fromVersion, toVersion)

        for uItem, version, uKind, status, uParent, pKind, dirties in history:
            kind = self.find(uKind)
            if not (pKind is None or pKind == DBItemWriter.NOITEM):
                prevKind = self.find(pKind)
            else:
                prevKind = None
            values = []
            references = []
            if kind is not None:
                for name, attr, k in kind.iterAttributes():
                    if name in dirties:
                        if kind.getOtherName(name, None, None) is not None:
                            references.append(name)
                        else:
                            values.append(name)
            yield uItem, version, kind, status, values, references, prevKind

    def _mergeItems(self, oldVersion, toVersion, history, refreshes,
                    unloads, also, mergeFn):

        merges = {}

        for args in self.store._items.iterHistory(self, oldVersion, toVersion):
            uItem, version, uKind, status, uParent, prevKind, dirties = args

            history.append(args)
            refreshes.add(uItem)

            item = self.find(uItem, False)
            if item is not None:
                if item.isDirty():
                    oldDirty = status & CItem.DIRTY
                    if uItem in merges:
                        od, x, d = merges[uItem]
                        merges[uItem] = (od | oldDirty, uParent,
                                         d.union(dirties))
                    else:
                        merges[uItem] = (oldDirty, uParent, set(dirties))

                elif item.itsVersion < version:
                    unloads[uItem] = item

            elif uItem in self._deletedRegistry:
                kind = self.find(uKind, False)
                if kind is None:
                    self._e_1_delete(uItem, uKind, oldVersion, version)
                else:
                    self._e_1_delete(uItem, kind, oldVersion, version)

            else:
                also.add(uItem)
                    
        try:
            for uItem, (oldDirty, uParent, dirties) in merges.iteritems():
            
                item = self.find(uItem, False)
                newDirty = item.getDirty()

                if oldDirty & CItem.KDIRTY:
                    raise NotImplementedError, 'merge with refresh kind change'

                if newDirty & CItem.KDIRTY:
                    if newDirty & CItem.VDIRTY:
                        oldDirty |= CItem.VDIRTY
                    if newDirty & CItem.RDIRTY:
                        oldDirty |= CItem.RDIRTY

                if newDirty & oldDirty & CItem.NDIRTY:
                    item._status |= CItem.NMERGED
                    self._mergeNDIRTY(item, uParent, oldVersion, toVersion)
                    oldDirty &= ~CItem.NDIRTY

                if newDirty & oldDirty & CItem.CDIRTY:
                    item._status |= CItem.CMERGED
                    item._children._mergeChanges(oldVersion, toVersion)
                    oldDirty &= ~CItem.CDIRTY

                if newDirty & oldDirty & CItem.RDIRTY:
                    item._status |= CItem.RMERGED
                    self._mergeRDIRTY(item, dirties, oldVersion, toVersion)
                    oldDirty &= ~CItem.RDIRTY

                if newDirty & oldDirty & CItem.VDIRTY:
                    item._status |= CItem.VMERGED
                    self._mergeVDIRTY(item, toVersion, dirties, mergeFn)
                    oldDirty &= ~CItem.VDIRTY

                if newDirty & oldDirty == 0:
                    if oldDirty & CItem.VDIRTY:
                        item._status |= CItem.VMERGED
                        self._mergeVDIRTY(item, toVersion, dirties, mergeFn)
                        oldDirty &= ~CItem.VDIRTY
                    if oldDirty & CItem.RDIRTY:
                        item._status |= CItem.RMERGED
                        self._mergeRDIRTY(item, dirties, oldVersion, toVersion)
                        oldDirty &= ~CItem.RDIRTY

                if newDirty and oldDirty:
                    raise VersionConflictError, (item, newDirty, oldDirty)

        except VersionConflictError:
            for uuid in merges.iterkeys():
                item = self.find(uuid, False)
                if item._status & CItem.MERGED:
                    item._revertMerge()
            raise

        else:
            for uuid in merges.iterkeys():
                item = self.find(uuid, False)
                if item._status & CItem.MERGED:
                    item._commitMerge(toVersion)
                    self._i_merged(item)

            return merges

    def _mergeNDIRTY(self, item, parentId, oldVersion, toVersion):

        newParentId = item.itsParent.itsUUID
        if parentId != newParentId:
            p = self.store._items.getItemParentId(self, oldVersion,
                                                  item.itsUUID)
            if p != parentId and p != newParentId:
                self._e_1_rename(item, p, newParentId)
    
        refs = self.store._refs
        p, n, name = refs.loadRef(self, parentId, toVersion, item.itsUUID)

        if name != item._name:
            self._e_2_rename(item, name)

    def _mergeRDIRTY(self, item, dirties, oldVersion, toVersion):

        dirties = HashTuple(dirties)
        store = self.store
        args = store._items.loadItem(self, toVersion, item.itsUUID)
        DBItemRMergeReader(store, item, dirties,
                           oldVersion, *args).readItem(self, [])

    def _mergeVDIRTY(self, item, toVersion, dirties, mergeFn):

        dirties = HashTuple(dirties)
        store = self.store
        args = store._items.loadItem(self, toVersion, item.itsUUID)
        DBItemVMergeReader(store, item, dirties,
                           mergeFn, *args).readItem(self, [])

    def _i_merged(self, item):

        self.logger.info('%s merged %s with newer versions, merge status: 0x%0.8x', self, item.itsPath, (item._status & CItem.MERGED))

    def _e_1_rename(self, item, parentId, newParentId):

        raise MergeError, ('rename', item, 'item %s moved to %s and %s' %(item.itsUUID, parentId, newParentId), MergeError.MOVE)

    def _e_2_rename(self, item, name):

        raise MergeError, ('rename', item, 'item %s renamed to %s and %s' %(item.itsUUID, item.itsName, name), MergeError.RENAME)

    def _e_1_delete(self, uItem, uKind, oldVersion, newVersion):

        raise MergeError, ('delete', uItem, 'item %s was deleted in this version (%d) but has later changes in version (%d) where it is of kind %s' %(uItem, oldVersion, newVersion, uKind), MergeError.CHANGE)
