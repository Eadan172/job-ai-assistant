/* Automatic detail capture. Manual scraping in content.js is unchanged. */
(function () {
    if (window.__JOB_AI_AUTO__) {
        return;
    }
    window.__JOB_AI_AUTO__ = true;

    var watcher = window.JobAIPage.createWatcher(window.JobAISites.all());
    var retryTimer = null;

    function log(name, extra) {
        console.log('[JobAI] ' + name, extra || '');
    }

    function emit(result) {
        if (!result || !result.event) {
            return;
        }
        var event = result.event;
        var raw = event.raw_job || {};
        if (result.detected) {
            log('DETAIL_PAGE_DETECTED', event.source);
            log('JD_EXTRACTED', {
                source: event.source,
                titleLength: raw.title ? raw.title.length : 0,
                textLength: raw.full_text ? raw.full_text.length : 0
            });
        }
        var id = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
        log('EVENT_QUEUED', event.event_type);
        chrome.runtime.sendMessage({
            action: 'enqueueJobEvent',
            event: {
                id: id,
                event_type: event.event_type,
                created_at: new Date().toISOString(),
                payload: {
                    event_id: id,
                    event_type: event.event_type,
                    source: event.source,
                    url: event.url,
                    captured_at: new Date().toISOString(),
                    raw_job: raw
                }
            }
        });
    }

    function scan() {
        var result = watcher.inspect(window.location, document);
        if (retryTimer) {
            clearTimeout(retryTimer);
            retryTimer = null;
        }
        if (result.retryIn) {
            retryTimer = setTimeout(scan, result.retryIn);
        }
        emit(result);
    }

    var schedule = window.JobAIPage.createDebouncer(window.JobAIPage.DEBOUNCE_MS, scan);

    function start() {
        schedule();
        window.JobAIPage.installHistoryHooks(window, function () {
            watcher.resetForNavigation();
            schedule();
        });
        if (typeof MutationObserver === 'function' && document.documentElement) {
            var observer = new MutationObserver(function () {
                schedule();
            });
            observer.observe(document.documentElement, {
                subtree: true,
                childList: true,
                characterData: true
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
