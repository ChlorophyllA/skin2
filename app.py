import os
import sqlite3
from flask import Flask, g, jsonify, request, render_template, send_from_directory, session
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import pandas as pd
from channel.web.WebChannel import WebChannel
import uuid
import base64
from io import BytesIO
import config
from PIL import Image
from ultralytics import YOLO

# --- 配置 ---
EXCEL_PATH = "全国医院信息.xlsx"
HOSPITAL_DB = "data.db"        # 医院数据库
SKIN_DB = "data_skin.db"       # 皮肤病数据库
HOSPITAL_PAGE_SIZE = 10
SKIN_PAGE_SIZE = 1  # 每页显示一条皮肤病信息

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = 'haohaoxuexi123'  # 设置安全的密钥

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 加载YOLOv8模型
model = YOLO('yolo/skin_detection.pt')  # 确保模型路径正确

# 加载配置文件
# config_path = os.path.join(os.path.dirname(__file__), 'config.json')
config.load_config('config.json')

# 确保配置正确加载
if not config.conf():
    raise RuntimeError("Failed to load configuration")

# 检查模型配置
model_config = config.conf().get("model")
if not model_config or not model_config.get("type"):
    raise RuntimeError("Invalid model configuration")

web_channel = WebChannel()

# 疾病描述数据库（示例，实际应用中应使用真实数据库）
disease_db = {
  "MEL": {
    "id": "melanoma",
    "name": "黑色素瘤",
    "name_en": "Melanoma",
    "description": "黑色素瘤是一种高度恶性的皮肤癌，起源于黑色素细胞。它通常表现为形状不规则、颜色不均匀的痣样病变，可能快速增大、出血或瘙痒。黑色素瘤容易转移，早期诊断和治疗至关重要。",
    "advice": "1. 立即就医进行专业诊断和治疗\n2. 避免阳光暴晒，使用高倍数防晒霜\n3. 定期进行皮肤自我检查\n4. 如病变有变化（大小、形状、颜色等）应及时就医\n5. 可能需要手术切除及后续治疗",
    "risk_level": "高",
    "common_locations": "背部、腿部、面部、手掌、脚底",
    "prevention": "避免过度日晒，定期皮肤检查，避免使用日光浴床",
    "treatment": "手术切除、免疫治疗、靶向治疗、化疗、放疗"
  },
  "NV": {
    "id": "melanocytic_nevus",
    "name": "黑素细胞痣",
    "name_en": "Melanocytic Nevus",
    "description": "黑素细胞痣俗称痣或色素痣，是由黑色素细胞组成的良性皮肤肿瘤。多数痣是先天性的，但也可能在成年期出现。通常表现为平坦或隆起的棕色至黑色斑点，边界清晰，大小不一。",
    "advice": "1. 定期观察痣的变化（ABCDE法则）\n2. 避免反复摩擦或刺激痣的部位\n3. 如痣出现快速增大、颜色改变、出血等症状应及时就医\n4. 防晒以减少新痣形成\n5. 美容需求或易摩擦部位可考虑手术切除",
    "risk_level": "低（但可能恶变）",
    "common_locations": "全身各处",
    "prevention": "防晒，避免刺激，定期检查",
    "treatment": "一般无需治疗，必要时手术切除"
  },
  "BCC": {
    "id": "basal_cell_carcinoma",
    "name": "基底细胞癌",
    "name_en": "Basal Cell Carcinoma",
    "description": "基底细胞癌是最常见的皮肤癌类型，起源于表皮基底层细胞。通常表现为珍珠样结节或溃疡性病变，生长缓慢，很少转移但可能局部侵袭。常见于长期阳光暴露部位。",
    "advice": "1. 尽早就医确诊和治疗\n2. 定期皮肤科检查\n3. 严格防晒，避免进一步日晒损伤\n4. 避免自行处理病变部位\n5. 治疗后定期随访以防复发",
    "risk_level": "中",
    "common_locations": "面部、颈部、头皮等阳光暴露部位",
    "prevention": "防晒，避免过度日晒，定期皮肤检查",
    "treatment": "手术切除、Mohs手术、冷冻治疗、光动力治疗"
  },
  "AKIEC": {
    "id": "actinic_keratosis",
    "name": "光化性角化病",
    "name_en": "Actinic Keratosis",
    "description": "光化性角化病又称日光性角化病，是长期紫外线暴露引起的皮肤癌前病变。表现为粗糙、鳞屑性斑块，颜色从肤色到红棕色不等，触感砂纸样。有发展为鳞状细胞癌的风险。",
    "advice": "1. 及时就医评估和治疗\n2. 严格防晒，使用SPF30+防晒霜\n3. 避免进一步阳光暴露\n4. 定期皮肤科随访\n5. 自我监测病变变化",
    "risk_level": "中（癌前病变）",
    "common_locations": "面部、耳朵、头皮、手背等阳光暴露部位",
    "prevention": "严格防晒，避免正午阳光，戴宽边帽",
    "treatment": "冷冻治疗、局部药物、光动力治疗、手术切除"
  },
  "BKL": {
    "id": "benign_keratosis",
    "name": "良性角化病",
    "name_en": "Benign Keratosis",
    "description": "良性角化病是一组良性表皮增生性疾病的统称，包括脂溢性角化病等。表现为边界清晰的褐色至黑色斑块，表面可有油腻性鳞屑或疣状突起，通常无症状且生长缓慢。",
    "advice": "1. 一般无需治疗，定期观察\n2. 避免搔抓或摩擦刺激\n3. 如影响外观或反复刺激可考虑去除\n4. 注意与恶性病变鉴别\n5. 如有快速变化应及时就医",
    "risk_level": "低",
    "common_locations": "面部、躯干、四肢",
    "prevention": "防晒，皮肤保湿",
    "treatment": "一般无需治疗，必要时冷冻、激光或手术去除"
  },
  "DF": {
    "id": "dermatofibroma",
    "name": "皮肤纤维瘤",
    "name_en": "Dermatofibroma",
    "description": "皮肤纤维瘤是一种常见的良性真皮肿瘤，通常由局部轻微损伤引起。表现为坚实、肤色至棕色的丘疹或结节，按压时中央可见酒窝征，生长缓慢，多无症状。",
    "advice": "1. 通常无需治疗，定期观察\n2. 避免反复摩擦刺激\n3. 如出现疼痛、瘙痒或快速增大应就医\n4. 美容需求可考虑手术切除\n5. 注意与恶性病变鉴别",
    "risk_level": "低",
    "common_locations": "四肢，尤其是小腿",
    "prevention": "避免皮肤损伤，及时处理伤口",
    "treatment": "观察，必要时手术切除"
  },
  "VASC": {
    "id": "vascular_lesion",
    "name": "血管病变",
    "name_en": "Vascular Lesion",
    "description": "血管病变包括多种血管异常性疾病，如血管瘤、蜘蛛痣、樱桃状血管瘤等。表现为红色至紫色的斑点或丘疹，按压可褪色。多数为良性，但需与恶性血管肿瘤鉴别。",
    "advice": "1. 根据类型由医生评估是否需要治疗\n2. 避免外伤导致出血\n3. 监测病变大小和形态变化\n4. 美容需求可考虑激光等治疗\n5. 如快速增大、出血或溃疡应及时就医",
    "risk_level": "低至中",
    "common_locations": "面部、躯干、四肢",
    "prevention": "避免外伤，防晒",
    "treatment": "观察、激光治疗、手术切除"
  }
}

# --- DB helper ---
def get_hospital_db():
    db = getattr(g, "_hospital_db", None)
    if db is None:
        db = g._hospital_db = sqlite3.connect(HOSPITAL_DB)
        db.row_factory = sqlite3.Row
    return db

def get_skin_db():
    db = getattr(g, "_skin_db", None)
    if db is None:
        db = g._skin_db = sqlite3.connect(SKIN_DB)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_hospital_db", None)
    if db:
        db.close()
    db = getattr(g, "_skin_db", None)
    if db:
        db.close()

# --- 医院数据初始化 ---
def create_table_and_import_hospitals():
    if os.path.exists(HOSPITAL_DB):
        return
    if not os.path.exists(EXCEL_PATH):
        print(f"Excel 文件未找到：{EXCEL_PATH}")
        return
    df = pd.read_excel(EXCEL_PATH, dtype=str, engine="openpyxl")
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]

    colmap = {}
    def find_col(possible_names):
        for name in possible_names:
            if name in df.columns:
                return name
        lowered = {str(c).strip().lower(): c for c in df.columns}
        for name in possible_names:
            key = name.strip().lower()
            if key in lowered:
                return lowered[key]
        return None

    colmap['province'] = find_col(["省份","省","所在省（或直辖市）","省/市"])
    colmap['city'] = find_col(["城市","市","所在城市","市/区"])
    colmap['hospital'] = find_col(["医院名称","医院","单位名称","机构名称"])
    colmap['address'] = find_col(["医院地址","地址","详细地址"])
    colmap['phone'] = find_col(["联系电话","电话","联系电话（门诊/总机）","电话1"])
    colmap['level'] = find_col(["医院等级","等级","医院等级（三级乙等）","级别"])
    colmap['departments'] = find_col(["重点科室","重点科室/特色科室","科室","重点科"])
    colmap['operation_mode'] = find_col(["经营方式","办院性质","经营形式"])
    colmap['email'] = find_col(["电子邮箱","邮箱","Email","E-mail"])
    colmap['website'] = find_col(["医院网站","网站","网址","网站地址"])

    if colmap['hospital'] is None:
        raise ValueError("Excel 中未检测到医院名称列")

    out_df = pd.DataFrame()
    out_df['province'] = df[colmap['province']] if colmap['province'] else ""
    out_df['city'] = df[colmap['city']] if colmap['city'] else ""
    out_df['hospital'] = df[colmap['hospital']]
    out_df['address'] = df[colmap['address']] if colmap['address'] else ""
    out_df['phone'] = df[colmap['phone']] if colmap['phone'] else ""
    out_df['level'] = df[colmap['level']] if colmap['level'] else ""
    out_df['departments'] = df[colmap['departments']] if colmap['departments'] else ""
    out_df['operation_mode'] = df[colmap['operation_mode']] if colmap['operation_mode'] else ""
    out_df['email'] = df[colmap['email']] if colmap['email'] else ""
    out_df['website'] = df[colmap['website']] if colmap['website'] else ""
    out_df = out_df.fillna("")

    conn = sqlite3.connect(HOSPITAL_DB)
    out_df.to_sql("hospitals", conn, index=False, if_exists="replace")
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_province ON hospitals(province)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_city ON hospitals(city)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_level ON hospitals(level)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dept ON hospitals(departments)")
    conn.commit()
    conn.close()
    print("已从 Excel 导入到 SQLite：", HOSPITAL_DB)

try:
    create_table_and_import_hospitals()
except Exception as e:
    print("初始化导入医院数据失败：", e)

# --- 首页 ---
@app.route("/")
def home():
    return render_template("home.html")  # 新首页，选择跳转 /hospital 或 /derm

# ----------------------
# 医院信息模块 /hospital
# ----------------------
@app.route("/hospital")
def hospital_index():
    return render_template("hospital.html")

@app.route("/api/suggestions")
def hospital_suggestions():
    field = request.args.get("field", "province")
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 20))
    db = get_hospital_db()
    cur = db.cursor()
    if field not in ("province", "hospital"):
        return jsonify([])
    if q == "":
        cur.execute(f"SELECT DISTINCT {field} AS val FROM hospitals WHERE {field} <> '' ORDER BY {field} LIMIT ?", (limit,))
        rows = [r["val"] for r in cur.fetchall()]
        return jsonify(rows)
    pattern = f"%{q}%"
    cur.execute(f"SELECT DISTINCT {field} AS val FROM hospitals WHERE {field} LIKE ? COLLATE NOCASE ORDER BY {field} LIMIT ?", (pattern, limit))
    rows = [r["val"] for r in cur.fetchall()]
    return jsonify(rows)

@app.route("/api/cities")
def hospital_cities():
    province = request.args.get("province", "").strip()
    db = get_hospital_db()
    cur = db.cursor()
    if province == "":
        cur.execute("SELECT DISTINCT city as val FROM hospitals WHERE city <> '' ORDER BY city")
    else:
        cur.execute("SELECT DISTINCT city as val FROM hospitals WHERE province = ? AND city <> '' ORDER BY city", (province,))
    rows = [r["val"] for r in cur.fetchall()]
    return jsonify(rows)

@app.route("/api/levels")
def hospital_levels():
    db = get_hospital_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT level as val FROM hospitals WHERE level <> '' ORDER BY level")
    rows = [r["val"] for r in cur.fetchall()]
    return jsonify(rows)

@app.route("/api/search", methods=["POST"])
def hospital_search():
    data = request.get_json() or {}
    province = (data.get("province") or "").strip()
    city = (data.get("city") or "").strip()
    level = (data.get("level") or "").strip()
    dept = (data.get("departments") or "").strip()
    page = int(data.get("page", 1))
    per_page = HOSPITAL_PAGE_SIZE

    params = []
    wheres = []
    if province:
        wheres.append("province = ?")
        params.append(province)
    if city:
        wheres.append("city = ?")
        params.append(city)
    if level:
        wheres.append("level = ?")
        params.append(level)
    if dept:
        dept_norm = dept.strip()
        if dept_norm.endswith("科"):
            dept_norm = dept_norm[:-1]
        wheres.append("REPLACE(departments, '科', '') LIKE ? COLLATE NOCASE")
        params.append(f"%{dept_norm}%")

    where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    db = get_hospital_db()
    cur = db.cursor()
    count_sql = f"SELECT COUNT(*) as cnt FROM hospitals {where_clause}"
    cur.execute(count_sql, params)
    total = cur.fetchone()["cnt"]
    offset = (page - 1) * per_page
    sql = f"SELECT province, city, hospital, address, phone, level, departments, operation_mode, email, website FROM hospitals {where_clause} ORDER BY hospital LIMIT ? OFFSET ?"
    cur.execute(sql, params + [per_page, offset])
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        for k, v in list(r.items()):
            r[k] = v.strip() if isinstance(v, str) else ""
    return jsonify({"total": total, "page": page, "per_page": per_page, "results": rows})

# ----------------------
# 皮肤病科普模块 /derm
# ----------------------
@app.route("/derm")
def derm_index():
    return render_template("derm.html")

@app.route("/api/skin/page")
def skin_page():
    page = int(request.args.get("page", 1))
    db = get_skin_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM skin_diseases")
    total = cur.fetchone()["cnt"]
    offset = page - 1
    cur.execute("SELECT * FROM skin_diseases LIMIT 1 OFFSET ?", (offset,))
    row = cur.fetchone()
    results = [dict(row)] if row else []
    return jsonify({"total": total, "page": page, "results": results})

@app.route("/api/skin/random")
def skin_random():
    db = get_skin_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM skin_diseases ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if row:
        return jsonify(dict(row))
    return jsonify({})

#-------------------
#智能问诊
#-------------------
@app.route('/diagnose')
def diagnose():
    # 为每个会话生成唯一ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('diagnose.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    if 'session_id' not in session:
        return jsonify({'error': 'Session not initialized'}), 400
    # print(1)
    data = request.get_json()
    question = data.get('question', '').strip()
    # print(question)
    
    if not question:
        return jsonify({'error': 'Empty question'}), 400
    
    try:
        # 使用Web Channel处理问题
        tmp=session['session_id'][:]
        reply = web_channel.build_reply(question, tmp)
        # print(1)
        return jsonify({'reply': reply})
    except Exception as e:
        app.logger.error(f"Error processing question: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

#-------------------
#皮肤病识别
#-------------------
@app.route('/recognition')
def recognition():
    return render_template('recognition.html')

# 图像识别API
@app.route('/recognize', methods=['POST'])
def recognize():
    if 'image' not in request.files:
        return jsonify({'error': '未上传图片'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    # 保存原始图片
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # 使用YOLOv8进行预测
    try:
        # 执行预测
        results = model(filepath)
        
        # 处理预测结果
        detections = []
        annotated_image = None
        
        for result in results:
            # 获取带标注的图像
            im_array = result.plot()  # 绘制边界框和标签的BGR numpy数组
            annotated_image = Image.fromarray(im_array[..., ::-1])  # RGB PIL图像
            
            # 提取检测信息
            for box in result.boxes:
                class_id = int(box.cls)
                class_name = model.names[class_id]
                confidence = float(box.conf)
                
                detections.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': box.xyxy[0].tolist()
                })
        
        # 按置信度排序
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 将标注图像转换为base64
        buffered = BytesIO()
        annotated_image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # 获取疾病详情
        if detections:
            top_disease = detections[0]['class_name']
            disease_info = disease_db.get(top_disease, {})
        else:
            disease_info = {}
        
        return jsonify({
            'status': 'success',
            'original_image': f"/static/uploads/{filename}",
            'annotated_image': img_str,
            'detections': detections,
            'disease_info': disease_info
        })
        
    except Exception as e:
        app.logger.error(f"识别错误: {str(e)}")
        return jsonify({'error': '处理图像时发生错误'}), 500

# 静态文件路由
@app.route("/static/<path:fname>")
def static_files(fname):
    return send_from_directory("static", fname)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
