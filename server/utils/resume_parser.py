import pdfplumber
from docx import Document
import os

def parse_resume(file_path):
    """
    解析简历文件
    file_path: 文件路径
    返回: 解析后的文本内容
    """
    try:
        # 根据文件扩展名选择解析方法
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return parse_pdf(file_path)
        elif ext == '.docx':
            return parse_docx(file_path)
        elif ext == '.txt':
            return parse_txt(file_path)
        else:
            raise Exception(f"不支持的文件格式: {ext}")
    except Exception as e:
        print(f"解析简历失败: {str(e)}")
        return ""

def parse_pdf(file_path):
    """
    解析PDF格式简历
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"解析PDF失败: {str(e)}")
    return text

def parse_docx(file_path):
    """
    解析DOCX格式简历
    """
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"解析DOCX失败: {str(e)}")
    return text

def parse_txt(file_path):
    """
    解析TXT格式简历
    """
    text = ""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception as e:
        print(f"解析TXT失败: {str(e)}")
    return text

def extract_resume_info(resume_text):
    """
    从简历文本中提取关键信息
    """
    import re
    
    info = {
        "name": "",
        "experience": "",
        "education": "",
        "skills": [],
        "contact": "",
        "email": ""
    }
    
    if not resume_text:
        return info
    
    # 提取姓名（通常在前几行）
    lines = resume_text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) <= 10 and not any(c.isdigit() for c in line):
            if not any(kw in line for kw in ['电话', '邮箱', '地址', '大学', '学院', '公司', '经验']):
                info["name"] = line
                break
    
    # 提取手机号
    phone_match = re.search(r'1[3-9]\d{9}', resume_text)
    if phone_match:
        info["contact"] = phone_match.group()
    
    # 提取邮箱
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
    if email_match:
        info["email"] = email_match.group()
    
    # 提取学历
    edu_keywords = ['博士', '硕士', '本科', '大专', '本科', '研究生', 'MBA', '学士']
    for kw in edu_keywords:
        if kw in resume_text:
            info["education"] = kw
            break
    
    # 提取工作年限
    exp_match = re.search(r'(\d+)\s*年.*经验|工作.*(\d+)\s*年', resume_text)
    if exp_match:
        years = exp_match.group(1) or exp_match.group(2)
        info["experience"] = f"{years}年"
    
    # 提取技能关键词
    skill_keywords = ['Python', 'Java', 'JavaScript', 'React', 'Vue', 'Node', 'SQL', 'MySQL', 
                      'MongoDB', 'Redis', 'Docker', 'Kubernetes', 'AWS', 'Git', 'Linux',
                      '机器学习', '深度学习', '数据分析', '项目管理', '产品', '运营',
                      'Excel', 'PPT', 'Photoshop', 'Figma', 'UI', 'UX']
    found_skills = []
    for skill in skill_keywords:
        if skill.lower() in resume_text.lower():
            found_skills.append(skill)
    info["skills"] = found_skills[:10]  # 最多10个技能
    
    return info