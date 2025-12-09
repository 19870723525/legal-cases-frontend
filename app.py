from flask import Flask, render_template, request, jsonify, send_file
from supabase import create_client
import os
from dotenv import load_dotenv
import csv
import io
import logging
from datetime import datetime
import hashlib

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 每页显示的数量
PAGE_SIZE = 10

def get_table_columns():
    """获取数据库表的所有列名，并检查是否有唯一标识符"""
    try:
        result = supabase.table("case1").select("*").limit(1).execute()
        if result.data:
            columns = list(result.data[0].keys())
            logger.info(f"数据库列名: {columns}")
            
            # 检查可能的唯一标识符
            possible_id_columns = ['id', 'ID', 'Id', '案号', '案件编号']
            found_id = None
            for col in possible_id_columns:
                if col in columns:
                    found_id = col
                    logger.info(f"找到可能的唯一标识符字段: {found_id}")
                    break
                    
            if not found_id:
                logger.warning("未找到明确的唯一标识符字段")
            
            return columns, found_id
        return ['案号', '审理法院', '裁判日期'], None
    except Exception as e:
        logger.error(f"获取列名失败: {e}")
        return ['案号', '审理法院', '裁判日期'], None

def get_filter_options():
    """获取筛选选项"""
    try:
        # 案件类型
        case_types = supabase.table("case1").select("案件类型").execute()
        case_type_options = list(set([item['案件类型'] for item in case_types.data if item.get('案件类型')]))
        
        # 申请结果
        result_types = supabase.table("case1").select("申请结果").execute()
        result_type_options = list(set([item['申请结果'] for item in result_types.data if item.get('申请结果')]))
        
        # 国家
        countries = supabase.table("case1").select("判决来源国").execute()
        country_options = list(set([item['判决来源国'] for item in countries.data if item.get('判决来源国')]))
        
        return {
            'case_types': sorted(case_type_options),
            'result_types': sorted(result_type_options),
            'countries': sorted(country_options)
        }
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        return {'case_types': [], 'result_types': [], 'countries': []}

def generate_case_id(row):
    """为案例生成唯一ID（使用案号和其他信息的组合）"""
    try:
        # 使用案号、审理法院、裁判日期生成唯一ID
        case_number = str(row.get('案号', ''))
        court = str(row.get('审理法院', ''))
        date = str(row.get('裁判日期', ''))
        
        # 如果案号不为空，直接用案号（进行简单编码）
        if case_number:
            # 创建简单的哈希值
            unique_string = f"{case_number}_{court}_{date}"
            return hashlib.md5(unique_string.encode()).hexdigest()[:10]
        else:
            # 如果案号为空，用所有信息生成哈希
            all_data = str(row)
            return hashlib.md5(all_data.encode()).hexdigest()[:10]
    except Exception as e:
        logger.error(f"生成案例ID失败: {e}")
        return "unknown"

@app.route("/", methods=["GET"])
def index():
    """首页搜索"""
    try:
        # 获取搜索参数
        anhao = request.args.get("anhao", "").strip()
        fayuan = request.args.get("fayuan", "").strip()
        date_start = request.args.get("date_start", "")
        date_end = request.args.get("date_end", "")
        case_type = request.args.get("case_type", "")
        result_type = request.args.get("result_type", "")
        country = request.args.get("country", "")
        page = int(request.args.get("page", 1))
        
        # 构建查询
        query = supabase.table("case1").select("*")
        
        # 添加筛选条件
        if anhao:
            query = query.ilike("案号", f"%{anhao}%")
        if fayuan:
            query = query.ilike("审理法院", f"%{fayuan}%")
        if case_type:
            query = query.eq("案件类型", case_type)
        if result_type:
            query = query.eq("申请结果", result_type)
        if country:
            query = query.ilike("判决来源国", f"%{country}%")
        if date_start:
            query = query.gte("裁判日期", f"{date_start}T00:00:00+08:00")
        if date_end:
            query = query.lte("裁判日期", f"{date_end}T23:59:59+08:00")
            
        # 排序和分页
        query = query.order("裁判日期", desc=True)
        from_index = (page - 1) * PAGE_SIZE
        to_index = from_index + PAGE_SIZE - 1
        query = query.range(from_index, to_index)
        
        # 执行查询
        result = query.execute()
        rows = result.data or []
        
        # 为每行数据生成唯一ID
        for row in rows:
            row['_generated_id'] = generate_case_id(row)
            logger.info(f"案号: {row.get('案号')}, 生成的ID: {row['_generated_id']}")
        
        # 检查第一行数据的字段
        if rows:
            logger.info(f"第一行数据的字段: {list(rows[0].keys())}")
            logger.info(f"第一行数据内容: {rows[0]}")
        
        has_next_page = len(rows) == PAGE_SIZE
        
        # 获取筛选选项
        filter_options = get_filter_options()
        
        # 首页只显示三列
        display_columns = ['案号', '审理法院', '裁判日期']
        
        return render_template(
            "index.html",
            rows=rows,
            page=page,
            has_next_page=has_next_page,
            anhao=anhao,
            fayuan=fayuan,
            date_start=date_start,
            date_end=date_end,
            case_type=case_type,
            result_type=result_type,
            country=country,
            display_columns=display_columns,
            filter_options=filter_options,
            PAGE_SIZE=PAGE_SIZE
        )
        
    except Exception as e:
        logger.error(f"搜索错误: {e}")
        return render_template(
            "index.html",
            rows=[],
            page=1,
            has_next_page=False,
            errors=[f"搜索过程中发生错误: {str(e)}"],
            display_columns=['案号', '审理法院', '裁判日期'],
            filter_options=get_filter_options(),
            PAGE_SIZE=PAGE_SIZE
        )

@app.route("/case/<case_id>")
def case_detail(case_id):
    """案例详情页面"""
    try:
        # 获取搜索参数（用于返回按钮）
        search_params = {
            'anhao': request.args.get("anhao", ""),
            'fayuan': request.args.get("fayuan", ""),
            'date_start': request.args.get("date_start", ""),
            'date_end': request.args.get("date_end", ""),
            'case_type': request.args.get("case_type", ""),
            'result_type': request.args.get("result_type", ""),
            'country': request.args.get("country", ""),
            'page': request.args.get("page", "1")
        }
        
        logger.info(f"请求案例详情，ID: {case_id}")
        
        # 由于没有真正的ID字段，我们需要查找所有记录
        # 获取所有案例（或者根据案号查找）
        result = supabase.table("case1").select("*").execute()
        
        # 查找匹配的案例
        found_case = None
        for case in result.data or []:
            # 生成这个案例的ID进行比较
            generated_id = generate_case_id(case)
            if generated_id == case_id:
                found_case = case
                break
        
        if not found_case:
            logger.warning(f"案例不存在: {case_id}")
            return render_template("error.html", error="案例不存在"), 404
            
        # 获取所有列
        columns, _ = get_table_columns()
        
        logger.info(f"成功获取案例: {found_case.get('案号', '未知案号')}")
        
        return render_template(
            "case_detail.html",
            case=found_case,
            all_columns=columns,
            search_params=search_params
        )
        
    except Exception as e:
        logger.error(f"获取案例详情错误: {e}")
        return render_template("error.html", error="获取案例详情失败"), 500

@app.route("/export")
def export_cases():
    """导出CSV"""
    try:
        # 获取搜索参数
        anhao = request.args.get("anhao", "").strip()
        fayuan = request.args.get("fayuan", "").strip()
        date_start = request.args.get("date_start", "")
        date_end = request.args.get("date_end", "")
        case_type = request.args.get("case_type", "")
        result_type = request.args.get("result_type", "")
        country = request.args.get("country", "")
        
        # 构建查询
        query = supabase.table("case1").select("*")
        
        if anhao:
            query = query.ilike("案号", f"%{anhao}%")
        if fayuan:
            query = query.ilike("审理法院", f"%{fayuan}%")
        if case_type:
            query = query.eq("案件类型", case_type)
        if result_type:
            query = query.eq("申请结果", result_type)
        if country:
            query = query.ilike("判决来源国", f"%{country}%")
        if date_start:
            query = query.gte("裁判日期", f"{date_start}T00:00:00+08:00")
        if date_end:
            query = query.lte("裁判日期", f"{date_end}T23:59:59+08:00")
        
        result = query.execute()
        rows = result.data or []
        
        # 创建CSV
        output = io.StringIO()
        if rows:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        else:
            # 空数据
            columns, _ = get_table_columns()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
        
        output.seek(0)
        filename = f"案例数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"导出错误: {e}")
        return "导出失败", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)