const test = require('node:test');
const assert = require('node:assert/strict');

require('../../extension/content-script/sites/common.js');
require('../../extension/content-script/sites/boss.js');
require('../../extension/content-script/sites/lagou.js');
require('../../extension/content-script/sites/51job.js');
require('../../extension/content-script/sites/zhaopin.js');
const page = require('../../extension/content-script/page-detector.js');

const BODY = '岗位职责\n负责后端系统开发与维护，并完成接口设计。\n任职要求\n熟悉 Python\n';

function locationFrom(href) {
    const url = new URL(href);
    return { href: href, hostname: url.hostname, pathname: url.pathname };
}

function documentWith(fields) {
    return {
        querySelector(selector) {
            const text = fields[selector];
            return text ? { textContent: text } : null;
        }
    };
}

function bossDoc(body) {
    const fields = {
        '.job-banner .name': 'Python 工程师',
        '.company-info .name': '示例公司',
        '.job-banner .salary': '25-35K',
        '.job-banner .location-address': '上海'
    };
    if (body) {
        fields['.job-sec-text'] = body;
    }
    return documentWith(fields);
}

const adapters = globalThis.JobAISites.all();

test('debounce stays inside the requested range', () => {
    assert.ok(page.DEBOUNCE_MS >= 500 && page.DEBOUNCE_MS <= 1000);
    assert.deepEqual(page.CONTENT_RETRY_MS, [1000, 2000, 4000]);
});

test('detail, list, home, and search pages', () => {
    const watcher = page.createWatcher(adapters);
    const detail = watcher.inspect(
        locationFrom('https://www.zhipin.com/job_detail/abc123.html'),
        bossDoc(BODY)
    );
    assert.equal(detail.state, 'EMITTED');
    assert.equal(detail.event.event_type, 'job.discovered');

    const list = watcher.inspect(
        locationFrom('https://www.zhipin.com/web/geek/job?query=python'),
        bossDoc(BODY)
    );
    assert.equal(list.state, 'LIST_PAGE');
    assert.equal(list.event, undefined);

    const home = watcher.inspect(locationFrom('https://www.zhipin.com/'), bossDoc(BODY));
    assert.equal(home.state, 'LIST_PAGE');
    const search = watcher.inspect(
        locationFrom('https://www.zhipin.com/web/geek/job?query=java'),
        bossDoc(BODY)
    );
    assert.equal(search.state, 'LIST_PAGE');
});

test('spa navigation emits the next job', () => {
    const watcher = page.createWatcher(adapters);
    const first = watcher.inspect(
        locationFrom('https://www.zhipin.com/job_detail/job-a.html'),
        bossDoc(BODY)
    );
    const secondDoc = bossDoc(BODY);
    secondDoc.querySelector = function (selector) {
        if (selector === '.job-banner .name') {
            return { textContent: '数据工程师' };
        }
        return bossDoc(BODY).querySelector(selector);
    };
    const second = watcher.inspect(
        locationFrom('https://www.zhipin.com/job_detail/job-b.html'),
        secondDoc
    );
    assert.equal(first.event.raw_job.title, 'Python 工程师');
    assert.equal(second.event.raw_job.title, '数据工程师');
    assert.notEqual(first.event.url, second.event.url);
});

test('async body is retried and then extracted once', () => {
    const watcher = page.createWatcher(adapters);
    const url = locationFrom('https://www.zhipin.com/job_detail/abc123.html?from=list');
    const waiting = watcher.inspect(url, bossDoc(''));
    assert.equal(waiting.state, 'WAITING_CONTENT');
    assert.equal(waiting.retryIn, 1000);
    const ready = watcher.inspect(url, bossDoc(BODY));
    assert.equal(ready.state, 'EMITTED');
    const again = watcher.inspect(url, bossDoc(BODY));
    assert.equal(again.duplicate, true);
    assert.equal(again.event, undefined);
});

test('incomplete body eventually emits a failure without repeating it', () => {
    const watcher = page.createWatcher(adapters);
    const url = locationFrom('https://www.zhipin.com/job_detail/abc123.html');
    const states = [];
    for (let i = 0; i < 5; i += 1) {
        states.push(watcher.inspect(url, bossDoc('')));
    }
    assert.equal(states[0].state, 'WAITING_CONTENT');
    assert.equal(states[1].retryIn, 2000);
    assert.equal(states[2].retryIn, 4000);
    assert.equal(states[3].state, 'EXTRACTION_FAILED');
    assert.equal(states[3].event.event_type, 'job.extraction_failed');
    assert.equal(states[4].event, undefined);
});

test('history hooks report pushState, replaceState, and popstate', () => {
    const seen = [];
    const win = {
        history: {
            pushState() {
                return 'pushed';
            },
            replaceState() {
                return 'replaced';
            }
        },
        addEventListener(name, fn) {
            win.listeners[name] = fn;
        },
        listeners: {}
    };
    page.installHistoryHooks(win, (name) => seen.push(name));
    assert.equal(win.history.pushState(), 'pushed');
    win.history.replaceState();
    win.listeners.popstate();
    assert.deepEqual(seen, ['pushState', 'replaceState', 'popstate']);
});

test('debouncer waits and collapses repeated calls', () => {
    const calls = [];
    let pending = null;
    const schedule = page.createDebouncer(800, () => calls.push('run'), {
        set(callback, delay) {
            pending = { callback: callback, delay: delay };
            return pending;
        },
        clear() {
            pending = null;
        }
    });
    schedule();
    schedule();
    assert.equal(pending.delay, 800);
    pending.callback();
    assert.deepEqual(calls, ['run']);
});
