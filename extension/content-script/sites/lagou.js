(function (root) {
    if (!root.JobAISites && typeof require === 'function') {
        require('./common.js');
    }
    var sites = root.JobAISites;
    sites.register(sites.createSiteAdapter({
        id: 'lagou',
        domain: 'lagou.com',
        displayName: '拉勾网',
        listSelectors: {
            jobList: '.position-list, .list_item_box, .position-list-box',
            jobItem: '.position-list-item, .item__10RTO, .list_item_box, .position-list-item',
            title: '.position-name, .position__10RTO, .p_top a, .position-name a',
            company: '.company-name, .company__10RTO, .company_name, .company-name a',
            salary: '.salary, .money__10RTO, .p_bot .money, .salary span',
            location: '.position-address, .address__10RTO, .p_bot .city, .position-address span',
            experience: '.position-demand span, .p_bot__10RTO li, .p_bot span, .position-demand li',
            education: '.position-demand span, .p_bot__10RTO li, .p_bot span, .position-demand li',
            description: '.position-desc, .job_bt__10RTO, .job_detail, .position-desc'
        },
        detail: {
            title: ['.position-head .name', '.job-name', '.position-name'],
            company: ['.company-name'],
            salary: ['.salary', '.money__10RTO'],
            location: ['.work_addr', '.position-address'],
            body: ['.job-detail', '.job_bt__10RTO']
        },
        isDetailUrl: function (host, path) {
            return host.indexOf('lagou.com') !== -1 && path.indexOf('/jobs/') !== -1 && /\d{3,}/.test(path);
        }
    }));
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = sites.all().filter(function (item) { return item.id === 'lagou'; })[0];
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
