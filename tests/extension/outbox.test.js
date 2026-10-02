const test = require('node:test');
const assert = require('node:assert/strict');

const outboxModule = require('../../extension/background/outbox.js');

function event(id) {
    return {
        id: id,
        event_type: 'job.discovered',
        created_at: '2026-10-02T10:00:00Z',
        payload: { event_id: id, event_type: 'job.discovered' }
    };
}

function harness(send, options) {
    const storage = outboxModule.memoryStorage();
    let clock = 1_000;
    const outbox = outboxModule.createOutbox(Object.assign({
        storage: storage,
        send: send,
        now: () => clock,
        delays: [10, 20, 40],
        maxRetry: 3
    }, options));
    return {
        storage: storage,
        outbox: outbox,
        at(value) {
            clock = value;
        }
    };
}

test('retry delays are bounded', () => {
    assert.deepEqual(outboxModule.RETRY_DELAYS_MS, [1000, 2000, 5000, 10000, 30000, 60000]);
    assert.equal(outboxModule.MAX_RETRY, 6);
});

test('successful post is marked sent and kept', async () => {
    const box = harness(async () => ({ data: { fingerprint: 'abc' } }));
    await box.outbox.enqueue(event('ok'));
    const results = await box.outbox.flush();
    assert.equal(results[0].status, 'SENT');
    assert.equal(results[0].fingerprint, 'abc');
    assert.equal((await box.storage.get('ok')).status, 'SENT');
});

test('network failure, timeout, and http 500 retry until success', async () => {
    let calls = 0;
    const box = harness(async () => {
        calls += 1;
        if (calls === 1) {
            throw new Error('offline');
        }
        if (calls === 2) {
            const timeout = new Error('TIMEOUT');
            timeout.name = 'AbortError';
            throw timeout;
        }
        if (calls === 3) {
            const error = new Error('HTTP_500');
            error.status = 500;
            throw error;
        }
        return { data: { fingerprint: 'fff' } };
    }, { maxRetry: 4 });
    await box.outbox.enqueue(event('retry'));
    let result = (await box.outbox.flush())[0];
    assert.equal(result.status, 'PENDING');
    assert.equal(result.error, 'NETWORK');
    assert.deepEqual(await box.outbox.flush(), []);
    box.at(result.nextRetryAt);
    result = (await box.outbox.flush())[0];
    assert.equal(result.error, 'TIMEOUT');
    box.at(result.nextRetryAt);
    result = (await box.outbox.flush())[0];
    assert.equal(result.error, 'HTTP_500');
    box.at(result.nextRetryAt);
    result = (await box.outbox.flush())[0];
    assert.equal(result.status, 'SENT');
    assert.equal((await box.storage.all()).length, 1);
});

test('exhausted retries stay stored as failed and can be requeued', async () => {
    const box = harness(async () => {
        const error = new Error('HTTP_500');
        error.status = 500;
        throw error;
    });
    await box.outbox.enqueue(event('give-up'));
    let failed = (await box.outbox.flush())[0];
    box.at(failed.nextRetryAt);
    failed = (await box.outbox.flush())[0];
    box.at(failed.nextRetryAt);
    failed = (await box.outbox.flush())[0];
    assert.equal(failed.status, 'FAILED');
    assert.equal((await box.storage.get('give-up')).status, 'FAILED');
    let sent = false;
    const recovered = harness(async () => {
        sent = true;
        return { data: { fingerprint: 'again' } };
    });
    await recovered.storage.put(await box.storage.get('give-up'));
    await recovered.outbox.requeueFailed();
    const result = (await recovered.outbox.flush())[0];
    assert.equal(sent, true);
    assert.equal(result.status, 'SENT');
});

test('validation failure is permanent', async () => {
    let calls = 0;
    const box = harness(async () => {
        calls += 1;
        const error = new Error('HTTP_422');
        error.status = 422;
        throw error;
    });
    await box.outbox.enqueue(event('bad'));
    const result = (await box.outbox.flush())[0];
    assert.equal(result.status, 'FAILED');
    assert.equal(result.error, 'HTTP_422');
    box.at(10_000);
    assert.deepEqual(await box.outbox.flush(), []);
    assert.equal(calls, 1);
    assert.equal((await box.storage.get('bad')).status, 'FAILED');
});
