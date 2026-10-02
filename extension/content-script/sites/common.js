/* Shared DOM helpers and the site registry.
 * List selectors stay here so content.js can keep the manual scraper.
 * The official job fingerprint is computed by server/utils/fingerprint.py.
 */
(function (root, factory) {
    var api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    root.JobAISites = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    var MIN_BODY_LENGTH = 40;
    var adapters = [];

    function hostname(location) {
        return String((location && location.hostname) || '').toLowerCase();
    }

    function pathname(location) {
        if (location && location.pathname) {
            return location.pathname;
        }
        try {
            return new URL(location.href).pathname;
        } catch (error) {
            return '';
        }
    }

    function firstText(doc, selectors) {
        if (!doc || !selectors) {
            return '';
        }
        for (var i = 0; i < selectors.length; i += 1) {
            var el = typeof doc.querySelector === 'function' ? doc.querySelector(selectors[i]) : null;
            var text = el && el.textContent ? String(el.textContent).trim() : '';
            if (text) {
                return text;
            }
        }
        return '';
    }

    function isHeading(line, words) {
        if (line.length > 16) {
            return false;
        }
        return words.some(function (word) {
            return line.indexOf(word) !== -1;
        });
    }

    function splitSections(text) {
        var result = {
            responsibilities: [],
            required_skills: [],
            preferred_skills: [],
            education: [],
            benefits: [],
            experience_years: ''
        };
        var section = 'responsibilities';
        String(text || '').split(/\n+/).forEach(function (raw) {
            var line = raw.trim();
            if (!line) {
                return;
            }
            if (isHeading(line, ['岗位职责', '工作职责', '职位描述', '工作内容'])) {
                section = 'responsibilities';
                return;
            }
            if (isHeading(line, ['任职要求', '岗位要求', '职位要求'])) {
                section = 'required_skills';
                return;
            }
            if (isHeading(line, ['优先条件', '加分项'])) {
                section = 'preferred_skills';
                return;
            }
            if (isHeading(line, ['福利待遇', '员工福利'])) {
                section = 'benefits';
                return;
            }
            if (/本科|硕士|博士|大专|学历不限/.test(line) && line.length <= 20) {
                result.education.push(line);
            }
            if (!result.experience_years && line.indexOf('经验') !== -1 && line.length <= 24) {
                result.experience_years = line;
            }
            result[section].push(line);
        });
        return result;
    }

    function createSiteAdapter(config) {
        return {
            id: config.id,
            domain: config.domain,
            displayName: config.displayName,
            listSelectors: config.listSelectors,
            canHandle: function (location) {
                return hostname(location).indexOf(config.domain) !== -1;
            },
            isDetailUrl: function (location) {
                return config.isDetailUrl(hostname(location), pathname(location).toLowerCase());
            },
            isJobDetailPage: function (location, document) {
                if (!this.isDetailUrl(location)) {
                    return false;
                }
                var title = firstText(document, config.detail.title);
                var company = firstText(document, config.detail.company);
                var body = firstText(document, config.detail.body);
                return Boolean(title && company && body && body.length >= MIN_BODY_LENGTH);
            },
            extractJob: function (document) {
                var body = firstText(document, config.detail.body);
                var sections = splitSections(body);
                return {
                    title: firstText(document, config.detail.title),
                    company: firstText(document, config.detail.company),
                    salary: firstText(document, config.detail.salary),
                    location: firstText(document, config.detail.location),
                    responsibilities: sections.responsibilities,
                    required_skills: sections.required_skills,
                    preferred_skills: sections.preferred_skills,
                    experience_years: sections.experience_years,
                    education: sections.education,
                    benefits: sections.benefits,
                    full_text: body
                };
            },
            fingerprint: function () {
                return null;
            }
        };
    }

    function register(adapter) {
        adapters.push(adapter);
    }

    function all() {
        return adapters.slice();
    }

    function legacySiteConfig() {
        var config = {};
        adapters.forEach(function (adapter) {
            config[adapter.domain] = {
                name: adapter.displayName,
                selectors: adapter.listSelectors
            };
        });
        return config;
    }

    return {
        MIN_BODY_LENGTH: MIN_BODY_LENGTH,
        createSiteAdapter: createSiteAdapter,
        register: register,
        all: all,
        legacySiteConfig: legacySiteConfig,
        firstText: firstText,
        splitSections: splitSections
    };
});
