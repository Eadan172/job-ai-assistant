/* Page state for detail detection. DOM observation stays in auto-capture.js. */
(function (root, factory) {
    var api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    root.JobAIPage = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    var DEBOUNCE_MS = 800;
    var CONTENT_RETRY_MS = [1000, 2000, 4000];

    function createWatcher(adapters) {
        var state = 'UNKNOWN';
        var attempts = 0;
        var lastPageKey = '';
        var failedUrl = '';
        var seenUrl = '';

        function inspect(location, document) {
            var href = (location && location.href) || '';
            if (href !== seenUrl) {
                seenUrl = href;
                attempts = 0;
                failedUrl = '';
            }
            var adapter = (adapters || []).filter(function (item) {
                return item.canHandle(location, document);
            })[0];
            if (!adapter) {
                state = 'UNKNOWN';
                return { state: state };
            }
            if (!adapter.isDetailUrl(location)) {
                state = 'LIST_PAGE';
                attempts = 0;
                return { state: state };
            }
            if (!adapter.isJobDetailPage(location, document)) {
                attempts += 1;
                if (attempts > CONTENT_RETRY_MS.length) {
                    state = 'EXTRACTION_FAILED';
                    if (failedUrl === href) {
                        return { state: state };
                    }
                    failedUrl = href;
                    return {
                        state: state,
                        event: {
                            event_type: 'job.extraction_failed',
                            source: adapter.id,
                            url: href,
                            raw_job: adapter.extractJob(document)
                        }
                    };
                }
                state = 'WAITING_CONTENT';
                return { state: state, retryIn: CONTENT_RETRY_MS[attempts - 1] };
            }
            var raw = adapter.extractJob(document);
            attempts = 0;
            failedUrl = '';
            var pageKey = [
                href.split('?')[0],
                raw.title,
                raw.company,
                raw.salary || '',
                raw.location || '',
                raw.full_text
            ].join('\n');
            if (pageKey === lastPageKey) {
                state = 'EMITTED';
                return { state: state, duplicate: true };
            }
            lastPageKey = pageKey;
            state = 'EMITTED';
            return {
                state: state,
                detected: true,
                event: {
                    event_type: 'job.discovered',
                    source: adapter.id,
                    url: href,
                    raw_job: raw
                }
            };
        }

        function resetForNavigation() {
            attempts = 0;
            failedUrl = '';
            seenUrl = '';
            lastPageKey = '';
            state = 'UNKNOWN';
        }

        return {
            inspect: inspect,
            resetForNavigation: resetForNavigation,
            getState: function () {
                return state;
            }
        };
    }

    function installHistoryHooks(win, onChange) {
        var history = win.history;
        ['pushState', 'replaceState'].forEach(function (name) {
            var original = history[name];
            if (typeof original !== 'function' || original.__jobAiWrapped) {
                return;
            }
            var wrapped = function () {
                var result = original.apply(history, arguments);
                onChange(name);
                return result;
            };
            wrapped.__jobAiWrapped = true;
            history[name] = wrapped;
        });
        if (typeof win.addEventListener === 'function') {
            win.addEventListener('popstate', function () {
                onChange('popstate');
            });
        }
    }

    function createDebouncer(wait, fn, timers) {
        var setTimer = timers && timers.set ? timers.set : function (callback, delay) {
            return setTimeout(callback, delay);
        };
        var clearTimer = timers && timers.clear ? timers.clear : function (id) {
            clearTimeout(id);
        };
        var timer = null;
        return function debounced() {
            if (timer !== null) {
                clearTimer(timer);
            }
            timer = setTimer(function () {
                timer = null;
                fn();
            }, wait);
        };
    }

    return {
        DEBOUNCE_MS: DEBOUNCE_MS,
        CONTENT_RETRY_MS: CONTENT_RETRY_MS,
        createWatcher: createWatcher,
        installHistoryHooks: installHistoryHooks,
        createDebouncer: createDebouncer
    };
});
