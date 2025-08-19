document.addEventListener('DOMContentLoaded', function() {
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('file-input');
  const previewImage = document.getElementById('preview-image');
  const changeImageBtn = document.getElementById('change-image-btn');
  const processBtn = document.getElementById('process-btn');
  const resetBtn = document.getElementById('reset-btn');
  const resultImage = document.getElementById('result-image');
  const resultsContainer = document.getElementById('results-container');
  const loading = document.getElementById('loading');
  const diseaseName = document.getElementById('disease-name');
  const confidence = document.getElementById('confidence');
  const probability = document.getElementById('probability');
  const diseaseDesc = document.getElementById('disease-desc');
  const diseaseAdvice = document.getElementById('disease-advice');
  const healthAdvice = document.getElementById('health-advice');
  
  let uploadedImage = null;
  
  // 点击上传区域触发文件选择
  uploadArea.addEventListener('click', (e) => {
    if (e.target !== changeImageBtn) {
      fileInput.click();
    }
  });
  
  // 拖拽功能
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#4a6fa5';
    uploadArea.style.backgroundColor = 'rgba(235, 245, 255, 0.7)';
  });
  
  uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#cbd5e1';
    uploadArea.style.backgroundColor = 'rgba(255, 255, 255, 0.6)';
  });
  
  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#cbd5e1';
    uploadArea.style.backgroundColor = 'rgba(255, 255, 255, 0.6)';
    
    if (e.dataTransfer.files.length) {
      handleFile(e.dataTransfer.files[0]);
    }
  });
  
  // 文件选择处理
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleFile(e.target.files[0]);
    }
  });
  
  // 更换图片按钮
  changeImageBtn.addEventListener('click', () => {
    fileInput.click();
  });
  
  function handleFile(file) {
    // 检查文件类型
    if (!file.type.match('image.*')) {
      alert('请上传图片文件 (JPG, PNG)');
      return;
    }
    
    // 检查文件大小 (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('文件大小不能超过5MB');
      return;
    }
    
    // 预览图片
    const reader = new FileReader();
    reader.onload = (e) => {
      uploadedImage = e.target.result;
      
      // 在拖拽区显示预览图片
      previewImage.src = uploadedImage;
      previewImage.classList.add('active');
      
      // 显示更换图片按钮
      changeImageBtn.style.display = 'block';
      
      // 添加已上传状态样式
      uploadArea.classList.add('has-image');
      
      // 启用识别按钮
      processBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }
  
  // 处理按钮点击
  processBtn.addEventListener('click', async () => {
    if (!uploadedImage) return;
    
    // 显示加载状态
    loading.style.display = 'block';
    resultsContainer.style.display = 'none';
    
    try {
      // 将图片数据发送到服务器
      const formData = new FormData();
      const blob = await fetch(uploadedImage).then(r => r.blob());
      formData.append('image', blob, 'skin_image.jpg');
      
      const response = await fetch('/recognize', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('识别失败');
      
      const result = await response.json();
      
      // 显示结果
      displayResults(result);
    } catch (error) {
      console.error('识别错误:', error);
      alert('识别过程中发生错误，请重试');
    } finally {
      loading.style.display = 'none';
    }
  });
  
  // 重置按钮
  resetBtn.addEventListener('click', () => {
    resetUploadArea();
  });
  
  // 重置上传区域
  function resetUploadArea() {
    fileInput.value = '';
    uploadedImage = null;
    previewImage.src = '';
    previewImage.classList.remove('active');
    changeImageBtn.style.display = 'none';
    uploadArea.classList.remove('has-image');
    processBtn.disabled = true;
    resultsContainer.style.display = 'none';
    diseaseName.textContent = '未识别';
    confidence.textContent = '0%';
    probability.textContent = '--';
    diseaseDesc.textContent = '--';
    diseaseAdvice.textContent = '--';
  }
  
  // 显示识别结果
  function displayResults(data) {
    resultsContainer.style.display = 'flex';
    
    // 更新结果图片（带标注）
    if (data.annotated_image) {
      resultImage.src = 'data:image/png;base64,' + data.annotated_image;
    } else {
      resultImage.src = previewImage.src;
    }
    
    // 更新诊断信息
    if (data.detections && data.detections.length > 0) {
      const topDetection = data.detections[0];
      diseaseName.textContent = topDetection.class_name;
      confidence.textContent = `${Math.round(topDetection.confidence * 100)}%`;
      probability.textContent = getProbabilityText(topDetection.confidence);
      
      // 这里可以扩展为根据疾病类型显示不同的描述和建议
      diseaseDesc.textContent = getDiseaseDescription(topDetection.class_name);
      diseaseAdvice.textContent = getDiseaseAdvice(topDetection.class_name);
    } else {
      diseaseName.textContent = '未发现皮肤病';
      confidence.textContent = '0%';
      probability.textContent = '低';
      diseaseDesc.textContent = '未在图片中检测到明显的皮肤病症状';
      diseaseAdvice.textContent = '如有疑虑，请咨询专业医生';
    }
  }
  
  function getProbabilityText(confidence) {
    if (confidence > 0.8) return '非常高';
    if (confidence > 0.6) return '高';
    if (confidence > 0.4) return '中等';
    return '低';
  }
  
  function getDiseaseDescription(disease) {
    // 这里可以连接数据库获取更详细的信息
    const descriptions = {
      'BKL': '良性角化病是一组良性表皮增生性疾病的统称，包括脂溢性角化病等。表现为边界清晰的褐色至黑色斑块，表面可有油腻性鳞屑或疣状突起，通常无症状且生长缓慢。',
      'AKIEC': '光化性角化病又称日光性角化病，是长期紫外线暴露引起的皮肤癌前病变。表现为粗糙、鳞屑性斑块，颜色从肤色到红棕色不等，触感砂纸样。有发展为鳞状细胞癌的风险。',
      'BCC': '基底细胞癌是最常见的皮肤癌类型，起源于表皮基底层细胞。通常表现为珍珠样结节或溃疡性病变，生长缓慢，很少转移但可能局部侵袭。常见于长期阳光暴露部位。',
      'NV': '黑素细胞痣俗称痣或色素痣，是由黑色素细胞组成的良性皮肤肿瘤。多数痣是先天性的，但也可能在成年期出现。通常表现为平坦或隆起的棕色至黑色斑点，边界清晰，大小不一。',
      'MEL': '黑色素瘤是一种恶性皮肤肿瘤，需要及时就医诊断治疗。',
      'DF':'皮肤纤维瘤是一种常见的良性真皮肿瘤，通常由局部轻微损伤引起。表现为坚实、肤色至棕色的丘疹或结节，按压时中央可见"酒窝征"，生长缓慢，多无症状。',
      'VASC':'血管病变包括多种血管异常性疾病，如血管瘤、蜘蛛痣、樱桃状血管瘤等。表现为红色至紫色的斑点或丘疹，按压可褪色。多数为良性，但需与恶性血管肿瘤鉴别。',
    };
    
    return descriptions[disease] || '这是一种症状较轻的皮肤病，若有担忧建议咨询专业医生获取详细信息。';
  }
  
  function getDiseaseAdvice(disease) {
    const advice = {
      'BKL': '1. 一般无需治疗，定期观察\n2. 避免搔抓或摩擦刺激\n3. 如影响外观或反复刺激可考虑去除\n4. 注意与恶性病变鉴别\n5. 如有快速变化应及时就医',
      'AKIEC': '1. 及时就医评估和治疗\n2. 严格防晒，使用SPF30+防晒霜\n3. 避免进一步阳光暴露\n4. 定期皮肤科随访\n5. 自我监测病变变化',
      'BCC': '1. 尽早就医确诊和治疗\n2. 定期皮肤科检查\n3. 严格防晒，避免进一步日晒损伤\n4. 避免自行处理病变部位\n5. 治疗后定期随访以防复发',
      'NV': '1. 定期观察痣的变化（ABCDE法则）\n2. 避免反复摩擦或刺激痣的部位\n3. 如痣出现快速增大、颜色改变、出血等症状应及时就医\n4. 防晒以减少新痣形成\n5. 美容需求或易摩擦部位可考虑手术切除',
      'MEL': '1. 立即就医进行专业诊断和治疗\n2. 避免阳光暴晒，使用高倍数防晒霜\n3. 定期进行皮肤自我检查\n4. 如病变有变化（大小、形状、颜色等）应及时就医\n5. 可能需要手术切除及后续治疗',
      'DF':'1. 通常无需治疗，定期观察\n2. 避免反复摩擦刺激\n3. 如出现疼痛、瘙痒或快速增大应就医\n4. 美容需求可考虑手术切除\n5. 注意与恶性病变鉴别',
      'VASC':'1. 根据类型由医生评估是否需要治疗\n2. 避免外伤导致出血\n3. 监测病变大小和形态变化\n4. 美容需求可考虑激光等治疗\n5. 如快速增大、出血或溃疡应及时就医'
    };
    
    return advice[disease] || '请及时咨询皮肤科医生获取专业建议。';
  }
});