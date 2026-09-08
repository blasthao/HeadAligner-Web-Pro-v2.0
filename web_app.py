# -*- coding: utf-8 -*-
"""
程序名称：颅脑CT体位配准及全自动量化质控软件 V2.0 (Streamlit 网页云端发布版 + PACS传输功能)
功能描述：100%保留物理内核与质控指标（内生同质性SNR/CNR、绝对物理中心、刚性投影角）。
          新增：自动加载底层模板、多DICOM文件夹 ZIP 智能批量解析、多显示窗位切换、DICOM子目录打包下载。
          新增：左侧栏 PACS C-ECHO 与 C-STORE 一键归档推送功能。
          国际化升级：全面打通 中文 / English / 日本語 / 한국어 全域动态语境对齐切换。
"""

import sys
import os
import time
import shutil
import tempfile
import zipfile
import numpy as np
import SimpleITK as sitk
import pandas as pd
import warnings
import streamlit as st
from pathlib import Path
from scipy.ndimage import center_of_mass, label, sum as ndi_sum, zoom
from scipy.stats import shapiro, ttest_rel, wilcoxon
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont

# ==============================
# 动态加载 PACS 相关依赖
# ==============================
try:
    import pydicom
    from pynetdicom import AE, VerificationPresentationContexts, StoragePresentationContexts, build_context
    HAS_PACS_LIBS = True
except ImportError:
    HAS_PACS_LIBS = False

warnings.filterwarnings('ignore')

# 配置网页标题与极宽布局
st.set_page_config(page_title="HeadAligner Web Pro v2.0", layout="wide")

# ==========================================
# 国际化语言包 (全面打通四国语言极客版)
# ==========================================
I18N = {
    'zh': {
        'title': '颅脑CT体位配准及全自动量化质控软件 V2.0 (云端版)',
        'input_label': '📦 第一步：上传待处理数据 (支持 NIfTI文件 / loose DICOM切片 / 包含批量 DICOM 文件夹的 .zip 压缩包):',
        'ref_label': '📐 上传标准空间参考模板 (系统未检测到默认模板时需手动上传):',
        'template_auto': '✅ 系统已自动挂载内置标准脑几何模板 (Auto-loaded default template).',
        'window_label': '📺 第二步：选择影像显示与 PACS 导出窗位预设:',
        'out_format_label': '💾 第三步：选择导出文件格式:',
        'window_brain': '颅脑软组织窗 (WW: 80, WL: 40)',
        'window_bone': '颅脑骨窗 (WW: 1500, WL: 450)',
        'keep_res': '保留原始空间分辨率',
        'run_btn': '🚀 启动全自动刚性配准与质量评估批处理',
        'success': '🎉 批量处理与统计分析全部完成！请在下方一键下载完整科研套件压缩包。',
        'preview_before': '矫正前 (Raw Image)',
        'preview_after': '矫正后 (Aligned Image)',
        'metrics_title': '📋 多中心群体统计学质控指标总结表',
        'err_upload': '❌ 请先上传待配准影像数据！',
        'err_template': '❌ 未检测到标准模板，请手动上传！',
        'err_invalid': '❌ 未识别到任何有效的 NIfTI 文件或 DICOM 序列，请检查上传内容！',
        'processing_prefix': '⚡ 正在分析与矫正第',
        'processing_mid': '例:',
        'download_btn': '📥 导出完整出版级科研套件包 (.zip)',
        'col_metric': '指标名称',
        'col_before': '矫正前统计描述',
        'col_after': '矫正后统计描述',
        'col_method': '检验方法',
        'col_stat': '统计量',
        'col_p': 'P值',
        'col_sig': '差异显著性',
        'col_imp': '平均改善率(%)',
        'test_t': '配对t检验 (t值)',
        'test_w': 'Wilcoxon符号秩检验 (Z值)',
        'pacs_title': '📡 PACS 归档配置',
        'pacs_send_btn': '📤 将生成的 DICOM 图像一键发送至 PACS',
        'pacs_ok': '🎉 成功！已将结果文件归档至 PACS。',
        'pacs_err': '❌ 无法建立 PACS 连接，请检查网络参数。',
        'pacs_test_ok': '✅ C-ECHO 成功！服务器通讯正常。',
        'pacs_test_err': '❌ C-ECHO 失败或无法建立关联，请检查网络配置。',
        'pacs_not_dicom': '⚠️ 提示：只有选择 "DICOM" 导出格式时，才支持 PACS 网络推送功能。'
    },
    'en': {
        'title': 'Cranial CT Registration & Quality Evaluation Software V2.0 (Web)',
        'input_label': '📦 Step 1: Upload moving data (Support .nii / .dcm / .zip for batch folders):',
        'ref_label': '📐 Upload standard template (if not auto-detected):',
        'template_auto': '✅ Default geometric brain template auto-mounted.',
        'window_label': '📺 Step 2: Select Display & Export Window Preset:',
        'out_format_label': '💾 Step 3: Select Export Format:',
        'window_brain': 'Brain Soft Tissue Window (WW: 80, WL: 40)',
        'window_bone': 'Bone Fracture Window (WW: 1500, WL: 450)',
        'keep_res': 'Keep Original Resolution',
        'run_btn': '🚀 Start Batch Registration & Evaluation',
        'success': '🎉 Batch processing completed! Download your comprehensive research suite below.',
        'preview_before': 'Before Registration',
        'preview_after': 'After Registration',
        'metrics_title': '📋 Population Statistical QC Summary',
        'err_upload': '❌ Please upload target medical image data first!',
        'err_template': '❌ Standard template not detected. Please upload manually!',
        'err_invalid': '❌ No valid NIfTI files or DICOM series detected. Please verify your upload content!',
        'processing_prefix': '⚡ Analyzing and correcting No.',
        'processing_mid': 'of:',
        'download_btn': '📥 Export Complete Publication-Grade Research Suite (.zip)',
        'col_metric': 'Metric Name',
        'col_before': 'Pre-alignment Description',
        'col_after': 'Post-alignment Description',
        'col_method': 'Statistical Method',
        'col_stat': 'Statistic',
        'col_p': 'P-value',
        'col_sig': 'Significance',
        'col_imp': 'Mean Improvement (%)',
        'test_t': 'Paired t-test (t-value)',
        'test_w': 'Wilcoxon Signed-Rank Test (Z-value)',
        'pacs_title': '📡 PACS Archive Config',
        'pacs_send_btn': '📤 Send Generated DICOMs to PACS',
        'pacs_ok': '🎉 Success! Results archived to PACS.',
        'pacs_err': '❌ Failed to establish PACS connection.',
        'pacs_test_ok': '✅ C-ECHO Success! Server is reachable.',
        'pacs_test_err': '❌ C-ECHO Failed! Check network configuration.',
        'pacs_not_dicom': '⚠️ Note: PACS transmission is only available when exporting as "DICOM".'
    },
    'jp': {
        'title': '頭部CT体位位置合わせおよび自動品質評価ソフト V2.0 (ウェブ版)',
        'input_label': '📦 ステップ 1：処理データのアップロード (.nii / .dcm / フォルダを含む .zip):',
        'ref_label': '📐 標準空間リファレンステンプレートのアップロード (自動検出されない場合):',
        'template_auto': '✅ デフォルトの頭部幾何学テンプレートが自動マウントされました。',
        'window_label': '📺 ステップ 2：画像表示およびPACSエクスポートのウインドウプリセットの選択:',
        'out_format_label': '💾 ステップ 3：エクスポート形式の選択:',
        'window_brain': '頭部軟部組織ウインドウ (WW: 80, WL: 40)',
        'window_bone': '骨ウインドウ (WW: 1500, WL: 450)',
        'keep_res': '元の空間解像度を維持する',
        'run_btn': '🚀 自動剛体位置合わせと多施設品質評価の一括処理を開始',
        'success': '🎉 一括処理と統計解析が完了しました！以下のリンクから研究スイートの圧縮ファイルをダウンロードしてください。',
        'preview_before': '補正前 (Raw Image)',
        'preview_after': '補正後 (Aligned Image)',
        'metrics_title': '📋 多施設共同研究統計学的品質管理指標要約表',
        'err_upload': '❌ 先に配准イメージデータをアップロードしてください！',
        'err_template': '❌ 標準テンプレートが検出されません。手動でアップロードしてください！',
        'err_invalid': '❌ 有効な NIfTI ファイルまたは DICOM シーケンスが識別されませんでした。アップロード内容を確認してください！',
        'processing_prefix': '⚡ 第 ',
        'processing_mid': ' 例を分析・補正中: ',
        'download_btn': '📥 完全な出版級研究スイートパックをエクスポート (.zip)',
        'col_metric': '指標名',
        'col_before': '補正前統計記述',
        'col_after': '補正後統計記述',
        'col_method': '検定方法',
        'col_stat': '統計量',
        'col_p': 'P値',
        'col_sig': '有意差',
        'col_imp': '平均改善率(%)',
        'test_t': '対応のあるt検定 (t値)',
        'test_w': 'Wilcoxon符号付順位検定 (Z値)',
        'pacs_title': '📡 PACS アーカイブ設定',
        'pacs_send_btn': '📤 生成されたDICOMをPACSに送信',
        'pacs_ok': '🎉 成功！結果がPACSにアーカイブされました。',
        'pacs_err': '❌ PACS接続を確立できません。',
        'pacs_test_ok': '✅ C-ECHO 成功！サーバーと通信可能です。',
        'pacs_test_err': '❌ C-ECHO 失敗！ネットワーク設定を確認してください。',
        'pacs_not_dicom': '⚠️ 注意：PACS送信は、エクスポート形式として「DICOM」を選択した場合のみサポートされます。'
    },
    'ko': {
        'title': '두부 CT 체위 정렬 및 자동 정량적 품질관리 소프트웨어 V2.0 (웹버전)',
        'input_label': '📦 1단계: 처리할 데이터 업로드 (.nii / .dcm / 폴더 포함 .zip 지원):',
        'ref_label': '📐 표준 공간 참조 템플릿 업로드 (자동 감지되지 않은 경우 수동 업로드):',
        'template_auto': '✅ 기본 두부 기하학 템플릿이 자동으로 마운트되었습니다.',
        'window_label': '📺 2단계: 영상 표시 및 PACS 내보내기 윈도우 프리셋 선택:',
        'out_format_label': '💾 3단계: 내보내기 파일 형식 선택:',
        'window_brain': '두부 연부조직 윈도우 (WW: 80, WL: 40)',
        'window_bone': '골 윈도우 (WW: 1500, WL: 450)',
        'keep_res': '원본 공간 해상도 유지',
        'run_btn': '🚀 자동 강체 정렬 및 다기관 품질 평가 배치 처리 시작',
        'success': '🎉 배치 처리 및 통계 분석이 완료되었습니다! 아래에서 연구용 데이터 세트 압축 파일을 다운로드하십시오.',
        'preview_before': '교정 전 (Raw Image)',
        'preview_after': '교정 후 (Aligned Image)',
        'metrics_title': '📋 다기관 공동 연구 통계적 품질관리 지표 요약표',
        'err_upload': '❌ 먼저 정렬할 영상 데이터를 업로드하십시오!',
        'err_template': '❌ 표준 템플릿이 감지되지 않았습니다. 수동으로 업로드하십시오!',
        'err_invalid': '❌ 유효한 NIfTI 파일 또는 DICOM 시퀀스를 인식하지 못했습니다. 업로드 내용을 확인하십시오!',
        'processing_prefix': '⚡ 제 ',
        'processing_mid': ' 례 분석 및 교정 중: ',
        'download_btn': '📥 완전한 출판급 연구용 데이터 세트 패키지 내보내기 (.zip)',
        'col_metric': '지표명',
        'col_before': '교정 전 통계 기술',
        'col_after': '교정 후 통계 기술',
        'col_method': '검정 방법',
        'col_stat': '통계량',
        'col_p': 'P값',
        'col_sig': '유의성',
        'col_imp': '평균 개선율(%)',
        'test_t': '대응표본 t-검정 (t값)',
        'test_w': 'Wilcoxon 부호순위 검정 (Z값)',
        'pacs_title': '📡 PACS 아카이브 설정',
        'pacs_send_btn': '📤 생성된 DICOM을 PACS로 전송',
        'pacs_ok': '🎉 성공! 결과가 PACS에 저장되었습니다.',
        'pacs_err': '❌ PACS 연결을 설정할 수 없습니다.',
        'pacs_test_ok': '✅ C-ECHO 성공! 서버와 통신할 수 있습니다.',
        'pacs_test_err': '❌ C-ECHO 실패! 네트워크 설정을 확인하십시오.',
        'pacs_not_dicom': '⚠️ 참고: PACS 전송은 내보내기 형식을 "DICOM"으로 선택한 경우에만 사용할 수 있습니다.'
    }
}

# ==========================================
# 自动加载本地默认模板模块
# ==========================================
def get_default_template_path():
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    path = os.path.join(base_path, "template", "standard_head.nii.gz")
    if os.path.exists(path):
        return path
    return None

# ==========================================
# 智能 Web 文件/ZIP/DICOM目录 解析引擎
# ==========================================
def process_uploaded_files(uploaded_files, tmp_in_dir):
    samples = []
    zip_files = [f for f in uploaded_files if f.name.endswith('.zip')]
    if zip_files:
        for zip_f in zip_files:
            zip_path = os.path.join(tmp_in_dir, zip_f.name)
            with open(zip_path, "wb") as f: f.write(zip_f.getbuffer())
            
            extract_dir = os.path.join(tmp_in_dir, zip_f.name + "_extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(extract_dir)
            
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.nii') or file.endswith('.nii.gz'):
                        samples.append({'type': 'NIfTI', 'path': os.path.join(root, file), 'name': file.replace('.nii.gz', '').replace('.nii', '')})
            
            reader = sitk.ImageSeriesReader()
            for root, dirs, files in os.walk(extract_dir):
                if any(f.lower().endswith('.dcm') or f.lower().endswith('.ima') for f in files):
                    series_IDs = reader.GetGDCMSeriesIDs(root)
                    for s_id in series_IDs:
                        samples.append({'type': 'DICOM', 'path': root, 'series_id': s_id, 'name': f"{os.path.basename(root)}_{s_id[:5]}"})

    nifti_files = [f for f in uploaded_files if f.name.endswith('.nii') or f.name.endswith('.nii.gz')]
    for f in nifti_files:
        path = os.path.join(tmp_in_dir, f.name)
        with open(path, "wb") as out_f: out_f.write(f.getbuffer())
        samples.append({'type': 'NIfTI', 'path': path, 'name': f.name.replace('.nii.gz', '').replace('.nii', '')})

    dcm_files = [f for f in uploaded_files if f.name.lower().endswith('.dcm') or f.name.lower().endswith('.ima')]
    if dcm_files:
        dcm_dir = os.path.join(tmp_in_dir, "Uploaded_DICOMs")
        os.makedirs(dcm_dir, exist_ok=True)
        for idx, f in enumerate(dcm_files):
            path = os.path.join(dcm_dir, f"{idx}_{f.name}")
            with open(path, "wb") as out_f: out_f.write(f.getbuffer())
                
        reader = sitk.ImageSeriesReader()
        series_IDs = reader.GetGDCMSeriesIDs(dcm_dir)
        for s_id in series_IDs:
            samples.append({'type': 'DICOM', 'path': dcm_dir, 'series_id': s_id, 'name': f"DICOM_Series_{s_id[:8]}"})
            
    return samples

def load_single(sample):
    if sample['type'] == 'DICOM':
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(sample['path'], sample['series_id'])
        reader.SetFileNames(dicom_names)
        reader.MetaDataDictionaryArrayUpdateOn()
        img = reader.Execute()
        tags = ["0010|0010", "0010|0020", "0020|000d", "0008|0060"]
        meta = {t: reader.GetMetaData(0, t) if reader.HasMetaDataKey(0, t) else "" for t in tags}
        return sitk.Cast(img, sitk.sitkFloat32), meta
    else:
        return sitk.ReadImage(sample['path'], sitk.sitkFloat32), {}

# ==========================================
# 安全无忧写入引擎 (防暴毙机制)
# ==========================================
def save_single(img, path, meta, out_format, window_index):
    img = sitk.Cast(img, sitk.sitkInt16)
    if out_format == "NIfTI":
        p = path if path.endswith(".nii.gz") else path + ".nii.gz"
        sitk.WriteImage(img, p)
    else:
        os.makedirs(path, exist_ok=True)
        writer = sitk.ImageFileWriter()
        writer.KeepOriginalImageUIDOn()
        
        # 🎯 核心修复 1：利用 pydicom 生成标准合规的全新序列 UID
        try:
            from pydicom.uid import generate_uid
            new_series_uid = generate_uid()
        except ImportError:
            timestamp = int(time.time() * 1000000)
            new_series_uid = f"1.2.826.0.1.3680043.2.1125.2.{timestamp}"
        
        study_uid = meta.get("0020|000d", "")
        if not study_uid or str(study_uid).strip() in ["NA", "None", ""]: 
            try:
                from pydicom.uid import generate_uid
                study_uid = generate_uid()
            except ImportError:
                study_uid = f"1.2.826.0.1.3680043.2.1125.3.{int(time.time() * 1000000)}"
            
        patient_id = meta.get("0010|0020", "")
        if not patient_id or str(patient_id).strip() in ["NA", "None", ""]: 
            patient_id = f"ID_{int(time.time())}"
            
        patient_name = meta.get("0010|0010", "")
        if not patient_name or str(patient_name).strip() in ["NA", "None", ""]: 
            patient_name = f"NAME_{int(time.time())}"
            
        modality = meta.get("0008|0060", "")
        if not modality or str(modality).strip() in ["NA", "None", ""]: 
            modality = "CT"

        # 【核心保护机制】：防弹闭包，专门捕获和清洗底层 C++ SWIG 抛出的 TypeError
        def safe_set_meta(img_slice, key, val):
            if val is None:
                val = ""
            # 去除空终止符和首尾空格
            val_str = str(val).replace('\x00', '').strip()
            
            try:
                # 第一步：直接尝试写入
                img_slice.SetMetaData(key, val_str)
            except TypeError:
                # 出现 TypeError，通常是因为底层 C++ 拒绝接收包含特殊/乱码字符的字符串
                # 第二步：尝试修复国内常见的 GBK 乱码读取问题 (提取原始字节并用GBK重新解码)
                try:
                    gbk_str = val_str.encode('latin-1').decode('gbk')
                    img_slice.SetMetaData(key, gbk_str)
                    return
                except:
                    pass
                
                # 第三步：暴力清洗为合法 UTF-8，丢弃任何会导致 SWIG 崩溃的代理字节
                try:
                    clean_str = val_str.encode('utf-8', errors='ignore').decode('utf-8')
                    img_slice.SetMetaData(key, clean_str)
                    return
                except:
                    pass
                
                # 第四步：终极回退，强制转换为纯 ASCII，丢弃所有中文字符以保证系统稳定不崩溃
                try:
                    ascii_str = val_str.encode('ascii', errors='ignore').decode('ascii')
                    img_slice.SetMetaData(key, ascii_str)
                except:
                    pass # 静默失败，舍弃该标签

        direction = img.GetDirection()
        for i in range(img.GetDepth()):
            image_slice = img[:, :, i]
            
            # 🎯 核心修复 2：为每一张生成的切片分配严格独立且合规的 SOPInstanceUID (0008|0018)
            try:
                from pydicom.uid import generate_uid
                sop_uid = generate_uid()
            except ImportError:
                sop_uid = f"1.2.826.0.1.3680043.2.1125.1.{int(time.time() * 1000000)}.{i}"
            safe_set_meta(image_slice, "0008|0018", sop_uid)
            
            # 🎯 核心修复 3：显式声明为 CT 图像类型，防止严苛的 PACS 因缺失 SOP Class UID 拒收
            safe_set_meta(image_slice, "0008|0016", "1.2.840.10008.5.1.4.1.1.2")
            
            # 🎯 核心修复 4：新生成的序列号强制推后至 1000，使其整齐排列在患者列表的最底部
            safe_set_meta(image_slice, "0020|0011", "1000") 
            
            safe_set_meta(image_slice, "0020|0013", str(i + 1))
            safe_set_meta(image_slice, "0008|0008", "DERIVED\\SECONDARY")
            safe_set_meta(image_slice, "0020|000e", new_series_uid)
            safe_set_meta(image_slice, "0020|000d", study_uid)
            safe_set_meta(image_slice, "0010|0020", patient_id)
            safe_set_meta(image_slice, "0010|0010", patient_name)
            safe_set_meta(image_slice, "0008|0060", modality)
            
            if window_index == 1:
                safe_set_meta(image_slice, "0028|1050", "450")
                safe_set_meta(image_slice, "0028|1051", "1500")
                series_desc = meta.get("0008|103e", "")
                safe_set_meta(image_slice, "0008|103e", str(series_desc) if series_desc else "Aligned_Bone_Series")
            else:
                safe_set_meta(image_slice, "0028|1050", "40")
                safe_set_meta(image_slice, "0028|1051", "80")
                series_desc = meta.get("0008|103e", "")
                safe_set_meta(image_slice, "0008|103e", str(series_desc) if series_desc else "Aligned_Brain_Series")
            
            slice_location = [img.GetOrigin()[j] + direction[6 + j] * img.GetSpacing()[2] * i for j in range(3)]
            safe_set_meta(image_slice, "0020|0032", "\\".join(map(str, slice_location)))
            
            writer.SetFileName(os.path.join(path, f"slice_{i:03d}.dcm"))
            writer.Execute(image_slice)

# ==========================================
# 核心医学图像处理与指标度量算法层
# ==========================================
def get_brain_mask_numpy(arr: np.ndarray, hu_low: float = -20, hu_high: float = 100, min_component_size: int = 500) -> np.ndarray:
    mask = (arr > hu_low) & (arr < hu_high)
    if not mask.any(): return np.zeros_like(arr, dtype=np.float32)
    labeled, num_components = label(mask)
    if num_components == 0: return np.zeros_like(arr, dtype=np.float32)
    component_sizes = ndi_sum(mask, labeled, range(1, num_components + 1))
    largest_component = np.argmax(component_sizes) + 1
    mask = (labeled == largest_component) & (component_sizes[largest_component - 1] >= min_component_size)
    return mask.astype(np.float32)

def extract_euler_angles(R: np.ndarray) -> tuple:
    sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
    if sy >= 1e-6:
        x = np.arctan2(R[2,1], R[2,2]); y = np.arctan2(-R[2,0], sy); z = np.arctan2(R[1,0], R[0,0])
    else:
        x = np.arctan2(-R[1,2], R[1,1]); y = np.arctan2(-R[2,0], sy); z = 0
    return np.abs(np.degrees(x)), np.abs(np.degrees(y)), np.abs(np.degrees(z))

def compute_centroid_shift(sitk_img, mask_arr):
    img_centroid_voxel = center_of_mass(mask_arr)
    if np.isnan(img_centroid_voxel[0]): return np.nan
    spacing_zyx = np.array([sitk_img.GetSpacing()[2], sitk_img.GetSpacing()[1], sitk_img.GetSpacing()[0]])
    center_z, center_y, center_x = (mask_arr.shape[0]-1)/2.0, (mask_arr.shape[1]-1)/2.0, (mask_arr.shape[2]-1)/2.0
    shift = np.array([img_centroid_voxel[0]-center_z, img_centroid_voxel[1]-center_y, img_centroid_voxel[2]-center_x]) * spacing_zyx
    return np.linalg.norm(shift)

def compute_snr(arr: np.ndarray) -> float:
    brain_pixels = arr[(arr >= 20) & (arr <= 50)]  
    if len(brain_pixels) < 100: return np.nan
    noise = np.std(brain_pixels)
    return float(np.mean(brain_pixels) / noise) if noise > 1e-5 else np.nan

def compute_cnr(arr: np.ndarray) -> float:
    brain_pixels = arr[(arr >= 20) & (arr <= 50)]; csf_pixels = arr[(arr >= 0) & (arr <= 15)]     
    if len(brain_pixels) < 100 or len(csf_pixels) < 50: return np.nan
    noise = np.std(brain_pixels)
    return float(np.abs(np.mean(brain_pixels) - np.mean(csf_pixels)) / noise) if noise > 1e-5 else np.nan

def extract_true_angles_fast(img_moving, fixed_template):
    try:
        initial_tx = sitk.CenteredTransformInitializer(fixed_template, img_moving, sitk.VersorRigid3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY)
        R_probe = sitk.ImageRegistrationMethod()
        R_probe.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50); R_probe.SetMetricSamplingStrategy(R_probe.RANDOM)
        R_probe.SetMetricSamplingPercentage(0.05); R_probe.SetInterpolator(sitk.sitkLinear)
        R_probe.SetOptimizerAsRegularStepGradientDescent(learningRate=0.1, minStep=1e-4, numberOfIterations=20) 
        R_probe.SetInitialTransform(initial_tx, inPlace=False)
        final_tx = R_probe.Execute(fixed_template, img_moving)
        origin = np.array(final_tx.TransformPoint((0.0, 0.0, 0.0)))
        R_matrix = np.column_stack((np.array(final_tx.TransformPoint((1.0, 0.0, 0.0)))-origin, np.array(final_tx.TransformPoint((0.0, 1.0, 0.0)))-origin, np.array(final_tx.TransformPoint((0.0, 0.0, 1.0)))-origin))
        return extract_euler_angles(R_matrix)
    except: return np.nan, np.nan, np.nan

def get_precision_mask(image):
    tissue_thresh = sitk.BinaryThreshold(image, -100, 200, 1, 0)
    cc = sitk.ConnectedComponent(tissue_thresh)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(cc)
    if stats.GetLabels():
        max_label = max(stats.GetLabels(), key=lambda l: stats.GetNumberOfPixels(l))
        brain_soft_mask = sitk.BinaryThreshold(cc, max_label, max_label, 1, 0)
        return sitk.BinaryMorphologicalClosing(sitk.BinaryDilate(brain_soft_mask, [12, 12, 3]), [5, 5, 2])
    return sitk.BinaryThreshold(image, -200, 3000, 1, 0)

def evaluate_sitk_image_quality(sitk_img):
    try:
        arr = sitk.GetArrayFromImage(sitk_img)
        mask = get_brain_mask_numpy(arr)
        if mask.sum() < 1000: raise ValueError
        centroid_shift = compute_centroid_shift(sitk_img, mask)
        left_volume = mask[:, :, :arr.shape[2] // 2].sum(); right_volume = mask[:, :, arr.shape[2] // 2:].sum()
        symmetry_index = min(left_volume, right_volume) / max(left_volume, right_volume) if max(left_volume, right_volume) > 0 else 1.0
        snr, cnr = compute_snr(arr), compute_cnr(arr)
        return {"centroid_shift_mm": round(float(centroid_shift), 4), "symmetry_index": round(float(symmetry_index), 4), "snr": round(float(snr), 4) if not np.isnan(snr) else np.nan, "cnr": round(float(cnr), 4) if not np.isnan(cnr) else np.nan}
    except: return {"centroid_shift_mm": np.nan, "symmetry_index": np.nan, "snr": np.nan, "cnr": np.nan}

def apply_brain_window(sitk_img, window_index):
    arr = sitk.GetArrayFromImage(sitk_img)
    wl, ww = (450, 1500) if window_index == 1 else (40, 80)
    return np.clip((arr[arr.shape[0] // 2, :, :] - (wl - ww / 2.0)) / ww * 255, 0, 255).astype(np.uint8)

# ==========================================
# Web App 主界面运行级流式框架
# ==========================================
def main():
    # 扩展侧边栏支持四国语言并发切换
    lang = st.sidebar.selectbox("🌐 Language / 语言 / 言語 / 언어", ["zh", "en", "jp", "ko"])
    d = I18N[lang]
    st.title(d['title'])
    st.markdown("---")
    
    # ==============================
    # 侧边栏：PACS 配置模块
    # ==============================
    st.sidebar.markdown("---")
    st.sidebar.header(d["pacs_title"])
    if not HAS_PACS_LIBS:
        st.sidebar.error("缺少 PACS 组件，请在终端执行:\npip install pydicom pynetdicom")
    else:
        pacs_ip = st.sidebar.text_input("Target IP / 目标 IP", value="127.0.0.1")
        pacs_port = st.sidebar.text_input("Target Port / 目标端口", value="104")
        pacs_remote_aet = st.sidebar.text_input("Remote AET / 目标 AET", value="PACS")
        pacs_local_aet = st.sidebar.text_input("Local AET / 本地 AET", value="Head_Align")
        
        if st.sidebar.button("📡 C-ECHO (测试连接)", width='stretch'):
            try:
                ae = AE(ae_title=pacs_local_aet.encode('utf-8'))
                ae.requested_contexts = VerificationPresentationContexts
                assoc = ae.associate(pacs_ip, int(pacs_port), ae_title=pacs_remote_aet.encode('utf-8'))
                if assoc.is_established:
                    status = assoc.send_c_echo()
                    assoc.release()
                    if status:
                        st.sidebar.success(d['pacs_test_ok'])
                    else:
                        st.sidebar.error(d['pacs_test_err'])
                else:
                    st.sidebar.error(d['pacs_test_err'])
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

    # 核心上传区与参数配置区
    uploaded_files = st.file_uploader(d['input_label'], type=["nii", "gz", "dcm", "zip"], accept_multiple_files=True)
    
    default_template = get_default_template_path()
    if default_template:
        st.success(d['template_auto'])
        uploaded_ref = None
        ref_path = default_template
    else:
        uploaded_ref = st.file_uploader(d['ref_label'], type=["nii", "gz"], accept_multiple_files=False)
        
    col1, col2 = st.columns(2)
    with col1:
        window_choice = st.selectbox(d['window_label'], [d['window_brain'], d['window_bone']])
        window_index = 1 if "1500" in window_choice or "骨" in window_choice else 0
        keep_res = st.checkbox(d['keep_res'], value=True)
    with col2:
        out_format = st.selectbox(d['out_format_label'], ["NIfTI", "DICOM"])
        if out_format != "DICOM":
            st.info(d['pacs_not_dicom'])

    if st.button(d['run_btn'], type="primary", width='stretch'):
        if not uploaded_files:
            st.error(d['err_upload'])
            return
        if not default_template and not uploaded_ref:
            st.error(d['err_template'])
            return
            
        # 清除之前的缓存状态
        st.session_state['dicoms_to_send'] = []
        st.session_state['batch_done'] = False
            
        tmp_dir = tempfile.mkdtemp()
        out_dir = os.path.join(tmp_dir, "output")
        os.makedirs(out_dir, exist_ok=True)
        
        if not default_template:
            ref_path = os.path.join(tmp_dir, "template.nii.gz")
            with open(ref_path, "wb") as f: f.write(uploaded_ref.getbuffer())
            
        samples = process_uploaded_files(uploaded_files, tmp_dir)
        if not samples:
            st.error(d['err_invalid'])
            return
            
        fixed_image = sitk.DICOMOrient(sitk.ReadImage(ref_path, sitk.sitkFloat32), 'LPS')
        fixed_mask = get_precision_mask(fixed_image)
        
        all_eval_data = []
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        # ================= 流式群组处理池 =================
        for idx, sample in enumerate(samples):
            raw_filename = sample['name']
            progress_text.info(f"{d['processing_prefix']} {idx+1}/{len(samples)} {d['processing_mid']} {raw_filename}")
            
            moving, metadata = load_single(sample)
            moving_lps = sitk.DICOMOrient(moving, 'LPS')
            
            before_metrics = evaluate_sitk_image_quality(moving_lps)
            before_preview = apply_brain_window(moving_lps, window_index)
            orig_spacing = moving.GetSpacing()
            
            initial_tx = sitk.CenteredTransformInitializer(fixed_image, moving_lps, sitk.VersorRigid3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY)
            R = sitk.ImageRegistrationMethod()
            R.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50); R.SetMetricFixedMask(fixed_mask); R.SetMetricMovingMask(get_precision_mask(moving_lps))
            R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.15); R.SetInterpolator(sitk.sitkLinear)
            R.SetOptimizerAsRegularStepGradientDescent(learningRate=1.0, minStep=1e-5, numberOfIterations=250)
            R.SetOptimizerScalesFromPhysicalShift(); R.SetShrinkFactorsPerLevel(shrinkFactors=[8, 4, 2]); R.SetSmoothingSigmasPerLevel(smoothingSigmas=[4, 2, 1])
            R.SetInitialTransform(initial_tx, inPlace=False)
            final_tx = R.Execute(fixed_image, moving_lps)
            
            resampler = sitk.ResampleImageFilter()
            if keep_res:
                new_size = [int(sz * sp / nsp) for sz, sp, nsp in zip(fixed_image.GetSize(), fixed_image.GetSpacing(), orig_spacing)]
                resampler.SetOutputSpacing(orig_spacing); resampler.SetSize(new_size); resampler.SetOutputDirection(fixed_image.GetDirection()); resampler.SetOutputOrigin(fixed_image.GetOrigin())
            else: resampler.SetReferenceImage(fixed_image)
            resampler.SetTransform(final_tx); resampler.SetDefaultPixelValue(-1024); resampler.SetInterpolator(sitk.sitkLinear)
            aligned = resampler.Execute(moving_lps)
            
            after_preview = apply_brain_window(aligned, window_index)
            after_metrics = evaluate_sitk_image_quality(aligned)
            
            origin = np.array(final_tx.TransformPoint((0.0, 0.0, 0.0)))
            R_matrix = np.column_stack((np.array(final_tx.TransformPoint((1.0, 0.0, 0.0)))-origin, np.array(final_tx.TransformPoint((0.0, 1.0, 0.0)))-origin, np.array(final_tx.TransformPoint((0.0, 0.0, 1.0)))-origin))
            sag_b, cor_b, tra_b = extract_euler_angles(R_matrix)
            sag_a, cor_a, tra_a = extract_true_angles_fast(aligned, fixed_image)
            
            def normalize_tilt(angle):
                if np.isnan(angle): return np.nan
                a = angle % 90
                return a if a <= 45 else 90 - a
                
            before_metrics.update({"angle_cor": round(normalize_tilt(cor_b), 4), "angle_sag": round(normalize_tilt(sag_b), 4), "angle_tra": round(normalize_tilt(tra_b), 4)})
            after_metrics.update({"angle_cor": round(normalize_tilt(cor_a), 4), "angle_sag": round(normalize_tilt(sag_a), 4), "angle_tra": round(normalize_tilt(tra_a), 4)})

            # 导出内生级联对齐文件
            out_name = f"aligned_{raw_filename}"
            save_path = os.path.join(out_dir, out_name)
            save_single(aligned, save_path, metadata, out_format, window_index)

            # 收集用于 PACS 推送的 DICOM 切片路径
            if out_format == "DICOM":
                dcm_files = [os.path.join(save_path, f) for f in os.listdir(save_path) if f.endswith('.dcm')]
                st.session_state['dicoms_to_send'].extend(dcm_files)

            # 绘制海报对比 JPEG (解决可执行环境字体隔离)
            if before_preview.shape != after_preview.shape:
                z_factors = [after_preview.shape[0]/before_preview.shape[0], after_preview.shape[1]/before_preview.shape[1]]
                before_preview_resized = zoom(before_preview, z_factors, order=1).astype(np.uint8)
            else: before_preview_resized = before_preview
            
            combined_preview = np.hstack((before_preview_resized, after_preview))
            pil_base = Image.fromarray(combined_preview).convert("RGB").resize((1024, int(1024 * combined_preview.shape[0] / combined_preview.shape[1])))
            poster = Image.new("RGB", (pil_base.width, pil_base.height + 300), "black")
            poster.paste(pil_base, (0, 0))
            draw = ImageDraw.Draw(poster)
            
            try: font_large, font_small = ImageFont.truetype("arial.ttf", 26), ImageFont.truetype("consola.ttf", 22)
            except: font_large = font_small = ImageFont.load_default()
            
            metric_symbols = ["Cor(Roll)", "Sag(Pitch)", "Tra(Yaw)", "Shift", "Symmetry", "SNR", "CNR"]
            keys_order = ["angle_cor", "angle_sag", "angle_tra", "centroid_shift_mm", "symmetry_index", "snr", "cnr"]
            
            draw.text((40, pil_base.height + 20), "Before (Raw Image)", fill=(52, 152, 219), font=font_large)
            draw.text((552, pil_base.height + 20), "After (Aligned)", fill=(52, 152, 219), font=font_large)
            
            y_offset = pil_base.height + 60
            for sym, key in zip(metric_symbols, keys_order):
                val_b, val_a = before_metrics.get(key, np.nan), after_metrics.get(key, np.nan)
                str_b, str_a = f"{float(val_b):.4f}" if not np.isnan(val_b) else "N/A", f"{float(val_a):.4f}" if not np.isnan(val_a) else "N/A"
                draw.text((40, y_offset), f"{sym:<12}: {str_b}", fill=(46, 204, 113), font=font_small)
                draw.text((552, y_offset), f"{sym:<12}: {str_a}", fill=(46, 204, 113), font=font_small)
                y_offset += 30
            poster.save(os.path.join(out_dir, f"{out_name}_preview.jpg"))
            
            # 网页前端渲染同步反馈
            v_col1, v_col2 = st.columns(2)
            with v_col1: st.image(before_preview, caption=f"{d['preview_before']} ({raw_filename})", width='stretch')
            with v_col2: st.image(after_preview, caption=d['preview_after'], width='stretch')
            
            row = {"file_name": raw_filename}
            for k, v in before_metrics.items(): row[f"before_{k}"] = v
            for k, v in after_metrics.items(): row[f"after_{k}"] = v
            all_eval_data.append(row)
            progress_bar.progress((idx + 1) / len(samples))
            
        # ================= 高阶组群假设检验国际化映射 =================
        df_samples = pd.DataFrame(all_eval_data)
        df_samples.to_csv(os.path.join(out_dir, "registration_quality_per_sample.csv"), index=False, encoding="utf-8-sig")
        metrics = ["angle_cor", "angle_sag", "angle_tra", "centroid_shift_mm", "symmetry_index", "snr", "cnr"]
        stats_results = []
        for metric in metrics:
            before_vals, after_vals = df_samples[f"before_{metric}"].dropna().values, df_samples[f"after_{metric}"].dropna().values
            if len(before_vals) < 2: continue
            try: _, p_b = shapiro(before_vals); _, p_a = shapiro(after_vals); is_normal = (p_b > 0.05) and (p_a > 0.05)
            except: is_normal = False
            try:
                if is_normal:
                    stat, p_val = ttest_rel(before_vals, after_vals)
                    test_type, b_desc, a_desc = d['test_t'], f"{np.mean(before_vals):.2f}±{np.std(before_vals):.2f}", f"{np.mean(after_vals):.2f}±{np.std(after_vals):.2f}"
                else:
                    w_stat, p_val = wilcoxon(before_vals, after_vals)
                    n = len(before_vals); mu = n * (n + 1) / 4.0; sigma = np.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
                    stat, test_type = np.abs((w_stat - mu) / sigma), d['test_w']
                    b_desc, a_desc = f"{np.median(before_vals):.2f} [{np.percentile(before_vals,25):.2f}, {np.percentile(before_vals,75):.2f}]", f"{np.median(after_vals):.2f} [{np.percentile(after_vals,25):.2f}, {np.percentile(after_vals,75):.2f}]"
            except: continue
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
            imp = np.mean((after_vals - before_vals)/(before_vals+1e-6))*100 if metric in ["symmetry_index","snr","cnr"] else np.mean((before_vals - after_vals)/(before_vals+1e-6))*100
            
            stats_results.append({
                d['col_metric']: metric.upper(), d['col_before']: b_desc, d['col_after']: a_desc,
                d['col_method']: test_type, d['col_stat']: round(stat,4), d['col_p']: round(p_val,6),
                d['col_sig']: sig, d['col_imp']: round(imp,2)
            })
            
        df_stats = pd.DataFrame(stats_results)
        df_stats.to_csv(os.path.join(out_dir, "registration_quality_statistics.csv"), index=False, encoding="utf-8-sig")
        
        # 绘图保护
        try:
            plt.rcParams["font.sans-serif"] = ["Arial", "sans-serif"]; plt.rcParams["axes.unicode_minus"] = False
            fig, axes = plt.subplots(3, 3, figsize=(18, 18)); axes = axes.flatten()
            for idx, m in enumerate(metrics):
                sns.boxplot(data=[df_samples[f"before_{m}"].dropna(), df_samples[f"after_{m}"].dropna()], ax=axes[idx], palette="muted", width=0.4)
                axes[idx].set_title(f"{m.replace('_', ' ').upper()} Comparison", fontsize=12); axes[idx].set_xticklabels(["Before", "After"]); axes[idx].grid(alpha=0.3)
            sig_data = df_samples[[f"before_{m}" for m in metrics] + [f"after_{m}" for m in metrics]].dropna()
            imp_rate = {m: (sig_data[f"after_{m}"] > sig_data[f"before_{m}"]).mean() * 100 if m in ["symmetry_index","snr","cnr"] else (sig_data[f"after_{m}"] < sig_data[f"before_{m}"]).mean() * 100 for m in metrics}
            axes[len(metrics)].bar(imp_rate.keys(), imp_rate.values(), color="darkgreen", alpha=0.7)
            axes[len(metrics)].set_title("Success Rate per Metric (%)", fontsize=12); axes[len(metrics)].tick_params(axis='x', rotation=30); axes[len(metrics)].grid(alpha=0.3)
            fig.delaxes(axes[-1]); plt.tight_layout()
            plt.savefig(os.path.join(out_dir, "registration_quality_visualization.png"), dpi=300, bbox_inches="tight")
            plt.close()
        except: pass
        
        progress_text.success(d['success'])
        archive_path = os.path.join(tmp_dir, "HeadAligner_Research_Suite")
        shutil.make_archive(archive_path, 'zip', out_dir)
        
        # 将分析表格结果与ZIP路径固化进 session_state，防止按钮点击时消失
        st.session_state['df_stats'] = df_stats
        st.session_state['archive_path'] = archive_path
        st.session_state['batch_done'] = True

    # ==============================
    # 动态渲染持久化的输出与组件
    # ==============================
    if st.session_state.get('batch_done'):
        with open(f"{st.session_state['archive_path']}.zip", "rb") as f:
            st.download_button(label=d['download_btn'], data=f, file_name="HeadAligner_Research_Suite.zip", mime="application/zip", width='stretch')
            
        st.markdown(f"### {d['metrics_title']}")
        st.dataframe(st.session_state['df_stats'], width='stretch')

    # ==============================
    # PACS 上传触发逻辑 (仅对 DICOM 结果有效)
    # ==============================
    if HAS_PACS_LIBS and st.session_state.get('dicoms_to_send'):
        st.write("---")
        st.subheader(d['pacs_send_btn'])
        if st.button(d['pacs_send_btn'], type="primary", width='stretch'):
            try:
                ae = AE(ae_title=pacs_local_aet.encode('utf-8'))
                
                # ==========================================================
                # 🎯 核心修复：精准动态收集要发送的 SOP Class 和 Transfer Syntax
                # 彻底抛弃庞大的 StoragePresentationContexts，突破 128 限制
                # ==========================================================
                contexts_dict = {}
                for dcm_path in st.session_state['dicoms_to_send']:
                    ds_test = pydicom.dcmread(dcm_path, stop_before_pixels=True)
                    sop = ds_test.SOPClassUID
                    tx = ds_test.file_meta.TransferSyntaxUID if hasattr(ds_test, 'file_meta') else pydicom.uid.ImplicitVRLittleEndian
                    
                    if sop not in contexts_dict:
                        contexts_dict[sop] = set()
                    contexts_dict[sop].add(tx)
                    # 💡 增加最基础的显式和隐式语法作为备选，极大提升各种 PACS 的兼容性
                    contexts_dict[sop].add(pydicom.uid.ExplicitVRLittleEndian)
                    contexts_dict[sop].add(pydicom.uid.ImplicitVRLittleEndian)

                custom_contexts = []
                for sop_class, tx_list in contexts_dict.items():
                    custom_contexts.append(build_context(sop_class, transfer_syntax=list(tx_list)))
                
                # 仅发送实际需要的 contexts，彻底避免 128 报错
                ae.requested_contexts = custom_contexts
                
                assoc = ae.associate(pacs_ip, int(pacs_port), ae_title=pacs_remote_aet.encode('utf-8'))

                if assoc.is_established:
                    sent_count = 0
                    total_dcm = len(st.session_state['dicoms_to_send'])
                    progress_pacs = st.progress(0)
                    
                    for i, dcm_path in enumerate(st.session_state['dicoms_to_send']):
                        ds = pydicom.dcmread(dcm_path)
                        status = assoc.send_c_store(ds)
                        # 0x0000(Success), 0xB000, 0xB006, 0xB007(Warnings 算作成功接收)
                        if status and status.Status in [0x0000, 0xB000, 0xB006, 0xB007]:
                            sent_count += 1
                        progress_pacs.progress((i + 1) / total_dcm)
                        
                    assoc.release()
                    
                    if sent_count == total_dcm:
                        st.success(f"{d['pacs_ok']} ({sent_count}/{total_dcm})")
                    else:
                        st.warning(f"⚠️ 传输结束，但仅有 {sent_count}/{total_dcm} 个文件被 PACS 接受。")
                else:
                    st.error(d['pacs_err'])
            except Exception as e:
                st.error(f"❌ PACS传输发生系统异常: {e}")

if __name__ == "__main__":
    main()