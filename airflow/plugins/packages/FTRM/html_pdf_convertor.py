"""
Author: Chunyu Yan
Date: 2025-07-13
Description: 
    This script converts SEC filing documents from HTML format to PDF format.
    It uses `pdfkit` with `wkhtmltopdf` to perform the conversion.
    HTML files are read from a CIK-specific folder and converted PDFs are saved to a corresponding location.

Dependencies:
    - pdfkit
    - wkhtmltopdf (ensure it's installed and accessible via the specified path)

Usage:
    Call `process_fillings_html_to_pdf(cik, root_folder_html, root_folder_pdf)` 
    with the desired CIK and folder paths.

"""

import pdfkit
import os
import logging
logger = logging.getLogger(__name__)


# Function to convert HTML files to PDF
def html_to_pdf(read_file, save_file):
    path_wkhtmltopdf = '/usr/bin/wkhtmltopdf'  # # Replace with actual path to wkhtmltopdf binary; in docker: which wkhtmltopdf
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    pdfkit.from_file(read_file, save_file, options={'encoding': 'utf-8',"enable-local-file-access":True})

            
# Convert all HTML files for a given CIK from a source folder to PDF and save to target folder
def process_fillings_html_to_pdf(cik, root_folder_html, root_folder_pdf):
    read_folder = os.path.join(root_folder_html, cik)
    save_folder = os.path.join(root_folder_pdf, cik)
    if not os.path.exists(read_folder):
        os.makedirs(read_folder)
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    if read_folder == f'{root_folder_html}/.DS_Store':
        return
    logger.info(f"Processing HTML files for CIK: {cik} from {read_folder} to {save_folder}")
    print(read_folder)
    for file in os.listdir(read_folder):
        read_path = os.path.join(read_folder, file)
        save_path = os.path.join(save_folder, os.path.splitext(file)[0] + '.pdf')
        # Skip if PDF already exists
        if os.path.exists(save_path):
            continue
        if os.path.splitext(read_path)[1] == '.html':
            logger.info(f"Converting {read_path} to {save_path}")
            html_to_pdf(read_path, save_path)