const provinceInput = document.getElementById("province-input");
const provinceSug = document.getElementById("province-suggestions");
const citySelect = document.getElementById("city-select");
const levelSelect = document.getElementById("level-select");
const deptInput = document.getElementById("dept-input");
const searchBtn = document.getElementById("search-btn");
const resetBtn = document.getElementById("reset-btn");
const resultsGrid = document.getElementById("results-grid");
const prevPageBtn = document.getElementById("prev-page");
const nextPageBtn = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");
const jumpPageInput = document.getElementById("jump-page-input");
const jumpPageBtn = document.getElementById("jump-page-btn");

let currentPage = 1;
let lastQuery = {}; // 保存当前查询条件
let totalResults = 0;
const PER_PAGE = 10;
let debounceTimer = null;

// Helper: fetch JSON
async function fetchJSON(url, opts){
  const res = await fetch(url, opts);
  if(!res.ok) throw new Error("Network error");
  return await res.json();
}

// 初始化等级列表
async function loadLevels(){
  try{
    const levels = await fetchJSON("/api/levels");
    levelSelect.innerHTML = '<option value="">全部等级</option>';
    levels.forEach(l => {
      const o = document.createElement("option");
      o.value = l;
      o.textContent = l;
      levelSelect.appendChild(o);
    });
  }catch(e){
    console.error("加载等级失败", e);
  }
}

// 省份输入框点击事件 - 显示全部省份
provinceInput.addEventListener("focus", () => {
  loadProvinceSuggestions("");
});

// 省份联想
provinceInput.addEventListener("input", e => {
  const q = e.target.value.trim();
  if(debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    loadProvinceSuggestions(q);
  }, 200);
});

// 点击页面空白处关闭省份建议框
document.addEventListener("click", (ev) => {
  if(!provinceSug.contains(ev.target) && ev.target !== provinceInput){
    provinceSug.innerHTML = "";
  }
});

// 加载省份联想
async function loadProvinceSuggestions(q){
  try{
    const url = `/api/suggestions?field=province&q=${encodeURIComponent(q)}&limit=30`;
    const arr = await fetchJSON(url);
    if(arr.length === 0){
      provinceSug.innerHTML = "";
      return;
    }
    const box = document.createElement("div");
    box.className = "list";
    arr.forEach(item => {
      const d = document.createElement("div");
      d.textContent = item;
      d.addEventListener("click", () => {
        provinceInput.value = item;
        provinceSug.innerHTML = "";
        // 省份确定后刷新城市联动
        loadCities(item);
      });
      box.appendChild(d);
    });
    provinceSug.innerHTML = "";
    provinceSug.appendChild(box);
  }catch(e){
    console.error(e);
  }
}

// 当省份改变（手动输入后），也要刷新城市
provinceInput.addEventListener("change", (e) => {
  const val = e.target.value.trim();
  loadCities(val);
});

// 加载城市联动（若 province 为空则加载全部城市）
async function loadCities(province){
  try{
    const url = `/api/cities?province=${encodeURIComponent(province || "")}`;
    const arr = await fetchJSON(url);
    citySelect.innerHTML = '<option value="">全部城市</option>';
    arr.forEach(c => {
      const o = document.createElement("option");
      o.value = c;
      o.textContent = c;
      citySelect.appendChild(o);
    });
  }catch(e){
    console.error("加载城市失败", e);
  }
}

// 搜索函数，调用后端接口
async function doSearch(page=1){
  currentPage = page;
  const payload = {
    province: provinceInput.value.trim(),
    city: citySelect.value,
    level: levelSelect.value,
    departments: deptInput.value.trim(),
    page: page
  };
  lastQuery = payload;
  try{
    searchBtn.disabled = true;
    const res = await fetchJSON("/api/search", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    totalResults = res.total || 0;
    renderResults(res.results || []);
    updatePagination();
  }catch(e){
    console.error("搜索失败", e);
    resultsGrid.innerHTML = "<div>搜索失败，请检查后端或控制台错误。</div>";
    hidePagination();
  }finally{
    searchBtn.disabled = false;
  }
}

// 渲染结果卡片
function renderResults(items){
  resultsGrid.innerHTML = "";
  if(!items || items.length === 0){
    resultsGrid.innerHTML = "<div>未找到匹配医院。</div>";
    hidePagination();
    return;
  }
  items.forEach(item => {
    const card = document.createElement("div");
    card.className = "card";
    const title = document.createElement("h3");
    title.textContent = item.hospital || "未命名医院";
    card.appendChild(title);

    // 按需显示已存在的字段
    const fields = [
      ["province", "省份"],
      ["city", "城市"],
      ["address", "医院地址"],
      ["phone", "联系电话"],
      ["level", "医院等级"],
      ["departments", "重点科室"],
      ["operation_mode", "经营方式"],
      ["email", "电子邮箱"],
      ["website", "医院网站"]
    ];
    fields.forEach(([key, label]) => {
      const val = item[key];
      if(val && val.trim() !== ""){
        const div = document.createElement("div");
        div.className = "meta";
        div.innerHTML = `<strong>${label}：</strong> ${escapeHtml(val)}`;
        card.appendChild(div);
      }
    });

    resultsGrid.appendChild(card);
  });
  showPagination();
}

// 显示分页控件
function showPagination(){
  prevPageBtn.style.display = "";
  nextPageBtn.style.display = "";
  pageInfo.style.display = "";
  jumpPageInput.style.display = "";
  jumpPageBtn.style.display = "";
}

// 隐藏分页控件
function hidePagination(){
  prevPageBtn.style.display = "none";
  nextPageBtn.style.display = "none";
  pageInfo.style.display = "none";
  jumpPageInput.style.display = "none";
  jumpPageBtn.style.display = "none";
}

// 分页更新
function updatePagination(){
  const totalPages = Math.max(1, Math.ceil(totalResults / PER_PAGE));
  pageInfo.textContent = `第 ${currentPage} / ${totalPages} 页 · 共 ${totalResults} 条`;
  prevPageBtn.disabled = currentPage <= 1;
  nextPageBtn.disabled = currentPage >= totalPages;
  jumpPageInput.value = currentPage;
  jumpPageInput.max = totalPages;
}

// 分页按钮事件
prevPageBtn.addEventListener("click", () => {
  if(currentPage > 1) doSearch(currentPage - 1);
});
nextPageBtn.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(totalResults / PER_PAGE));
  if(currentPage < totalPages) doSearch(currentPage + 1);
});

// 跳转按钮事件
jumpPageBtn.addEventListener("click", () => {
  let val = parseInt(jumpPageInput.value);
  const totalPages = Math.max(1, Math.ceil(totalResults / PER_PAGE));
  if (isNaN(val) || val < 1) val = 1;
  if (val > totalPages) val = totalPages;
  if (val !== currentPage) {
    doSearch(val);
  }
});

// 逃逸 HTML
function escapeHtml(s){
  return s.replace(/[&<>"']/g, function(m){ return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]; });
}

// 事件绑定
searchBtn.addEventListener("click", () => doSearch(1));
// 重置按钮
resetBtn.addEventListener("click", () => {
  provinceInput.value = "";
  provinceSug.innerHTML = "";
  citySelect.innerHTML = '<option value="">全部城市</option>';
  levelSelect.selectedIndex = 0;
  deptInput.value = "";
  currentPage = 1;
  totalResults = 0;
  resultsGrid.innerHTML = "";
  pageInfo.textContent = "";
  hidePagination();
  // 载入所有城市/等级
  loadCities("");
  loadLevels();
});

//prevPageBtn.addEventListener("click", () => {
//  if(currentPage > 1) doSearch(currentPage - 1);
//});
//nextPageBtn.addEventListener("click", () => {
//  const totalPages = Math.max(1, Math.ceil(totalResults / PER_PAGE));
//  if(currentPage < totalPages) doSearch(currentPage + 1);
//});

// 页面首次加载
window.addEventListener("load", () => {
  loadLevels();
  loadCities("");
  hidePagination();
});