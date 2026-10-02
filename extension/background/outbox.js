/* Durable event queue. Records stay after FAILED so they can be sent later. */
(function (root, factory) {
    var api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    root.JobAIOutbox = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    var RETRY_DELAYS_MS = [1000, 2000, 5000, 10000, 30000, 60000];
    var MAX_RETRY = RETRY_DELAYS_MS.length;

    function errorInfo(error) {
        var status = error && error.status;
        if (status === 400 || status === 422) {
            return { name: 'HTTP_' + status, permanent: true };
        }
        if (status) {
            return { name: 'HTTP_' + status, permanent: false };
        }
        if (error && (error.name === 'AbortError' || error.message === 'TIMEOUT')) {
            return { name: 'TIMEOUT', permanent: false };
        }
        return { name: 'NETWORK', permanent: false };
    }

    function memoryStorage(seed) {
        var rows = new Map(seed || []);
        return {
            put: function (row) {
                rows.set(row.id, Object.assign({}, row));
                return Promise.resolve();
            },
            get: function (id) {
                var row = rows.get(id);
                return Promise.resolve(row ? Object.assign({}, row) : null);
            },
            all: function () {
                return Promise.resolve(Array.from(rows.values()).map(function (row) {
                    return Object.assign({}, row);
                }));
            }
        };
    }

    function openIndexedDbStorage() {
        var dbPromise = new Promise(function (resolve, reject) {
            var request = indexedDB.open('job-ai-outbox', 1);
            request.onupgradeneeded = function () {
                var db = request.result;
                if (!db.objectStoreNames.contains('events')) {
                    db.createObjectStore('events', { keyPath: 'id' });
                }
            };
            request.onsuccess = function () {
                resolve(request.result);
            };
            request.onerror = function () {
                reject(request.error);
            };
        });

        function withStore(mode, fn) {
            return dbPromise.then(function (db) {
                return new Promise(function (resolve, reject) {
                    var tx = db.transaction('events', mode);
                    var store = tx.objectStore('events');
                    var request = fn(store);
                    request.onsuccess = function () {
                        resolve(request.result);
                    };
                    request.onerror = function () {
                        reject(request.error);
                    };
                });
            });
        }

        return {
            put: function (row) {
                return withStore('readwrite', function (store) {
                    return store.put(row);
                });
            },
            get: function (id) {
                return withStore('readonly', function (store) {
                    return store.get(id);
                });
            },
            all: function () {
                return withStore('readonly', function (store) {
                    return store.getAll();
                });
            }
        };
    }

    function createOutbox(options) {
        var storage = options.storage;
        var send = options.send;
        var now = options.now || function () {
            return Date.now();
        };
        var delays = options.delays || RETRY_DELAYS_MS;
        var maxRetry = options.maxRetry || delays.length;

        function enqueue(event) {
            var record = {
                id: event.id,
                event_type: event.event_type,
                payload: event.payload,
                created_at: event.created_at,
                status: 'PENDING',
                retry_count: 0,
                last_error: null,
                next_retry_at: null
            };
            return storage.put(record).then(function () {
                return Object.assign({}, record);
            });
        }

        function flush() {
            var clock = now();
            return storage.all().then(function (rows) {
                var due = rows.filter(function (row) {
                    return row.status === 'PENDING' && (row.next_retry_at === null || row.next_retry_at <= clock);
                });
                return due.reduce(function (chain, row) {
                    return chain.then(function (results) {
                        return deliver(row, clock).then(function (result) {
                            results.push(result);
                            return results;
                        });
                    });
                }, Promise.resolve([]));
            });
        }

        function deliver(row, clock) {
            row.status = 'SENDING';
            return storage.put(row).then(function () {
                return send(row);
            }).then(function (response) {
                row.status = 'SENT';
                row.last_error = null;
                row.next_retry_at = null;
                return storage.put(row).then(function () {
                    var data = response && response.data ? response.data : {};
                    return {
                        id: row.id,
                        status: row.status,
                        fingerprint: data.fingerprint || null,
                        sessionId: data.session_id || null
                    };
                });
            }).catch(function (error) {
                var info = errorInfo(error);
                row.retry_count += 1;
                row.last_error = info.name;
                if (info.permanent || row.retry_count >= maxRetry) {
                    row.status = 'FAILED';
                    row.next_retry_at = null;
                } else {
                    row.status = 'PENDING';
                    row.next_retry_at = clock + delays[Math.min(row.retry_count - 1, delays.length - 1)];
                }
                return storage.put(row).then(function () {
                    return {
                        id: row.id,
                        status: row.status,
                        fingerprint: null,
                        error: row.last_error,
                        nextRetryAt: row.next_retry_at
                    };
                });
            });
        }

        function requeueFailed() {
            return storage.all().then(function (rows) {
                var failed = rows.filter(function (row) {
                    return row.status === 'FAILED';
                });
                return failed.reduce(function (chain, row) {
                    row.status = 'PENDING';
                    row.retry_count = 0;
                    row.next_retry_at = null;
                    return chain.then(function () {
                        return storage.put(row);
                    });
                }, Promise.resolve());
            });
        }

        return {
            enqueue: enqueue,
            flush: flush,
            requeueFailed: requeueFailed
        };
    }

    return {
        RETRY_DELAYS_MS: RETRY_DELAYS_MS,
        MAX_RETRY: MAX_RETRY,
        errorInfo: errorInfo,
        memoryStorage: memoryStorage,
        openIndexedDbStorage: openIndexedDbStorage,
        createOutbox: createOutbox
    };
});
