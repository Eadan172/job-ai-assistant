const test = require('node:test');
const assert = require('node:assert/strict');

require('../../extension/content-script/sites/common.js');
const boss = require('../../extension/content-script/sites/boss.js');
const lagou = require('../../extension/content-script/sites/lagou.js');
const job51 = require('../../extension/content-script/sites/51job.js');
const zhaopin = require('../../extension/content-script/sites/zhaopin.js');

const BODY = [
    '岗位职责',
    '负责 Python 后端接口开发和维护，保证服务稳定。',
    '任职要求',
    '熟悉 Python 和 FastAPI',
    '3年以上工作经验',
    '本科',
    '福利待遇',
    '五险一金和补充医疗保险'
].join('\n');

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

test('boss detail page requires url, title, company, and body', () => {
    const detail = locationFrom('https://www.zhipin.com/job_detail/abc123.html?ka=search');
    const ready = documentWith({
        '.job-banner .name': 'Python 工程师',
        '.company-info .name': '示例公司',
        '.job-banner .salary': '25-35K',
        '.job-banner .location-address': '上海',
        '.job-sec-text': BODY
    });
    assert.equal(boss.isJobDetailPage(detail, ready), true);
    const job = boss.extractJob(ready);
    assert.equal(job.title, 'Python 工程师');
    assert.equal(job.company, '示例公司');
    assert.equal(job.salary, '25-35K');
    assert.equal(job.location, '上海');
    assert.ok(job.responsibilities.some((line) => line.includes('Python 后端')));
    assert.ok(job.required_skills.some((line) => line.includes('FastAPI')));
    assert.equal(job.fingerprint ? job.fingerprint() : boss.fingerprint(job), null);
    assert.equal(boss.isJobDetailPage(locationFrom('https://www.zhipin.com/web/geek/job?query=python'), ready), false);
    assert.equal(boss.isJobDetailPage(locationFrom('https://www.zhipin.com/'), ready), false);
    assert.equal(boss.listSelectors.jobItem.includes('company-job-item'), true);
});

test('lagou, 51job, and zhaopin detail pages', () => {
    const cases = [
        [lagou, 'https://www.lagou.com/wn/jobs/1234567.html', {
            '.position-head .name': '后端工程师',
            '.company-name': '示例公司',
            '.salary': '20-30K',
            '.work_addr': '杭州',
            '.job-detail': BODY
        }],
        [job51, 'https://jobs.51job.com/shanghai/12345678.html', {
            '.cn h1': '后端工程师',
            '.cname': '示例公司',
            '.cn strong': '15-25K',
            '.msg': '上海',
            '.job-detail-content': BODY
        }],
        [zhaopin, 'https://www.zhaopin.com/jobdetail/CC123456.htm', {
            '.summary-plane__title': '后端工程师',
            '.company__title': '示例公司',
            '.summary-plane__salary': '18-28K',
            '.summary-plane__info li': '北京',
            '.describt': BODY
        }]
    ];
    cases.forEach(([adapter, href, fields]) => {
        assert.equal(adapter.isJobDetailPage(locationFrom(href), documentWith(fields)), true);
        assert.equal(adapter.extractJob(documentWith(fields)).company, '示例公司');
    });
    assert.equal(job51.isDetailUrl(locationFrom('https://we.51job.com/pc/search?keyword=python')), false);
    assert.equal(zhaopin.isDetailUrl(locationFrom('https://www.zhaopin.com/sou/jl530/kwpython')), false);
    assert.equal(lagou.isDetailUrl(locationFrom('https://www.lagou.com/wn/jobs')), false);
});
