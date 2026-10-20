# HeadAligner Web Pro v2.0 🧠

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Cranial CT Registration & Quality Evaluation Software V2.0 (Streamlit Cloud + PACS Edition).

## Overview
HeadAligner Web Pro is a fully automated toolkit designed for cranial CT spatial alignment and image quality control (QC). It retains a 100% physically accurate core for precise registration while offering a modern, accessible web interface. 

This tool is highly suited for multicenter clinical research, offering fully automated robust registration, internal homogeneity tracking (SNR/CNR), absolute physical center computation, and rigid projection angle extraction.

## Features ✨
- **Multilingual Support**: Fully localized in English, Chinese (Simplified), Japanese, and Korean.
- **Smart Data Parsing**: Drag-and-drop support for NIfTI (`.nii`, `.nii.gz`), loose DICOM slices, and `.zip` archives containing complex DICOM hierarchies.
- **Auto-Template Mounting**: Automatically mounts default standard brain geometric templates for zero-click referencing.
- **Automated QA Metrics**: Calculates Centroid Shift, Symmetry Index, SNR, CNR, and 3D Euler Angles (Coronal, Sagittal, Transverse).
- **Batch Processing & Statistical Analysis**: Runs batch alignment and auto-generates multi-center statistical QA summaries (Shapiro-Wilk, Paired t-test, Wilcoxon signed-rank test).
- **PACS Integration**: One-click C-ECHO testing and C-STORE archiving of generated DICOMs directly to hospital PACS nodes.
- **Publication-Ready Export**: Downloads a comprehensive `.zip` containing aligned NIfTI/DICOM files, statistical `.csv` reports, and high-res visualization `.jpg` posters.

## Template & Acknowledgements 📐
This software utilizes the high-resolution unbiased CT brain template from [muschellij2/high_res_ct_template](https://github.com/muschellij2/high_res_ct_template). If you use this software or its embedded template in your academic research, please cite the template publication:

> Muschelli, John. “A Publicly Available, High Resolution, Unbiased CT Brain Template.” International Conference on Information Processing and Management of Uncertainty in Knowledge-Based Systems. Springer, Cham, 2020. 
> DOI: [10.1007/978-3-030-50153-2_27](https://doi.org/10.1007/978-3-030-50153-2_27)

## Deployment on Streamlit Cloud ☁️

1. Fork or clone this repository to your GitHub account.
2. Ensure `web_app.py`, `requirements.txt`, and the `template/` folder are in the root directory.
3. Log in to [Streamlit Community Cloud](https://share.streamlit.io/).
4. Click **New app** and select your repository, branch, and set the main file path to `web_app.py`.
5. Click **Deploy!**

## Local Installation 💻

To run the application locally:

```bash
# Clone the repository
git clone [https://github.com/yourusername/HeadAligner.git](https://github.com/yourusername/HeadAligner.git)
cd HeadAligner

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run web_app.py

```

## Developer & Contact 📬

Developed by radiology technologist at **Nanjing Medical University Fourth Affiliated Hospital**.
For inquiries, software copyright details, or academic collaboration, please contact: `blasthao@hotmail.com`.

