/**
 * SkillUNO 网页商店 · 模组集工具
 *
 * 数据源：collections/collections.json
 * 页面通过 window.COLLECTIONS_URL 声明路径（默认同目录 collections.json）
 */

const _COLLECTIONS_URL =
    (typeof window !== 'undefined' && window.COLLECTIONS_URL) || 'collections.json';

/**
 * 拉取 collections.json
 */
async function loadCollections() {
    const res = await fetch(_COLLECTIONS_URL, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
}

/**
 * 按 ID 查找模组集
 */
async function findCollectionById(collId) {
    const data = await loadCollections();
    return (data.collections || []).find(c => c.id === collId) || null;
}

/**
 * 按 ID 列表批量加载模组元数据
 * 用 api.js 的 loadMod 加载 {ID}.json
 * 失败的项返回 { ID, _missing: true }
 */
async function loadModsByIds(ids) {
    const results = await Promise.allSettled(
        ids.map(id => loadMod(`${id}.json`))
    );
    return ids.map((id, i) => {
        const r = results[i];
        return r.status === 'fulfilled'
            ? r.value
            : { ID: id, _missing: true };
    });
}

/**
 * 判断是否官方模组
 */
function isOfficialMod(modId) {
    return /^S\d+$/.test(modId);
}
