/**
 * SkillUNO 网页商店 · 数据 API
 *
 * 数据来源：web/mods/ 目录（相对路径，不走 CDN）
 * 部署时由 GitHub Actions 把 mods/*.json 复制进 web/mods/
 *
 * 页面需声明 window.DATA_ROOT：
 *   web/index.html       →  'mods/'
 *   web/mods/index.html  →  './'
 *   web/mods/detail.html →  './'
 */

const DATA_ROOT = (typeof window !== 'undefined' && window.DATA_ROOT) || 'mods/';
const MOD_INDEX_URL = DATA_ROOT + 'mod_idx.json';
const OFFICIAL_LIST_URL = DATA_ROOT + 'official.json';

/**
 * 拉取第三方索引
 */
async function loadModIndex() {
    const res = await fetch(MOD_INDEX_URL, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status} on ${MOD_INDEX_URL}`);
    return await res.json();
}

/**
 * 拉取官方模组文件名列表（唯一数据源）
 */
async function loadOfficialFileList() {
    try {
        const res = await fetch(OFFICIAL_LIST_URL, { cache: 'no-cache' });
        if (!res.ok) return [];
        const data = await res.json();
        return Array.isArray(data.mods) ? data.mods : [];
    } catch (err) {
        console.warn('official.json 拉取失败：', err);
        return [];
    }
}

/**
 * 拉取单个模组元数据
 */
async function loadMod(filename) {
    const res = await fetch(DATA_ROOT + filename, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status} on ${filename}`);
    return await res.json();
}

/**
 * 官方模组列表
 */
async function loadOfficialMods() {
    const files = await loadOfficialFileList();
    const results = await Promise.allSettled(files.map(loadMod));
    return results
        .filter(r => r.status === 'fulfilled')
        .map(r => ({ ...r.value, builtin: true }));
}

/**
 * 所有模组（官方 + handpicked + other），按 ID 去重，官方优先
 */
async function loadAllMods() {
    const [official, index] = await Promise.all([
        loadOfficialMods(),
        loadModIndex().catch(() => ({ handpicked: [], other: [] })),
    ]);
    const thirdPartyFiles = [
        ...(index.handpicked || []),
        ...(index.other || []),
    ];
    const thirdPartyResults = await Promise.allSettled(thirdPartyFiles.map(loadMod));
    const thirdParty = thirdPartyResults
        .filter(r => r.status === 'fulfilled')
        .map(r => r.value);

    const seen = new Set();
    const merged = [];
    for (const m of [...official, ...thirdParty]) {
        const id = m.ID || m.id;
        if (id && !seen.has(id)) {
            seen.add(id);
            merged.push(m);
        }
    }
    return merged;
}
