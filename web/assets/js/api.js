/**
 * SkillUNO 网页商店 · 数据 API
 * 数据源：jsDelivr（国内可达）
 */

const CDN_BASE = 'https://cdn.jsdelivr.net/gh/zhuyiming0208/SkillUNO@main/';
const MOD_INDEX_URL = CDN_BASE + 'mods/mod_idx.json';
const MOD_BASE_URL = CDN_BASE + 'mods/';

/**
 * 拉取 mod_idx.json
 */
async function loadModIndex() {
    const res = await fetch(MOD_INDEX_URL, { cache: 'no-cache' });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
}

/**
 * 拉取单个模组元数据（filename 例如 "example.json"）
 */
async function loadMod(filename) {
    const res = await fetch(MOD_BASE_URL + filename, { cache: 'no-cache' });
    if (!res.ok) {
        throw new Error(`HTTP ${res.status} on ${filename}`);
    }
    return await res.json();
}

/**
 * 硬编码官方模组
 */
async function loadOfficialMods() {
    return [
        { id: 'S1', name: '经典赛季', skills: 16, builtin: true,
          description: '基础技能池，适合入门。' },
        { id: 'S2', name: '被动觉醒', skills: 8, builtin: true,
          description: '被动技与合纵连横。' },
        { id: 'S3', name: '同盟赛季', skills: 0, builtin: true,
          description: '预留赛季。' },
        { id: 'S4', name: '补丁赛季', skills: 8, builtin: true,
          description: '防御与情报技能。' },
    ];
}

/**
 * 拉取所有模组（handpicked + other）
 */
async function loadAllMods() {
    const index = await loadModIndex();
    const files = [
        ...(index.handpicked || []),
        ...(index.other || []),
    ];
    const results = await Promise.allSettled(files.map(loadMod));
    return results
        .filter(r => r.status === 'fulfilled')
        .map(r => r.value);
}
